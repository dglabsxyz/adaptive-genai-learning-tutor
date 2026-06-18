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
from .agent_tools import (
    collected_source_refs,
    reset_agent_context,
    reset_source_sink,
    set_agent_context,
    set_source_sink,
)

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

    # Seed from the request-scoped sink first — captures source_refs from subagent
    # tool calls that never appear in the orchestrator's own message list.
    _ingest({"source_refs": collected_source_refs()})

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


def _unwrap_interrupts(result: dict[str, Any]) -> tuple[str | None, list[Any]]:
    """Split deepagents interrupts into (clarification_question, action_requests).

    Two interrupt shapes exist: the HITL approval gate (``commit_progress``) carries
    ``action_requests``; the missing-info ``request_clarification`` tool carries
    ``{"type": "clarification", "question": ...}``.
    """
    clarification: str | None = None
    requests: list[Any] = []
    for itp in result.get("__interrupt__", []) or []:
        value = getattr(itp, "value", itp)
        if isinstance(value, dict) and value.get("type") == "clarification":
            clarification = value.get("question") or value.get("message")
        elif isinstance(value, dict) and "action_requests" in value:
            requests.extend(value["action_requests"])
        elif isinstance(value, dict) and "question" in value:
            clarification = value.get("question")
        elif isinstance(value, list):
            requests.extend(value)
        else:
            requests.append(value)
    return clarification, requests


def _format(result: dict[str, Any], *, learner_id: str, tenant_id: str, thread_id: str) -> dict[str, Any]:
    clarification, requests = _unwrap_interrupts(result)
    base = {"learner_id": learner_id, "tenant_id": tenant_id, "thread_id": thread_id}
    if clarification:
        return {
            **base,
            "needs_clarification": True,
            "interrupt": {"type": "clarification", "question": clarification, "action_requests": []},
        }
    if requests:
        return {
            **base,
            "needs_clarification": True,
            "interrupt": {"type": "approval", "action_requests": requests},
        }
    return {**base, "message": _final_message(result), "source_refs": _collect_source_refs(result)}


def _invoke(payload: Any, *, learner_id: str, thread_id: str | None, tenant_id: str | None) -> dict[str, Any]:
    tenant, base_thread_id, config = _thread_config(learner_id, thread_id, tenant_id)
    token = set_agent_context(learner_id, tenant)
    sink_token = set_source_sink()
    try:
        result = build_tutor_agent().invoke(payload, config=config)
        # _format must run while the source sink is still set (it reads collected_source_refs()).
        formatted = _format(result, learner_id=learner_id, tenant_id=tenant, thread_id=base_thread_id)
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
        formatted = {
            "learner_id": learner_id,
            "tenant_id": tenant,
            "thread_id": base_thread_id,
            "message": RECURSION_FALLBACK_MESSAGE,
            "source_refs": collected_source_refs()[:8],
        }
    finally:
        reset_source_sink(sink_token)
        reset_agent_context(token)
    return formatted


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


# --- Streaming (step-progress) -------------------------------------------------
# Human-readable labels for the orchestrator's tool calls, surfaced as live progress.
_TOOL_LABELS = {
    "write_todos": "Planning the approach…",
    "search_course_material": "Searching the course corpus…",
    "assess_skills": "Assessing your current level…",
    "view_progress": "Reviewing your progress…",
    "recommend_path": "Building your study path…",
    "next_exercise": "Writing a source-backed exercise…",
    "grade_answer": "Grading your answer…",
    "commit_progress": "Preparing to save your progress…",
    "request_clarification": "Asking a clarifying question…",
}


def _tool_calls(message: Any) -> list[Any]:
    return getattr(message, "tool_calls", None) or []


def _step_label(update: dict[str, Any]) -> str | None:
    """Map a ``stream_mode='updates'`` delta to one short progress label, or None."""
    if not isinstance(update, dict):
        return None
    for _node, delta in update.items():
        messages = delta.get("messages") if isinstance(delta, dict) else None
        for message in messages or []:
            for call in _tool_calls(message):
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
                args = (call.get("args") if isinstance(call, dict) else getattr(call, "args", {})) or {}
                if name == "task":
                    sub = args.get("subagent_type") or args.get("description") or "a specialist"
                    return f"Consulting {sub}…"
                if name in _TOOL_LABELS:
                    return _TOOL_LABELS[name]
    return None


def _snapshot_result(agent: Any, config: dict[str, Any]) -> dict[str, Any]:
    """Read the final graph state after streaming into the ``_format`` input shape."""
    snapshot = agent.get_state(config)
    values = getattr(snapshot, "values", {}) or {}
    result: dict[str, Any] = {"messages": values.get("messages", [])}
    interrupts: list[Any] = list(getattr(snapshot, "interrupts", []) or [])
    if not interrupts:
        for task in getattr(snapshot, "tasks", []) or []:
            interrupts.extend(getattr(task, "interrupts", None) or [])
    result["__interrupt__"] = interrupts
    return result


def stream_tutor_turn(
    learner_id: str,
    message: str,
    thread_id: str | None = None,
    tenant_id: str | None = None,
):
    """Yield ``{'type':'step',...}`` progress events, then one terminal ``{'type':'final',...}``.

    The final event mirrors ``run_tutor_turn`` (message + source_refs, or an interrupt). Step
    events are derived from the orchestrator's tool calls as the turn proceeds. Resume is still
    handled by ``resume_tutor_turn`` (non-streamed).
    """
    tenant, base_thread_id, config = _thread_config(learner_id, thread_id, tenant_id)
    token = set_agent_context(learner_id, tenant)
    sink_token = set_source_sink()
    seen: set[str] = set()
    try:
        agent = build_tutor_agent()
        payload = {"messages": [{"role": "user", "content": message}]}
        try:
            for update in agent.stream(payload, config=config, stream_mode="updates"):
                label = _step_label(update)
                if label and label not in seen:
                    seen.add(label)
                    yield {"type": "step", "label": label}
            result = _snapshot_result(agent, config)
            final = _format(result, learner_id=learner_id, tenant_id=tenant, thread_id=base_thread_id)
        except GraphRecursionError:
            logger.warning(
                "streamed tutor turn hit the recursion limit (learner=%s thread=%s tenant=%s)",
                learner_id,
                base_thread_id,
                tenant,
                exc_info=True,
            )
            final = {
                "learner_id": learner_id,
                "tenant_id": tenant,
                "thread_id": base_thread_id,
                "message": RECURSION_FALLBACK_MESSAGE,
                "source_refs": collected_source_refs()[:8],
            }
        yield {"type": "final", **final}
    finally:
        reset_source_sink(sink_token)
        reset_agent_context(token)
