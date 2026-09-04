"""Stage 06: best-of-N and in-context RL loop. Stretch stage.

Parses args, loads its config, creates a run directory with a manifest, calls
one stub, exits. No other logic lives here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from audit import bon, runs

STAGE = "06_bon"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    parser.add_argument("--transcripts-run", default=None, help="Stage 01 run_id. Defaults to the latest.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    transcripts_run = args.transcripts_run or runs.latest_run("01_generate")

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)

    bon.run_bon(
        runs.results_path(transcripts_run, "transcripts.jsonl"),
        config["n_samples"],
        config["rounds"],
        config["selection_rule"],
    )

    print(run_id)


if __name__ == "__main__":
    main()
