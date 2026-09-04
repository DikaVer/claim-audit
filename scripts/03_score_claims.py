"""Stage 03: estimator scores P(true) per claim, in each configured context mode.

Parses args, loads its config, creates a run directory with a manifest, calls
one stub, exits. No other logic lives here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from audit import estimator, runs

STAGE = "03_score"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--transcripts-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    parser.add_argument("--claims-run", default=None, help="Stage 02 run_id. Defaults to the latest.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    transcripts_run = args.transcripts_run or runs.latest_run("01_generate")
    claims_run = args.claims_run or runs.latest_run("02_claims")

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)

    estimator.score_all(
        runs.results_path(transcripts_run, "transcripts.jsonl"),
        runs.results_path(claims_run, "claims.jsonl"),
        config["context_mode"],
        config["estimator_model"],
        "prompts/estimator.md",
    )

    print(run_id)


if __name__ == "__main__":
    main()
