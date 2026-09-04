"""Stage 03: estimator scores P(true) per claim, in each configured context mode.

Reads `transcripts.jsonl` and `tasks.jsonl` from a stage 01 run and
`claims.jsonl` from a stage 02 run, makes one cached estimator call per
(claim, context mode), and writes `scores.jsonl` plus `summary.json` under
`results/<run_id>/`. A call that fails stops the run; re-running resumes from
the cache, so only the failed calls are paid for again.
"""

from __future__ import annotations

import argparse
import json
from itertools import islice
from pathlib import Path

from audit import cache, estimator, runs

STAGE = "03_score"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--transcripts-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    parser.add_argument("--claims-run", default=None, help="Stage 02 run_id. Defaults to the latest.")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Score claims from the first N transcripts only, for the spot-check batch. Recorded in the manifest.",
    )
    parser.add_argument(
        "--modes", nargs="+", default=None,
        help="Override the config's context modes for this run, for example `--modes no_transcript`. Recorded in the manifest.",
    )
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    transcripts_run = args.transcripts_run or runs.latest_run("01_generate")
    claims_run = args.claims_run or runs.latest_run("02_claims")
    config["transcripts_run"] = transcripts_run
    config["claims_run"] = claims_run
    overrides = {}
    if args.limit is not None:
        overrides["limit"] = args.limit
    if args.modes is not None:
        overrides["context_mode"] = args.modes
        config["context_mode"] = args.modes
    if overrides:
        config["overrides"] = overrides
    estimator_model = config["estimator_model"] or models["estimator"]["deployment"]

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)
    print(f"run {run_id}, transcripts {transcripts_run}, claims {claims_run}, estimator {estimator_model}")

    claims_path = runs.results_path(claims_run, "claims.jsonl")
    if args.limit is not None:
        claims_path = _head(runs.results_path(transcripts_run, "transcripts.jsonl"), claims_path, args.limit, run_dir)
    scores = estimator.score_all(
        runs.results_path(transcripts_run, "transcripts.jsonl"),
        claims_path,
        config["context_mode"],
        estimator_model,
        "prompts/estimator.md",
        max_workers=config["max_workers"],
        only_verifiable=config["only_verifiable"],
    )

    with open(run_dir / "scores.jsonl", "w", encoding="utf-8") as fh:
        for s in scores:
            fh.write(s.model_dump_json() + "\n")

    summary = summarise(scores)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    stats = cache.cache_stats()
    runs.finish_manifest(
        run_dir, n_model_calls=stats["hits"] + stats["misses"], estimated_cost_usd=stats["cost_usd"]
    )
    print(json.dumps({**summary, "cache": stats}, indent=2))
    print(run_id)


def summarise(scores) -> dict:
    """Per mode: how many scores, and whether they spread or collapse.

    The estimator prompt exists to stop the model rounding to 0, 0.5 or 1.
    `n_distinct` and `frac_at_anchors` show whether it held on the batch, so a
    collapsed mode is visible here before stage 05 tries to fit a reliability
    plot to it.
    """
    out: dict[str, dict] = {}
    for mode in sorted({s.context_mode for s in scores}):
        ps = sorted(s.p_true for s in scores if s.context_mode == mode)
        out[mode] = {
            "n": len(ps),
            "mean": round(sum(ps) / len(ps), 3),
            "quartiles": [ps[len(ps) * q // 4] for q in (1, 2, 3)],
            "n_distinct": len(set(ps)),
            "frac_at_anchors": round(sum(p in (0.0, 0.5, 1.0) for p in ps) / len(ps), 3),
            "n_below_half": sum(p < 0.5 for p in ps),
        }
    return {"n_scores": len(scores), "by_mode": out, "n_claims": len({s.claim_id for s in scores})}


def _head(transcripts_path: Path, claims_path: Path, n: int, run_dir: Path) -> Path:
    """Claims from the first `n` transcripts, written into the run dir so the manifest's input is on disk."""
    with open(transcripts_path, encoding="utf-8") as fh:
        keep = {json.loads(line)["transcript_id"] for line in islice(fh, n)}
    out = run_dir / "claims_subset.jsonl"
    with open(claims_path, encoding="utf-8") as src, open(out, "w", encoding="utf-8") as dst:
        for line in src:
            if json.loads(line)["transcript_id"] in keep:
                dst.write(line)
    return out


if __name__ == "__main__":
    main()
