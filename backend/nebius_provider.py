"""Nebius Token Factory (OpenAI-compatible) provider with deterministic fallback.

This is the integration point for Nebius Token Factory models:

- chat / reasoning ............ Llama 3.1 70B Instruct (configurable)
- text embeddings ............. BAAI/bge-en-icl (configurable)

Design goals:

- **Use Nebius first, fall back to local whenever needed.** Every call raises
  ``LLMUnavailable`` instead of crashing the request, so callers can degrade to
  the deterministic engine. ``available()`` lets callers check cheaply.
- **No import-time side effects / no network at import.** The HTTP client and
  settings are read lazily inside calls.
- **No new heavy dependencies.** Uses ``httpx`` (already required) against the
  OpenAI-compatible REST surface rather than the ``openai`` SDK.
- **Secrets stay in env.** The API key is read from settings, never logged.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Sequence

import httpx

from .settings import get_settings


class LLMUnavailable(RuntimeError):
    """Raised when the Nebius provider is disabled, unconfigured, or errored.

    Callers should catch this and fall back to deterministic behavior.
    """


def available() -> bool:
    """True when the Nebius provider is enabled and has an API key."""
    settings = get_settings()
    return settings.llm_provider == "nebius" and bool(settings.nebius_api_key)


def embeddings_available() -> bool:
    """True when a Nebius API key exists (embeddings work independent of llm_provider)."""
    return bool(get_settings().nebius_api_key)


def _headers() -> dict[str, str]:
    key = get_settings().nebius_api_key
    if not key:
        raise LLMUnavailable("NEBIUS_API_KEY is not set")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


@lru_cache(maxsize=1)
def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(base_url=settings.nebius_base_url, timeout=settings.nebius_timeout_seconds)


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = _client().post(path, headers=_headers(), json=payload)
    except httpx.HTTPError as exc:  # network/timeout
        raise LLMUnavailable(f"Nebius request failed: {type(exc).__name__}") from exc
    if response.status_code != 200:
        # Surface a short, non-sensitive reason; never include the API key.
        raise LLMUnavailable(f"Nebius HTTP {response.status_code}: {response.text[:200]}")
    return response.json()


def chat(
    messages: Sequence[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 800,
) -> str:
    """Return assistant text for a chat completion, or raise ``LLMUnavailable``.

    ``messages`` follows the OpenAI chat schema:
    ``[{"role": "system"|"user"|"assistant", "content": "..."}]``.
    """
    if not available():
        raise LLMUnavailable("Nebius provider is not active (set TUTOR_LLM_PROVIDER=nebius + NEBIUS_API_KEY)")
    settings = get_settings()
    payload: dict[str, Any] = {
        "model": model or settings.nebius_llm_model,
        "messages": list(messages),
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }
    data = _post("/chat/completions", payload)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailable("Nebius returned an unexpected chat payload") from exc


def embed(texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
    """Return one embedding vector per input text, or raise ``LLMUnavailable``."""
    if not get_settings().nebius_api_key:
        raise LLMUnavailable("NEBIUS_API_KEY is not set")
    settings = get_settings()
    model_name = model or settings.nebius_embedding_model
    data = _post("/embeddings", {"model": model_name, "input": list(texts)})
    try:
        rows = sorted(data["data"], key=lambda row: row.get("index", 0))
        return [row["embedding"] for row in rows]
    except (KeyError, TypeError) as exc:
        raise LLMUnavailable("Nebius returned an unexpected embeddings payload") from exc


def status() -> dict[str, Any]:
    """Non-secret provider status for health/admin surfaces."""
    settings = get_settings()
    return {
        "provider": "nebius",
        "nebius_key_present": bool(settings.nebius_api_key),
        "active": available(),
        "llm_model": settings.nebius_llm_model,
        "embedding_model": settings.nebius_embedding_model,
        "base_url": settings.nebius_base_url,
    }
