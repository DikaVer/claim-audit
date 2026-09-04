"""Stage 02: extract atomic claims from the stage 01 transcripts.

Reads `transcripts.jsonl` from a stage 01 run, makes one cached extractor call
per transcript, and writes `claims.jsonl` plus `summary.json` under
`results/<run_id>/`. Transcripts with no report stay in the summary as
zero-claim transcripts rather than being dropped, since they concentrate in
the honest classes and dropping them would bias stage 05.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from audit import cache, claims, runs

STAGE = "02_claims"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--input-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Extract from the first N transcripts only, for the spot-check batch. Recorded in the manifest.",
    )
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    input_run = args.input_run or runs.latest_run("01_generate")
    config["input_run"] = input_run
    if args.limit is not None:
        config["overrides"] = {"limit": args.limit}
    extractor_model = config["extractor_model"] or models["extractor"]["deployment"]

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)
    print(f"run {run_id}, input {input_run}, extractor {extractor_model}")

    transcripts_path = runs.results_path(input_run, "transcripts.jsonl")
    if args.limit is not None:
        transcripts_path = _head(transcripts_path, args.limit, run_dir)
    items = claims.extract_all(
        transcripts_path, extractor_model, "prompts/claim_extraction.md", config["max_workers"]
    )

    with open(run_dir / "claims.jsonl", "w", encoding="utf-8") as fh:
        for c in items:
            fh.write(c.model_dump_json() + "\n")

    summary = summarise(items, claims.load_transcripts(transcripts_path))
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    stats = cache.cache_stats()
    runs.finish_manifest(
        run_dir, n_model_calls=stats["hits"] + stats["misses"], estimated_cost_usd=stats["cost_usd"]
    )
    print(json.dumps({**summary, "cache": stats}, indent=2))
    print(run_id)


def summarise(items, transcripts) -> dict:
    """Counts that show whether extraction worked, split the way stage 05 will read them."""
    per_transcript = Counter(c.transcript_id for c in items)
    by_label: dict[str, list[int]] = {}
    for t in transcripts:
        by_label.setdefault(t.label, []).append(per_transcript[t.transcript_id])
    return {
        "n_transcripts": len(transcripts),
        "n_claims": len(items),
        "by_type": dict(Counter(c.type for c in items)),
        "n_verifiable": sum(c.verifiable for c in items),
        "n_empty_depends_on": sum(not c.depends_on for c in items),
        "zero_claim_transcripts": [t.transcript_id for t in transcripts if not per_transcript[t.transcript_id]],
        "mean_claims_by_label": {k: round(sum(v) / len(v), 2) for k, v in sorted(by_label.items())},
    }


def _head(path: Path, n: int, run_dir: Path) -> Path:
    """The first `n` transcripts, written into the run dir so the manifest's input is on disk."""
    out = run_dir / "transcripts_subset.jsonl"
    with open(path, encoding="utf-8") as src, open(out, "w", encoding="utf-8") as dst:
        for i, line in enumerate(src):
            if i >= n:
                break
            dst.write(line)
    return out


if __name__ == "__main__":
    main()
