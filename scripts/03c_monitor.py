"""Stage 3c: the whole-transcript baseline monitor, one call per transcript.

Reads `transcripts.jsonl` from a stage 01 run and writes `monitor.jsonl` plus
`summary.json` under `results/<run_id>/`. The monitor sees the estimator's
`full` context, nothing more, so its AUROC is the baseline the claim-level
estimator is compared against.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from audit import cache, monitor_baseline, runs

STAGE = "03c_monitor"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--input-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    input_run = args.input_run or runs.latest_run("01_generate")
    config["input_run"] = input_run
    monitor_model = config["monitor_model"] or models["monitor"]["deployment"]

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)
    print(f"run {run_id}, input {input_run}, monitor {monitor_model}")

    transcripts_path = runs.results_path(input_run, "transcripts.jsonl")
    items = monitor_baseline.score_all(transcripts_path, monitor_model, "prompts/baseline_monitor.md", config["max_workers"])
    with open(run_dir / "monitor.jsonl", "w", encoding="utf-8") as fh:
        for m in items:
            fh.write(m.model_dump_json() + "\n")

    labels = {}
    with open(transcripts_path, encoding="utf-8") as fh:
        for line in fh:
            t = json.loads(line)
            labels[t["transcript_id"]] = t["label"]
    summary = {"n": len(items), "by_label": {}}
    for label in sorted(set(labels.values())):
        ms = [m for m in items if labels[m.transcript_id] == label]
        summary["by_label"][label] = {
            "n": len(ms), "mean_p_cheat": round(sum(m.p_cheat for m in ms) / len(ms), 3),
            "verdicts": dict(Counter(m.verdict for m in ms)),
        }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    stats = cache.cache_stats()
    runs.finish_manifest(run_dir, n_model_calls=stats["hits"] + stats["misses"], estimated_cost_usd=stats["cost_usd"])
    print(json.dumps({**summary, "cache": stats}, indent=2))
    print(run_id)


if __name__ == "__main__":
    main()
