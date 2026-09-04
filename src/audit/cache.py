"""Disk cache for model calls. No script may call the OpenAI client directly."""

from __future__ import annotations

from pathlib import Path

CACHE_DIR = Path(".cache")


def cache_key(model: str, params: dict, messages: list[dict]) -> str:
    """Compute the cache key for one model call.

    Inputs: the model name, the sampling parameters, the message list.
    Outputs: a sha256 hex digest over a canonical, key-sorted serialisation.
    Invariant: logically identical calls give the same key regardless of dict
    ordering.
    """
    raise NotImplementedError


def call_model(model: str, messages: list[dict], **params) -> dict:
    """Make one cached model call.

    Inputs: the model name, the messages, the sampling parameters.
    Outputs: the raw API response dict, read from `.cache/` on a hit and from
    the API on a miss.
    Invariant: this is the only place in the repository that talks to the
    OpenAI client. Every hit and miss is counted, so `runs.py` can report
    `n_model_calls` and `estimated_cost_usd`.
    """
    raise NotImplementedError


def cache_stats() -> dict:
    """Report the calls made since process start.

    Inputs: none.
    Outputs: hits, misses, total tokens and estimated cost in USD.
    Invariant: counts cover this process only, so a manifest describes one run.
    """
    raise NotImplementedError
