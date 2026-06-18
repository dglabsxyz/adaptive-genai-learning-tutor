"""Runtime configuration compatibility layer for the local-first tutor."""

from __future__ import annotations

import os

from .settings import get_settings

settings = get_settings()

ROOT_DIR = settings.root_dir
CORPUS_DIR = settings.corpus_dir
DATA_DIR = settings.data_dir
VECTOR_INDEX_PATH = settings.vector_index_path
LEARNER_STORE_PATH = settings.learner_store_path
EXERCISE_STORE_PATH = settings.exercise_store_path
AUDIT_LOG_PATH = settings.audit_log_path


def ensure_data_dir() -> None:
    get_settings().data_dir.mkdir(parents=True, exist_ok=True)


def configure_langsmith() -> None:
    """Honor LangSmith env vars while keeping local runs dependency-free.

    Sets both the modern ``LANGSMITH_*`` names (read natively by the current
    SDK) and the legacy ``LANGCHAIN_*`` names for backward compatibility.
    """
    active = get_settings()
    if active.langsmith_tracing:
        os.environ.setdefault("LANGSMITH_TRACING", active.langsmith_tracing)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", active.langsmith_tracing)
    if active.langsmith_project:
        os.environ.setdefault("LANGSMITH_PROJECT", active.langsmith_project)
        os.environ.setdefault("LANGCHAIN_PROJECT", active.langsmith_project)
    if active.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", active.langsmith_api_key)
        os.environ.setdefault("LANGCHAIN_API_KEY", active.langsmith_api_key)
