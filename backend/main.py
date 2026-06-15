"""FastAPI entrypoint for the Adaptive GenAI Learning Tutor."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .analytics import cohort_progress, evidence_timeline, intervention_recommendations, learner_export
from .audit import current_request_id, read_audit_events, write_audit_event
from .auth import Identity, get_identity, require_learner_access, require_role
from .config import configure_langsmith, ensure_data_dir
from .corpus import corpus_stats
from .dependencies import get_vector_index
from .graph import resume_tutor_turn, run_tutor_turn
from .infographics import generate_infographic
from .models import (
    AnswerRequest,
    AnswerResponse,
    APIResponse,
    ChatRequest,
    ChatResponse,
    ChatResumeRequest,
    DiagnosticRequest,
    DiagnosticResponse,
    ExerciseRequest,
    ExerciseResponse,
    HealthResponse,
    ProgressResponse,
    SourceSearchResponse,
    StudyPlanRequest,
    StudyPlanResponse,
)
from .observability import configure_logging, request_context_middleware
from .rate_limit import enforce_rate_limit
from .settings import get_settings
from .stores import reset_learner_progress
from .source_governance import (
    citation_audit,
    index_status,
    retrieval_evaluation_report,
    source_quality_report,
)
from .supabase_store import supabase_enabled
from .tools import (
    search_course_material_impl,
    tutor_assess_skills_impl,
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
    tutor_view_progress_impl,
)

configure_langsmith()
ensure_data_dir()
configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_vector_index().ensure()
    yield

app = FastAPI(
    title="Adaptive GenAI Learning Tutor",
    description="Local-first tutor grounded in the genai_research corpus.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(request_context_middleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": exc.detail,
            },
            "request_id": current_request_id(),
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": exc.errors(),
            },
            "request_id": current_request_id(),
        },
    )


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    stats = corpus_stats()
    return {
        "ok": True,
        "corpus": stats,
        "vector_index_ready": True,
        "supabase_enabled": supabase_enabled(),
        "repository_backend": settings.active_repository_backend,
    }


@app.get("/identity", response_model=APIResponse)
def identity(identity: Identity = Depends(get_identity)) -> dict:
    return {
        "identity": identity.model_dump(),
        "auth_mode": settings.auth_mode,
        "local_identity_switcher": settings.app_env == "local",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, identity: Identity = Depends(get_identity)) -> dict:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    require_learner_access(identity, body.learner_id)
    enforce_rate_limit("chat", tenant_id=identity.tenant_id, user_id=identity.user_id)
    return run_tutor_turn(
        learner_id=body.learner_id,
        message=body.message,
        thread_id=body.thread_id,
        tenant_id=identity.tenant_id,
    )


@app.post("/chat/resume", response_model=ChatResponse)
def chat_resume(body: ChatResumeRequest, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, body.learner_id)
    enforce_rate_limit("chat", tenant_id=identity.tenant_id, user_id=identity.user_id)
    return resume_tutor_turn(
        learner_id=body.learner_id,
        resume=body.resume,
        thread_id=body.thread_id,
        tenant_id=identity.tenant_id,
    )


@app.post("/diagnostic", response_model=DiagnosticResponse)
def diagnostic(body: DiagnosticRequest, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, body.learner_id)
    return tutor_assess_skills_impl(
        learner_id=body.learner_id,
        goal=body.goal,
        answers=body.answers,
        tenant_id=identity.tenant_id,
    )


@app.post("/exercise", response_model=ExerciseResponse)
def exercise(body: ExerciseRequest, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, body.learner_id)
    enforce_rate_limit("exercise", tenant_id=identity.tenant_id, user_id=identity.user_id)
    return tutor_get_next_exercise_impl(
        learner_id=body.learner_id,
        skill=body.skill,
        goal=body.goal,
        exercise_type=body.exercise_type,
        tenant_id=identity.tenant_id,
    )


@app.post("/answer", response_model=AnswerResponse)
def answer(body: AnswerRequest, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, body.learner_id)
    enforce_rate_limit("answer", tenant_id=identity.tenant_id, user_id=identity.user_id)
    return tutor_submit_answer_impl(
        learner_id=body.learner_id,
        exercise_id=body.exercise_id,
        answer=body.answer,
        tenant_id=identity.tenant_id,
    )


@app.get("/progress/{learner_id}", response_model=ProgressResponse)
def progress(learner_id: str, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, learner_id)
    return tutor_view_progress_impl(learner_id=learner_id, tenant_id=identity.tenant_id)


@app.get("/progress/{learner_id}/evidence", response_model=APIResponse)
def progress_evidence(
    learner_id: str,
    skill: str | None = None,
    identity: Identity = Depends(get_identity),
) -> dict:
    require_learner_access(identity, learner_id)
    return evidence_timeline(learner_id=learner_id, skill=skill, tenant_id=identity.tenant_id)


@app.get("/progress/{learner_id}/export", response_model=APIResponse)
def export_progress(learner_id: str, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, learner_id)
    return learner_export(learner_id=learner_id, tenant_id=identity.tenant_id)


@app.post("/progress/{learner_id}/reset", response_model=APIResponse)
def reset_progress_endpoint(
    learner_id: str,
    payload: dict | None = None,
    identity: Identity = Depends(get_identity),
) -> dict:
    """Reset a learner's mastery state. Guarded: requires explicit confirmation and is audited."""
    require_learner_access(identity, learner_id)
    body = payload or {}
    if not body.get("confirm"):
        raise HTTPException(status_code=400, detail='Reset is destructive; resend with {"confirm": true}.')
    return reset_learner_progress(
        learner_id=learner_id,
        tenant_id=identity.tenant_id,
        scope=body.get("scope", "all"),
    )


@app.post("/study-plan", response_model=StudyPlanResponse)
def study_plan(body: StudyPlanRequest, identity: Identity = Depends(get_identity)) -> dict:
    require_learner_access(identity, body.learner_id)
    return tutor_recommend_path_impl(
        learner_id=body.learner_id,
        goal=body.goal,
        tenant_id=identity.tenant_id,
    )


@app.post("/infographic", response_model=APIResponse)
def infographic_endpoint(payload: dict, identity: Identity = Depends(get_identity)) -> dict:
    """Generate a source-backed SVG infographic and verify its text is legible (Qwen3-VL)."""
    topic = (payload or {}).get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
    enforce_rate_limit("infographic", tenant_id=identity.tenant_id, user_id=identity.user_id)
    return generate_infographic(
        topic,
        tenant_id=identity.tenant_id,
        learner_id=identity.user_id,
        k=int((payload or {}).get("k", 5)),
    )


@app.get("/sources/search", response_model=SourceSearchResponse)
def source_search(
    q: str = Query(..., min_length=1),
    k: int = 5,
    identity: Identity = Depends(get_identity),
) -> dict:
    enforce_rate_limit("source_search", tenant_id=identity.tenant_id, user_id=identity.user_id)
    return search_course_material_impl(query=q, k=k, tenant_id=identity.tenant_id)


@app.get("/cohort/progress", response_model=APIResponse)
def cohort_progress_endpoint(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"educator", "admin"})
    return cohort_progress(tenant_id=identity.tenant_id)


@app.get("/cohort/interventions", response_model=APIResponse)
def cohort_interventions_endpoint(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"educator", "admin"})
    return intervention_recommendations(tenant_id=identity.tenant_id)


@app.get("/admin/source-quality", response_model=APIResponse)
def admin_source_quality(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"admin"})
    return source_quality_report()


@app.get("/admin/index-status", response_model=APIResponse)
def admin_index_status(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"admin"})
    return index_status()


@app.post("/admin/index/rebuild", response_model=APIResponse)
def admin_rebuild_index(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"admin"})
    get_vector_index(rebuild=True)
    payload = index_status()
    write_audit_event("index_rebuild", tenant_id=identity.tenant_id, user_id=identity.user_id, role=identity.role)
    return payload


@app.get("/admin/retrieval-evaluation", response_model=APIResponse)
def admin_retrieval_evaluation(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"admin"})
    return retrieval_evaluation_report()


@app.get("/admin/audit-events", response_model=APIResponse)
def admin_audit_events(
    learner_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    identity: Identity = Depends(get_identity),
) -> dict:
    require_role(identity, {"admin"})
    return {
        "events": read_audit_events(
            tenant_id=identity.tenant_id,
            learner_id=learner_id,
            event_type=event_type,
            limit=limit,
        )
    }


@app.get("/admin/integrations", response_model=APIResponse)
def admin_integrations(identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"admin"})
    return {
        "repository_backend": settings.active_repository_backend,
        "supabase_enabled": supabase_enabled(),
        "vector_provider": settings.vector_provider,
        "llm_provider": settings.llm_provider,
        "langsmith_tracing": bool(settings.langsmith_tracing),
    }


@app.post("/admin/citation-audit", response_model=APIResponse)
def admin_citation_audit(payload: dict, identity: Identity = Depends(get_identity)) -> dict:
    require_role(identity, {"admin"})
    return citation_audit(payload)
