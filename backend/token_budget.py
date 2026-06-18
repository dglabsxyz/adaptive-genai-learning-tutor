"""Per-user daily token budget enforcement.

LLM-029: Implements token budgets to prevent cost explosion from runaway agents
or abuse. Tracks estimated token usage per user per day and blocks requests
when the budget is exhausted.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from fastapi import HTTPException, status

from .audit import write_audit_event
from .settings import get_settings

logger = logging.getLogger("backend.token_budget")


@dataclass(frozen=True)
class TokenBudgetDecision:
    allowed: bool
    used: int
    limit: int
    remaining: int
    warning: bool = False  # True if approaching limit


class TokenBudgetStore(Protocol):
    def get_usage(self, scope: str, day: str) -> int: ...
    def increment_usage(self, scope: str, day: str, tokens: int) -> int: ...


class MemoryTokenBudgetStore:
    """In-memory token budget store (resets on restart)."""

    def __init__(self) -> None:
        self._usage: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def get_usage(self, scope: str, day: str) -> int:
        with self._lock:
            return self._usage.get((scope, day), 0)

    def increment_usage(self, scope: str, day: str, tokens: int) -> int:
        with self._lock:
            key = (scope, day)
            self._usage[key] = self._usage.get(key, 0) + tokens
            # Cleanup old entries (keep only today and yesterday)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            yesterday = (datetime.now(timezone.utc).date().toordinal() - 1)
            yesterday_str = datetime.fromordinal(yesterday).strftime("%Y-%m-%d")
            for old_key in list(self._usage):
                if old_key[1] not in {today, yesterday_str}:
                    del self._usage[old_key]
            return self._usage[key]


class SQLiteTokenBudgetStore:
    """SQLite-backed token budget store (persists across restarts)."""

    def __init__(self) -> None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.rate_limit_path  # Reuse rate limit DB
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
                create table if not exists token_budget_usage (
                  scope text not null,
                  day text not null,
                  tokens integer not null,
                  updated_at integer not null,
                  primary key (scope, day)
                )
                """
            )
            connection.execute(
                "create index if not exists idx_token_budget_day on token_budget_usage(day)"
            )

    def get_usage(self, scope: str, day: str) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "select tokens from token_budget_usage where scope = ? and day = ?",
                (scope, day),
            ).fetchone()
            return int(row[0]) if row else 0

    def increment_usage(self, scope: str, day: str, tokens: int) -> int:
        now = int(time.time())
        with self._lock, self._connect() as connection:
            # Cleanup entries older than 7 days
            cutoff_day = (datetime.now(timezone.utc).date().toordinal() - 7)
            cutoff_str = datetime.fromordinal(cutoff_day).strftime("%Y-%m-%d")
            connection.execute("delete from token_budget_usage where day < ?", (cutoff_str,))

            connection.execute(
                """
                insert into token_budget_usage(scope, day, tokens, updated_at)
                values (?, ?, ?, ?)
                on conflict(scope, day)
                do update set tokens = tokens + ?, updated_at = ?
                """,
                (scope, day, tokens, now, tokens, now),
            )
            row = connection.execute(
                "select tokens from token_budget_usage where scope = ? and day = ?",
                (scope, day),
            ).fetchone()
            return int(row[0]) if row else tokens


class TokenBudgetEnforcer:
    """Enforces per-user daily token budgets."""

    def __init__(self) -> None:
        settings = get_settings()
        self.store: TokenBudgetStore
        if settings.rate_limit_backend == "memory":
            self.store = MemoryTokenBudgetStore()
        else:
            self.store = SQLiteTokenBudgetStore()

    def check(self, *, tenant_id: str, user_id: str, estimated_tokens: int = 0) -> TokenBudgetDecision:
        """Check if user can make a request with estimated token usage."""
        settings = get_settings()
        if not settings.token_budget_enabled:
            return TokenBudgetDecision(allowed=True, used=0, limit=0, remaining=0)

        limit = settings.token_budget_daily_limit
        warning_threshold = settings.token_budget_warning_threshold
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        scope = f"{tenant_id}:{user_id}"

        current_usage = self.store.get_usage(scope, today)
        remaining = max(0, limit - current_usage)
        warning = current_usage >= (limit * warning_threshold)

        # Block if current usage already exceeds limit
        if current_usage >= limit:
            return TokenBudgetDecision(
                allowed=False,
                used=current_usage,
                limit=limit,
                remaining=0,
                warning=True,
            )

        return TokenBudgetDecision(
            allowed=True,
            used=current_usage,
            limit=limit,
            remaining=remaining,
            warning=warning,
        )

    def record_usage(self, *, tenant_id: str, user_id: str, tokens: int) -> int:
        """Record token usage for a user. Returns total usage for the day."""
        settings = get_settings()
        if not settings.token_budget_enabled or tokens <= 0:
            return 0

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        scope = f"{tenant_id}:{user_id}"
        return self.store.increment_usage(scope, today, tokens)


_enforcer: TokenBudgetEnforcer | None = None


def get_token_budget_enforcer() -> TokenBudgetEnforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = TokenBudgetEnforcer()
    return _enforcer


def check_token_budget(*, tenant_id: str, user_id: str, estimated_tokens: int = 0) -> TokenBudgetDecision:
    """Check if user can proceed with the request.

    Call this before invoking the LLM. Raises HTTPException if budget exhausted.
    """
    settings = get_settings()
    if not settings.token_budget_enabled:
        return TokenBudgetDecision(allowed=True, used=0, limit=0, remaining=0)

    decision = get_token_budget_enforcer().check(
        tenant_id=tenant_id,
        user_id=user_id,
        estimated_tokens=estimated_tokens,
    )

    if decision.warning and decision.allowed:
        logger.warning(
            "User approaching token budget limit: tenant=%s user=%s used=%d limit=%d",
            tenant_id,
            user_id,
            decision.used,
            decision.limit,
        )

    if not decision.allowed:
        write_audit_event(
            "token_budget_exceeded",
            tenant_id=tenant_id,
            user_id=user_id,
            outcome="blocked",
            metadata={"used": decision.used, "limit": decision.limit},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily token budget exceeded ({decision.used:,}/{decision.limit:,} tokens). "
            "Budget resets at midnight UTC.",
            headers={"X-Token-Budget-Used": str(decision.used), "X-Token-Budget-Limit": str(decision.limit)},
        )

    return decision


def record_token_usage(*, tenant_id: str, user_id: str, tokens: int) -> None:
    """Record token usage after a successful LLM call."""
    if tokens <= 0:
        return

    enforcer = get_token_budget_enforcer()
    total = enforcer.record_usage(tenant_id=tenant_id, user_id=user_id, tokens=tokens)

    settings = get_settings()
    if total >= settings.token_budget_daily_limit:
        logger.warning(
            "User exhausted token budget: tenant=%s user=%s total=%d",
            tenant_id,
            user_id,
            total,
        )
