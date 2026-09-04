"""AUROC, Brier, ECE, bootstrap CIs, per-mutation breakdown. Reads results only."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from audit.schema import Claim, ClaimScore, Transcript


def aggregate_claim_score(scores: list[ClaimScore], claims: list[Claim], how: str) -> float:
    """Reduce one transcript's claim scores to a single number.

    Inputs: the ClaimScores for one transcript, the matching Claims, and the
    aggregation rule, `min` or `mean`.
    Outputs: the aggregate over verifiable claims only.
    Invariant: unverifiable claims are excluded. A transcript with no verifiable
    claims returns NaN rather than a default value.
    """
    raise NotImplementedError


def signature_features(
    transcript: Transcript, claims: list[Claim], scores: list[ClaimScore]
) -> dict:
    """Compute the per-transcript claim signature.

    Inputs: one Transcript with its Claims and ClaimScores.
    Outputs: claim count, fraction unverifiable, fraction with p_true below 0.5,
    fraction with empty depends_on, plus transcript length for the
    length-matched control.
    Invariant: features depend on claims and scores only, never on the label.
    """
    raise NotImplementedError


def auroc(y_true: list[int], y_score: list[float]) -> float:
    """Area under the ROC curve.

    Inputs: binary labels and continuous scores of equal length.
    Outputs: AUROC in [0, 1].
    Invariant: returns NaN when one class is absent, rather than raising.
    """
    raise NotImplementedError


def brier(y_true: list[int], y_prob: list[float]) -> float:
    """Brier score of probabilistic predictions.

    Inputs: binary truth values and predicted probabilities.
    Outputs: the mean squared error of the probabilities, lower is better.
    Invariant: probabilities are used as given, never rescaled.
    """
    raise NotImplementedError


def ece(y_true: list[int], y_prob: list[float], n_bins: int) -> float:
    """Expected calibration error.

    Inputs: binary truth values, predicted probabilities, and the number of
    equal-width bins.
    Outputs: the bin-weighted mean gap between confidence and accuracy.
    Invariant: empty bins contribute nothing.
    """
    raise NotImplementedError


def bootstrap_ci(
    values: list[float], statistic: str, bootstrap_n: int, seed: int
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval.

    Inputs: the sample, the name of the statistic, the number of resamples, and
    the seed.
    Outputs: the 2.5th and 97.5th percentile of the resampled statistic.
    Invariant: the same seed gives the same interval.
    """
    raise NotImplementedError


def per_mutation_breakdown(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Break a metric down by task variant and hack method.

    Inputs: a per-transcript frame carrying variant, hack_method, label and scores.
    Outputs: one row per (variant, hack_method) with the metric and its CI.
    Invariant: groups below the minimum count are reported as such, not silently
    dropped.
    """
    raise NotImplementedError


def analyse(run_dir: Path, metrics: list[str], bootstrap_n: int, figures: list[str]) -> None:
    """Stage 05 entrypoint. Compute every metric and write every figure.

    Inputs: the stage 05 run directory, the metric names, the bootstrap
    resample count, and the figure names.
    Outputs: nothing. Tables and figures are written into `run_dir`.
    Invariant: reads the earlier stages' outputs from `results/` only, and makes
    no model calls.
    """
    raise NotImplementedError
