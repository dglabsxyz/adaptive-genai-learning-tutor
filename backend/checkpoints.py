"""Durable LangGraph checkpointing.

Uses the official ``langgraph-checkpoint-sqlite`` saver for single-instance
durability (interrupt/resume survives restarts) and the in-memory saver for
throwaway tests. This replaces an earlier bespoke saver that pickled the entire
checkpoint map into one SQLite row on every write and depended on ``MemorySaver``
internals — the official saver is incremental, versioned, and maintained.

For multi-instance / horizontal scale, set ``TUTOR_GRAPH_CHECKPOINTER_BACKEND=postgres``
with a ``DATABASE_URL``; the factory then uses the official
``langgraph.checkpoint.postgres.PostgresSaver`` (install the ``postgres`` extra).
Every backend falls back to in-memory on any error so startup never crashes.
"""

from __future__ import annotations

import logging
import sqlite3

from langgraph.checkpoint.memory import MemorySaver

from .settings import get_settings

logger = logging.getLogger("backend.checkpoints")


def _build_postgres_saver(database_url: str):
    """Open a shared PostgresSaver and run idempotent setup.

    Kept separate so the factory stays readable and so tests can monkeypatch it.
    Returns a saver whose connection stays open for the process lifetime.
    """
    from langgraph.checkpoint.postgres import PostgresSaver

    # from_conn_string yields a context manager; enter it manually so the
    # connection lives for the whole process (the app holds one saver).
    saver_cm = PostgresSaver.from_conn_string(database_url)
    saver = saver_cm.__enter__()
    saver.setup()  # idempotent: creates checkpoint tables if missing
    return saver


def build_checkpointer():
    """Return a checkpointer per settings, falling back to memory on any error."""
    settings = get_settings()
    backend = settings.graph_checkpointer_backend
    if backend == "memory":
        return MemorySaver()
    if backend == "postgres":
        if not settings.database_url:
            logger.warning("checkpointer backend is 'postgres' but DATABASE_URL is unset; using memory")
            return MemorySaver()
        try:
            return _build_postgres_saver(settings.database_url)
        except Exception:  # pragma: no cover - durability is best-effort; never crash startup
            logger.warning("postgres checkpointer unavailable; falling back to memory", exc_info=True)
            return MemorySaver()
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        settings.data_dir.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the saver is shared across FastAPI worker threads.
        connection = sqlite3.connect(str(settings.graph_checkpoint_path), check_same_thread=False)
        saver = SqliteSaver(connection)
        saver.setup()  # idempotent: creates checkpoint tables if missing
        return saver
    except Exception:  # pragma: no cover - durability is best-effort; never crash startup
        # If the sqlite saver package or file is unavailable, keep working in-memory.
        return MemorySaver()
