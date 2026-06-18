"""Unit coverage for the deep-agent memory store factory backend selection.

Mirrors ``tests/test_checkpointer_backends.py``: the postgres branch (including
graceful fallback to in-memory) is covered without requiring a live Postgres, so
the offline gate stays deterministic and needs no ``postgres`` extra. The
in-memory default is what every offline run and the live demo use.
"""

import pytest
from langgraph.store.memory import InMemoryStore

import backend.agent_store as agent_store
from backend.agent_store import build_store
from backend.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_backend_returns_in_memory_store(monkeypatch):
    monkeypatch.delenv("TUTOR_AGENT_STORE_BACKEND", raising=False)
    get_settings.cache_clear()

    assert isinstance(build_store(), InMemoryStore)


def test_memory_backend_returns_in_memory_store(monkeypatch):
    monkeypatch.setenv("TUTOR_AGENT_STORE_BACKEND", "memory")
    get_settings.cache_clear()

    assert isinstance(build_store(), InMemoryStore)


def test_postgres_backend_without_url_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("TUTOR_AGENT_STORE_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TUTOR_DATABASE_URL", raising=False)
    get_settings.cache_clear()

    assert isinstance(build_store(), InMemoryStore)


def test_postgres_backend_with_url_uses_postgres_store(monkeypatch):
    monkeypatch.setenv("TUTOR_AGENT_STORE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example:5432/postgres")
    get_settings.cache_clear()

    captured: dict[str, str] = {}
    sentinel = object()

    def fake_build(url: str):
        captured["url"] = url
        return sentinel

    monkeypatch.setattr(agent_store, "_build_postgres_store", fake_build)

    store = build_store()

    assert store is sentinel
    assert captured["url"] == "postgresql://u:p@db.example:5432/postgres"


def test_postgres_backend_with_failing_store_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("TUTOR_AGENT_STORE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example:5432/postgres")
    get_settings.cache_clear()

    def boom(url: str):
        raise RuntimeError("no postgres reachable")

    monkeypatch.setattr(agent_store, "_build_postgres_store", boom)

    assert isinstance(build_store(), InMemoryStore)
