"""Per-tenant/user fixed-window rate limits for API and MCP actions."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status

from .audit import write_audit_event
from .settings import get_settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimitStore(Protocol):
    def increment(self, scope: str, action: str, window_start: int, window_seconds: int) -> int: ...


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self._counts: dict[tuple[str, str, int], int] = {}
        self._lock = threading.Lock()

    def increment(self, scope: str, action: str, window_start: int, window_seconds: int) -> int:
        key = (scope, action, window_start)
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            cutoff = int(time.time()) - (window_seconds * 2)
            for old_key in list(self._counts):
                if old_key[2] < cutoff:
                    del self._counts[old_key]
            return self._counts[key]


class SQLiteRateLimitStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.settings.rate_limit_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("pragma journal_mode=wal")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists rate_limit_counters (
                  scope text not null,
                  action text not null,
                  window_start integer not null,
                  count integer not null,
                  updated_at integer not null,
                  primary key (scope, action, window_start)
                )
                """
            )
            connection.execute(
                "create index if not exists idx_rate_limit_updated_at on rate_limit_counters(updated_at)"
            )

    def increment(self, scope: str, action: str, window_start: int, window_seconds: int) -> int:
        now = int(time.time())
        cutoff = now - (window_seconds * 2)
        with self._lock, self._connect() as connection:
            connection.execute("delete from rate_limit_counters where updated_at < ?", (cutoff,))
            connection.execute(
                """
                insert into rate_limit_counters(scope, action, window_start, count, updated_at)
                values (?, ?, ?, 1, ?)
                on conflict(scope, action, window_start)
                do update set count = count + 1, updated_at = excluded.updated_at
                """,
                (scope, action, window_start, now),
            )
            row = connection.execute(
                """
                select count from rate_limit_counters
                where scope = ? and action = ? and window_start = ?
                """,
                (scope, action, window_start),
            ).fetchone()
        return int(row[0]) if row else 1


class RateLimiter:
    def __init__(self) -> None:
        settings = get_settings()
        self.store: RateLimitStore
        if settings.rate_limit_backend == "memory":
            self.store = MemoryRateLimitStore()
        else:
            self.store = SQLiteRateLimitStore()

    def check(self, *, action: str, tenant_id: str, user_id: str | None) -> RateLimitDecision:
        settings = get_settings()
        limit = max(1, settings.rate_limit_for_action(action))
        window_seconds = max(1, settings.rate_limit_window_seconds)
        now = int(time.time())
        window_start = (now // window_seconds) * window_seconds
        scope = f"{tenant_id}:{user_id or 'anonymous'}"
        count = self.store.increment(scope, action, window_start, window_seconds)
        remaining = max(0, limit - count)
        retry_after = max(1, window_seconds - (now - window_start))
        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=retry_after,
        )


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def enforce_rate_limit(action: str, *, tenant_id: str, user_id: str | None) -> RateLimitDecision:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return RateLimitDecision(allowed=True, limit=0, remaining=0, retry_after_seconds=0)
    decision = get_rate_limiter().check(action=action, tenant_id=tenant_id, user_id=user_id)
    if decision.allowed:
        return decision
    write_audit_event(
        "rate_limit_exceeded",
        tenant_id=tenant_id,
        user_id=user_id,
        outcome="blocked",
        metadata={"action": action, "limit": decision.limit, "retry_after_seconds": decision.retry_after_seconds},
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Rate limit exceeded for {action}. Retry after {decision.retry_after_seconds} seconds.",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )
