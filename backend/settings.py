"""Typed runtime settings with safe local defaults."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent

# Honor a local .env for real runs (uvicorn / MCP / scripts) so configured keys
# like QWEN_API_KEY are picked up. Skipped under pytest so the test gates stay
# offline and deterministic regardless of what is in .env. Existing process env
# always wins (override=False).
if "pytest" not in sys.modules and (ROOT_DIR / ".env").exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT_DIR / ".env", override=False)
    except Exception:  # pragma: no cover - dotenv is optional at runtime
        pass


def _path_from_env(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser().resolve()


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _llm_provider_default() -> str:
    """Use Qwen first when a key is present, else stay deterministic.

    An explicit ``TUTOR_LLM_PROVIDER`` always wins so operators can force a mode.
    """
    explicit = os.getenv("TUTOR_LLM_PROVIDER")
    if explicit:
        return explicit
    if os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY"):
        return "qwen"
    return "deterministic"


class AppSettings(BaseModel):
    """Application settings used by API, tools, MCP, and scripts."""

    root_dir: Path = ROOT_DIR
    app_env: str = Field(default="local")
    corpus_dir: Path = Field(default=ROOT_DIR / "genai_research")
    data_dir: Path = Field(default=ROOT_DIR / "data")
    vector_index_path: Path = Field(default=ROOT_DIR / "data" / "vector_index.json")
    learner_store_path: Path = Field(default=ROOT_DIR / "data" / "learners.json")
    exercise_store_path: Path = Field(default=ROOT_DIR / "data" / "exercises.json")
    audit_log_path: Path = Field(default=ROOT_DIR / "data" / "audit_events.jsonl")
    graph_checkpoint_path: Path = Field(default=ROOT_DIR / "data" / "graph_checkpoints.sqlite3")
    rate_limit_path: Path = Field(default=ROOT_DIR / "data" / "rate_limits.sqlite3")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    request_body_limit_bytes: int = 64_000
    auth_mode: Literal["local", "disabled", "jwt", "oidc"] = "local"
    local_tenant_id: str = "local"
    local_user_id: str = "demo-learner"
    local_role: Literal["learner", "educator", "admin"] = "learner"
    auth_jwt_algorithms: list[str] = Field(default_factory=lambda: ["RS256", "HS256"])
    auth_jwt_secret: str | None = None
    auth_jwt_public_key: str | None = None
    auth_issuer: str | None = None
    auth_audience: str | None = None
    oidc_discovery_url: str | None = None
    oidc_jwks_url: str | None = None
    oidc_jwks_cache_ttl_seconds: int = 300
    auth_user_claim: str = "sub"
    auth_tenant_claim: str = "tenant_id"
    auth_role_claim: str = "role"
    auth_require_tenant_claim: bool = False
    graph_checkpointer_backend: Literal["memory", "sqlite", "postgres"] = "sqlite"
    database_url: str | None = None
    # Cross-session /memories/ store for the deep agent. "memory" is process-local
    # (resets on restart); "postgres" durably persists memories via DATABASE_URL.
    agent_store_backend: Literal["memory", "postgres"] = "memory"
    rate_limit_enabled: bool = True
    rate_limit_backend: Literal["memory", "sqlite"] = "sqlite"
    rate_limit_window_seconds: int = 60
    rate_limit_chat: int = 60
    rate_limit_exercise: int = 40
    rate_limit_answer: int = 80
    rate_limit_source_search: int = 120
    rate_limit_mcp_tool: int = 160
    rate_limit_default: int = 300
    repository_backend: Literal["json", "supabase"] = "json"
    vector_provider: Literal["local", "pgvector", "qwen"] = "local"
    llm_provider: Literal["deterministic", "openai", "qwen"] = "deterministic"
    llm_temperature: float = 0.0
    # Qwen / DashScope (OpenAI-compatible) configuration.
    qwen_api_key: str | None = None
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_llm_model: str = "qwen-plus"
    qwen_embedding_model: str = "text-embedding-v4"
    qwen_vl_model: str = "qwen3-vl-plus"
    qwen_image_model: str = "qwen-image-2.0"
    qwen_timeout_seconds: float = 60.0
    qwen_embedding_batch: int = 10
    # Optional: let qwen3.7-plus add a short coaching note to graded answers.
    # Off by default so tests/gates stay deterministic and offline.
    llm_coaching_enabled: bool = False
    langsmith_tracing: str | None = None
    langsmith_project: str | None = None
    langsmith_api_key: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_vector_tenant_id: str | None = None

    @property
    def qwen_enabled(self) -> bool:
        return bool(self.qwen_api_key)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def active_repository_backend(self) -> str:
        if self.repository_backend == "supabase" and self.supabase_enabled:
            return "supabase"
        return "json"

    def rate_limit_for_action(self, action: str) -> int:
        return {
            "chat": self.rate_limit_chat,
            "exercise": self.rate_limit_exercise,
            "answer": self.rate_limit_answer,
            "source_search": self.rate_limit_source_search,
            "mcp_tool": self.rate_limit_mcp_tool,
        }.get(action, self.rate_limit_default)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    data_dir = _path_from_env("TUTOR_DATA_DIR", ROOT_DIR / "data")
    default_cors = ["*"] if os.getenv("TUTOR_ENV", "local").lower() not in {"prod", "production"} else []
    return AppSettings(
        app_env=os.getenv("TUTOR_ENV", os.getenv("APP_ENV", "local")),
        corpus_dir=_path_from_env("GENAI_RESEARCH_DIR", ROOT_DIR / "genai_research"),
        data_dir=data_dir,
        vector_index_path=data_dir / "vector_index.json",
        learner_store_path=data_dir / "learners.json",
        exercise_store_path=data_dir / "exercises.json",
        audit_log_path=data_dir / "audit_events.jsonl",
        graph_checkpoint_path=data_dir / "graph_checkpoints.sqlite3",
        rate_limit_path=data_dir / "rate_limits.sqlite3",
        cors_origins=_csv_env("TUTOR_CORS_ORIGINS", default_cors),
        request_body_limit_bytes=_int_env("TUTOR_REQUEST_BODY_LIMIT_BYTES", 64000),
        auth_mode=os.getenv("TUTOR_AUTH_MODE", "local"),  # type: ignore[arg-type]
        local_tenant_id=os.getenv("TUTOR_LOCAL_TENANT_ID", "local"),
        local_user_id=os.getenv("TUTOR_LOCAL_USER_ID", "demo-learner"),
        local_role=os.getenv("TUTOR_LOCAL_ROLE", "learner"),  # type: ignore[arg-type]
        auth_jwt_algorithms=_csv_env("TUTOR_AUTH_JWT_ALGORITHMS", ["RS256", "HS256"]),
        auth_jwt_secret=os.getenv("TUTOR_AUTH_JWT_SECRET"),
        auth_jwt_public_key=os.getenv("TUTOR_AUTH_JWT_PUBLIC_KEY"),
        auth_issuer=os.getenv("TUTOR_AUTH_ISSUER") or os.getenv("TUTOR_OIDC_ISSUER"),
        auth_audience=os.getenv("TUTOR_AUTH_AUDIENCE") or os.getenv("TUTOR_OIDC_AUDIENCE"),
        oidc_discovery_url=os.getenv("TUTOR_OIDC_DISCOVERY_URL"),
        oidc_jwks_url=os.getenv("TUTOR_OIDC_JWKS_URL"),
        oidc_jwks_cache_ttl_seconds=_int_env("TUTOR_OIDC_JWKS_CACHE_TTL_SECONDS", 300),
        auth_user_claim=os.getenv("TUTOR_AUTH_USER_CLAIM", "sub"),
        auth_tenant_claim=os.getenv("TUTOR_AUTH_TENANT_CLAIM", "tenant_id"),
        auth_role_claim=os.getenv("TUTOR_AUTH_ROLE_CLAIM", "role"),
        auth_require_tenant_claim=_bool_env(
            "TUTOR_AUTH_REQUIRE_TENANT_CLAIM",
            os.getenv("TUTOR_ENV", os.getenv("APP_ENV", "local")).lower() in {"prod", "production"},
        ),
        graph_checkpointer_backend=os.getenv(
            "TUTOR_GRAPH_CHECKPOINTER_BACKEND",
            os.getenv("CHECKPOINTER_BACKEND", "sqlite"),
        ),  # type: ignore[arg-type]
        database_url=os.getenv("TUTOR_DATABASE_URL") or os.getenv("DATABASE_URL"),
        agent_store_backend=os.getenv("TUTOR_AGENT_STORE_BACKEND", "memory"),  # type: ignore[arg-type]
        rate_limit_enabled=_bool_env("TUTOR_RATE_LIMIT_ENABLED", True),
        rate_limit_backend=os.getenv("TUTOR_RATE_LIMIT_BACKEND", "sqlite"),  # type: ignore[arg-type]
        rate_limit_window_seconds=_int_env("TUTOR_RATE_LIMIT_WINDOW_SECONDS", 60),
        rate_limit_chat=_int_env("TUTOR_RATE_LIMIT_CHAT", 60),
        rate_limit_exercise=_int_env("TUTOR_RATE_LIMIT_EXERCISE", 40),
        rate_limit_answer=_int_env("TUTOR_RATE_LIMIT_ANSWER", 80),
        rate_limit_source_search=_int_env("TUTOR_RATE_LIMIT_SOURCE_SEARCH", 120),
        rate_limit_mcp_tool=_int_env("TUTOR_RATE_LIMIT_MCP_TOOL", 160),
        rate_limit_default=_int_env("TUTOR_RATE_LIMIT_DEFAULT", 300),
        repository_backend=os.getenv("TUTOR_REPOSITORY_BACKEND", "json"),  # type: ignore[arg-type]
        vector_provider=os.getenv("TUTOR_VECTOR_PROVIDER", "local"),  # type: ignore[arg-type]
        llm_provider=_llm_provider_default(),  # type: ignore[arg-type]
        llm_temperature=_float_env("LLM_TEMPERATURE", _float_env("TUTOR_LLM_TEMPERATURE", 0.0)),
        qwen_api_key=os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY"),
        qwen_base_url=os.getenv(
            "QWEN_BASE_URL",
            os.getenv("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
        ),
        qwen_llm_model=os.getenv("QWEN_LLM_MODEL", "qwen-plus"),
        qwen_embedding_model=os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v4"),
        qwen_vl_model=os.getenv("QWEN_VL_MODEL", "qwen3-vl-plus"),
        qwen_image_model=os.getenv("QWEN_IMAGE_MODEL", "qwen-image-2.0"),
        qwen_timeout_seconds=_float_env("QWEN_TIMEOUT_SECONDS", 60.0),
        qwen_embedding_batch=_int_env("QWEN_EMBEDDING_BATCH", 10),
        llm_coaching_enabled=_bool_env("TUTOR_LLM_COACHING", False),
        langsmith_tracing=os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2"),
        langsmith_project=os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT"),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_service_role_key=(
            os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        ),
        supabase_vector_tenant_id=os.getenv("TUTOR_VECTOR_TENANT_ID"),
    )
