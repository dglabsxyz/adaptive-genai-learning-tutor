"""Local file-backed persistence for learner state and generated exercises."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
from datetime import date
from pathlib import Path
from typing import Any

from .audit import write_audit_event
from .config import EXERCISE_STORE_PATH, LEARNER_STORE_PATH, ensure_data_dir
from .state_integrity import sign_json, verify_json
from .mastery import band_label, review_days
from .models import (
    Exercise,
    LearnerProfile,
    SkillProgress,
    SourceRef,
    default_progress,
    next_review_for,
    status_for_proficiency,
    utc_now,
)
from .repositories import ExerciseRepository, LearnerRepository
from .settings import get_settings


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    """Atomic write with HMAC signature for integrity protection (AGT-022, WEB-030)."""
    ensure_data_dir()
    # Sign the payload before writing
    signed_payload = sign_json(payload)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(signed_payload, handle, indent=2)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _tenant_id(tenant_id: str | None) -> str:
    return tenant_id or get_settings().local_tenant_id


def _scoped_key(tenant_id: str | None, item_id: str) -> str:
    tenant = _tenant_id(tenant_id)
    if tenant == get_settings().local_tenant_id:
        return item_id
    return f"{tenant}:{item_id}"


def _review_is_due(progress: SkillProgress) -> bool:
    if not progress.next_review or progress.attempts == 0:
        return False
    try:
        return date.fromisoformat(progress.next_review) <= date.today()
    except ValueError:
        return False


def _status_reason(skill: str, status: str, proficiency: float) -> str:
    return f"{skill} is {status} because proficiency is {proficiency:.2f} ({band_label(status)})."


def _next_review_reason(status: str, next_review: str | None) -> str | None:
    if not next_review:
        return None
    days = review_days(status)
    cadence = "tomorrow" if days == 1 else f"in {days} days"
    return f"Next review is {next_review} because {status} skills are scheduled {cadence}."


def _apply_review_due(profile: LearnerProfile) -> LearnerProfile:
    for progress in profile.progress.values():
        if _review_is_due(progress) and progress.status in {"developing", "proficient", "mastered"}:
            previous = progress.status
            progress.status = "review"
            progress.status_reason = (
                f"{progress.skill} moved from {previous} to review because the next review date "
                f"{progress.next_review} has arrived."
            )
    return profile


class LearnerStore:
    def __init__(self, path: Path = LEARNER_STORE_PATH):
        self.path = path
        self._lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        ensure_data_dir()
        if not self.path.exists():
            return {"learners": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        _atomic_write(self.path, payload)

    def get(self, learner_id: str, tenant_id: str | None = None) -> LearnerProfile:
        tenant = _tenant_id(tenant_id)
        key = _scoped_key(tenant, learner_id)
        with self._lock:
            payload = self._read()
            raw = payload["learners"].get(key)
            if raw is None:
                profile = LearnerProfile(learner_id=learner_id, tenant_id=tenant, progress=default_progress())
                payload["learners"][key] = profile.model_dump()
                self._write(payload)
                return profile
            profile = LearnerProfile.model_validate(raw)
            profile.tenant_id = profile.tenant_id or tenant
            for skill, progress in default_progress().items():
                profile.progress.setdefault(skill, progress)
            return _apply_review_due(profile)

    def save(self, profile: LearnerProfile, tenant_id: str | None = None) -> LearnerProfile:
        profile.tenant_id = _tenant_id(tenant_id or profile.tenant_id)
        profile.updated_at = utc_now()
        key = _scoped_key(profile.tenant_id, profile.learner_id)
        with self._lock:
            payload = self._read()
            payload["learners"][key] = profile.model_dump()
            self._write(payload)
        return profile

    def add_goal(self, learner_id: str, goal: str, tenant_id: str | None = None) -> LearnerProfile:
        profile = self.get(learner_id, tenant_id=tenant_id)
        if goal and goal not in profile.goals:
            profile.goals.append(goal)
        return self.save(profile)

    def update_skill(
        self,
        learner_id: str,
        skill: str,
        proficiency: float | None = None,
        score_delta: float | None = None,
        source_refs: list[SourceRef] | None = None,
        evidence: list[str] | None = None,
        attempted: bool = False,
        correct: bool = False,
        tenant_id: str | None = None,
    ) -> LearnerProfile:
        tenant = _tenant_id(tenant_id)
        profile = self.get(learner_id, tenant_id=tenant)
        current = profile.progress.get(skill) or SkillProgress(skill=skill)
        previous_status = current.status
        previous_proficiency = current.proficiency
        if proficiency is not None:
            current.proficiency = max(0.0, min(1.0, proficiency))
        elif score_delta is not None:
            current.proficiency = max(0.0, min(1.0, current.proficiency + score_delta))
        current.status = status_for_proficiency(current.proficiency)
        if attempted:
            current.attempts += 1
            current.correct_streak = current.correct_streak + 1 if correct else 0
            current.last_reviewed = utc_now()
            current.next_review = next_review_for(current.status)
            current.next_review_reason = _next_review_reason(current.status, current.next_review)
        if source_refs:
            merged = {ref.source_id: ref for ref in current.source_refs}
            for ref in source_refs:
                merged[ref.source_id] = ref
            current.source_refs = list(merged.values())[:8]
        if evidence:
            current.evidence = evidence[:8]
        current.status_reason = _status_reason(skill, current.status, current.proficiency)
        current.last_change = {
            "from_status": previous_status,
            "to_status": current.status,
            "proficiency_before": round(previous_proficiency, 2),
            "proficiency_after": round(current.proficiency, 2),
            "proficiency_delta": round(current.proficiency - previous_proficiency, 2),
            "evidence": current.evidence,
            "at": utc_now(),
        }
        profile.progress[skill] = current
        saved = self.save(profile, tenant_id=tenant)
        write_audit_event(
            "progress_update",
            learner_id=learner_id,
            tenant_id=tenant,
            metadata={
                "skill": skill,
                "from_status": previous_status,
                "to_status": current.status,
                "proficiency_before": round(previous_proficiency, 2),
                "proficiency_after": round(current.proficiency, 2),
                "attempted": attempted,
                "correct": correct,
            },
        )
        return saved

    def append_history(
        self,
        learner_id: str,
        event: dict[str, Any],
        tenant_id: str | None = None,
    ) -> LearnerProfile:
        profile = self.get(learner_id, tenant_id=tenant_id)
        profile.history.append({"at": utc_now(), **event})
        profile.history = profile.history[-80:]
        return self.save(profile, tenant_id=tenant_id)

    def list_profiles(self, tenant_id: str | None = None) -> list[LearnerProfile]:
        tenant = _tenant_id(tenant_id)
        with self._lock:
            raw_items = list(self._read().get("learners", {}).values())
        profiles = [LearnerProfile.model_validate(item) for item in raw_items]
        return [profile for profile in profiles if _tenant_id(profile.tenant_id) == tenant]


class ExerciseStore:
    def __init__(self, path: Path = EXERCISE_STORE_PATH):
        self.path = path
        self._lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        ensure_data_dir()
        if not self.path.exists():
            return {"exercises": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        _atomic_write(self.path, payload)

    def create_id(self) -> str:
        return f"ex_{secrets.token_hex(5)}"

    def save(self, exercise: Exercise) -> Exercise:
        exercise.tenant_id = _tenant_id(exercise.tenant_id)
        with self._lock:
            payload = self._read()
            payload["exercises"][exercise.id] = exercise.model_dump()
            self._write(payload)
        return exercise

    def get(self, exercise_id: str, tenant_id: str | None = None) -> Exercise | None:
        with self._lock:
            raw = self._read()["exercises"].get(exercise_id)
        if raw is None:
            return None
        exercise = Exercise.model_validate(raw)
        if tenant_id and _tenant_id(exercise.tenant_id) != _tenant_id(tenant_id):
            return None
        return exercise

    def list_for_learner(self, learner_id: str, tenant_id: str | None = None) -> list[Exercise]:
        tenant = _tenant_id(tenant_id)
        with self._lock:
            raw_items = list(self._read().get("exercises", {}).values())
        exercises = [Exercise.model_validate(item) for item in raw_items]
        return [
            exercise
            for exercise in exercises
            if exercise.learner_id == learner_id and _tenant_id(exercise.tenant_id) == tenant
        ]


def _build_repositories() -> tuple[LearnerRepository, ExerciseRepository]:
    settings = get_settings()
    if settings.repository_backend == "supabase" and settings.supabase_enabled:
        from .repositories.supabase import SupabaseExerciseRepository, SupabaseLearnerRepository

        return SupabaseLearnerRepository(), SupabaseExerciseRepository()
    return LearnerStore(), ExerciseStore()


learner_store, exercise_store = _build_repositories()


def reset_learner_progress(
    learner_id: str,
    tenant_id: str | None = None,
    scope: str = "all",
) -> dict[str, Any]:
    """Reset a learner's mastery state to defaults. Backend-agnostic and audited.

    This is the real, guarded destructive action behind the graph's
    confirmation interrupt and the ``/progress/{learner_id}/reset`` endpoint.
    History is preserved (a reset event is appended) so the action stays
    auditable; only forward-looking mastery/active state is cleared.
    """
    tenant = _tenant_id(tenant_id)
    profile = learner_store.get(learner_id, tenant_id=tenant)
    cleared_skills = sorted(profile.progress.keys())
    profile.progress = default_progress()
    profile.active_exercise_id = None
    profile.study_plan = []
    if scope == "all":
        profile.goals = []
    profile.history.append(
        {"at": utc_now(), "type": "progress_reset", "scope": scope, "skills_cleared": len(cleared_skills)}
    )
    learner_store.save(profile, tenant_id=tenant)
    write_audit_event(
        "progress_reset",
        learner_id=learner_id,
        tenant_id=tenant,
        outcome="completed",
        metadata={"scope": scope, "skills_cleared": len(cleared_skills)},
    )
    return {
        "learner_id": learner_id,
        "tenant_id": tenant,
        "reset": True,
        "scope": scope,
        "skills_cleared": cleared_skills,
        "message": f"Progress reset for {learner_id} ({len(cleared_skills)} skills cleared).",
    }
