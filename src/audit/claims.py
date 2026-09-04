"""Extract atomic claims with dependencies from the agent's visible messages."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import get_args

from tqdm import tqdm

from audit import cache, verify
from audit.schema import Claim, ClaimType, Transcript
from audit.transcripts import _CODE_BLOCK

# Structured-output schema for the extractor. `verifiable` is not asked for:
# it is a function of `type` and computed by `is_verifiable`, per the rule that
# labels are computed rather than typed.
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "claims",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["claims"],
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["text", "type", "negated", "depends_on"],
                        "properties": {
                            "text": {"type": "string"},
                            "type": {"type": "string", "enum": list(get_args(ClaimType))},
                            "negated": {"type": "boolean"},
                            "depends_on": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                }
            },
        },
    },
}


def extract_claims(transcript: Transcript, extractor_model: str, prompt_path: str) -> list[Claim]:
    """Extract every atomic claim the agent made in one transcript.

    Inputs: the Transcript, the extractor model name, the path to
    `prompts/claim_extraction.md`.
    Outputs: one Claim per atomic assertion, with `type`, `depends_on` and
    `verifiable` filled in.
    Invariant: the extractor states what was claimed, never whether it is true.
    Every id in `depends_on` must exist in `transcript.messages`.
    """
    # No prose, no claims. Decided in code rather than left to the prompt:
    # given a code-only final message the extractor fell back to an earlier
    # attempt and reported its claims, which stage 04 would then verify
    # against the final outcome.
    if not transcript.final_report:
        return []
    params = _extractor_params()
    response = cache.call_model(
        extractor_model,
        [
            {"role": "system", "content": Path(prompt_path).read_text(encoding="utf-8")},
            {"role": "user", "content": render_for_extractor(transcript)},
        ],
        **params,
    )
    raw = json.loads(response["choices"][0]["message"]["content"])["claims"]
    known_ids = {m["id"] for m in transcript.messages} | {
        tc["id"] for m in transcript.messages for tc in m.get("tool_calls", [])
    }
    claims: list[Claim] = []
    for k, c in enumerate(raw):
        text = c["text"].strip()
        if not text:
            continue
        claims.append(
            Claim(
                claim_id=f"{transcript.transcript_id}-c{k}",
                transcript_id=transcript.transcript_id,
                text=text,
                type=c["type"],
                negated=c["negated"],
                # An id the model invented is dropped rather than failing the
                # transcript. Stage 05 reads "fraction with empty depends_on"
                # as a feature, so dropping is visible there.
                depends_on=[d for d in c["depends_on"] if d in known_ids],
                verifiable=is_verifiable(c["type"]),
            )
        )
    return claims


def is_verifiable(claim_type: str) -> bool:
    """Say whether a ground-truth checker exists for this claim type.

    Inputs: a ClaimType value.
    Outputs: True for every type `verify.py` has a checker for, False for `other`.
    Invariant: agrees with the checkers registered in `verify.py`.
    """
    return hasattr(verify, f"check_{claim_type}")


def extract_all(
    transcripts_path: Path, extractor_model: str, prompt_path: str, max_workers: int = 8
) -> list[Claim]:
    """Stage 02 entrypoint. Extract claims for every transcript in a stage 01 file.

    Inputs: the path to stage 01's `transcripts.jsonl`, the extractor model
    name, the path to `prompts/claim_extraction.md`.
    Outputs: every Claim from every Transcript, in transcript order.
    Invariant: one call to `extract_claims` per Transcript, nothing else.
    """
    transcripts = load_transcripts(transcripts_path)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        per_transcript = list(
            tqdm(
                pool.map(lambda t: extract_claims(t, extractor_model, prompt_path), transcripts),
                total=len(transcripts), desc="extract",
            )
        )
    return [c for claims in per_transcript for c in claims]


def load_transcripts(path: Path) -> list[Transcript]:
    with open(path, encoding="utf-8") as fh:
        return [Transcript.model_validate_json(line) for line in fh if line.strip()]


def render_for_extractor(transcript: Transcript) -> str:
    """The agent's final message as the extractor sees it.

    Only the final assistant message is shown, tagged with its id so
    `depends_on` can point at it. Earlier attempts are withheld: told to use
    them as context only, the extractor still lifted claims from them, and a
    superseded "all tests pass" would then be verified against the final
    outcome. The harness's feedback messages carry test output, which is an
    outcome, and the task prompt carries the served test file. Neither is a
    claim the agent made, and both would give the extractor a route to the
    label that has nothing to do with claims. Code blocks are replaced by a
    marker for the same reason: the code is what the agent did, the prose is
    what it claimed.
    """
    final = [m for m in transcript.messages if m["role"] == "assistant"][-1]
    body = _CODE_BLOCK.sub("[code block omitted]", final["content"])
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    parts = [f"[{final['id']}] assistant (final report):\n{body}"]
    for tc in final.get("tool_calls", []):
        parts.append(f"[{tc['id']}] tool call from {final['id']}: {tc['function']}({json.dumps(tc['arguments'])})")
    return "\n\n".join(parts)


def _extractor_params() -> dict:
    """Sampling parameters for the extractor role, read from `configs/models.yaml`."""
    from audit import runs

    role = runs.load_config(Path("configs/models.yaml"))["extractor"]
    return {
        "temperature": role["temperature"],
        "max_tokens": role["max_tokens"],
        "response_format": _RESPONSE_FORMAT,
    }
