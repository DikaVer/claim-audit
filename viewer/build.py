"""Build a self-contained HTML viewer for one run in `results/`.

Read only. This script never writes to `results/` and never touches a manifest,
because `runs.py` is the only writer there.

The run data is inlined into the page at build time rather than fetched at view
time, because a `file://` page cannot fetch a sibling file: browsers give it the
opaque `null` origin and block the request. Inlining keeps the output openable
by double-click, with no server and no new dependencies.

Usage:
    python viewer/build.py              # newest run in results/
    python viewer/build.py --run <run_id>
    python viewer/build.py --all
    python viewer/build.py --all --no-reasoning   # for a large grid
    python viewer/build.py --results <05_analyse run_id>   # the results dashboard
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
TEMPLATE = Path(__file__).resolve().parent / "template.html"
RESULTS_TEMPLATE = Path(__file__).resolve().parent / "results.html"
DIST = Path(__file__).resolve().parent / "dist"

# Only the transcript-facing stages so far. A stage that starts writing a new
# file adds it here and the matching tab in template.html picks it up.
JSONL_FILES = {
    "tasks": "tasks.jsonl",
    "transcripts": "transcripts.jsonl",
    "claims": "claims.jsonl",
    "scores": "scores.jsonl",
    "verdicts": "verdicts.jsonl",
}

# Guard against a pathological diff on a large generated test file.
MAX_DIFF_LINES = 4000


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def side_by_side(left_text: str, right_text: str) -> dict:
    """Align two files line by line for the two-column diff.

    Each side is a list of `[op, line]`, where op is `=` unchanged, `-` or `+`
    changed, and `~` a padding row that keeps the two columns in step.
    """
    left = left_text.splitlines()[:MAX_DIFF_LINES]
    right = right_text.splitlines()[:MAX_DIFF_LINES]
    lrows: list[list[str]] = []
    rrows: list[list[str]] = []
    changed = 0

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, left, right).get_opcodes():
        lchunk = left[i1:i2]
        rchunk = right[j1:j2]
        if tag == "equal":
            lrows += [["=", x] for x in lchunk]
            rrows += [["=", x] for x in rchunk]
            continue
        changed += max(len(lchunk), len(rchunk))
        pad = max(len(lchunk), len(rchunk))
        lrows += [["-", x] for x in lchunk] + [["~", ""]] * (pad - len(lchunk))
        rrows += [["+", x] for x in rchunk] + [["~", ""]] * (pad - len(rchunk))

    return {"left": lrows, "right": rrows, "n_changed": changed}


def collect(run_dir: Path, drop_reasoning: bool = False) -> dict:
    payload: dict = {
        "run_id": run_dir.name,
        "manifest": read_json(run_dir / "manifest.json"),
        "summary": read_json(run_dir / "summary.json"),
    }
    for key, name in JSONL_FILES.items():
        payload[key] = read_jsonl(run_dir / name)

    # A stage 02 to 04 run holds only its own output. Its transcripts and tasks
    # live in the stage 01 run named in its manifest, so follow that pointer.
    # Reasoning is dropped on that path: the claim tabs never show it, and a
    # whole grid of traces is 50 MB.
    input_run = (payload["manifest"].get("config") or {}).get("input_run")
    if input_run and not payload["transcripts"]:
        src = RESULTS / input_run
        payload["input_run"] = input_run
        payload["transcripts"] = read_jsonl(src / JSONL_FILES["transcripts"])
        payload["tasks"] = read_jsonl(src / JSONL_FILES["tasks"])
        drop_reasoning = True

    if drop_reasoning:
        # Reasoning is roughly 200k characters per transcript, so a whole grid
        # inlines into a page too heavy to open. Dropping it keeps the rest.
        for transcript in payload["transcripts"]:
            transcript["reasoning"] = []

    for task in payload["tasks"]:
        task["diff"] = side_by_side(
            task.get("original_tests", ""), task.get("variant_tests", "")
        )
    return payload


def build(run_dir: Path, drop_reasoning: bool = False, spotcheck: Path | None = None) -> Path:
    payload = collect(run_dir, drop_reasoning)
    if spotcheck is not None:
        # A review exported from the Spot check tab, embedded so the page opens
        # with those judgements loaded and a second reader can audit them.
        payload["spotcheck"] = read_json(spotcheck)
    # `</script>` anywhere in a transcript would close the data block early.
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__TITLE__", run_dir.name).replace("__PAYLOAD__", blob)

    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{run_dir.name}.html"
    out.write_text(html, encoding="utf-8")
    return out


def collect_results(run_dir: Path) -> dict:
    """Everything a stage 05 run rests on, joined by the run ids in its manifest.

    Transcripts carry their final report and final code block only, never the
    messages or the reasoning, so a whole grid stays a few megabytes.
    """
    import base64
    import csv
    import re

    manifest = read_json(run_dir / "manifest.json")
    inputs = (manifest.get("config") or {}).get("inputs") or {}
    payload: dict = {"run_id": run_dir.name, "manifest": manifest, "metrics": read_json(run_dir / "metrics.json")}
    with (run_dir / "per_transcript.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in list(r.items()):
            if v in ("", "nan"):
                r[k] = None
            elif v in ("True", "False"):
                r[k] = v == "True"
            else:
                try:
                    r[k] = float(v) if re.fullmatch(r"-?\d+(\.\d+)?(e-?\d+)?", v) else v
                except ValueError:
                    pass
    payload["per_transcript"] = rows

    block = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
    transcripts = []
    for t in read_jsonl(RESULTS / inputs["transcripts_run"] / "transcripts.jsonl"):
        last = next((m for m in reversed(t["messages"]) if m["role"] == "assistant"), None)
        code = block.findall(last["content"])[-1] if last and block.findall(last["content"]) else ""
        transcripts.append({"transcript_id": t["transcript_id"], "label": t["label"], "variant": t["variant"],
                            "final_report": t["final_report"], "final_code": code, "n_chars": t["n_chars"]})
    payload["transcripts"] = transcripts
    payload["claims"] = read_jsonl(RESULTS / inputs["claims_run"] / "claims.jsonl")
    payload["scores"] = read_jsonl(RESULTS / inputs["scores_run"] / "scores.jsonl")
    payload["verdicts"] = read_jsonl(RESULTS / inputs["verdicts_run"] / "verdicts.jsonl")
    payload["gaps"] = read_jsonl(RESULTS / inputs["gap_run"] / "gaps.jsonl") if inputs.get("gap_run") else []
    payload["monitor"] = read_jsonl(RESULTS / inputs["monitor_run"] / "monitor.jsonl") if inputs.get("monitor_run") else []
    payload["figures"] = {p.stem: base64.b64encode(p.read_bytes()).decode("ascii")
                          for p in sorted((run_dir / "figures").glob("*.png"))} if (run_dir / "figures").exists() else {}
    return payload


def build_results(run_dir: Path) -> Path:
    payload = collect_results(run_dir)
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = RESULTS_TEMPLATE.read_text(encoding="utf-8").replace("__TITLE__", run_dir.name).replace("__PAYLOAD__", blob)
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"results-{run_dir.name}.html"
    out.write_text(html, encoding="utf-8")
    return out


def run_dirs() -> list[Path]:
    return sorted(d for d in RESULTS.iterdir() if d.is_dir() and (d / "manifest.json").exists())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", help="run id under results/. Defaults to the newest.")
    parser.add_argument("--all", action="store_true", help="build every run.")
    parser.add_argument(
        "--spotcheck", type=Path, default=None,
        help="a JSON file exported from the Spot check tab, embedded as the page's initial review.",
    )
    parser.add_argument("--results", help="a 05_analyse run id: build the results dashboard for it instead.")
    parser.add_argument(
        "--no-reasoning",
        action="store_true",
        help="leave the reasoning traces out, for runs too large to inline them.",
    )
    args = parser.parse_args()

    runs = run_dirs()
    if not runs:
        raise SystemExit(f"no runs with a manifest under {RESULTS}")

    if args.results:
        out = build_results(RESULTS / args.results)
        print(f"{out}  ({out.stat().st_size / 1024:.0f} kB)")
        return

    if args.all:
        targets = runs
    elif args.run:
        targets = [d for d in runs if d.name == args.run]
        if not targets:
            raise SystemExit(f"run {args.run!r} not found. Available: {[d.name for d in runs]}")
    else:
        targets = [runs[-1]]

    for run_dir in targets:
        out = build(run_dir, args.no_reasoning, args.spotcheck)
        kb = out.stat().st_size / 1024
        print(f"{out}  ({kb:.0f} kB)")
        if kb > 20_000 and not args.no_reasoning:
            print("  large page. Rebuild with --no-reasoning if the browser struggles.")

    index = DIST / "index.html"
    links = "\n".join(
        f'<li><a href="{d.name}.html">{d.name}</a></li>' for d in sorted(run_dirs(), reverse=True)
        if (DIST / f"{d.name}.html").exists()
    )
    index.write_text(
        "<!doctype html><meta charset=utf-8><title>claim-audit runs</title>"
        "<style>body{font:15px/1.6 system-ui;margin:40px auto;max-width:640px}</style>"
        f"<h1>claim-audit runs</h1><ul>{links}</ul>",
        encoding="utf-8",
    )
    print(f"{index}")


if __name__ == "__main__":
    main()
