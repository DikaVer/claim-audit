"""Score P(true) per claim. The estimator never sees outcomes."""

from __future__ import annotations

from pathlib import Path

from audit.schema import Claim, ClaimScore, ContextMode, Transcript


def build_context(transcript: Transcript, context_mode: ContextMode) -> str:
    """Render the transcript as the estimator is allowed to see it.

    Inputs: the Transcript and the context mode.
    Outputs: `full` gives the whole transcript minus outcomes, `no_test_diff`
    additionally hides every change to test files, `no_transcript` gives nothing
    so the estimator returns its prior.
    Invariant: test results and the final pass/fail are stripped from every
    mode, without exception. `Transcript.tests_passed` and `Transcript.label`
    must never reach the returned string.
    """
    raise NotImplementedError


def score_claim(
    claim: Claim,
    transcript: Transcript,
    context_mode: ContextMode,
    estimator_model: str,
    prompt_path: str,
) -> ClaimScore:
    """Return the estimator's probability that one claim is true.

    Inputs: the Claim, its Transcript, the context mode, the estimator model
    name, the path to `prompts/estimator.md`.
    Outputs: a ClaimScore with `p_true` in [0, 1] and a one-sentence justification.
    Invariant: the estimator is consequence-invariant. It sees only what
    `build_context` returns, so test results and the final pass/fail are
    stripped from every context mode.
    """
    raise NotImplementedError


def score_all(
    transcripts_path: Path,
    claims_path: Path,
    context_modes: list[ContextMode],
    estimator_model: str,
    prompt_path: str,
) -> list[ClaimScore]:
    """Stage 03 entrypoint. Score every claim in every requested context mode.

    Inputs: the stage 01 transcripts file, the stage 02 claims file, the context
    modes to run, the estimator model name, the path to `prompts/estimator.md`.
    Outputs: one ClaimScore per (claim, context mode) pair.
    Invariant: every score goes through `build_context`, so test results and the
    final pass/fail are stripped in every mode.
    """
    raise NotImplementedError
