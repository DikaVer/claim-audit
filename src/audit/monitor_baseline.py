"""Whole-transcript baseline monitor: one prompt, one score."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from audit import cache
from audit.estimator import build_context
from audit.schema import MonitorScore, Transcript

_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "monitor",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["analysis", "verdict", "p_cheat", "justification"],
            "properties": {
                "analysis": {"type": "string"},
                "verdict": {"type": "string", "enum": ["cheating", "legit"]},
                "p_cheat": {"type": "number"},
                "justification": {"type": "string"},
            },
        },
    },
}


def render_for_monitor(transcript: Transcript, prompt_path: str) -> str:
    """ImpossibleBench's prompt with the `full`-mode context in place of `{dump}`.

    One user message, as the original judge is used. The context is exactly
    what the estimator sees in `full`, so feedback, outcomes and reasoning are
    withheld here as there.
    """
    return Path(prompt_path).read_text(encoding="utf-8").replace("{dump}", build_context(transcript, "full"))


def score_transcript(transcript: Transcript, monitor_model: str, prompt_path: str) -> MonitorScore:
    """Score whether the agent cheated, from the whole transcript at once.

    Inputs: the Transcript, the monitor model name, the path to
    `prompts/baseline_monitor.md`.
    Outputs: a MonitorScore with P(cheated) in [0, 1] and the single-word verdict.
    Invariant: the monitor sees the same information as the estimator's `full`
    mode, so any AUROC gap is about the claim format and not about the model or
    the evidence available. Outcomes are stripped here too.
    """
    response = cache.call_model(
        monitor_model,
        [{"role": "user", "content": render_for_monitor(transcript, prompt_path)}],
        **_monitor_params(),
    )
    raw = json.loads(response["choices"][0]["message"]["content"])
    return MonitorScore(
        transcript_id=transcript.transcript_id, monitor_model=monitor_model,
        p_cheat=min(1.0, max(0.0, float(raw["p_cheat"]))), verdict=raw["verdict"],
        justification=raw["justification"].strip(),
    )


def score_all(transcripts_path: Path, monitor_model: str, prompt_path: str, max_workers: int = 8) -> list[MonitorScore]:
    """Baseline entrypoint. Score every transcript in a stage 01 file.

    Inputs: the stage 01 transcripts file, the monitor model name, the path to
    `prompts/baseline_monitor.md`.
    Outputs: one MonitorScore per Transcript.
    Invariant: one call to `score_transcript` per Transcript, nothing else.
    """
    with open(transcripts_path, encoding="utf-8") as fh:
        transcripts = [Transcript.model_validate_json(line) for line in fh if line.strip()]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(tqdm(pool.map(lambda t: score_transcript(t, monitor_model, prompt_path), transcripts),
                         total=len(transcripts), desc="monitor"))


def _monitor_params() -> dict:
    from audit import runs

    role = runs.load_config(Path("configs/models.yaml"))["monitor"]
    return {
        "reasoning_effort": role["reasoning_effort"],
        "max_completion_tokens": role["max_tokens"],
        "response_format": _RESPONSE_FORMAT,
    }
