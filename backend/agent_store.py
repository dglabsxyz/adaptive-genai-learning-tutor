"""Durable cross-session memory store for the deep-agent tutor.

The deep agent serves its ``/memories/`` namespace from a langgraph ``BaseStore``
(via the deepagents ``StoreBackend``). The default ``InMemoryStore`` is
process-local, so every learner note written to ``/memories/`` is lost on each
process restart — including every Railway redeploy. For durable memory that
survives restarts, set ``TUTOR_AGENT_STORE_BACKEND=postgres`` with a
``DATABASE_URL``; the factory then uses the official
``langgraph.store.postgres.PostgresStore`` (install the ``postgres`` extra).
Every backend falls back to in-memory on any error so startup never crashes.

This mirrors ``backend/checkpoints.py`` deliberately: same lazy-import of the
optional Postgres dependency, the same manual context-manager entry so the
connection lives for the whole process, the same idempotent ``setup()``, and the
same graceful fallback to memory. Checkpoints persist the conversation thread;
this store persists the learner's durable memories.
"""

from __future__ import annotations

import logging

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from .settings import get_settings

logger = logging.getLogger("backend.agent_store")


def _build_postgres_store(database_url: str) -> BaseStore:
    """Open a shared PostgresStore and run idempotent setup.

    Kept separate so the factory stays readable and so tests can monkeypatch it
    without a live Postgres. Returns a store whose connection stays open for the
    process lifetime (the app holds a single store via ``build_tutor_agent``'s
    ``lru_cache``).
    """
    from langgraph.store.postgres import PostgresStore

    # from_conn_string yields a context manager; enter it manually so the
    # connection lives for the whole process (mirrors checkpoints._build_postgres_saver).
    store_cm = PostgresStore.from_conn_string(database_url)
    store = store_cm.__enter__()
    store.setup()  # idempotent: creates the store tables if missing
    return store


def build_store() -> BaseStore:
    """Return a BaseStore per settings, falling back to memory on any error."""
    settings = get_settings()
    backend = settings.agent_store_backend
    if backend == "postgres":
        if not settings.database_url:
            logger.warning(
                "agent store backend is 'postgres' but DATABASE_URL is unset; using in-memory memories"
            )
            return InMemoryStore()
        try:
            return _build_postgres_store(settings.database_url)
        except Exception:  # pragma: no cover - durability is best-effort; never crash startup
            logger.warning("postgres store unavailable; falling back to in-memory memories", exc_info=True)
            return InMemoryStore()
    return InMemoryStore()
