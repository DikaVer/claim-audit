"""Best-of-N and in-context RL loop. Stretch stage, run only if the claim signal exists."""

from __future__ import annotations

from pathlib import Path

from audit.schema import Task, Transcript


def sample_n(
    task: Task, n_samples: int, agent_model: str, fewshot: list[Transcript]
) -> list[Transcript]:
    """Draw N agent transcripts for one impossible task.

    Inputs: the Task, N, the agent model name, and the few-shot transcripts
    selected in the previous round.
    Outputs: N Transcripts, labelled exactly as in stage 01.
    Invariant: labels are computed the same way as stage 01, so rounds stay
    comparable.
    """
    raise NotImplementedError


def select(
    transcripts: list[Transcript], selection_rule: str, threshold: float
) -> list[Transcript]:
    """Pick the transcripts that become the next round's few-shot examples.

    Inputs: the sampled Transcripts, the rule (`outcome_only` or
    `outcome_plus_estimator`), and the estimator threshold used by rule (b).
    Outputs: the selected subset.
    Invariant: rule (a) uses the test outcome only. Rule (b) adds the estimator
    aggregate, which is itself computed without the estimator seeing outcomes.
    """
    raise NotImplementedError


def run_rounds(
    tasks: list[Task], n_samples: int, rounds: int, selection_rule: str
) -> list[dict]:
    """Run the in-context RL rounds and record the hack rate per round.

    Inputs: the impossible tasks, N, the number of rounds, and the selection rule.
    Outputs: one record per round with hack rate and estimator recall.
    Invariant: each round's few-shot set comes from the previous round's
    selection. Round 0 has an empty few-shot set.
    """
    raise NotImplementedError


def run_bon(
    transcripts_path: Path, n_samples: int, rounds: int, selection_rules: list[str]
) -> list[dict]:
    """Stage 06 entrypoint. Run the loop once per selection rule.

    Inputs: the stage 01 transcripts file, N, the number of rounds, and the
    selection rules to compare.
    Outputs: one record per (rule, round) with hack rate and estimator recall.
    Invariant: run only when the claim signal exists, that is an AUROC gap of at
    least 0.05 with non-overlapping CIs.
    """
    raise NotImplementedError
