"""Persistence protocols used by JSON and production repository adapters."""

from __future__ import annotations

from typing import Protocol

from backend.models import Exercise, LearnerProfile, SourceRef


class LearnerRepository(Protocol):
    def get(self, learner_id: str, tenant_id: str | None = None) -> LearnerProfile: ...
    def save(self, profile: LearnerProfile, tenant_id: str | None = None) -> LearnerProfile: ...
    def add_goal(self, learner_id: str, goal: str, tenant_id: str | None = None) -> LearnerProfile: ...
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
    ) -> LearnerProfile: ...
    def append_history(
        self,
        learner_id: str,
        event: dict,
        tenant_id: str | None = None,
    ) -> LearnerProfile: ...
    def list_profiles(self, tenant_id: str | None = None) -> list[LearnerProfile]: ...


class ExerciseRepository(Protocol):
    def create_id(self) -> str: ...
    def save(self, exercise: Exercise) -> Exercise: ...
    def get(self, exercise_id: str, tenant_id: str | None = None) -> Exercise | None: ...
    def list_for_learner(self, learner_id: str, tenant_id: str | None = None) -> list[Exercise]: ...
