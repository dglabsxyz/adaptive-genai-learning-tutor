"""Request runtime for the deep-agent tutor.

Drop-in replacement for the old ``backend.graph.run_tutor_turn`` /
``resume_tutor_turn``: same call signatures and the same response contract
(``learner_id``, ``tenant_id``, ``thread_id``, and either an ``interrupt`` for the
human-in-the-loop gate or a final ``message``), but powered by the deepagents
orchestrator instead of the hand-built graph.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from .agent import build_tutor_agent
from .agent_tools import reset_agent_context, set_agent_context

logger = logging.getLogger("backend.agent_runtime")

# Headroom for plan -> delegate -> subagent loops. The deepagents recursion
# limit is the hard backstop against runaway loops (course concept).
RECURSION_LIMIT = 80

# Shown when a turn exhausts the recursion budget without converging. Kept honest
# and actionable rather than surfacing a raw 500/stack trace to the learner.
RECURSION_FALLBACK_MESSAGE = (
    "I wasn't able to finish working through that this time. Could you narrow it down a little — "
    "for example, name one topic to focus on, or ask for a single exercise — and I'll pick it right "
    "back up?"
)


def _thread_config(learner_id: str, thread_id: str | None, tenant_id: str | None) -> tuple[str, str, dict[str, Any]]:
    tenant = tenant_id or "local"
    base_thread_id = thread_id or learner_id
    graph_thread_id = base_thread_id if tenant == "local" else f"{tenant}:{base_thread_id}"
    return tenant, base_thread_id, {
        "configurable": {"thread_id": graph_thread_id},
        "recursion_limit": RECURSION_LIMIT,
    }


def _text(content: Any) -> str:
    """Normalize an AIMessage content (str or list of content blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content is not None else ""


def _final_message(result: dict[str, Any]) -> str:
    for message in reversed(result.get("messages", []) or []):
        if getattr(message, "type", None) == "ai" and not getattr(message, "tool_calls", None):
            text = _text(getattr(message, "content", ""))
            if text.strip():
                return text
    messages = result.get("messages") or []
    return _text(getattr(messages[-1], "content", "")) if messages else "No tutor response was produced."


def _collect_source_refs(result: dict[str, Any], *, limit: int = 8) -> list[dict[str, Any]]:
    """Best-effort: pull structured source_refs out of the turn's tool messages.

    The tutor tools (search_course_material, next_exercise, grade_answer, …) return
    a ``source_refs`` list in the SourceRef shape. This scans the run's tool messages,
    parses their JSON content, and collects + dedupes those refs so the ``/chat``
    response can populate the structured ``source_refs`` field (the frontend Sources
    view). Refs that only live inside a subagent's private transcript won't surface
    here; the agent still cites them inline in its message text, and the deterministic
    REST endpoints (/exercise, /answer, /study-plan, /sources/search) carry the full set.
    """
    seen: set[str] = set()
    refs: list[dict[str, Any]] = []

    def _ingest(payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        candidates = payload.get("source_refs")
        if not isinstance(candidates, list):
            return
        for ref in candidates:
            if not isinstance(ref, dict):
                continue
            key = ref.get("source_id") or ref.get("path") or ref.get("title")
            if not key or key in seen:
                continue
            seen.add(str(key))
            refs.append(ref)

    for message in result.get("messages", []) or []:
        if getattr(message, "type", None) != "tool":
            continue
        content = getattr(message, "content", None)
        if isinstance(content, str):
            try:
                _ingest(json.loads(content))
            except (ValueError, TypeError):
                continue
        elif isinstance(content, dict):
            _ingest(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    _ingest(block)
                elif isinstance(block, str):
                    try:
                        _ingest(json.loads(block))
                    except (ValueError, TypeError):
                        pass
    return refs[:limit]


def _pending_requests(result: dict[str, Any]) -> list[Any]:
    """Unwrap deepagents HITL interrupts into a flat list of action requests."""
    requests: list[Any] = []
    for interrupt in result.get("__interrupt__", []) or []:
        value = getattr(interrupt, "value", interrupt)
        if isinstance(value, dict) and "action_requests" in value:
            requests.extend(value["action_requests"])
        elif isinstance(value, list):
            requests.extend(value)
        else:
            requests.append(value)
    return requests


def _format(result: dict[str, Any], *, learner_id: str, tenant_id: str, thread_id: str) -> dict[str, Any]:
    requests = _pending_requests(result)
    if requests:
        return {
            "learner_id": learner_id,
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "needs_clarification": True,
            "interrupt": {"action_requests": requests},
        }
    return {
        "learner_id": learner_id,
        "tenant_id": tenant_id,
        "thread_id": thread_id,
        "message": _final_message(result),
        "source_refs": _collect_source_refs(result),
    }


def _invoke(payload: Any, *, learner_id: str, thread_id: str | None, tenant_id: str | None) -> dict[str, Any]:
    tenant, base_thread_id, config = _thread_config(learner_id, thread_id, tenant_id)
    token = set_agent_context(learner_id, tenant)
    try:
        result = build_tutor_agent().invoke(payload, config=config)
    except GraphRecursionError:
        # The agent exhausted its step budget without converging. Degrade gracefully:
        # log it (the LangSmith trace captures the full trajectory) and return a clean,
        # contract-shaped reply instead of a 500/hang.
        logger.warning(
            "tutor turn hit the recursion limit without converging (learner=%s thread=%s tenant=%s)",
            learner_id,
            base_thread_id,
            tenant,
            exc_info=True,
        )
        return {
            "learner_id": learner_id,
            "tenant_id": tenant,
            "thread_id": base_thread_id,
            "message": RECURSION_FALLBACK_MESSAGE,
            "source_refs": [],
        }
    finally:
        reset_agent_context(token)
    return _format(result, learner_id=learner_id, tenant_id=tenant, thread_id=base_thread_id)


def run_tutor_turn(
    learner_id: str,
    message: str,
    thread_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    return _invoke(
        {"messages": [{"role": "user", "content": message}]},
        learner_id=learner_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
    )


def resume_tutor_turn(
    learner_id: str,
    resume: str | dict[str, Any],
    thread_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    return _invoke(
        Command(resume=resume),
        learner_id=learner_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
    )
