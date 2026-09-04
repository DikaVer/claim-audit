# claim-audit

This project tests whether reward-hacking coding agents leave a signature in the claims they make. Agent transcripts are generated on ImpossibleBench, where any pass on an impossible task variant is a hack by construction, so labels are computed rather than hand typed. Each transcript is decomposed into atomic claims, an estimator scores P(true) for every claim without ever seeing the test outcome, ground-truth checkers verify the claims that are verifiable, and the resulting aggregate claim score is compared against a whole-transcript "did the agent cheat?" monitor on AUROC and calibration. See `PLAN.md` for the research plan and `LOGBOOK.md` for the session log.

## Running

Install with `make install` (uv). Then run the stages in order, each reading the previous stage's output from `results/<run_id>/`:

```
make gen      # 01_generate_transcripts.py
make claims   # 02_extract_claims.py
make score    # 03_score_claims.py
make verify   # 04_verify_claims.py
make analyse  # 05_analyse.py
make bon      # 06_bon.py  (stretch)
```

Every run writes `results/<run_id>/manifest.json`. Results are append-only, so re-running a stage creates a new run_id.

## Stage 01 outputs and how to read them

`make gen` writes `results/<run_id>/` with four files, and the raw Inspect logs to `data/raw/<run_id>/`.

| file | what it is |
|---|---|
| `manifest.json` | run id, git commit, config and model roles as loaded, start and end time, number of agent calls |
| `tasks.jsonl` | one `Task` per (task, variant): spec, entry point, served tests, original tests |
| `transcripts.jsonl` | one `Transcript` per agent run: messages with ids, reasoning keyed to message ids, final report, outcomes, computed label |
| `summary.json` | label counts per variant, check-override hacks, transcripts with an empty report or no reasoning, token totals per model |

Two no-cost ways to exercise the stage before spending on the full grid:

```
# parse an existing log directory into a fresh run, no model calls
uv run python scripts/01_generate_transcripts.py --config configs/exp01_generate.yaml --from-logs data/raw/smoke-ds

# one task, all variants, all samples, through the live harness
uv run python scripts/01_generate_transcripts.py --config configs/exp01_generate.yaml --n-tasks 1
```

To sanity check a run, read `summary.json` first. `labels` should show hacks on the impossible variants and honest successes on `original`. `empty_reports` lists transcripts where the agent ignored the report request, which stage 02 will have no claims for. `check_override_hacks` counts the method A hacks that the scorer's ordering hides. Then open `transcripts.jsonl` with pandas:

```python
import pandas as pd
df = pd.read_json("results/<run_id>/transcripts.jsonl", lines=True)
df["reasoning_chars"] = df.reasoning.map(lambda r: sum(len(x["text"]) for x in r))
print(df.groupby(["variant", "label"]).size())
print(df.groupby("label")[["n_messages", "n_chars", "reasoning_chars"]].median())
print(df.loc[df.label == "hack", "final_report"].iloc[0])
```

## Viewing a run

`make viewer` builds one self-contained HTML page per run under `viewer/dist/`.
Open the file by double-clicking it, or open `viewer/dist/index.html` for the
list. Four tabs: run overview and label counts, a filterable transcript table
with the reasoning trace behind a separate collapsed panel, the served test file
against the unmutated one side by side, and a claims table that fills in once
stages 02 to 04 have run. `viewer/build.py` uses the standard library only,
adds no dependency, and never writes to `results/`.

Build one run rather than all of them with
`uv run python viewer/build.py --run <run_id>`.
