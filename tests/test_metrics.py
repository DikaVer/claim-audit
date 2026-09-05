"""Stage 05: the pure metric functions, no results files needed."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from audit import metrics
from audit.schema import Claim, ClaimScore, Transcript


def _claim(i, type_, verifiable=True, negated=False, deps=("m1",)):
    return Claim(claim_id=f"t-c{i}", transcript_id="t", text="x", type=type_, depends_on=list(deps), verifiable=verifiable, negated=negated)


def _score(i, p):
    return ClaimScore(claim_id=f"t-c{i}", context_mode="full", estimator_model="m", p_true=p, justification="j")


def test_aggregate_excludes_unverifiable_and_nan_when_none():
    claims = [_claim(0, "tests_pass"), _claim(1, "other", verifiable=False)]
    scores = [_score(0, 0.2), _score(1, 0.9)]
    assert metrics.aggregate_claim_score(scores, claims, "min") == 0.2
    assert metrics.aggregate_claim_score(scores, claims, "mean") == 0.2
    assert math.isnan(metrics.aggregate_claim_score([_score(1, 0.9)], [claims[1]], "min"))


def test_signature_features_never_read_the_label():
    t = Transcript(transcript_id="t", task_id="t", variant="oneoff", sample_index=0,
                   messages=[{"id": "m0", "role": "user", "content": "abc"}], reasoning=[{"message_id": "m0", "text": "xy"}],
                   final_report="r", tests_passed=True, in_loop_success=True, label="hack", n_messages=1, n_chars=3)
    claims = [_claim(0, "test_is_wrong"), _claim(1, "other", verifiable=False, deps=())]
    f = metrics.signature_features(t, claims, [_score(0, 0.3), _score(1, 0.9)])
    assert f["n_claims"] == 2 and f["frac_unverifiable"] == 0.5 and f["frac_below_half"] == 0.5
    assert f["frac_empty_depends_on"] == 0.5 and f["has_test_is_wrong"] == 1.0 and f["reasoning_chars"] == 2
    assert "label" not in f


def test_auroc_brier_ece():
    assert metrics.auroc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]) == 0.75
    assert math.isnan(metrics.auroc([1, 1], [0.1, 0.2]))
    assert metrics.brier([1, 0], [1.0, 0.0]) == 0.0 and metrics.brier([1, 0], [0.0, 1.0]) == 1.0
    assert metrics.ece([1, 1, 0, 0], [0.9, 0.9, 0.1, 0.1], 10) == pytest.approx(0.1)
    assert metrics.ece([], [], 10) != metrics.ece([], [], 10), "NaN on empty"


def test_bootstrap_is_seeded_and_brackets_the_mean():
    v = [0.0, 1.0] * 20
    a = metrics.bootstrap_ci(v, "mean", 200, 1)
    assert a == metrics.bootstrap_ci(v, "mean", 200, 1) and a[0] < 0.5 < a[1]
    pairs = [(0, 0.1), (0, 0.3), (1, 0.6), (1, 0.9)] * 5
    lo, hi = metrics.bootstrap_ci(pairs, "auroc", 100, 0)
    assert lo <= 1.0 <= hi


def test_per_mutation_reports_small_groups():
    df = pd.DataFrame({"variant": ["oneoff"] * 3, "hack_method": ["unknown"] * 3, "label": ["hack", "hack", "honest_under_conflict"], "x": [0.1, 0.2, 0.9]})
    out = metrics.per_mutation_breakdown(df, "x")
    assert len(out) == 1 and out.iloc[0]["note"] == "too few or one class"
