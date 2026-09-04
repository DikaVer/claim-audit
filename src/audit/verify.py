"""Ground-truth checkers, one per claim type. No model calls happen here."""

from __future__ import annotations

from pathlib import Path

from audit.schema import Claim, ClaimVerdict, Transcript


def check_tests_pass(claim: Claim, transcript: Transcript) -> ClaimVerdict:
    """Verify a `tests_pass` claim against the actual test run.

    Inputs: the Claim and its Transcript.
    Outputs: a ClaimVerdict, true iff the served tests actually passed.
    Invariant: reads the recorded outcome, never a model.
    """
    raise NotImplementedError


def check_tests_unmodified(claim: Claim, transcript: Transcript) -> ClaimVerdict:
    """Verify a `tests_unmodified` claim from a diff of the test files.

    Inputs: the Claim and its Transcript.
    Outputs: a ClaimVerdict, true iff no test file differs from what was served.
    Invariant: the diff is computed from files, never inferred from messages.
    """
    raise NotImplementedError


def check_impl_follows_spec(claim: Claim, transcript: Transcript) -> ClaimVerdict:
    """Verify an `impl_follows_spec` claim by running the original unmutated tests.

    Inputs: the Claim and its Transcript.
    Outputs: a ClaimVerdict, true iff the agent's code passes the original tests.
    Invariant: the original tests are used, not the variant tests the agent saw.
    """
    raise NotImplementedError


def check_test_is_wrong(claim: Claim, transcript: Transcript) -> ClaimVerdict:
    """Verify a `test_is_wrong` claim from the task variant.

    Inputs: the Claim and its Transcript.
    Outputs: a ClaimVerdict, true iff the variant is impossible.
    Invariant: depends only on the variant, so it needs no test run.
    """
    raise NotImplementedError


def verify_claim(claim: Claim, transcript: Transcript, checkers: list[str]) -> ClaimVerdict:
    """Dispatch one claim to the checker for its type.

    Inputs: the Claim, its Transcript, the checker names enabled in the config.
    Outputs: a ClaimVerdict. `is_true` is None when the type has no enabled checker.
    Invariant: `other` claims always come back unverified.
    """
    raise NotImplementedError


def verify_all(
    transcripts_path: Path, claims_path: Path, checkers: list[str]
) -> list[ClaimVerdict]:
    """Stage 04 entrypoint. Verify every claim against ground truth.

    Inputs: the stage 01 transcripts file, the stage 02 claims file, and the
    checker names enabled in the config.
    Outputs: one ClaimVerdict per Claim.
    Invariant: no model is called anywhere in this module.
    """
    raise NotImplementedError
