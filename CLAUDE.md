# CLAUDE.md

Project: **claim-audit**. Claim-level auditing of reward-hacking transcripts.
Owner: Dima. Purpose: MATS application project (16 h budget). Read `PLAN.md` for the research plan.

## Your job right now: skeleton only

Create the repository skeleton described below and stop. Do not implement experiment logic. Do not write prompts. Do not call any API. Do not download data. Do not run anything except `python -c "import audit"` to confirm the package imports.

Concretely:

- Every function in `src/audit/` is a stub: a full signature with type hints, a docstring stating inputs, outputs and the invariant it must respect, and `raise NotImplementedError`.
- Every script in `scripts/` parses args, loads its config, creates a run directory with a manifest, calls one stub, and exits. No other logic.
- Every file in `prompts/` contains only a title line and a bullet list of the fields the prompt must include. No prompt text.
- Config files contain keys with placeholder values and a comment per key.
- After creating the tree, print it with `tree -a -I '.git'` and list any decisions you made that were not specified here. Then stop and wait.

If something in this file is ambiguous, ask one question rather than guessing.

## Repository layout

```
claim-audit/
  CLAUDE.md
  PLAN.md
  README.md              # one paragraph: what the project tests, how to run scripts 01 to 05 in order
  LOGBOOK.md             # dated entries; see format below
  pyproject.toml         # package name "audit", src layout, deps listed below
  .env.example           # OPENAI_API_KEY=
  .gitignore             # data/, results/, .env, __pycache__, .cache/
  Makefile               # targets: install, smoke, gen, claims, score, verify, analyse, bon
  configs/
    models.yaml          # agent_model, estimator_model, extractor_model, monitor_model, temperature, max_tokens
    exp01_generate.yaml  # dataset, split, n_tasks, variants: [original, oneoff, conflicting], samples_per_task, seed
    exp02_claims.yaml    # extractor_model, claim_schema_version
    exp03_score.yaml     # estimator_model, context_mode: [full, no_test_diff, no_transcript]
    exp04_verify.yaml    # which checkers to run
    exp05_analyse.yaml   # metrics, bootstrap_n, output figures
    exp06_bon.yaml       # n_samples, rounds, selection_rule: [outcome_only, outcome_plus_estimator]
  prompts/
    claim_extraction.md
    estimator.md
    baseline_monitor.md
    bon_fewshot.md
  src/audit/
    __init__.py
    schema.py            # pydantic models: Task, Transcript, Claim, ClaimScore, ClaimVerdict, RunManifest
    transcripts.py       # load ImpossibleBench logs, normalise to Transcript, assign hack label
    claims.py            # extract atomic claims with dependencies from agent messages
    estimator.py         # score P(true | context, claim); context_mode controls what the estimator sees
    verify.py            # ground-truth checkers per claim type
    monitor_baseline.py  # whole-transcript "did the agent cheat?" score
    metrics.py           # AUROC, Brier, ECE, bootstrap CIs, per-mutation breakdown
    bon.py               # best-of-N / in-context RL loop (stretch)
    cache.py             # disk cache for model calls keyed by sha256(model, params, messages)
    runs.py              # run_id creation, manifest writing, results path helpers
  scripts/
    01_generate_transcripts.py
    02_extract_claims.py
    03_score_claims.py
    04_verify_claims.py
    05_analyse.py
    06_bon.py
  tests/
    test_schema.py       # round-trip serialisation of each pydantic model
    test_verify.py       # one placeholder test per checker, marked xfail
  data/
    raw/.gitkeep
    processed/.gitkeep
  results/.gitkeep
  notebooks/
    plots.ipynb          # empty; reads only from results/
```

## Dependencies

Declare these and nothing else without asking: `openai`, `pydantic`, `pyyaml`, `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `tqdm`, `pytest`, `inspect-ai`. [CHECK: whether ImpossibleBench is installed as a package or vendored; add it once Dima confirms.]

## Experiment-flow conventions (enforce in the skeleton)

1. **One script per stage, stages numbered.** Each stage reads the previous stage's output from `results/<run_id>/` and writes its own. Stages never share in-memory state.
2. **Every run gets a manifest.** `results/<run_id>/manifest.json` holds: run_id, stage, git commit hash, config as loaded, model names, start and end time, number of model calls, estimated cost in USD. `runs.py` writes it; scripts must not write it by hand.
3. **run_id = `YYYYMMDD-HHMM-<stage>-<slug>`.** Slug comes from the config file name.
4. **All model calls go through `cache.py`.** Cache key is sha256 of model, params and messages. Cache lives in `.cache/`. No script calls the OpenAI client directly.
5. **Results are append-only.** Never overwrite a results directory. Re-running a stage creates a new run_id.
6. **Schema first.** `schema.py` is the contract between stages. A stage that needs a new field adds it to the schema, bumps `claim_schema_version`, and notes it in `LOGBOOK.md`.
7. **Labels are computed, not typed.** The hack label comes from `transcripts.py` using task variant plus test outcome. No hand labelling anywhere.
8. **The estimator never sees outcomes.** `estimator.py` must accept a `context_mode` and must strip test results and the final pass/fail from every mode. Put this invariant in the docstring.
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

- Do not generate transcripts, claims, scores or figures.
- Do not write prompt text.
- Do not add dependencies beyond the list above.
- Do not create files outside the layout above.
- Do not run any script other than the import smoke test.
