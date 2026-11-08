"""Stage 05: metrics, controls and figures. Reads results only, calls no model.

Parses args, loads its config, creates a run directory with a manifest, calls
`metrics.analyse`, exits. The input run ids are taken from the config so the
manifest records exactly which runs the numbers came from.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit import metrics, runs

STAGE = "05_analyse"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="Stage config in configs/.")
    args = parser.parse_args()

    config = runs.load_config(args.config)
    models = runs.load_config(Path("configs/models.yaml"))
    inputs = dict(config["inputs"])
    inputs["monitor_run"] = inputs.get("monitor_run") or runs.latest_run("03c_monitor")
    config["inputs"] = inputs

    run_id = runs.make_run_id(STAGE, args.config)
    run_dir = runs.create_run_dir(run_id)
    runs.write_manifest(run_dir, STAGE, config, models)
    print(f"run {run_id}, inputs {json.dumps(inputs)}")

    metrics.analyse(run_dir, config["metrics"], config["bootstrap_n"], config["figures"], inputs=inputs,
                    seed=config["seed"], n_length_bins=config["n_length_bins"])
    runs.finish_manifest(run_dir, n_model_calls=0, estimated_cost_usd=0.0)
    print((run_dir / "metrics.json").read_text(encoding="utf-8")[:3000])
    print(run_id)


if __name__ == "__main__":
    main()
