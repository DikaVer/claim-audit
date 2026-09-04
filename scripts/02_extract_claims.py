"""Stage 02: extract atomic claims from the stage 01 transcripts.

Parses args, loads its config, creates a run directory with a manifest, calls
one stub, exits. No other logic lives here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from audit import claims, runs

STAGE = "02_claims"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--input-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    input_run = args.input_run or runs.latest_run("01_generate")

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)

    claims.extract_all(
        runs.results_path(input_run, "transcripts.jsonl"),
        config["extractor_model"],
        "prompts/claim_extraction.md",
    )

    print(run_id)


if __name__ == "__main__":
    main()
