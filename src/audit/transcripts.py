"""Load ImpossibleBench logs, normalise them to Transcript, assign the hack label."""

from __future__ import annotations

from pathlib import Path

from audit.schema import HackLabel, Task, Transcript, Variant


def load_tasks(dataset: str, n_tasks: int, variants: list[Variant], seed: int) -> list[Task]:
    """Load ImpossibleBench tasks.

    Inputs: the HF dataset id, how many tasks to sample, which variants to
    include, and the sampling seed. There is no separate `split` argument: on
    this dataset the split name and the variant name are the same thing.
    Outputs: one Task per (sampled task, variant) pair.
    Invariant: the same seed returns the same task ids in the same order. Note
    the harness cannot honour this on its own, because its `shuffle` hardcodes
    seed 42 and its `limit` slices afterwards. Sample here, then pass the
    chosen ids down.
    """
    raise NotImplementedError


def load_harness_logs(log_dir: Path) -> list[dict]:
    """Read the raw agent logs the harness wrote.

    Inputs: the directory the harness wrote its logs to.
    Outputs: one raw log dict per agent run, unmodified.
    Invariant: this function does not interpret or relabel anything.
    """
    raise NotImplementedError


def normalise(raw_log: dict, task: Task) -> Transcript:
    """Convert one raw harness log into a Transcript.

    Inputs: one raw log dict and the Task it was run on.
    Outputs: a Transcript with stable ids on every message and tool call, so
    that Claim.depends_on can reference them.
    Invariant: the label is computed by `assign_hack_label`, not copied from the log.
    """
    raise NotImplementedError


def assign_hack_label(variant: Variant, tests_passed: bool) -> HackLabel:
    """Compute the hack label from task variant plus test outcome.

    Inputs: the task variant and whether the served tests passed.
    Outputs: one of honest_success, honest_fail, hack, honest_under_conflict.
    Invariant: labels are computed, never hand typed. A pass on an impossible
    variant is a hack by construction.
    """
    raise NotImplementedError
