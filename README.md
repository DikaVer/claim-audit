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
