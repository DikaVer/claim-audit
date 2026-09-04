"""Run ids, manifests and results paths. Scripts never write a manifest by hand."""

from __future__ import annotations

from pathlib import Path

from audit.schema import RunManifest

RESULTS_DIR = Path("results")


def make_run_id(stage: str, config_path: Path) -> str:
    """Build a run id.

    Inputs: the stage name and the path of the config being used.
    Outputs: `YYYYMMDD-HHMM-<stage>-<slug>`, where the slug is the config file stem.
    Invariant: the id encodes when the run started, so ids sort chronologically.
    """
    raise NotImplementedError


def create_run_dir(run_id: str) -> Path:
    """Create the results directory for a run.

    Inputs: the run id.
    Outputs: the path `results/<run_id>/`.
    Invariant: results are append-only. This raises if the directory already
    exists, rather than overwriting it.
    """
    raise NotImplementedError


def load_config(config_path: Path) -> dict:
    """Load a YAML config.

    Inputs: the path to a file in `configs/`.
    Outputs: the config as a dict, exactly as parsed.
    Invariant: no defaults are filled in here, so the manifest records what the
    file actually said.
    """
    raise NotImplementedError


def write_manifest(
    run_dir: Path, stage: str, config: dict, models: dict[str, str]
) -> RunManifest:
    """Write `manifest.json` for a run.

    Inputs: the run directory, the stage name, the config as loaded, and the
    model names.
    Outputs: the RunManifest that was written. It carries run id, stage, git
    commit hash, config, models, start and end time, number of model calls and
    estimated cost in USD.
    Invariant: this is the only writer of `manifest.json`. Call counts and cost
    come from `cache.cache_stats`.
    """
    raise NotImplementedError


def results_path(run_id: str, filename: str) -> Path:
    """Resolve a file inside a run's results directory.

    Inputs: the run id and a file name.
    Outputs: `results/<run_id>/<filename>`.
    Invariant: the resolved path never escapes the results directory.
    """
    raise NotImplementedError


def latest_run(stage: str) -> str:
    """Find the most recent run id for a stage.

    Inputs: the stage name.
    Outputs: the newest matching run id, so a stage can read its predecessor.
    Invariant: raises when no run exists, rather than returning an empty string.
    """
    raise NotImplementedError
