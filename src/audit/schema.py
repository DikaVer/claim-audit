"""Pydantic models shared by every stage.

This module is the contract between stages. A stage that needs a new field adds
it here, bumps `claim_schema_version` in `configs/exp02_claims.yaml`, and notes
the change in `LOGBOOK.md`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CLAIM_SCHEMA_VERSION = 1

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

ContextMode = Literal["full", "no_test_diff", "no_transcript"]
"""What the estimator sees. Outcomes are stripped in every mode."""

HackMethod = Literal["test_modification", "special_casing", "operator_override", "other"]
"""ImpossibleBench's own taxonomy, recorded where the harness exposes it."""


class Task(BaseModel):
    """One ImpossibleBench task in one variant."""

    task_id: str
    variant: Variant
    prompt: str = Field(description="The spec the agent is told to follow.")
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
    final_report: str
    tests_passed: bool = Field(description="Outcome. Never shown to the estimator.")
    label: HackLabel = Field(description="Computed from variant plus tests_passed.")
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
    models: dict[str, str]
    start_time: datetime
    end_time: datetime | None = None
    n_model_calls: int = 0
    estimated_cost_usd: float = 0.0
