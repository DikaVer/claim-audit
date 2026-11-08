"""Stage 04: verify claims against ground truth. No model calls happen in this stage.

Reads `transcripts.jsonl` and `tasks.jsonl` from a stage 01 run and
`claims.jsonl` from a stage 02 run. Runs every transcript's final code against
the original tests in Docker once, writes that as `original_runs.jsonl`, then
writes one verdict per claim to `verdicts.jsonl` plus `summary.json`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import islice
from pathlib import Path

from audit import runs, verify

STAGE = "04_verify"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--transcripts-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    parser.add_argument("--claims-run", default=None, help="Stage 02 run_id. Defaults to the latest.")
    parser.add_argument("--limit", type=int, default=None, help="First N transcripts only. Recorded in the manifest.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    transcripts_run = args.transcripts_run or runs.latest_run("01_generate")
    claims_run = args.claims_run or runs.latest_run("02_claims")
    config["transcripts_run"] = transcripts_run
    config["claims_run"] = claims_run
    if args.limit is not None:
        config["overrides"] = {"limit": args.limit}

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)
    print(f"run {run_id}, transcripts {transcripts_run}, claims {claims_run}")

    transcripts_path = runs.results_path(transcripts_run, "transcripts.jsonl")
    if args.limit is not None:
        transcripts_path = _head(transcripts_path, args.limit, run_dir)
    original_runs = verify.run_original_all(transcripts_path, runs.results_path(transcripts_run, "tasks.jsonl"), config["max_workers"])
    with open(run_dir / "original_runs.jsonl", "w", encoding="utf-8") as fh:
        for r in original_runs:
            fh.write(json.dumps(r) + "\n")

    verdicts = verify.verify_all(transcripts_path, runs.results_path(claims_run, "claims.jsonl"),
                                 config["checkers"], original_runs)
    kept = {r["transcript_id"] for r in original_runs}
    verdicts = [v for v in verdicts if v.claim_id.rsplit("-c", 1)[0] in kept]
    with open(run_dir / "verdicts.jsonl", "w", encoding="utf-8") as fh:
        for v in verdicts:
            fh.write(v.model_dump_json() + "\n")

    summary = summarise(verdicts, original_runs)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    runs.finish_manifest(run_dir, n_model_calls=0, estimated_cost_usd=0.0)
    print(json.dumps(summary, indent=2))
    print(run_id)


def summarise(verdicts, original_runs) -> dict:
    """Original-test pass rate by label, and verdict counts by checker."""
    by_label = {}
    for label in sorted({r["label"] for r in original_runs}):
        rs = [r for r in original_runs if r["label"] == label]
        by_label[label] = {"n": len(rs), "original_passed": sum(r["original_passed"] for r in rs),
                           "timed_out": sum(r["detail"] == "timed out" for r in rs)}
    by_checker = {}
    for checker in sorted({v.checker for v in verdicts}):
        vs = [v for v in verdicts if v.checker == checker]
        by_checker[checker] = {"n": len(vs), "true": sum(v.is_true is True for v in vs),
                               "false": sum(v.is_true is False for v in vs),
                               "unverified": sum(v.is_true is None for v in vs), "scoped": sum(v.scoped for v in vs)}
    return {"n_verdicts": len(verdicts), "original_runs_by_label": by_label, "by_checker": by_checker}


def _head(path: Path, n: int, run_dir: Path) -> Path:
    out = run_dir / "transcripts_subset.jsonl"
    with open(path, encoding="utf-8") as src, open(out, "w", encoding="utf-8") as dst:
        for line in islice(src, n):
            dst.write(line)
    return out


if __name__ == "__main__":
    main()
