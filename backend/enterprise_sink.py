"""Best-effort enterprise persistence sink (Supabase relational tables).

When the Supabase repository backend is active, this mirrors graded answers,
recommended study plans, and audit events into their dedicated tables
(``answers``, ``study_plans``, ``audit_events``). Without it, those tables stay
empty because the primary data already lives elsewhere: audit in a JSONL file,
the active plan as JSONB on ``learner_profiles``, and answers only transiently
during grading.

Design contract:
- **No-op + offline-safe under json/local.** Every entry point returns
  immediately unless the Supabase backend is both selected and configured, so
  dev/test runs never touch the network.
- **Best-effort.** All writes are wrapped so a transient Supabase failure is
  logged and swallowed — it must never break answer grading, path
  recommendation, or audit logging on the request hot path.
- **No new model contract.** These are append-only analytical mirrors; the
  authoritative state remains the learner/exercise repositories.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from .models import utc_now
from .settings import get_settings

logger = logging.getLogger("backend.enterprise_sink")


def _supabase_active() -> bool:
    settings = get_settings()
    return settings.repository_backend == "supabase" and settings.supabase_enabled


def _client():
    # Lazy import avoids a circular import at module load
    # (repositories.supabase -> stores -> audit -> enterprise_sink).
    from .repositories.supabase import SupabaseREST

    return SupabaseREST()


def record_answer(
    *,
    tenant_id: str,
    learner_id: str,
    exercise_id: str,
    answer: str,
    score: float | None,
    verdict: str | None,
    covered_points: list[str] | None,
    missed_points: list[str] | None,
) -> None:
    """Persist a graded answer. The raw answer is hashed, never stored verbatim."""
    if not _supabase_active():
        return
    try:
        row = {
            "tenant_id": tenant_id,
            "learner_id": learner_id,
            "exercise_id": exercise_id,
            "answer_hash": hashlib.sha256((answer or "").encode("utf-8")).hexdigest(),
            "answer_length": len(answer or ""),
            "score": score,
            "verdict": verdict,
            "covered_points": covered_points or [],
            "missed_points": missed_points or [],
            "created_at": utc_now(),
        }
        _client().insert("answers", [row])
    except Exception:  # pragma: no cover - best-effort mirror
        logger.warning("answers sink failed for exercise %s", exercise_id, exc_info=True)


def record_study_plan(
    *,
    tenant_id: str,
    learner_id: str,
    goal: str,
    modules: list[dict[str, Any]] | None,
) -> None:
    """Persist a recommended study plan as a point-in-time row (plan history)."""
    if not _supabase_active():
        return
    try:
        _client().insert(
            "study_plans",
            [
                {
                    "tenant_id": tenant_id,
                    "learner_id": learner_id,
                    "goal": goal,
                    "modules": modules or [],
                    "created_at": utc_now(),
                }
            ],
        )
    except Exception:  # pragma: no cover - best-effort mirror
        logger.warning("study_plans sink failed for learner %s", learner_id, exc_info=True)


def mirror_audit_event(event: dict[str, Any]) -> None:
    """Mirror a JSONL audit event into ``audit_events`` (idempotent on event_id)."""
    if not _supabase_active():
        return
    try:
        _client().upsert(
            "audit_events",
            [
                {
                    "tenant_id": event.get("tenant_id"),
                    "event_id": event.get("event_id"),
                    "request_id": event.get("request_id"),
                    "user_id": event.get("user_id"),
                    "role": event.get("role"),
                    "learner_id": event.get("learner_id"),
                    "event_type": event.get("event_type"),
                    "outcome": event.get("outcome", "success"),
                    "metadata": event.get("metadata") or {},
                    "created_at": event.get("at") or utc_now(),
                }
            ],
            "event_id",
        )
    except Exception:  # pragma: no cover - best-effort mirror
        logger.warning("audit_events sink failed for %s", event.get("event_id"), exc_info=True)
