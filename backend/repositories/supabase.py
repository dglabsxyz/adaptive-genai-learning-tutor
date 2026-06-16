"""Optional Supabase REST repository adapters.

These adapters are loaded only when a deployment opts into Supabase settings.
They intentionally preserve the same model contract as the JSON repositories.
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.models import Exercise, LearnerProfile, SkillProgress, SourceRef, default_progress, utc_now
from backend.settings import AppSettings, get_settings
from backend.stores import LearnerStore, _tenant_id


class SupabaseREST:
    def __init__(self, settings: AppSettings | None = None):
        self.settings = settings or get_settings()
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        base_url = self.settings.supabase_url.rstrip("/")
        self.base_url = base_url if base_url.endswith("/rest/v1") else base_url + "/rest/v1"
        self.headers = {
            "apikey": self.settings.supabase_service_role_key,
            "authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "content-type": "application/json",
        }

    def get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        response = httpx.get(f"{self.base_url}/{table}", headers=self.headers, params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def upsert(self, table: str, rows: list[dict[str, Any]], conflict: str) -> None:
        headers = {**self.headers, "prefer": "resolution=merge-duplicates"}
        response = httpx.post(
            f"{self.base_url}/{table}",
            headers=headers,
            params={"on_conflict": conflict},
            json=rows,
            timeout=20,
        )
        response.raise_for_status()

    def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Insert new rows. ``return=minimal`` so no SELECT grant is required."""
        headers = {**self.headers, "prefer": "return=minimal"}
        response = httpx.post(
            f"{self.base_url}/{table}",
            headers=headers,
            json=rows,
            timeout=20,
        )
        response.raise_for_status()

    def rpc(self, function_name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        response = httpx.post(
            f"{self.base_url}/rpc/{function_name}",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


class SupabaseLearnerRepository(LearnerStore):
    """Learner repository backed by Supabase REST.

    It inherits deterministic update behavior from LearnerStore and overrides
    reads/writes. Tests can mock SupabaseREST without requiring network access.
    """

    def __init__(self, client: SupabaseREST | None = None):
        super().__init__()
        self.client = client or SupabaseREST()

    def get(self, learner_id: str, tenant_id: str | None = None) -> LearnerProfile:
        tenant = _tenant_id(tenant_id)
        rows = self.client.get(
            "learner_profiles",
            {
                "tenant_id": f"eq.{tenant}",
                "learner_id": f"eq.{learner_id}",
                "select": "*",
                "limit": "1",
            },
        )
        if not rows:
            profile = LearnerProfile(learner_id=learner_id, tenant_id=tenant, progress=default_progress())
            return self.save(profile, tenant_id=tenant)
        row = rows[0]
        progress_rows = self.client.get(
            "skill_progress",
            {
                "tenant_id": f"eq.{tenant}",
                "learner_id": f"eq.{learner_id}",
                "select": "*",
            },
        )
        progress = default_progress()
        for item in progress_rows:
            progress[item["skill"]] = SkillProgress(
                skill=item["skill"],
                proficiency=float(item.get("proficiency") or 0),
                status=item.get("status") or "exposure",
                attempts=item.get("attempts") or 0,
                correct_streak=item.get("correct_streak") or 0,
                last_reviewed=item.get("last_reviewed"),
                next_review=item.get("next_review"),
                source_refs=[SourceRef.model_validate(ref) for ref in item.get("source_refs") or []],
                evidence=item.get("evidence") or [],
                status_reason=item.get("status_reason"),
                next_review_reason=item.get("next_review_reason"),
                last_change=item.get("last_change"),
            )
        return LearnerProfile(
            learner_id=learner_id,
            tenant_id=tenant,
            goals=row.get("goals") or [],
            progress=progress,
            active_exercise_id=row.get("active_exercise_id"),
            study_plan=row.get("study_plan") or [],
            history=row.get("history") or [],
            created_at=row.get("created_at") or utc_now(),
            updated_at=row.get("updated_at") or utc_now(),
        )

    def save(self, profile: LearnerProfile, tenant_id: str | None = None) -> LearnerProfile:
        profile.tenant_id = _tenant_id(tenant_id or profile.tenant_id)
        profile.updated_at = utc_now()
        self.client.upsert(
            "learner_profiles",
            [
                {
                    "tenant_id": profile.tenant_id,
                    "learner_id": profile.learner_id,
                    "goals": profile.goals,
                    "active_exercise_id": profile.active_exercise_id,
                    "study_plan": profile.study_plan,
                    "history": profile.history,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                }
            ],
            "tenant_id,learner_id",
        )
        rows = []
        for skill, progress in profile.progress.items():
            rows.append(
                {
                    "tenant_id": profile.tenant_id,
                    "learner_id": profile.learner_id,
                    "skill": skill,
                    "proficiency": progress.proficiency,
                    "status": progress.status,
                    "attempts": progress.attempts,
                    "correct_streak": progress.correct_streak,
                    "last_reviewed": progress.last_reviewed,
                    "next_review": progress.next_review,
                    "source_refs": [ref.model_dump() for ref in progress.source_refs],
                    "evidence": progress.evidence,
                    "status_reason": progress.status_reason,
                    "next_review_reason": progress.next_review_reason,
                    "last_change": progress.last_change,
                    "updated_at": profile.updated_at,
                }
            )
        if rows:
            self.client.upsert("skill_progress", rows, "tenant_id,learner_id,skill")
        return profile


class SupabaseExerciseRepository:
    def __init__(self, client: SupabaseREST | None = None):
        self.client = client or SupabaseREST()

    def create_id(self) -> str:
        from backend.stores import ExerciseStore

        return ExerciseStore().create_id()

    def save(self, exercise: Exercise) -> Exercise:
        self.client.upsert(
            "exercises",
            [
                {
                    "tenant_id": exercise.tenant_id,
                    "id": exercise.id,
                    "learner_id": exercise.learner_id,
                    "skill": exercise.skill,
                    "exercise_type": exercise.exercise_type,
                    "difficulty": exercise.difficulty,
                    "prompt": exercise.prompt,
                    "choices": exercise.choices,
                    "answer_key": exercise.answer_key,
                    "expected_points": exercise.expected_points,
                    "rubric": exercise.rubric,
                    "hints": exercise.hints,
                    "source_refs": [ref.model_dump() for ref in exercise.source_refs],
                    "created_at": exercise.created_at,
                }
            ],
            "tenant_id,id",
        )
        return exercise

    def get(self, exercise_id: str, tenant_id: str | None = None) -> Exercise | None:
        tenant = _tenant_id(tenant_id)
        rows = self.client.get(
            "exercises",
            {"tenant_id": f"eq.{tenant}", "id": f"eq.{exercise_id}", "select": "*", "limit": "1"},
        )
        if not rows:
            return None
        row = rows[0]
        return Exercise(
            id=row["id"],
            learner_id=row["learner_id"],
            tenant_id=row["tenant_id"],
            skill=row["skill"],
            exercise_type=row["exercise_type"],
            difficulty=row["difficulty"],
            prompt=row["prompt"],
            choices=row.get("choices") or [],
            answer_key=row.get("answer_key") or [],
            expected_points=row.get("expected_points") or [],
            rubric=row["rubric"],
            hints=row.get("hints") or [],
            source_refs=[SourceRef.model_validate(ref) for ref in row.get("source_refs") or []],
            created_at=row.get("created_at") or utc_now(),
        )

    def list_for_learner(self, learner_id: str, tenant_id: str | None = None) -> list[Exercise]:
        tenant = _tenant_id(tenant_id)
        rows = self.client.get(
            "exercises",
            {"tenant_id": f"eq.{tenant}", "learner_id": f"eq.{learner_id}", "select": "*"},
        )
        exercises = [self.get(row["id"], tenant_id=tenant) for row in rows if row.get("id")]
        return [exercise for exercise in exercises if exercise is not None]
