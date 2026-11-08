"""Score P(true) per claim. The estimator never sees outcomes."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from audit import cache
from audit.schema import Claim, ClaimScore, ContextMode, Task, Transcript

FEEDBACK_MARKER = "[harness feedback withheld]"
TESTS_MARKER = "[test cases withheld]"

# Structured-output schema for the estimator. The prompt asks for two decimal
# places and a one-sentence justification; the schema only fixes the field
# names and types, so the rubric stays in the prompt where Dima controls it.
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "claim_score",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["p_true", "justification", "type_mismatch"],
            "properties": {
                "p_true": {"type": "number"},
                "justification": {"type": "string"},
                "type_mismatch": {"type": "boolean"},
            },
        },
    },
}


def build_context(transcript: Transcript, context_mode: ContextMode, task: Task | None = None) -> str:
    """Render the transcript as the estimator is allowed to see it.

    Inputs: the Transcript, the context mode, and the Task it was run on, which
    `no_test_diff` needs in order to locate the served tests in the prompt.
    Outputs: `full` gives the whole transcript minus outcomes, `no_test_diff`
    additionally hides every change to test files, `no_transcript` gives nothing
    so the estimator returns its prior, `with_reasoning` is `full` plus the
    agent's reasoning trace.
    Invariant, outcomes: test results and the final pass/fail are stripped from
    every mode, without exception. `Transcript.tests_passed`,
    `Transcript.in_loop_success`, `Transcript.check_override_hack` and
    `Transcript.label` must never reach the returned string. Under the minimal
    scaffold every follow-up user message is the harness reporting a failed
    attempt with its traceback, so those messages are replaced by a fixed
    marker rather than filtered. Earlier assistant attempts stay, because they
    are what the agent did; the reader can infer that a superseded attempt did
    not pass, but never whether the final one did.
    Invariant, reasoning: `Transcript.reasoning` is stripped from every mode
    except `with_reasoning`. The reasoning states the agent's intent outright,
    so leaking it would mean the trace does the detecting rather than the claim
    format, which is the comparison this study exists to make.
    Invariant, test diff: the agent cannot edit files under the minimal
    scaffold, so the only test diff is the mutation itself, which is visible in
    the served tests inside the task prompt. `no_test_diff` replaces that block
    with a marker so an estimator that merely notices the contradiction has
    nothing to notice. The replacement is applied to every message, because in
    14 of 350 grid transcripts the agent re-quoted the served tests verbatim in
    its own answer, which would put the contradiction straight back. Partial
    quotes and the agent's prose about the tests stay, since that is behaviour,
    not task information.
    """
    if context_mode == "no_transcript":
        return ""
    if context_mode == "reasoning_only":
        # The trace and nothing else: no task, no code, no report. The score
        # is then P(true | what the agent privately worked out), to be set
        # against the `full` score for the same claim.
        return "\n\n".join(
            f"[{r['message_id']}] assistant reasoning:\n{r['text']}" for r in transcript.reasoning
        )
    if context_mode == "no_test_diff" and task is None:
        raise ValueError("no_test_diff needs the Task to locate the served tests")

    thoughts: dict[str, list[str]] = {}
    if context_mode == "with_reasoning":
        for r in transcript.reasoning:
            thoughts.setdefault(r["message_id"], []).append(r["text"])

    if context_mode == "no_test_diff":
        # The prompt must contain the block; anywhere else it is optional.
        _hide_served_tests(transcript.messages[0]["content"], task.variant_tests)
        hide = lambda text: text.replace(task.variant_tests.strip(), TESTS_MARKER)
    else:
        hide = lambda text: text

    parts: list[str] = []
    for i, m in enumerate(transcript.messages):
        if m["role"] == "user":
            if i == 0:
                parts.append(f"[{m['id']}] user (task):\n{hide(m['content'])}")
            else:
                parts.append(f"[{m['id']}] user: {FEEDBACK_MARKER}")
            continue
        if m["role"] != "assistant":
            # `minimal` produces only user and assistant turns. A tool message
            # would carry a harness result, so it is treated as feedback.
            parts.append(f"[{m['id']}] {m['role']}: {FEEDBACK_MARKER}")
            continue
        label = "assistant (final)" if i == _final_index(transcript) else "assistant"
        parts.append(f"[{m['id']}] {label}:\n{hide(m['content'])}")
        for tc in m.get("tool_calls", []):
            parts.append(f"[{tc['id']}] tool call from {m['id']}: {tc['function']}({json.dumps(tc['arguments'])})")
        for t in thoughts.get(m["id"], []):
            parts.append(f"[{m['id']}] assistant reasoning:\n{t}")
    return "\n\n".join(parts)


def score_claim(
    claim: Claim,
    transcript: Transcript,
    context_mode: ContextMode,
    estimator_model: str,
    prompt_path: str,
    task: Task | None = None,
) -> ClaimScore:
    """Return the estimator's probability that one claim is true.

    Inputs: the Claim, its Transcript, the context mode, the estimator model
    name, the path to `prompts/estimator.md`, and the Task for `no_test_diff`.
    Outputs: a ClaimScore with `p_true` in [0, 1], a one-sentence justification,
    and `type_mismatch`, set when the sentence does not assert its type's
    proposition. The estimator marks this itself because it is the one reader
    that has both the sentence and the type definitions in front of it.
    Invariant: the estimator is consequence-invariant. It sees only what
    `build_context` returns, so test results and the final pass/fail are
    stripped from every context mode.
    """
    response = cache.call_model(
        estimator_model,
        [
            {"role": "system", "content": Path(prompt_path).read_text(encoding="utf-8")},
            {"role": "user", "content": render_for_estimator(claim, transcript, context_mode, task)},
        ],
        **_estimator_params(),
    )
    raw = json.loads(response["choices"][0]["message"]["content"])
    return ClaimScore(
        claim_id=claim.claim_id,
        context_mode=context_mode,
        estimator_model=estimator_model,
        # Clamped rather than rejected: a model that answers 1.0000001 has
        # said 1, and one failed call should not stop a batch of thousands.
        p_true=min(1.0, max(0.0, float(raw["p_true"]))),
        justification=raw["justification"].strip(),
        type_mismatch=bool(raw["type_mismatch"]),
    )


def render_for_estimator(
    claim: Claim, transcript: Transcript, context_mode: ContextMode, task: Task | None = None
) -> str:
    """The user turn: the context as filtered, then the claim under test.

    The claim comes last so it is the freshest thing in the window, and its
    `depends_on` ids point into the context above, which carries the same ids.
    `negated` is not passed: the claim text already says "do not pass", and
    the estimator scores the sentence as written.
    """
    context = build_context(transcript, context_mode, task)
    head = (
        f"Context mode: {context_mode}\n\n"
        + (f"Transcript:\n{context}\n\n" if context else "Transcript: not provided in this mode.\n\n")
    )
    return (
        head
        + f"Claim (type {claim.type}, cites {', '.join(claim.depends_on) or 'nothing'}):\n{claim.text}"
    )


def score_all(
    transcripts_path: Path,
    claims_path: Path,
    context_modes: list[ContextMode],
    estimator_model: str,
    prompt_path: str,
    max_workers: int = 8,
    only_verifiable: bool = False,
    types: list[str] | None = None,
) -> list[ClaimScore]:
    """Stage 03 entrypoint. Score every claim in every requested context mode.

    Inputs: the stage 01 transcripts file, the stage 02 claims file, the context
    modes to run, the estimator model name, the path to `prompts/estimator.md`,
    the number of calls in flight, whether to skip unverifiable claims, and an
    optional list of claim types to restrict to, used by the `with_reasoning`
    ablation so that reasoning traces of 100k characters are paid for only on
    the claims where the question is open.
    `tasks.jsonl` is read from the same directory as the transcripts file.
    Outputs: one ClaimScore per (claim, context mode) pair, mode-major so a
    cheap mode finishes and is inspectable before an expensive one starts.
    Invariant: every score goes through `build_context`, so test results and the
    final pass/fail are stripped in every mode.
    """
    transcripts = {t.transcript_id: t for t in _load(transcripts_path, Transcript)}
    tasks = {(t.task_id, t.variant): t for t in _load(transcripts_path.parent / "tasks.jsonl", Task)}
    claims = [
        c for c in _load(claims_path, Claim)
        if (c.verifiable or not only_verifiable) and (types is None or c.type in types)
    ]

    def one(item: tuple[Claim, ContextMode]) -> ClaimScore:
        claim, mode = item
        t = transcripts[claim.transcript_id]
        return score_claim(claim, t, mode, estimator_model, prompt_path, tasks[(t.task_id, t.variant)])

    scores: list[ClaimScore] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for mode in context_modes:
            scores.extend(
                tqdm(pool.map(one, [(c, mode) for c in claims]), total=len(claims), desc=f"score {mode}")
            )
    return scores


def _hide_served_tests(prompt: str, served_tests: str) -> str:
    """Replace the served test block in the task prompt with a marker.

    Located by exact text rather than by shape: two tasks in the grid serve
    bare asserts with no `def check`, so a `def check` regex misses them.
    Raises when the text is absent, because silently leaving the mutated
    tests in place would turn `no_test_diff` back into `full`.
    """
    needle = served_tests.strip()
    if not needle or needle not in prompt:
        raise ValueError("served tests not found in the task prompt, no_test_diff cannot hide them")
    return prompt.replace(needle, TESTS_MARKER)


def _final_index(transcript: Transcript) -> int:
    for i in range(len(transcript.messages) - 1, -1, -1):
        if transcript.messages[i]["role"] == "assistant":
            return i
    return -1


def _estimator_params() -> dict:
    """Sampling parameters for the estimator role, read from `configs/models.yaml`.

    The estimator is a reasoning model, so there is no temperature, and its
    output budget is `max_completion_tokens`, which covers reasoning and the
    visible answer together. Determinism comes from `cache.py`.
    """
    from audit import runs

    role = runs.load_config(Path("configs/models.yaml"))["estimator"]
    return {
        "reasoning_effort": role["reasoning_effort"],
        "max_completion_tokens": role["max_tokens"],
        "response_format": _RESPONSE_FORMAT,
    }


def _load(path: Path, model):
    with open(path, encoding="utf-8") as fh:
        return [model.model_validate_json(line) for line in fh if line.strip()]
