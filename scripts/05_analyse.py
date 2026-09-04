"""Stage 05: metrics, controls and figures. Reads results only, calls no model.

Parses args, loads its config, creates a run directory with a manifest, calls
one stub, exits. No other logic lives here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from audit import metrics, runs

STAGE = "05_analyse"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)

    metrics.analyse(
        run_dir,
        config["metrics"],
        config["bootstrap_n"],
        config["figures"],
    )

    print(run_id)


if __name__ == "__main__":
    main()
