"""Learner analytics, evidence timelines, and export bundles."""

from __future__ import annotations

from typing import Any

from .audit import read_audit_events
from .stores import exercise_store, learner_store


def cohort_progress(tenant_id: str | None = None) -> dict[str, Any]:
    profiles = learner_store.list_profiles(tenant_id=tenant_id)
    skill_totals: dict[str, list[float]] = {}
    learners = []
    for profile in profiles:
        weakest = sorted(profile.progress.values(), key=lambda item: item.proficiency)[:3]
        learners.append(
            {
                "learner_id": profile.learner_id,
                "updated_at": profile.updated_at,
                "active_exercise_id": profile.active_exercise_id,
                "weakest_skills": [
                    {
                        "skill": item.skill,
                        "status": item.status,
                        "proficiency": round(item.proficiency, 2),
                        "next_review": item.next_review,
                    }
                    for item in weakest
                ],
            }
        )
        for skill, progress in profile.progress.items():
            skill_totals.setdefault(skill, []).append(progress.proficiency)
    skill_summary = [
        {
            "skill": skill,
            "average_proficiency": round(sum(values) / max(1, len(values)), 2),
            "learner_count": len(values),
        }
        for skill, values in sorted(skill_totals.items())
    ]
    risk_areas = [item for item in skill_summary if item["average_proficiency"] < 0.35]
    return {
        "tenant_id": tenant_id or "local",
        "learner_count": len(profiles),
        "skill_summary": skill_summary,
        "risk_areas": risk_areas,
        "learners": learners,
    }


def intervention_recommendations(tenant_id: str | None = None) -> dict[str, Any]:
    profiles = learner_store.list_profiles(tenant_id=tenant_id)
    recommendations: list[dict[str, Any]] = []
    for profile in profiles:
        candidates = sorted(
            profile.progress.values(),
            key=lambda item: (item.status != "review", item.proficiency),
        )[:3]
        for progress in candidates:
            if progress.status not in {"exposure", "review"} and progress.proficiency >= 0.35:
                continue
            recommendations.append(
                {
                    "learner_id": profile.learner_id,
                    "skill": progress.skill,
                    "status": progress.status,
                    "proficiency": round(progress.proficiency, 2),
                    "rationale": progress.status_reason
                    or f"{progress.skill} is a cohort intervention candidate based on current mastery.",
                    "next_action": f"Assign one source-backed {progress.skill} exercise and review missed rubric points.",
                    "source_refs": [ref.model_dump() for ref in progress.source_refs[:3]],
                }
            )
    return {"tenant_id": tenant_id or "local", "recommendations": recommendations[:50]}


def evidence_timeline(learner_id: str, skill: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
    profile = learner_store.get(learner_id, tenant_id=tenant_id)
    events = []
    for item in profile.history:
        if skill and item.get("skill") not in {skill, None}:
            continue
        events.append(item)
    if skill and skill in profile.progress:
        progress = profile.progress[skill]
        if progress.last_change:
            events.append({"type": "last_change", "skill": skill, **progress.last_change})
        for evidence in progress.evidence:
            events.append({"type": "evidence", "skill": skill, "evidence": evidence})
    return {"learner_id": learner_id, "skill": skill, "events": events[-100:]}


def learner_export(learner_id: str, tenant_id: str | None = None) -> dict[str, Any]:
    profile = learner_store.get(learner_id, tenant_id=tenant_id)
    exercises = exercise_store.list_for_learner(learner_id, tenant_id=tenant_id)
    return {
        "tenant_id": profile.tenant_id,
        "learner": profile.model_dump(),
        "exercises": [exercise.model_dump() for exercise in exercises],
        "audit_events": read_audit_events(tenant_id=profile.tenant_id, learner_id=learner_id, limit=500),
    }
