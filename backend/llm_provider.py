"""Qwen (DashScope OpenAI-compatible) provider with deterministic fallback.

This is the single integration point for the Qwen 3.7 family of models:

- chat / reasoning ............ ``qwen3.7-plus`` (configurable)
- text embeddings ............. ``text-embedding-v4`` (Qwen3 embedding)
- vision (image understanding)  ``qwen3-vl-plus``

Design goals:

- **Use Qwen first, fall back to local whenever needed.** Every call raises
  ``LLMUnavailable`` instead of crashing the request, so callers can degrade to
  the deterministic engine. ``available()`` lets callers check cheaply.
- **No import-time side effects / no network at import.** The HTTP client and
  settings are read lazily inside calls.
- **No new heavy dependencies.** Uses ``httpx`` (already required) against the
  OpenAI-compatible REST surface rather than the ``openai`` SDK.
- **Secrets stay in env.** The API key is read from settings, never logged.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Any, Sequence

import httpx

from .settings import get_settings


class LLMUnavailable(RuntimeError):
    """Raised when the Qwen provider is disabled, unconfigured, or errored.

    Callers should catch this and fall back to deterministic behavior.
    """


def available() -> bool:
    """True when the Qwen provider is enabled and has an API key."""
    settings = get_settings()
    return settings.llm_provider == "qwen" and bool(settings.qwen_api_key)


def embeddings_available() -> bool:
    """True when a Qwen API key exists (embeddings work independent of llm_provider)."""
    return bool(get_settings().qwen_api_key)


def _headers() -> dict[str, str]:
    key = get_settings().qwen_api_key
    if not key:
        raise LLMUnavailable("QWEN_API_KEY is not set")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


@lru_cache(maxsize=1)
def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(base_url=settings.qwen_base_url, timeout=settings.qwen_timeout_seconds)


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = _client().post(path, headers=_headers(), json=payload)
    except httpx.HTTPError as exc:  # network/timeout
        raise LLMUnavailable(f"Qwen request failed: {type(exc).__name__}") from exc
    if response.status_code != 200:
        # Surface a short, non-sensitive reason; never include the API key.
        raise LLMUnavailable(f"Qwen HTTP {response.status_code}: {response.text[:200]}")
    return response.json()


def chat(
    messages: Sequence[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 800,
    enable_thinking: bool | None = None,
) -> str:
    """Return assistant text for a chat completion, or raise ``LLMUnavailable``.

    ``messages`` follows the OpenAI chat schema:
    ``[{"role": "system"|"user"|"assistant", "content": "..."}]``.
    """
    if not available():
        raise LLMUnavailable("Qwen provider is not active (set TUTOR_LLM_PROVIDER=qwen + QWEN_API_KEY)")
    settings = get_settings()
    payload: dict[str, Any] = {
        "model": model or settings.qwen_llm_model,
        "messages": list(messages),
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }
    # Some Qwen3 "thinking" models reject non-streaming calls unless thinking is
    # explicitly disabled. Default to off for deterministic, parseable output.
    payload["enable_thinking"] = False if enable_thinking is None else enable_thinking
    try:
        data = _post("/chat/completions", payload)
    except LLMUnavailable as exc:
        # Retry once without the non-standard field if the endpoint rejected it.
        if "enable_thinking" in str(exc):
            payload.pop("enable_thinking", None)
            data = _post("/chat/completions", payload)
        else:
            raise
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailable("Qwen returned an unexpected chat payload") from exc


def embed(texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
    """Return one embedding vector per input text, or raise ``LLMUnavailable``."""
    if not get_settings().qwen_api_key:
        raise LLMUnavailable("QWEN_API_KEY is not set")
    settings = get_settings()
    model_name = model or settings.qwen_embedding_model
    out: list[list[float]] = []
    batch = max(1, settings.qwen_embedding_batch)
    items = list(texts)
    for start in range(0, len(items), batch):
        chunk = items[start : start + batch]
        data = _post("/embeddings", {"model": model_name, "input": chunk})
        try:
            rows = sorted(data["data"], key=lambda row: row.get("index", 0))
            out.extend(row["embedding"] for row in rows)
        except (KeyError, TypeError) as exc:
            raise LLMUnavailable("Qwen returned an unexpected embeddings payload") from exc
    return out


def vision(prompt: str, image_png: bytes, *, model: str | None = None, max_tokens: int = 700) -> str:
    """Ask a Qwen vision model about a PNG image. Returns text or raises.

    Used to verify that text rendered into an infographic is legible/correct.
    """
    if not get_settings().qwen_api_key:
        raise LLMUnavailable("QWEN_API_KEY is not set")
    settings = get_settings()
    data_url = "data:image/png;base64," + base64.b64encode(image_png).decode("ascii")
    payload = {
        "model": model or settings.qwen_vl_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    data = _post("/chat/completions", payload)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailable("Qwen VL returned an unexpected payload") from exc


def status() -> dict[str, Any]:
    """Non-secret provider status for health/admin surfaces."""
    settings = get_settings()
    return {
        "provider": settings.llm_provider,
        "qwen_key_present": bool(settings.qwen_api_key),
        "active": available(),
        "llm_model": settings.qwen_llm_model,
        "embedding_model": settings.qwen_embedding_model,
        "vl_model": settings.qwen_vl_model,
        "base_url": settings.qwen_base_url,
    }
