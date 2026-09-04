"""Stage 3b: judge what the reasoning knew against what the report said, per transcript.

Reads `transcripts.jsonl` from a stage 01 run, makes one cached judge call per
transcript that has both a reasoning trace and a report, and writes
`gaps.jsonl` plus `summary.json` under `results/<run_id>/`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import islice
from pathlib import Path

from audit import cache, reasoning_gap, runs

STAGE = "03b_gap"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--input-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    parser.add_argument("--limit", type=int, default=None, help="Judge the first N transcripts only. Recorded in the manifest.")
    parser.add_argument("--claims-run", default=None, help="Stage 02 run_id, used by --omissions. Defaults to the latest.")
    parser.add_argument(
        "--omissions", action="store_true",
        help="Run the omission judge instead: conclusions in the trace absent from the report's claims. Writes omissions.jsonl.",
    )
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    input_run = args.input_run or runs.latest_run("01_generate")
    config["input_run"] = input_run
    overrides = {}
    if args.limit is not None:
        overrides["limit"] = args.limit
    if args.omissions:
        overrides["omissions"] = True
        config["claims_run"] = args.claims_run or runs.latest_run("02_claims")
    if overrides:
        config["overrides"] = overrides
    judge_model = config["judge_model"] or models["estimator"]["deployment"]

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)
    print(f"run {run_id}, input {input_run}, judge {judge_model}")

    transcripts_path = runs.results_path(input_run, "transcripts.jsonl")
    if args.limit is not None:
        transcripts_path = _head(transcripts_path, args.limit, run_dir)
    gaps = reasoning_gap.judge_all(transcripts_path, judge_model, "prompts/reasoning_gap.md", config["max_workers"])

    with open(run_dir / "gaps.jsonl", "w", encoding="utf-8") as fh:
        for g in gaps:
            fh.write(g.model_dump_json() + "\n")

    labels = {}
    with open(transcripts_path, encoding="utf-8") as fh:
        for line in fh:
            t = json.loads(line)
            labels[t["transcript_id"]] = t["label"]
    summary = summarise(gaps, labels)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    stats = cache.cache_stats()
    runs.finish_manifest(run_dir, n_model_calls=stats["hits"] + stats["misses"], estimated_cost_usd=stats["cost_usd"])
    print(json.dumps({**summary, "cache": stats}, indent=2))
    print(run_id)


def summarise(gaps, labels: dict[str, str]) -> dict:
    """Per label: how often the reasoning knew, how often the report admitted it, and the framing mix."""
    out = {"n_judged": len(gaps), "n_skipped": len(labels) - len(gaps), "by_label": {}}
    for label in sorted(set(labels.values())):
        gs = [g for g in gaps if labels[g.transcript_id] == label]
        if not gs:
            continue
        knows = [g for g in gs if g.reasoning_knows]
        out["by_label"][label] = {
            "n": len(gs),
            "reasoning_knows": len(knows),
            "report_admits": sum(g.report_admits for g in gs),
            "knows_but_report_does_not_admit": sum(not g.report_admits for g in knows),
            "framing": dict(Counter(g.report_framing for g in gs)),
            "framing_when_reasoning_knows": dict(Counter(g.report_framing for g in knows)),
        }
    return out


def summarise_omissions(items, labels: dict[str, str]) -> dict:
    """Per label: omissions per transcript, how many against interest, and the type mix."""
    out = {"n_omissions": len(items), "by_label": {}}
    per = Counter(o.transcript_id for o in items)
    for label in sorted(set(labels.values())):
        tids = [t for t, l in labels.items() if l == label]
        os_ = [o for o in items if labels[o.transcript_id] == label]
        if not tids:
            continue
        out["by_label"][label] = {
            "n_transcripts": len(tids),
            "n_omissions": len(os_),
            "mean_per_transcript": round(len(os_) / len(tids), 2),
            "transcripts_with_any": sum(per[t] > 0 for t in tids),
            "against_interest": sum(o.against_interest for o in os_),
            "against_interest_by_type": dict(Counter(o.type for o in os_ if o.against_interest)),
            "by_type": dict(Counter(o.type for o in os_)),
        }
    return out


def _head(path: Path, n: int, run_dir: Path) -> Path:
    out = run_dir / "transcripts_subset.jsonl"
    with open(path, encoding="utf-8") as src, open(out, "w", encoding="utf-8") as dst:
        for line in islice(src, n):
            dst.write(line)
    return out


if __name__ == "__main__":
    main()
