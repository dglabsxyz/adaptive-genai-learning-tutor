"""Context-bound tools for the deepagents tutor.

The underlying ``*_impl`` functions are learner- and tenant-scoped, but the LLM
must never supply (or hallucinate) a learner id or a tenant UUID. So these
wrappers expose only the *semantic* arguments to the model and read the
learner/tenant from a per-request context variable that the API sets before
invoking the agent. This keeps multi-tenant scoping authoritative and
server-controlled while the agent still reasons in plain task terms.
"""

from __future__ import annotations

import contextvars
from typing import Any

from langchain_core.tools import tool
from langgraph.types import interrupt

from .audit import write_audit_event
from .stores import learner_store
from .tools import (
    search_course_material_impl,
    tutor_assess_skills_impl,
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
    tutor_view_progress_impl,
)

# Per-request binding of (learner_id, tenant_id). Set by the API before invoke.
_agent_ctx: contextvars.ContextVar[dict[str, str | None]] = contextvars.ContextVar(
    "agent_ctx", default={"learner_id": None, "tenant_id": None}
)

# Per-turn "do this once" registry. Qwen sometimes re-calls an authoring/grading tool
# after it already got a good result instead of finalizing — looping to the recursion
# limit AND duplicating side effects (multiple exercises, double-counted mastery). This
# dict (reset at the start of every turn, shared by the orchestrator + its subagents via
# the contextvar) caches the first result per action; repeat calls get the SAME result
# plus a hard directive to stop and present it.
_turn_actions: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("agent_turn_actions", default={})


def set_agent_context(learner_id: str, tenant_id: str | None) -> contextvars.Token:
    _turn_actions.set({})  # fresh per-turn registry before any tool runs
    return _agent_ctx.set({"learner_id": learner_id, "tenant_id": tenant_id})


def _turn_once(key: Any, produce: Any) -> dict[str, Any]:
    """Return the cached per-turn result for ``key``, else produce + cache it.

    ``key`` includes the call's arguments, so a genuinely different request (e.g. a
    short-answer then a multiple-choice exercise) still produces a fresh result, while an
    identical repeat returns the cached result with a ``_directive`` telling the model to
    stop re-calling and present what it already has. This makes the authoring/grading
    tools idempotent per turn — converging the turn and preventing duplicate writes
    (multiple exercises, double-counted mastery) — without blocking legitimate variation.
    """
    reg = _turn_actions.get()
    if not isinstance(reg, dict):
        return produce()
    k = str(key)
    cached = reg.get(k)
    if cached is not None:
        directive = (
            "You already produced this result earlier in this turn — do NOT call this tool "
            "again with the same arguments. Present the result you already have to the learner "
            "as your final reply now."
        )
        return {**cached, "_directive": directive} if isinstance(cached, dict) else cached
    result = produce()
    reg[k] = result
    return result


def reset_agent_context(token: contextvars.Token) -> None:
    _agent_ctx.reset(token)


# Per-request accumulator of source_refs surfaced by tools. Subagent tool calls
# run in this same request context (the learner/tenant contextvar already proves
# that), so appending here captures citations from subagent retrievals too — which
# the message-scan in agent_runtime cannot see (they live in isolated subagent state).
_source_sink: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "agent_source_sink", default=None
)

# Per-request accumulator for mastery_update from grade_answer. The grader-critic
# subagent's tool messages are not visible to the orchestrator's message list, so
# we capture the deterministic mastery data here for agent_runtime to surface.
_mastery_sink: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "agent_mastery_sink", default=None
)


def set_source_sink() -> contextvars.Token:
    return _source_sink.set([])


def reset_source_sink(token: contextvars.Token) -> None:
    _source_sink.reset(token)


def collected_source_refs() -> list[dict[str, Any]]:
    sink = _source_sink.get()
    return list(sink) if sink else []


def collected_mastery_update() -> dict[str, Any] | None:
    """Return the most recent mastery_update captured from grade_answer, or None."""
    return _mastery_sink.get()


def _sink_add(refs: Any) -> None:
    sink = _source_sink.get()
    if sink is None or not isinstance(refs, list):
        return
    for ref in refs:
        if isinstance(ref, dict):
            sink.append(ref)


def _ctx() -> tuple[str, str | None]:
    ctx = _agent_ctx.get()
    learner_id = ctx.get("learner_id")
    if not learner_id:
        raise RuntimeError("agent context is not set (no learner_id); call set_agent_context first")
    return learner_id, ctx.get("tenant_id")


def get_memory_namespace(ctx: Any = None) -> tuple[str, ...]:
    """Return a tenant+learner scoped namespace tuple for the StoreBackend.

    AGT-020, AGT-021: Memory must be isolated per tenant and per learner to prevent
    cross-session poisoning and cross-tenant data leakage.
    """
    agent_context = _agent_ctx.get()
    tenant = agent_context.get("tenant_id") or "default"
    learner = agent_context.get("learner_id") or "anonymous"
    # Namespace format: ("tutor", "<tenant>", "<learner>")
    # This ensures each learner's /memories/ are fully isolated.
    return ("tutor", str(tenant), str(learner))


# --- Corpus retrieval (shared by every subagent) --------------------------
@tool
def search_course_material(query: str, k: int = 5) -> dict[str, Any]:
    """Search the GenAI course corpus and return source-backed hits with citations.
    Always use this before teaching, planning, or authoring so claims are grounded."""
    _, tenant = _ctx()
    result = search_course_material_impl(query, k=k, tenant_id=tenant)
    _sink_add(result.get("source_refs"))
    return result


# --- Diagnostic ------------------------------------------------------------
@tool
def assess_skills(goal: str, answers: list[str] | None = None) -> dict[str, Any]:
    """Estimate the current learner's skill levels for a goal using source-backed probes.
    Call this at most once per turn."""
    learner_id, tenant = _ctx()

    def _produce() -> dict[str, Any]:
        result = tutor_assess_skills_impl(learner_id, goal, answers=answers, tenant_id=tenant)
        _sink_add(result.get("source_refs"))
        return result

    return _turn_once(("assessment", goal), _produce)


@tool
def view_progress() -> dict[str, Any]:
    """Return the current learner's mastery, goals, and active exercise."""
    learner_id, tenant = _ctx()
    return tutor_view_progress_impl(learner_id, tenant_id=tenant)


# --- Path planning ---------------------------------------------------------
@tool
def recommend_path(goal: str) -> dict[str, Any]:
    """Build an ordered, prerequisite-aware study path for the current learner's goal.
    Call this at most once per turn."""
    learner_id, tenant = _ctx()

    def _produce() -> dict[str, Any]:
        result = tutor_recommend_path_impl(learner_id, goal, tenant_id=tenant)
        _sink_add(result.get("source_refs"))
        return result

    return _turn_once(("path", goal), _produce)


# --- Exercise authoring ----------------------------------------------------
@tool
def next_exercise(skill: str | None = None, goal: str | None = None, exercise_type: str | None = None) -> dict[str, Any]:
    """Author and persist the next source-backed exercise for the current learner.
    Call this AT MOST ONCE per turn — after it returns an exercise, present that exercise
    to the learner; do not call it again."""
    learner_id, tenant = _ctx()

    def _produce() -> dict[str, Any]:
        result = tutor_get_next_exercise_impl(
            learner_id, skill=skill, goal=goal, exercise_type=exercise_type, tenant_id=tenant
        )
        _sink_add(result.get("source_refs"))
        return result

    return _turn_once(("exercise", skill, exercise_type), _produce)


# --- Grading (deterministic) ----------------------------------------------
@tool
def grade_answer(answer: str, exercise_id: str | None = None) -> dict[str, Any]:
    """Grade the current learner's answer deterministically and persist the mastery change.
    The score/verdict come from code, not from the model — report them, do not overrule them.
    Call this AT MOST ONCE per turn — grading twice would double-count mastery."""
    learner_id, tenant = _ctx()

    def _produce() -> dict[str, Any]:
        result = tutor_submit_answer_impl(learner_id, answer, exercise_id=exercise_id, tenant_id=tenant)
        _sink_add(result.get("source_refs"))
        # Capture the deterministic mastery data so agent_runtime can surface it in the
        # final response — the grader-critic subagent's tool messages are not visible
        # in the orchestrator's message list.
        if result.get("mastery_update"):
            _mastery_sink.set({
                "mastery_update": result["mastery_update"],
                "skill": result.get("skill"),
                "score": result.get("score"),
                "verdict": result.get("verdict"),
                "covered_points": result.get("covered_points"),
                "missed_points": result.get("missed_points"),
            })
        return result

    return _turn_once(("grade", exercise_id), _produce)


# --- HITL gate: finalize the session (the course's publish_post analog) -----
@tool
def commit_progress(summary: str) -> dict[str, Any]:
    """Finalize this tutoring session: record a one-line summary to the learner's history.
    This is a consequential write and runs behind a human-approval gate."""
    learner_id, tenant = _ctx()
    learner_store.append_history(learner_id, {"type": "session_committed", "summary": summary}, tenant_id=tenant)
    event = write_audit_event(
        "session_committed",
        learner_id=learner_id,
        tenant_id=tenant,
        outcome="completed",
        metadata={"summary_length": len(summary or "")},
    )
    # Include the current mastery snapshot so the UI can render it authoritatively.
    # This is the single source of truth for percentages — the LLM prose must not invent numbers.
    profile = learner_store.get(learner_id, tenant_id=tenant)
    mastery_snapshot = {
        skill: {
            "proficiency": round(prog.proficiency, 2),
            "status": prog.status,
            "attempts": prog.attempts,
        }
        for skill, prog in profile.progress.items()
    }
    return {
        "committed": True,
        "learner_id": learner_id,
        "event_id": event.get("event_id"),
        "summary": summary,
        "mastery_snapshot": mastery_snapshot,
    }


# --- HITL clarification: pause the graph to ask the learner for missing info -----
@tool
def request_clarification(question: str) -> str:
    """Ask the learner ONE concise question and PAUSE the turn until they answer.
    Use this ONLY when the request is too vague or missing required detail to act on
    (e.g., no learning goal given, or an exercise request with no skill and no goal).
    Never guess missing information — ask. Returns the learner's answer as a string."""
    answer = interrupt({"type": "clarification", "question": question})
    if isinstance(answer, dict):
        return str(answer.get("answer") or answer.get("user_message") or answer.get("message") or "")
    return str(answer)


SUBAGENT_TOOLSETS = {
    "diagnostic": [search_course_material, assess_skills, view_progress],
    "path_planner": [search_course_material, recommend_path],
    "exercise_author": [search_course_material, next_exercise],
    "grader_critic": [search_course_material, grade_answer],
}
