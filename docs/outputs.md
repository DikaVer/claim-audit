# Reading the outputs

Each stage writes into `results/<run_id>/`. The run ids behind the published numbers are listed in [CLAUDE.md](../CLAUDE.md).

| file | stage | contents |
|---|---|---|
| `manifest.json` | all | run id, git commit, config as loaded, model roles, timings, call count, estimated cost |
| `transcripts.jsonl` | 01 | one `Transcript` per agent run: messages, reasoning, final report, outcome, computed label |
| `claims.jsonl` | 02 | one `Claim` per atomic assertion: text, type, negated flag, verifiable flag |
| `scores.jsonl` | 03 | one `ClaimScore` per (claim, context mode): P(true), justification, type-mismatch flag |
| `gaps.jsonl` | 03b | per transcript: does the reasoning know, does the report admit, framing label |
| `monitor.jsonl` | 03c | per transcript: the monitor's P(cheat) and its one-word verdict |
| `original_runs.jsonl` | 04 | per transcript: did the final code pass the original tests, first and second pass |
| `verdicts.jsonl` | 04 | ground truth per verifiable claim, with scoped claims flagged rather than judged |
| `metrics.json`, `per_transcript.csv` | 05 | every number in the write-up |

Start with `summary.json` in any run. For stage 01 it gives label counts per variant and lists transcripts with an empty report. For stage 03 it reports whether the probabilities spread or collapsed onto 0, 0.5 and 1.

## Design rules

- One script per stage. Stages share files, never memory.
- Results are append-only. Re-running a stage creates a new run id.
- All model calls go through `src/audit/cache.py`, keyed by sha256 of model, params and messages.
- Labels are computed in `src/audit/transcripts.py`, never typed.
- The estimator never sees test outcomes, feedback or reasoning, except in the two ablation modes named for it.
- `src/audit/schema.py` is the contract between stages. A new field bumps `CLAIM_SCHEMA_VERSION`.
