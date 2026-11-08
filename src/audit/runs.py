"""Run ids, manifests and results paths. Scripts never write a manifest by hand."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

from audit.schema import RunManifest

RESULTS_DIR = Path("results")
MANIFEST_NAME = "manifest.json"


def make_run_id(stage: str, config_path: Path) -> str:
    """Build a run id.

    Inputs: the stage name and the path of the config being used.
    Outputs: `YYYYMMDD-HHMM-<stage>-<slug>`, where the slug is the config file stem.
    Invariant: the id encodes when the run started, so ids sort chronologically.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"{stamp}-{stage}-{Path(config_path).stem}"


def create_run_dir(run_id: str) -> Path:
    """Create the results directory for a run.

    Inputs: the run id.
    Outputs: the path `results/<run_id>/`.
    Invariant: results are append-only. This raises if the directory already
    exists, rather than overwriting it.
    """
    run_dir = RESULTS_DIR / run_id
    # This is the append-only guarantee. Ids have minute resolution, so two runs
    # of one stage and config inside the same minute collide here rather than
    # one clobbering the other.
    if run_dir.exists():
        raise FileExistsError(
            f"{run_dir} already exists. Results are append-only and run ids have "
            "minute resolution: wait a minute and start again."
        )
    run_dir.mkdir(parents=True)
    return run_dir


def load_config(config_path: Path) -> dict:
    """Load a YAML config.

    Inputs: the path to a file in `configs/`.
    Outputs: the config as a dict, exactly as parsed.
    Invariant: no defaults are filled in here, so the manifest records what the
    file actually said.
    """
    with open(config_path, encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ValueError(f"{config_path} did not parse to a mapping")
    return config


def git_commit() -> str:
    """Current HEAD hash, or "unknown" when not inside a git checkout."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_manifest(
    run_dir: Path, stage: str, config: dict, models: dict[str, dict]
) -> RunManifest:
    """Write `manifest.json` for a run.

    Inputs: the run directory, the stage name, the config as loaded, and the
    model roles as loaded from `configs/models.yaml`.
    Outputs: the RunManifest that was written. It carries run id, stage, git
    commit hash, config, models and start time. `end_time`, `n_model_calls`
    and `estimated_cost_usd` are filled in by `finish_manifest`.
    Invariant: this module is the only writer of `manifest.json`. Writing the
    start manifest first means a crashed run still leaves a record of what it
    was trying to do.
    """
    manifest = RunManifest(
        run_id=run_dir.name,
        stage=stage,
        git_commit=git_commit(),
        config=config,
        models=models,
        start_time=datetime.now(),
    )
    _write(run_dir, manifest)
    return manifest


def finish_manifest(
    run_dir: Path, n_model_calls: int, estimated_cost_usd: float
) -> RunManifest:
    """Close a run's manifest with its end time, call count and cost.

    Inputs: the run directory, the number of model calls the run made, and the
    estimated cost in USD. Stages 02 onwards take both from `cache.cache_stats`.
    Stage 01 cannot, because Inspect drives the agent, so it counts assistant
    messages in the harness logs instead.
    Outputs: the updated RunManifest.
    """
    manifest = read_manifest(run_dir)
    manifest.end_time = datetime.now()
    manifest.n_model_calls = n_model_calls
    manifest.estimated_cost_usd = estimated_cost_usd
    _write(run_dir, manifest)
    return manifest


def read_manifest(run_dir: Path) -> RunManifest:
    """Read and validate a run's manifest."""
    return RunManifest.model_validate_json(
        (run_dir / MANIFEST_NAME).read_text(encoding="utf-8")
    )


def results_path(run_id: str, filename: str) -> Path:
    """Resolve a file inside a run's results directory.

    Inputs: the run id and a file name.
    Outputs: `results/<run_id>/<filename>`.
    Invariant: the resolved path never escapes the results directory.
    """
    base = (RESULTS_DIR / run_id).resolve()
    path = (base / filename).resolve()
    if base != path and base not in path.parents:
        raise ValueError(f"{filename!r} escapes {base}")
    return path


def latest_run(stage: str) -> str:
    """Find the most recent run id for a stage.

    Inputs: the stage name.
    Outputs: the newest matching run id, so a stage can read its predecessor.
    Invariant: raises when no run exists, rather than returning an empty string.
    """
    marker = f"-{stage}-"
    candidates = sorted(
        p.name
        for p in RESULTS_DIR.iterdir()
        if p.is_dir() and marker in p.name and (p / MANIFEST_NAME).exists()
    ) if RESULTS_DIR.exists() else []
    if not candidates:
        raise FileNotFoundError(f"no run for stage {stage!r} under {RESULTS_DIR}")
    # Ids start with YYYYMMDD-HHMM, so lexical order is chronological order.
    return candidates[-1]


def _write(run_dir: Path, manifest: RunManifest) -> None:
    (run_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
