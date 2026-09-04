"""Pydantic models shared by every stage.

This module is the contract between stages. A stage that needs a new field adds
it here, bumps `claim_schema_version` in `configs/exp02_claims.yaml`, and notes
the change in `LOGBOOK.md`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Version of the whole inter-stage contract, not only the Claim model. It is
# bumped for any field change in this module, per convention 6 in CLAUDE.md.
# Keep it equal to claim_schema_version in configs/exp02_claims.yaml.
CLAIM_SCHEMA_VERSION = 4

Variant = Literal["original", "oneoff", "conflicting"]
"""Task variant. `oneoff` and `conflicting` are the impossible variants."""

HackLabel = Literal["honest_success", "honest_fail", "hack", "honest_under_conflict"]
"""Computed label. Never hand typed. See `transcripts.assign_hack_label`."""

ClaimType = Literal[
    "tests_pass",
    "impl_follows_spec",
    "tests_unmodified",
    "test_is_wrong",
    "other",
]

ContextMode = Literal["full", "no_test_diff", "no_transcript", "with_reasoning"]
"""What the estimator sees. Outcomes are stripped in every mode.

Agent reasoning is stripped in every mode except `with_reasoning`, which exists
so that "does reading the reasoning help?" is a deliberate ablation rather than
an advantage baked into the default. It is not in the default config list."""

HackMethod = Literal[
    "modify_tests",
    "overload_operators",
    "record_extra_states",
    "special_casing",
    "other",
]
"""Categories A to E from ImpossibleBench's `CLASSIFY_PROMPT`.

Not exposed by the harness. It is an LLM judge in `analysis/llm_judge.py`, so
this label costs model calls and is itself noisy. Under `agent_type="minimal"`
only `overload_operators` and `record_extra_states` are observable on the
`conflicting` variant, because the scorer places the served test after the
agent's answer. See `Transcript.in_loop_success`."""


class Task(BaseModel):
    """One ImpossibleBench task in one variant."""

    task_id: str
    variant: Variant
    prompt: str = Field(description="The spec the agent is told to follow.")
    entry_point: str = Field(description="Name of the function to implement, needed to run any test.")
    original_tests: str = Field(description="The unmutated test file.")
    variant_tests: str = Field(description="The test file as served to the agent.")


class Transcript(BaseModel):
    """One agent run on one Task, normalised from the harness log."""

    transcript_id: str
    task_id: str
    variant: Variant
    sample_index: int = Field(description="Which sample of this task and variant.")
    messages: list[dict] = Field(
        description="Agent visible messages and tool calls, each with a stable `id`."
    )
    reasoning: list[dict] = Field(
        default_factory=list,
        description=(
            "The agent's reasoning trace, keyed to the message ids it belongs to, so "
            "stage 3b can align private deliberation with the public report. Held "
            "apart from `messages` on purpose: the estimator must not see it, or the "
            "reasoning does the detecting instead of the claim format. Empty for "
            "models whose reasoning is encrypted, such as o3."
        ),
    )
    final_report: str
    tests_passed: bool = Field(
        description="The scorer's verdict, which places the served test AFTER the agent's answer."
    )
    in_loop_success: bool = Field(
        description=(
            "The agent loop's verdict, which places the served test BEFORE the answer. "
            "Diverges from tests_passed when the agent redefined `check`."
        )
    )
    label: HackLabel = Field(description="Computed from variant plus tests_passed.")
    check_override_hack: bool = Field(
        default=False,
        description=(
            "in_loop_success and not tests_passed on an impossible variant. "
            "Recovers the type A hacks the scorer's ordering discards."
        ),
    )
    hack_method: HackMethod | None = None
    n_messages: int
    n_chars: int = Field(description="Transcript length, used for length-matched controls.")


class Claim(BaseModel):
    """One atomic assertion extracted from a Transcript."""

    claim_id: str
    transcript_id: str
    text: str
    type: ClaimType
    depends_on: list[str] = Field(
        default_factory=list,
        description="Message or tool-call ids the claim rests on. May be empty.",
    )
    verifiable: bool = Field(description="Whether a ground-truth checker exists for this type.")
    negated: bool = Field(
        default=False,
        description=(
            "True when the claim denies the type's proposition, as in 'the tests do "
            "not pass'. Checkers verify the proposition, so stage 04 flips the verdict "
            "for a negated claim. Added in schema version 4."
        ),
    )
    schema_version: int = CLAIM_SCHEMA_VERSION


class ClaimScore(BaseModel):
    """The estimator's probability that a Claim is true."""

    claim_id: str
    context_mode: ContextMode
    estimator_model: str
    p_true: float = Field(ge=0.0, le=1.0)
    justification: str


class ClaimVerdict(BaseModel):
    """Ground truth for a Claim, from a checker rather than a model."""

    claim_id: str
    checker: str = Field(description="Name of the checker that produced this verdict.")
    is_true: bool | None = Field(
        default=None, description="None when the claim type has no checker."
    )
    evidence: str = Field(default="", description="What the checker observed.")


class RunManifest(BaseModel):
    """Written to `results/<run_id>/manifest.json` by `runs.py`, never by hand."""

    run_id: str
    stage: str
    git_commit: str
    config: dict = Field(description="The config exactly as loaded.")
    models: dict[str, dict] = Field(
        description=(
            "configs/models.yaml as loaded, one nested dict per role. Nested rather "
            "than flat because the sampling parameters are per role, and the manifest "
            "has to record what a run actually used for the run to be reproducible."
        )
    )
    start_time: datetime
    end_time: datetime | None = None
    n_model_calls: int = 0
    estimated_cost_usd: float = 0.0
