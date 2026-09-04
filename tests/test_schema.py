"""Round-trip serialisation of each pydantic model in `audit.schema`.

`schema.py` is the contract between stages, so a field that does not survive
`model_dump_json` then `model_validate_json` is a broken contract.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from audit.schema import (
    Claim,
    ClaimScore,
    ClaimVerdict,
    RunManifest,
    Task,
    Transcript,
)

MODELS_AND_PAYLOADS = [
    (
        Task,
        {
            "task_id": "t0",
            "variant": "original",
            "prompt": "spec",
            "entry_point": "f",
            "original_tests": "assert f(1) == 1",
            "variant_tests": "assert f(1) == 1",
        },
    ),
    (
        Transcript,
        {
            "transcript_id": "tr0",
            "task_id": "t0",
            "variant": "conflicting",
            "sample_index": 0,
            "messages": [{"id": "m0", "role": "assistant", "content": "done"}],
            "reasoning": [{"message_id": "m0", "text": "I will special-case this."}],
            "final_report": "tests pass",
            "tests_passed": True,
            "in_loop_success": True,
            "check_override_hack": False,
            "label": "hack",
            "hack_method": "record_extra_states",
            "n_messages": 1,
            "n_chars": 9,
        },
    ),
    (
        Claim,
        {
            "claim_id": "c0",
            "transcript_id": "tr0",
            "text": "The tests pass.",
            "type": "tests_pass",
            "depends_on": ["m0"],
            "verifiable": True,
        },
    ),
    (
        ClaimScore,
        {
            "claim_id": "c0",
            "context_mode": "full",
            "estimator_model": "placeholder",
            "p_true": 0.5,
            "justification": "no evidence either way",
        },
    ),
    (
        ClaimVerdict,
        {
            "claim_id": "c0",
            "checker": "check_tests_pass",
            "is_true": False,
            "evidence": "the served tests failed",
        },
    ),
    (
        RunManifest,
        {
            "run_id": "20260904-1410-01_generate-exp01_generate",
            "stage": "01_generate",
            "git_commit": "0" * 40,
            "config": {"n_tasks": 60},
            "models": {"agent": {"deployment": "DeepSeek-V3.2", "reasoning_effort": "medium"}},
            "start_time": datetime(2026, 9, 4, 14, 10),
            "end_time": None,
            "n_model_calls": 0,
            "estimated_cost_usd": 0.0,
        },
    ),
]


@pytest.mark.parametrize(
    "model_cls,payload", MODELS_AND_PAYLOADS, ids=lambda v: getattr(v, "__name__", "")
)
def test_round_trip(model_cls, payload):
    """A model survives a JSON round trip unchanged."""
    original = model_cls(**payload)
    restored = model_cls.model_validate_json(original.model_dump_json())
    assert restored == original
