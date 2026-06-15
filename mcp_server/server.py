"""FastMCP intent tools for the Adaptive GenAI Learning Tutor.

Run with:
  uv run python mcp_server/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.tools import (  # noqa: E402
    search_course_material_impl,
    tutor_assess_skills_impl,
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
    tutor_view_progress_impl,
)
from backend.analytics import cohort_progress, intervention_recommendations  # noqa: E402
from backend.audit import write_audit_event  # noqa: E402
from backend.rate_limit import enforce_rate_limit  # noqa: E402
from backend.source_governance import citation_audit, source_quality_report  # noqa: E402

mcp = FastMCP("adaptive-genai-learning-tutor")


def _require_mcp_access(
    tool_name: str,
    *,
    learner_id: str | None = None,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
    metadata: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    user = user_id or learner_id or "mcp-local-user"
    if role not in {"learner", "educator", "admin"}:
        raise ValueError("role must be learner, educator, or admin")
    if role == "learner" and learner_id and user != learner_id:
        raise ValueError("learner role can only access its own learner_id")
    try:
        enforce_rate_limit("mcp_tool", tenant_id=tenant_id, user_id=user)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        raise ValueError(detail) from exc
    write_audit_event(
        "mcp_tool_call",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user,
        role=role,
        metadata={"tool_name": tool_name, **(metadata or {})},
    )
    return tenant_id, user, role


def _require_role(role: str, allowed: set[str]) -> None:
    if role not in allowed:
        raise ValueError(f"{role} role is not allowed for this MCP tool")


def _sources(refs: list[dict[str, Any]] | None) -> str:
    if not refs:
        return "Sources: none"
    lines = ["Sources:"]
    for ref in refs[:5]:
        citations = ref.get("citations") or []
        citation_text = f" ({citations[0]})" if citations else ""
        researched = f" · researched {ref.get('last_researched_at')}" if ref.get("last_researched_at") else ""
        lines.append(
            f"- {ref.get('title')} [{ref.get('record_type')}] "
            f"{ref.get('path')}{researched}{citation_text}"
        )
    return "\n".join(lines)


@mcp.tool()
def tutor_search_course_material(
    query: str,
    k: int = 5,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """Search the local genai_research corpus and return formatted source-backed results."""
    _require_mcp_access(
        "tutor_search_course_material",
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"query_length": len(query), "k": k},
    )
    payload = search_course_material_impl(query=query, k=k, tenant_id=tenant_id)
    lines = [f"# Search: {query}", payload["summary"]]
    for result in payload["results"]:
        lines.append(f"\n## {result['title']}")
        lines.append(f"{result['record_type']} · score {result['score']} · {result['path']}")
        lines.append(result["summary"])
        if result["citations"]:
            lines.append(f"Citation: {result['citations'][0]}")
    return "\n".join(lines)


@mcp.tool()
def tutor_assess_skills(
    learner_id: str,
    goal: str,
    answers: list[str] | None = None,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """Run a diagnostic for a learner goal and persist mastery updates."""
    _require_mcp_access(
        "tutor_assess_skills",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"goal_length": len(goal)},
    )
    payload = tutor_assess_skills_impl(learner_id=learner_id, goal=goal, answers=answers, tenant_id=tenant_id)
    lines = [f"# Diagnostic for {learner_id}", payload["summary"]]
    for item in payload["assessment"]:
        lines.append(f"- {item['skill']}: {item['status']} ({item['proficiency']})")
    lines.append(_sources(payload["source_refs"]))
    return "\n".join(lines)


@mcp.tool()
def tutor_get_next_exercise(
    learner_id: str,
    skill: str | None = None,
    goal: str | None = None,
    exercise_type: str | None = None,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """Create the next source-backed exercise for a learner."""
    _require_mcp_access(
        "tutor_get_next_exercise",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"skill": skill, "exercise_type": exercise_type},
    )
    payload = tutor_get_next_exercise_impl(
        learner_id=learner_id,
        skill=skill,
        goal=goal,
        exercise_type=exercise_type,  # type: ignore[arg-type]
        tenant_id=tenant_id,
    )
    exercise = payload["exercise"]
    lines = [
        f"# Exercise: {exercise['skill']}",
        f"Type: {exercise['exercise_type']} · Difficulty: {exercise['difficulty']}",
        exercise["prompt"],
        "\nRubric:",
    ]
    if exercise.get("choices"):
        lines.append("\nChoices:")
        lines.extend(f"- {choice}" for choice in exercise["choices"])
    lines.extend(f"- {point}" for point in exercise["expected_points"])
    lines.append(f"\nexercise_id: {exercise['id']}")
    lines.append(_sources(payload["source_refs"]))
    return "\n".join(lines)


@mcp.tool()
def tutor_submit_answer(
    learner_id: str,
    answer: str,
    exercise_id: str | None = None,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """Grade an answer against the active or specified exercise and persist progress."""
    _require_mcp_access(
        "tutor_submit_answer",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"exercise_id": exercise_id, "answer_length": len(answer)},
    )
    payload = tutor_submit_answer_impl(
        learner_id=learner_id,
        answer=answer,
        exercise_id=exercise_id,
        tenant_id=tenant_id,
    )
    if payload.get("needs_clarification"):
        return f"Clarification needed: {payload['message']}\n{_sources(payload.get('source_refs'))}"
    lines = [
        f"# Grade: {payload['skill']}",
        f"Score: {payload['score']}",
        f"Verdict: {payload['verdict']}",
        payload["explanation"],
        "\nCovered:",
    ]
    lines.extend(f"- {point}" for point in payload["covered_points"])
    lines.append("\nMissed:")
    lines.extend(f"- {point}" for point in payload["missed_points"])
    mastery = payload.get("mastery_update") or {}
    if mastery:
        lines.append("\nMastery update:")
        lines.append(
            f"- {mastery.get('previous_status')} -> {mastery.get('new_status')} "
            f"({mastery.get('proficiency_before')} -> {mastery.get('proficiency_after')})"
        )
        if mastery.get("status_reason"):
            lines.append(f"- {mastery['status_reason']}")
        if mastery.get("next_review_reason"):
            lines.append(f"- {mastery['next_review_reason']}")
    lines.append(_sources(payload["source_refs"]))
    return "\n".join(lines)


@mcp.tool()
def tutor_view_progress(
    learner_id: str,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """View the same persistent learner progress used by the local app."""
    _require_mcp_access(
        "tutor_view_progress",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
    )
    payload = tutor_view_progress_impl(learner_id=learner_id, tenant_id=tenant_id)
    lines = [f"# Progress for {learner_id}"]
    for skill, entry in payload["progress"].items():
        review = f", next review {entry['next_review']}" if entry.get("next_review") else ""
        lines.append(f"- {skill}: {entry['status']} ({entry['proficiency']:.2f}), attempts {entry['attempts']}{review}")
        if entry.get("status_reason"):
            lines.append(f"  Evidence: {entry['status_reason']}")
    if payload.get("active_exercise_id"):
        lines.append(f"\nActive exercise: {payload['active_exercise_id']}")
    return "\n".join(lines)


@mcp.tool()
def tutor_recommend_path(
    learner_id: str,
    goal: str,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """Recommend a source-backed study path and persist it to learner state."""
    _require_mcp_access(
        "tutor_recommend_path",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"goal_length": len(goal)},
    )
    payload = tutor_recommend_path_impl(learner_id=learner_id, goal=goal, tenant_id=tenant_id)
    lines = [f"# Study path for {learner_id}", payload["summary"]]
    for module in payload["modules"]:
        lines.append(f"\n{module['order']}. {module['skill']} [{module['status']}]")
        lines.append(module["milestone"])
        lines.append(module["review_checkpoint"])
    lines.append(_sources(payload["source_refs"]))
    return "\n".join(lines)


@mcp.tool()
def tutor_review_cohort_progress(
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "educator",
) -> str:
    """Review cohort-level progress, risk areas, and intervention counts."""
    _require_mcp_access("tutor_review_cohort_progress", tenant_id=tenant_id, user_id=user_id, role=role)
    _require_role(role, {"educator", "admin"})
    payload = cohort_progress(tenant_id=tenant_id)
    lines = [
        f"# Cohort progress: {tenant_id}",
        f"Learners: {payload['learner_count']}",
        f"Risk areas: {len(payload['risk_areas'])}",
    ]
    for area in payload["risk_areas"][:8]:
        lines.append(f"- {area['skill']}: {area['average_proficiency']}")
    return "\n".join(lines)


@mcp.tool()
def tutor_assign_learning_path(
    learner_id: str,
    goal: str,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "educator",
) -> str:
    """Assign a source-backed learning path to a learner."""
    _require_mcp_access(
        "tutor_assign_learning_path",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"goal_length": len(goal)},
    )
    _require_role(role, {"educator", "admin"})
    payload = tutor_recommend_path_impl(learner_id=learner_id, goal=goal, tenant_id=tenant_id)
    lines = [f"# Assigned path for {learner_id}", payload["summary"]]
    lines.extend(f"- {module['order']}. {module['skill']}: {module['milestone']}" for module in payload["modules"])
    lines.append(_sources(payload["source_refs"]))
    return "\n".join(lines)


@mcp.tool()
def tutor_audit_source_grounding(
    query: str,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "admin",
) -> str:
    """Audit source grounding for a query and summarize corpus quality signals."""
    _require_mcp_access(
        "tutor_audit_source_grounding",
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"query_length": len(query)},
    )
    _require_role(role, {"educator", "admin"})
    payload = search_course_material_impl(query=query, k=5, tenant_id=tenant_id)
    audit = citation_audit(payload)
    quality = source_quality_report()
    lines = [
        f"# Source grounding audit: {query}",
        f"Source refs: {audit['source_ref_count']}",
        f"Missing citations in response refs: {len(audit['missing_citations'])}",
        f"Corpus records missing citations: {quality['missing_citations_count']}",
    ]
    lines.append(_sources(payload["source_refs"]))
    return "\n".join(lines)


@mcp.tool()
def tutor_escalate_learning_gap(
    learner_id: str,
    skill: str,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "educator",
) -> str:
    """Escalate a learner skill gap with current evidence and a source-backed next action."""
    _require_mcp_access(
        "tutor_escalate_learning_gap",
        learner_id=learner_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"skill": skill},
    )
    _require_role(role, {"educator", "admin"})
    progress = tutor_view_progress_impl(learner_id=learner_id, tenant_id=tenant_id)["progress"].get(skill)
    recommendations = intervention_recommendations(tenant_id=tenant_id)["recommendations"]
    match = next((item for item in recommendations if item["learner_id"] == learner_id and item["skill"] == skill), None)
    if not progress:
        return f"No progress found for {learner_id} on {skill}."
    lines = [
        f"# Learning gap: {learner_id} / {skill}",
        f"Status: {progress['status']} ({progress['proficiency']:.2f})",
        progress.get("status_reason") or "No status reason recorded.",
        match["next_action"] if match else f"Assign one source-backed {skill} exercise and review missed rubric points.",
    ]
    lines.append(_sources(progress.get("source_refs")))
    return "\n".join(lines)


@mcp.tool()
def tutor_generate_infographic(
    topic: str,
    tenant_id: str = "local",
    user_id: str | None = None,
    role: str = "learner",
) -> str:
    """Generate a source-backed SVG infographic and verify its text is legible (Qwen3-VL)."""
    _require_mcp_access(
        "tutor_generate_infographic",
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        metadata={"topic_length": len(topic)},
    )
    from backend.infographics import generate_infographic

    result = generate_infographic(topic, tenant_id=tenant_id, learner_id=user_id)
    sc = result["structural_check"]
    verification = result["verification"]
    lines = [
        f"# Infographic: {topic}",
        f"Generator: {result['generator']}",
        f"Legible and correct: {result['legible_and_correct']}",
        f"Structural: text_elements={sc['text_element_count']}, min_font={sc['min_font_size']}, all_present={sc['all_intended_present']}",
        f"VL check: used={verification.get('vl_used')}, legible={verification.get('legible')}",
    ]
    for kind in ("svg", "png"):
        if result.get("paths", {}).get(kind):
            lines.append(f"{kind.upper()}: {result['paths'][kind]}")
    for source in (result.get("sources") or [])[:5]:
        lines.append(f"- {source.get('title')} {source.get('path')}")
    return "\n".join(lines)


def smoke_check() -> None:
    learner_id = "mcp-smoke-learner"
    goal = "I want to learn AI agents."
    print(tutor_assess_skills(learner_id, goal, answers=["RAG and MCP are still fuzzy."]))
    print()
    print(tutor_recommend_path(learner_id, goal))
    print()
    exercise_text = tutor_get_next_exercise(learner_id, skill="RAG", exercise_type="multiple_choice")
    print(exercise_text)
    print()
    print(
        tutor_submit_answer(
            learner_id,
            "B. It should retrieve local corpus records, cite sources, and keep missing metadata unknown.",
        )
    )
    print()
    print(tutor_view_progress(learner_id))


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        smoke_check()
    else:
        mcp.run()
