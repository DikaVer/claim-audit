"""Disk cache for model calls. No script may call the OpenAI client directly."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

CACHE_DIR = Path(".cache")

# USD per one million tokens, (input, output). Azure OpenAI list prices.
# A deployment missing here is called and cached as normal, but its tokens are
# reported as unpriced rather than silently costed at zero.
PRICES_PER_M = {
    "gpt-4o": (2.50, 10.00),
    # List price. On promotion at (4.00, 20.00) until 30 November 2026, so the
    # manifest overstates the bill by a quarter to a third until then. Cached
    # input tokens are not discounted here either. Both errors are upward.
    "gpt-5.6-sol": (5.00, 30.00),
    # [CHECK: gpt-5.5 and gpt-5 Azure prices, only if the fallback ladder is used]
}

_lock = threading.Lock()
_stats = {"hits": 0, "misses": 0, "input_tokens": 0, "output_tokens": 0, "unpriced_tokens": 0, "cost_usd": 0.0}
_client = None


def cache_key(model: str, params: dict, messages: list[dict]) -> str:
    """Compute the cache key for one model call.

    Inputs: the model name, the sampling parameters, the message list.
    Outputs: a sha256 hex digest over a canonical, key-sorted serialisation.
    Invariant: logically identical calls give the same key regardless of dict
    ordering.
    """
    payload = json.dumps(
        {"model": model, "params": params, "messages": messages},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def call_model(model: str, messages: list[dict], **params) -> dict:
    """Make one cached model call.

    Inputs: the model name, the messages, the sampling parameters.
    Outputs: the raw API response dict, read from `.cache/` on a hit and from
    the API on a miss.
    Invariant: this is the only place in the repository that talks to the
    OpenAI client. Every hit and miss is counted, so `runs.py` can report
    `n_model_calls` and `estimated_cost_usd`.
    """
    key = cache_key(model, params, messages)
    path = CACHE_DIR / key[:2] / f"{key}.json"
    if path.exists():
        response = json.loads(path.read_text(encoding="utf-8"))
        _record(model, response, hit=True)
        return response

    response = _client_instance().chat.completions.create(
        model=model, messages=messages, **params
    ).model_dump(mode="json")
    # Written to a sibling then renamed, so a crash mid-write cannot leave a
    # truncated file that a later run would read as a hit.
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    _record(model, response, hit=False)
    return response


def cache_stats() -> dict:
    """Report the calls made since process start.

    Inputs: none.
    Outputs: hits, misses, total tokens and estimated cost in USD.
    Invariant: counts cover this process only, so a manifest describes one run.
    """
    with _lock:
        return dict(_stats)


def _record(model: str, response: dict, hit: bool) -> None:
    usage = response.get("usage") or {}
    n_in = usage.get("prompt_tokens") or 0
    n_out = usage.get("completion_tokens") or 0
    price = PRICES_PER_M.get(model)
    with _lock:
        _stats["hits" if hit else "misses"] += 1
        _stats["input_tokens"] += n_in
        _stats["output_tokens"] += n_out
        # Cost is counted on hits too: the manifest states what a run would
        # have cost, so a cached re-run is not mistaken for a free stage.
        if price is None:
            _stats["unpriced_tokens"] += n_in + n_out
        else:
            _stats["cost_usd"] += (n_in * price[0] + n_out * price[1]) / 1e6


def _client_instance():
    global _client
    # Under the lock: extract_all fans out over threads, and two of them
    # arriving here together must not build two clients.
    with _lock:
        if _client is not None:
            return _client
        from openai import AzureOpenAI

        _load_dotenv()
        _client = AzureOpenAI(
            api_key=os.environ["AZUREAI_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZUREAI_OPENAI_BASE_URL"],
            api_version=os.environ["AZUREAI_OPENAI_API_VERSION"],
            max_retries=5,
        )
        return _client


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Read KEY=VALUE lines from `.env` into the environment, never overriding.

    Inspect loads `.env` on its own for stage 01. The other stages call the
    client directly and python-dotenv is not a declared dependency, so this
    does the same job with the standard library.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
