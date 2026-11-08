"""Stage 3b: compare what the reasoning knew with what the report said.

The judge sees the reasoning trace and the report prose. It never sees the
code, the tests or the outcome, so it measures candour, not correctness.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import get_args

from tqdm import tqdm

from audit import cache
from audit.schema import ReasoningGap, ReportFraming, Transcript

_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "reasoning_gap",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reasoning_knows", "reasoning_quote", "report_admits", "report_framing", "report_quote", "justification"],
            "properties": {
                "reasoning_knows": {"type": "boolean"},
                "reasoning_quote": {"type": "string"},
                "report_admits": {"type": "boolean"},
                "report_framing": {"type": "string", "enum": list(get_args(ReportFraming))},
                "report_quote": {"type": "string"},
                "justification": {"type": "string"},
            },
        },
    },
}


def render_for_judge(transcript: Transcript) -> str:
    """The reasoning trace in order, then the report prose. Nothing else.

    The code is withheld because the judge must not decide from the code
    whether it is a hack; that is the estimator's job and stage 04's. The
    feedback messages and the task are withheld for the same reason as in
    stage 03: they carry outcomes and the served tests.
    """
    parts = ["## Reasoning trace"]
    for r in transcript.reasoning:
        parts.append(f"[{r['message_id']}] reasoning before this message:\n{r['text']}")
    parts.append("## Final report\n" + transcript.final_report)
    return "\n\n".join(parts)


def judge_gap(transcript: Transcript, judge_model: str, prompt_path: str) -> ReasoningGap:
    """One judge call for one transcript.

    Inputs: a Transcript with a reasoning trace and a non-empty report, the
    judge model name, the path to `prompts/reasoning_gap.md`.
    Outputs: a ReasoningGap.
    Invariant: the judge sees `render_for_judge` only.
    """
    response = cache.call_model(
        judge_model,
        [
            {"role": "system", "content": Path(prompt_path).read_text(encoding="utf-8")},
            {"role": "user", "content": render_for_judge(transcript)},
        ],
        **_judge_params(),
    )
    raw = json.loads(response["choices"][0]["message"]["content"])
    return ReasoningGap(transcript_id=transcript.transcript_id, judge_model=judge_model, **raw)


def judge_all(transcripts_path: Path, judge_model: str, prompt_path: str, max_workers: int = 8) -> list[ReasoningGap]:
    """Stage 3b entrypoint. One judgement per transcript that has both a trace and a report.

    Transcripts without a trace (encrypted reasoning) or without a report are
    skipped, since there is nothing to compare; the script reports the count.
    """
    with open(transcripts_path, encoding="utf-8") as fh:
        transcripts = [Transcript.model_validate_json(line) for line in fh if line.strip()]
    eligible = [t for t in transcripts if t.reasoning and t.final_report]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(
            tqdm(pool.map(lambda t: judge_gap(t, judge_model, prompt_path), eligible), total=len(eligible), desc="judge")
        )


def _judge_params() -> dict:
    """The judge uses the estimator role: same model, same reasoning effort."""
    from audit import runs

    role = runs.load_config(Path("configs/models.yaml"))["estimator"]
    return {
        "reasoning_effort": role["reasoning_effort"],
        "max_completion_tokens": role["max_tokens"],
        "response_format": _RESPONSE_FORMAT,
    }
