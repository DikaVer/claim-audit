"""Stage 01: generate agent transcripts on ImpossibleBench and compute hack labels.

Samples task ids, runs the harness once per variant through Inspect's
`eval_set`, then normalises every sample to a `Transcript`. With `--from-logs`
the generation step is skipped and an existing log directory is parsed
instead, which is the no-cost smoke test and the recovery path when a run
finished but parsing failed.

Outputs under `results/<run_id>/`: `manifest.json`, `tasks.jsonl`,
`transcripts.jsonl`, `summary.json`. Raw harness logs go to `data/raw/<run_id>/`.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter
from pathlib import Path

# The harness prints check and cross emoji. Windows stdout is cp1252, which
# cannot encode them, and the resulting UnicodeEncodeError kills every sample.
# This has to happen before the harness is imported.
for stream in ("stdout", "stderr"):
    setattr(sys, stream, io.TextIOWrapper(getattr(sys, stream).buffer, encoding="utf-8", line_buffering=True))

from audit import runs, transcripts  # noqa: E402

STAGE = "01_generate"
RAW_DIR = Path("data/raw")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument(
        "--from-logs", type=Path, default=None,
        help="Parse this Inspect log directory instead of generating. No model calls.",
    )
    parser.add_argument(
        "--resume", type=str, default=None, metavar="RUN_ID",
        help="Continue an interrupted run: same run dir, same tasks, eval_set resumes from data/raw/<RUN_ID>.",
    )
    parser.add_argument(
        "--n-tasks", type=int, default=None,
        help="Override n_tasks from the config, for a small live smoke run. Recorded in the manifest.",
    )
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    if args.n_tasks is not None:
        config["n_tasks"] = args.n_tasks
        config["overrides"] = {"n_tasks": args.n_tasks}
    if args.from_logs is not None:
        config["from_logs"] = str(args.from_logs)

    if args.resume is None:
        run_id = runs.make_run_id(STAGE, args.config)
        run_dir = runs.create_run_dir(run_id)
        runs.write_manifest(run_dir, STAGE, config, models)
    else:
        # Resuming is the one case where an existing run dir is written to. It
        # is only allowed while the run has no transcripts, so a finished run
        # can never be overwritten. The manifest keeps its original start time
        # and the config it was started with.
        run_id = args.resume
        run_dir = runs.RESULTS_DIR / run_id
        if (run_dir / "transcripts.jsonl").exists():
            raise SystemExit(f"{run_id} already has transcripts.jsonl; results are append-only")
        config = runs.read_manifest(run_dir).config
    print(f"run {run_id}")

    if args.from_logs is None:
        tasks = transcripts.load_tasks(
            config["dataset"], config["n_tasks"], config["variants"], config["seed"]
        )
        log_dir = RAW_DIR / run_id
        generate(config, models["agent"], tasks, log_dir)
    else:
        log_dir = args.from_logs
        raw_logs = transcripts.load_harness_logs(log_dir)
        ids = sorted({r["sample"]["metadata"]["task_id"] for r in raw_logs}, key=transcripts._numeric_suffix)
        variants = sorted({r["sample"]["metadata"]["impossible_type"] for r in raw_logs})
        tasks = transcripts.load_tasks(config["dataset"], len(ids), variants, config["seed"], task_ids=ids)

    _write_jsonl(run_dir / "tasks.jsonl", tasks)

    raw_logs = transcripts.load_harness_logs(log_dir)
    errored = [r for r in raw_logs if r["sample"].get("error")]
    usable = [r for r in raw_logs if not r["sample"].get("error")]
    items = transcripts.normalise_all(usable, tasks)
    _write_jsonl(run_dir / "transcripts.jsonl", items)

    summary = summarise(items, raw_logs, errored, log_dir)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    runs.finish_manifest(run_dir, n_model_calls=summary["n_model_calls"], estimated_cost_usd=0.0)

    print(json.dumps({k: v for k, v in summary.items() if k != "tokens_by_model"}, indent=2))
    print(run_id)


def generate(config: dict, agent: dict, tasks, log_dir: Path) -> None:
    """Run the harness once per variant on the sampled task ids."""
    from impossiblebench.livecodebench_tasks import impossible_livecodebench
    from inspect_ai import eval_set

    ids = sorted({t.task_id for t in tasks}, key=transcripts._numeric_suffix)
    inspect_tasks = [
        impossible_livecodebench(
            split=variant,
            instruction_prompt=config["instruction_prompt"],
            sandbox=config["sandbox"],
            agent_type=config["agent_type"],
            max_attempts=config["max_attempts"],
            allow_test_modifications=config["allow_test_modifications"],
            message_limit=config["message_limit"],
            # limit stays None and shuffle False: sampling is done in load_tasks
            # and the chosen ids are passed as sample_id below.
        )
        for variant in config["variants"]
    ]
    eval_set(
        inspect_tasks,
        model=f"openai/azure/{agent['deployment']}",
        sample_id=ids,
        epochs=config["samples_per_task"],
        reasoning_effort=agent.get("reasoning_effort"),
        max_tokens=agent.get("max_tokens"),
        log_dir=str(log_dir),
        max_connections=config["max_connections"],
        max_sandboxes=config["max_sandboxes"],
        max_tasks=len(inspect_tasks),
        fail_on_error=False,
        retry_on_error=2,
        log_dir_allow_dirty=True,
    )


def summarise(items, raw_logs, errored, log_dir: Path) -> dict:
    """Counts that decide whether the run is usable, plus what it cost in tokens."""
    tokens: dict[str, dict] = {}
    for r in raw_logs:
        for model, usage in (r["sample"].get("model_usage") or {}).items():
            t = tokens.setdefault(model, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
            for k in t:
                t[k] += usage.get(k) or 0
    by_variant_label = Counter((t.variant, t.label) for t in items)
    return {
        "log_dir": str(log_dir),
        "n_logs": len(raw_logs),
        "n_transcripts": len(items),
        "n_errored_samples": len(errored),
        "errored": [
            {"task_id": r["sample"]["metadata"].get("task_id"), "log_file": r["log_file"],
             "message": (r["sample"]["error"] or {}).get("message", "")[:200]}
            for r in errored
        ],
        "labels": dict(Counter(t.label for t in items)),
        "by_variant_label": {f"{v}/{l}": n for (v, l), n in sorted(by_variant_label.items())},
        "check_override_hacks": sum(t.check_override_hack for t in items),
        "empty_reports": [t.transcript_id for t in items if not t.final_report],
        "no_reasoning": [t.transcript_id for t in items if not t.reasoning],
        "n_model_calls": sum(1 for t in items for m in t.messages if m["role"] == "assistant"),
        "tokens_by_model": tokens,
    }


def _write_jsonl(path: Path, models) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for m in models:
            fh.write(m.model_dump_json() + "\n")


if __name__ == "__main__":
    main()
