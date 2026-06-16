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


def set_agent_context(learner_id: str, tenant_id: str | None) -> contextvars.Token:
    return _agent_ctx.set({"learner_id": learner_id, "tenant_id": tenant_id})


def reset_agent_context(token: contextvars.Token) -> None:
    _agent_ctx.reset(token)


def _ctx() -> tuple[str, str | None]:
    ctx = _agent_ctx.get()
    learner_id = ctx.get("learner_id")
    if not learner_id:
        raise RuntimeError("agent context is not set (no learner_id); call set_agent_context first")
    return learner_id, ctx.get("tenant_id")


# --- Corpus retrieval (shared by every subagent) --------------------------
@tool
def search_course_material(query: str, k: int = 5) -> dict[str, Any]:
    """Search the GenAI course corpus and return source-backed hits with citations.
    Always use this before teaching, planning, or authoring so claims are grounded."""
    _, tenant = _ctx()
    return search_course_material_impl(query, k=k, tenant_id=tenant)


# --- Diagnostic ------------------------------------------------------------
@tool
def assess_skills(goal: str, answers: list[str] | None = None) -> dict[str, Any]:
    """Estimate the current learner's skill levels for a goal using source-backed probes."""
    learner_id, tenant = _ctx()
    return tutor_assess_skills_impl(learner_id, goal, answers=answers, tenant_id=tenant)


@tool
def view_progress() -> dict[str, Any]:
    """Return the current learner's mastery, goals, and active exercise."""
    learner_id, tenant = _ctx()
    return tutor_view_progress_impl(learner_id, tenant_id=tenant)


# --- Path planning ---------------------------------------------------------
@tool
def recommend_path(goal: str) -> dict[str, Any]:
    """Build an ordered, prerequisite-aware study path for the current learner's goal."""
    learner_id, tenant = _ctx()
    return tutor_recommend_path_impl(learner_id, goal, tenant_id=tenant)


# --- Exercise authoring ----------------------------------------------------
@tool
def next_exercise(skill: str | None = None, goal: str | None = None, exercise_type: str | None = None) -> dict[str, Any]:
    """Author and persist the next source-backed exercise for the current learner."""
    learner_id, tenant = _ctx()
    return tutor_get_next_exercise_impl(
        learner_id, skill=skill, goal=goal, exercise_type=exercise_type, tenant_id=tenant
    )


# --- Grading (deterministic) ----------------------------------------------
@tool
def grade_answer(answer: str, exercise_id: str | None = None) -> dict[str, Any]:
    """Grade the current learner's answer deterministically and persist the mastery change.
    The score/verdict come from code, not from the model — report them, do not overrule them."""
    learner_id, tenant = _ctx()
    return tutor_submit_answer_impl(learner_id, answer, exercise_id=exercise_id, tenant_id=tenant)


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
    return {"committed": True, "learner_id": learner_id, "event_id": event.get("event_id"), "summary": summary}


SUBAGENT_TOOLSETS = {
    "diagnostic": [search_course_material, assess_skills, view_progress],
    "path_planner": [search_course_material, recommend_path],
    "exercise_author": [search_course_material, next_exercise],
    "grader_critic": [search_course_material, grade_answer],
}
