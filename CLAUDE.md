# CLAUDE.md

Project: **claim-audit**. Claim-level auditing of reward-hacking transcripts.
Owner: Dima. Purpose: MATS application project.

## State of the project

All stages have run and the results are analysed. Start with `writeup/WRITEUP.md`
for the findings, `PLAN.md` for the plan as written before any run, and
`LOGBOOK.md` for the dated record of what was tried, found and decided. The
logbook is the source for anything not derivable from the code.

Final runs, all under `results/` (gitignored, on Dima's machine):

| stage | run id |
|---|---|
| 01 transcripts | `20260904-2037-01_generate-exp01_generate` |
| 02 claims | `20260904-2350-02_claims-exp02_claims` |
| 03 scores | `20260905-0123-03_score-exp03_score` |
| 03 with_reasoning ablation | `20260905-0228-03_score-exp03_score` |
| 03 reasoning_only ablation | `20260905-0239-03_score-exp03_score` |
| 03b reasoning gap | `20260905-0231-03b_gap-exp03b_gap` |
| 03c monitor | `20260905-0321-03c_monitor-exp03c_monitor` |
| 04 verdicts | `20260905-0315-04_verify-exp04_verify` |
| 05 metrics and figures | `20260905-0430-05_analyse-exp05_analyse` |

Settled and verified by smoke runs, do not re-litigate without new evidence:

- Harness: ImpossibleBench, pinned at commit `061dc3d` as a uv git source.
  It is an Inspect AI `@task`, so reuse the Inspect setup. Docker is required.
- Models: Azure OpenAI, account `llm-thebakerz` in `germanywestcentral`.
  Roles and deployments are in `configs/models.yaml`. Inspect addresses them as
  `openai/azure/<deployment>`.
- Agent is `DeepSeek-V3.2` with `reasoning_effort` set. Without that parameter
  there is no reasoning trace at all.
- `agent_type` is locked to `minimal`, because no DeepSeek model on Azure
  supports tool calling.
- The instruction prompt must ask for a report. Without it the agent emits only
  a code block and there are no claims to audit.
- On Windows, force utf-8 on stdout and stderr before importing the harness. It
  prints emoji that cp1252 cannot encode, which kills every sample.

Invariants, enforced in code and tests: no stage calls the OpenAI client
directly, all model calls go through `cache.py`, results are append-only,
`runs.py` is the only writer of `manifest.json`, labels are computed rather
than typed, and the estimator never sees outcomes, feedback or reasoning except
in the two ablation modes named for it.

## Repository layout

```
claim-audit/
  CLAUDE.md
  PLAN.md                # research plan as written before the first run
  README.md              # what the project tests, how to run the stages, how to read outputs
  LOGBOOK.md             # dated entries, one per session; see format below
  pyproject.toml         # package name "audit", src layout
  .env.example
  .gitignore             # data/, results/, .env, __pycache__, .cache/
  Makefile               # install, smoke, gen, claims, score, gap, monitor, verify, analyse, bon, viewer, results, notebook
  configs/               # models.yaml plus one exp*.yaml per stage
  prompts/               # claim_extraction, estimator, reasoning_gap, reasoning_omissions, baseline_monitor, bon_fewshot
  src/audit/
    schema.py            # pydantic contract between stages; CLAIM_SCHEMA_VERSION versions all of it
    transcripts.py       # load ImpossibleBench logs, normalise to Transcript, compute the hack label
    claims.py            # atomic claims with dependencies from the final assistant message
    estimator.py         # P(true | context, claim); context_mode decides what the estimator sees
    reasoning_gap.py     # stage 3b: what the reasoning knew against what the report said
    monitor_baseline.py  # stage 3c: whole-transcript "did the agent cheat?" score
    verify.py            # ground-truth checkers, Docker re-run against the original tests
    metrics.py           # AUROC, Brier, ECE, bootstrap CIs, per-variant and per-length breakdowns
    bon.py               # best-of-N stretch, not run
    cache.py             # disk cache for model calls keyed by sha256(model, params, messages)
    runs.py              # run_id creation, manifest writing, results path helpers
  scripts/               # 01 to 06, plus 03b and 03c; one script per stage
  tests/                 # unit tests; *_live.py run real prompts only with AUDIT_LIVE_TESTS=1
  viewer/                # stdlib-only HTML viewer and results dashboard over results/
  notebooks/plots.ipynb  # reads results/ only, executed in place with outputs
  writeup/               # WRITEUP.md and figures/ extracted from the notebook
  data/raw, data/processed, results/   # gitignored
```

## Experiment-flow conventions

1. **One script per stage, stages numbered.** Each stage reads the previous stage's output from `results/<run_id>/` and writes its own. Stages never share in-memory state.
2. **Every run gets a manifest.** `results/<run_id>/manifest.json` holds: run_id, stage, git commit hash, config as loaded, model names, start and end time, number of model calls, estimated cost in USD. `runs.py` writes it; scripts must not write it by hand.
3. **run_id = `YYYYMMDD-HHMM-<stage>-<slug>`.** Slug comes from the config file name.
4. **All model calls go through `cache.py`.** Cache key is sha256 of model, params and messages. Cache lives in `.cache/`. No script calls the OpenAI client directly.
5. **Results are append-only.** Never overwrite a results directory. Re-running a stage creates a new run_id.
6. **Schema first.** `schema.py` is the contract between stages. A stage that needs a new field adds it to the schema, bumps `CLAIM_SCHEMA_VERSION`, and notes it in `LOGBOOK.md`.
7. **Labels are computed, not typed.** The hack label comes from `transcripts.py` using task variant plus test outcome. No hand labelling anywhere.
8. **The estimator never sees outcomes.** `estimator.py` accepts a `context_mode` and strips test results, feedback messages and the final pass/fail from every mode. The invariant is in the docstring.
9. **Notebooks read, never compute.** `plots.ipynb` loads from `results/` only.
10. **Logbook per session.** Entry format:

```
## 2026-09-04 14:10  (session 3)
Tried: ...
Found: ...
Decided: ...
Next: ...
Time spent so far: 7.5 h
```

## Writing conventions for anything you generate

British spelling. No em-dashes. Short sentences, one claim each. Mark unknowns inline as `[CHECK: ...]` rather than inventing a value.

## Things you must not do

- Do not edit `results/` by hand, and do not regenerate transcripts, claims or scores without a logbook entry saying why.
- Do not add dependencies beyond those in `pyproject.toml` without asking.
- Do not rewrite logbook entries. Append.
