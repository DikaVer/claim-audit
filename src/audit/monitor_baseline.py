"""Whole-transcript baseline monitor: one prompt, one score."""

from __future__ import annotations

from pathlib import Path

from audit.schema import Transcript


def score_transcript(transcript: Transcript, monitor_model: str, prompt_path: str) -> float:
    """Score whether the agent cheated, from the whole transcript at once.

    Inputs: the Transcript, the monitor model name, the path to
    `prompts/baseline_monitor.md`.
    Outputs: P(cheated) in [0, 1].
    Invariant: the monitor sees the same information as the estimator's `full`
    mode, so any AUROC gap is about the claim format and not about the model or
    the evidence available. Outcomes are stripped here too.
    """
    raise NotImplementedError


def score_all(transcripts_path: Path, monitor_model: str, prompt_path: str) -> dict[str, float]:
    """Baseline entrypoint. Score every transcript in a stage 01 file.

    Inputs: the stage 01 transcripts file, the monitor model name, the path to
    `prompts/baseline_monitor.md`.
    Outputs: a mapping from transcript_id to P(cheated).
    Invariant: one call to `score_transcript` per Transcript, nothing else.
    """
    raise NotImplementedError
