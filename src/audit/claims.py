"""Extract atomic claims with dependencies from the agent's visible messages."""

from __future__ import annotations

from pathlib import Path

from audit.schema import Claim, Transcript


def extract_claims(transcript: Transcript, extractor_model: str, prompt_path: str) -> list[Claim]:
    """Extract every atomic claim the agent made in one transcript.

    Inputs: the Transcript, the extractor model name, the path to
    `prompts/claim_extraction.md`.
    Outputs: one Claim per atomic assertion, with `type`, `depends_on` and
    `verifiable` filled in.
    Invariant: the extractor states what was claimed, never whether it is true.
    Every id in `depends_on` must exist in `transcript.messages`.
    """
    raise NotImplementedError


def is_verifiable(claim_type: str) -> bool:
    """Say whether a ground-truth checker exists for this claim type.

    Inputs: a ClaimType value.
    Outputs: True for every type `verify.py` has a checker for, False for `other`.
    Invariant: agrees with the checkers registered in `verify.py`.
    """
    raise NotImplementedError


def extract_all(transcripts_path: Path, extractor_model: str, prompt_path: str) -> list[Claim]:
    """Stage 02 entrypoint. Extract claims for every transcript in a stage 01 file.

    Inputs: the path to stage 01's `transcripts.jsonl`, the extractor model
    name, the path to `prompts/claim_extraction.md`.
    Outputs: every Claim from every Transcript, in transcript order.
    Invariant: one call to `extract_claims` per Transcript, nothing else.
    """
    raise NotImplementedError
