"""Pydantic models shared by API, tools, graph, and MCP."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .mastery import next_review_date, status_for_score

MASTERY_STATES = Literal["exposure", "developing", "proficient", "mastered", "review"]
EXERCISE_TYPES = Literal[
    "short_answer",
    "design_critique",
    "architecture_scenario",
    "implementation_prompt",
    "multiple_choice",
]

SKILL_TOPICS = [
    "LLMs",
    "prompt engineering",
    "context engineering",
    "RAG",
    "AI agents",
    "MCP",
    "AI coding",
    "AI safety and evaluation",
    "fine-tuning",
    "multimodal AI",
]


class SourceRef(BaseModel):
    source_id: str
    record_type: str
    slug: str | None = None
    title: str
    path: str
    citations: list[str] = Field(default_factory=list)
    snippet: str | None = None
    last_researched_at: str | None = None


class SearchHit(BaseModel):
    score: float
    source_ref: SourceRef
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillProgress(BaseModel):
    skill: str
    proficiency: float = 0.0
    status: MASTERY_STATES = "exposure"
    attempts: int = 0
    correct_streak: int = 0
    last_reviewed: str | None = None
    next_review: str | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    status_reason: str | None = None
    next_review_reason: str | None = None
    last_change: dict[str, Any] | None = None


class LearnerProfile(BaseModel):
    learner_id: str
    tenant_id: str = "local"
    goals: list[str] = Field(default_factory=list)
    progress: dict[str, SkillProgress] = Field(default_factory=dict)
    active_exercise_id: str | None = None
    study_plan: list[dict[str, Any]] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now())
    updated_at: str = Field(default_factory=lambda: utc_now())


class Exercise(BaseModel):
    id: str
    learner_id: str
    tenant_id: str = "local"
    skill: str
    exercise_type: EXERCISE_TYPES = "short_answer"
    difficulty: MASTERY_STATES = "developing"
    prompt: str
    choices: list[str] = Field(default_factory=list)
    answer_key: list[str] = Field(default_factory=list)
    expected_points: list[str] = Field(default_factory=list)
    rubric: str
    hints: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utc_now())


class ChatRequest(BaseModel):
    learner_id: str = "demo-learner"
    message: str
    thread_id: str | None = None


class ChatResumeRequest(BaseModel):
    learner_id: str = "demo-learner"
    thread_id: str
    resume: str | dict[str, Any]


class DiagnosticRequest(BaseModel):
    learner_id: str = "demo-learner"
    goal: str
    answers: list[str] = Field(default_factory=list)


class StudyPlanRequest(BaseModel):
    learner_id: str = "demo-learner"
    goal: str


class ExerciseRequest(BaseModel):
    learner_id: str = "demo-learner"
    skill: str | None = None
    goal: str | None = None
    exercise_type: EXERCISE_TYPES | None = None


class AnswerRequest(BaseModel):
    learner_id: str = "demo-learner"
    exercise_id: str | None = None
    answer: str


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class HealthResponse(APIResponse):
    ok: bool
    corpus: dict[str, Any]
    vector_index_ready: bool
    supabase_enabled: bool
    repository_backend: str = "json"


class ChatResponse(APIResponse):
    learner_id: str
    thread_id: str | None = None
    message: str | None = None
    needs_clarification: bool | None = None
    interrupt: dict[str, Any] | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class DiagnosticResponse(APIResponse):
    learner_id: str
    goal: str
    summary: str
    diagnostic_questions: list[str] = Field(default_factory=list)
    assessment: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class ExerciseResponse(APIResponse):
    learner_id: str
    exercise: dict[str, Any]
    source_refs: list[SourceRef] = Field(default_factory=list)


class AnswerResponse(APIResponse):
    learner_id: str
    exercise_id: str | None = None
    needs_clarification: bool | None = None
    message: str | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class ProgressResponse(APIResponse):
    learner_id: str
    goals: list[str] = Field(default_factory=list)
    active_exercise_id: str | None = None
    progress: dict[str, dict[str, Any]] = Field(default_factory=dict)
    study_plan: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None = None


class StudyPlanResponse(APIResponse):
    learner_id: str
    goal: str
    summary: str
    modules: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class SourceSearchResponse(APIResponse):
    query: str
    summary: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def next_review_for(status: str) -> str:
    return next_review_date(status)


def status_for_proficiency(score: float) -> str:
    return status_for_score(score)


def default_progress() -> dict[str, SkillProgress]:
    return {skill: SkillProgress(skill=skill) for skill in SKILL_TOPICS}
