"""Durable LangGraph checkpointing.

Uses the official ``langgraph-checkpoint-sqlite`` saver for single-instance
durability (interrupt/resume survives restarts) and the in-memory saver for
throwaway tests. This replaces an earlier bespoke saver that pickled the entire
checkpoint map into one SQLite row on every write and depended on ``MemorySaver``
internals — the official saver is incremental, versioned, and maintained.

For multi-instance / horizontal scale, swap ``SqliteSaver`` for
``langgraph.checkpoint.postgres.PostgresSaver`` behind the same factory.
"""

from __future__ import annotations

import sqlite3

from langgraph.checkpoint.memory import MemorySaver

from .settings import get_settings


def build_checkpointer():
    """Return a checkpointer per settings, falling back to memory on any error."""
    settings = get_settings()
    if settings.graph_checkpointer_backend == "memory":
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
