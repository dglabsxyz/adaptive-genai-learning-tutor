"""Live verification that the Supabase backend persists the full enterprise schema.

Runs the real tutor flow (recommend path -> next exercise -> submit answer)
against the live Supabase project and asserts that rows land in the tables that
used to stay empty (``answers``, ``study_plans``, ``audit_events``) and that
``skill_progress.source_refs`` now round-trips.

Requires the Supabase backend to be configured (SUPABASE_URL + service-role key,
TUTOR_REPOSITORY_BACKEND=supabase). It creates a uniquely-named throwaway learner
and deletes it (with FK cascade) at the end unless ``--keep`` is passed.

    uv run python scripts/verify_supabase_coverage.py
"""

from __future__ import annotations

import sys
import uuid

import httpx

from backend.settings import get_settings
from backend.tools import (
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
)

GOOD_ANSWER = (
    "Retrieve relevant course records with vector search or keyword search before answering, "
    "ground the response in the retrieved source snippets and cite them, preserve uncertainty "
    "when evidence is missing rather than inventing facts, and evaluate retrieval and answer "
    "faithfulness with a held-out question set."
)


def main() -> int:
    keep = "--keep" in sys.argv
    settings = get_settings()
    if settings.active_repository_backend != "supabase":
        print("FAIL: Supabase backend is not active. Set TUTOR_REPOSITORY_BACKEND=supabase "
              "and SUPABASE_URL + service-role key in .env.")
        return 2

    from backend.repositories.supabase import SupabaseREST

    client = SupabaseREST(settings)
    tenant = settings.local_tenant_id
    learner = f"coverage-verify-{uuid.uuid4().hex[:8]}"
    print(f"tenant={tenant}\nlearner={learner}\n")

    # --- Exercise the real flow ---------------------------------------------
    tutor_recommend_path_impl(learner, "learn RAG and AI agents")
    exercise = tutor_get_next_exercise_impl(learner, skill="RAG")["exercise"]
    graded = tutor_submit_answer_impl(learner, GOOD_ANSWER, exercise_id=exercise["id"])
    print(f"graded: score={graded.get('score')} verdict={graded.get('verdict')}\n")

    # --- Assert the rows landed ---------------------------------------------
    def count(table: str, extra: dict[str, str] | None = None) -> int:
        params = {"tenant_id": f"eq.{tenant}", "learner_id": f"eq.{learner}", "select": "*"}
        params.update(extra or {})
        return len(client.get(table, params))

    progress_rows = client.get(
        "skill_progress",
        {"tenant_id": f"eq.{tenant}", "learner_id": f"eq.{learner}", "skill": "eq.RAG", "select": "skill,source_refs"},
    )
    source_refs = progress_rows[0].get("source_refs") if progress_rows else []

    checks = {
        "study_plans row written": count("study_plans") >= 1,
        "answers row written": count("answers") >= 1,
        "audit_events mirrored": count("audit_events") >= 1,
        "skill_progress.source_refs round-trips": bool(source_refs),
    }
    print("Coverage checks:")
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if source_refs:
        print(f"\n  source_refs on RAG skill: {len(source_refs)} ref(s), first title="
              f"{source_refs[0].get('title')!r}")

    # --- Clean up the throwaway learner (FK cascade clears children) ---------
    if not keep:
        base = client.base_url
        resp = httpx.delete(
            f"{base}/learner_profiles",
            headers={**client.headers, "prefer": "return=minimal"},
            params={"tenant_id": f"eq.{tenant}", "learner_id": f"eq.{learner}"},
            timeout=20,
        )
        resp.raise_for_status()
        print(f"\nCleaned up throwaway learner {learner} (cascade).")

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        print(f"\nRESULT: FAIL ({len(failed)} check(s) failed)")
        return 1
    print("\nRESULT: PASS — full enterprise schema coverage verified live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
