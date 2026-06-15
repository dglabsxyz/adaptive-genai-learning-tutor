# Project Review — Adaptive GenAI Learning Tutor

**Snapshot:** 2026-06-14 ~23:27Z. **Lens:** PRD/HANDOFF/README + LangChain / LangGraph / LangSmith harness best practices.

> ⚠️ **Moving target.** The codebase was being actively written during this review. Between snapshots the MCP server went 6→10 tools, `backend/` grew from 12 to ~24 modules, the test suite went 11→20 passing, and `.env.example` filled out from a stub. Treat everything below as a point-in-time read; some items may already be in progress or resolved. Re-verify after the build settles.

---

## Executive summary

This is in much better shape than `HANDOFF.md` implies. The handoff describes a bare MVP with Phases 1–6 as future work, but the code already implements most of that roadmap. **At snapshot, every Python quality gate was green:**

- `pytest` → **20 passed**
- `scripts/api_contract_smoke.py` → **ok** (real RBAC: learner `403`, admin `200` on `/admin/integrations`)
- `scripts/corpus_immutability_check.py` → **ok (386 files)**
- `mcp_server/server.py --smoke` → **ok (10 intent tools, auth/role enforced)**

Source-backed grounding, tenant isolation, durable-ish interrupt/resume, and corpus immutability all work. The gaps below are mostly **durability hardening, verification, and doc hygiene** — not missing features.

> Frontend gates (`npm test`, `npm run build`, `npm run test:e2e`, `npm audit`) could **not** be run in this environment — see "Verification still needed."

---

## HANDOFF phase status (vs. what's actually in the code)

| Phase | Intent | Status | Evidence |
|---|---|---|---|
| 1 — Foundations | settings, repos, logging, audit, response models, check command | ✅ Implemented | `settings.py`, `repositories/`, `observability.py`, `audit.py`, `scripts/check_all.py` |
| 2 — Persistence | migrations, Postgres/Supabase repo, tenant IDs, export/backup, migrate | ✅ Implemented | `supabase/migrations/00{1,2}_*.sql`, `repositories/supabase.py`, `scripts/{export,backup,restore,migrate}_*.py` |
| 3 — Auth / RBAC / Tenancy | identity, roles, tenant scoping, RBAC tests | ✅ Implemented | `auth.py`, RBAC enforced in API + MCP, `test_enterprise_foundations.py` |
| 4 — Retrieval / Source governance | corpus/index versions, citation audit, retrieval eval, pgvector adapter | ⚠️ Mostly | `source_governance.py` (`citation_audit`, `retrieval_evaluation_report`), `pgvector_store.py`; **no LangSmith eval harness** |
| 5 — Learner modeling | mastery policy, review scheduler, evidence timeline, cohort analytics | ✅ Implemented | `mastery.py`, `analytics.py`, `scripts/review_scheduler.py` |
| 6 — Production UI / ops | role-aware nav, admin pages, deployment docs | ⚠️ Mostly | `frontend/src/App.jsx` (690 lines, Learner/Educator/Admin/Sources), `docs/deployment.md`; **frontend gates unverified** |

---

## What's left to be done

1. **Update `HANDOFF.md` — it is stale and misleading.** Its "Current State" still describes the MVP and lists Phases 1–6 as future work, but they're largely built. A next agent reading it will redo finished work. *Cheapest, highest-value fix.* Rewrite "Current State" + mark phases done.

2. **The destructive reset/delete flow is a no-op.** `graph.py` interrupts on "delete/reset/wipe progress," but there is **no** `reset_progress`/`delete_progress` implementation anywhere. "delete progress" actually classifies as the `progress` intent and just *views* progress; confirming or declining the interrupt changes nothing. Either implement an audited reset path (endpoint + intent + audit event), or drop the guard so it isn't security theater. (PRD/HANDOFF both call for a *real* guarded destructive action.)

3. **Wire a LangSmith evaluation harness (Phase 4/5).** `citation_audit()` and `retrieval_evaluation_report()` exist as in-app deterministic reports, but there are no LangSmith **datasets + `client.evaluate`** regression experiments for retrieval and grading. Add fixtures for the core topics (LLMs, prompt eng, context eng, RAG, agents, MCP, safety/eval) and an LLM-as-judge (`openevals`) for grading quality, with a deterministic fallback. Tracing is already configured, so this is a natural next step.

4. **Confirm the configurable LLM provider layer.** `TUTOR_LLM_PROVIDER=deterministic` is the only path observed; no LLM provider adapter module was found. HANDOFF wants an *optional* LLM evaluator with deterministic fallback — verify whether that adapter exists and, if not, add it behind the env flag.

5. **(Optional / scale) LangGraph deployment packaging.** The graph runs in-process only; there's no `langgraph.json`. The current checkpointer is single-instance (see Improvement #1), so horizontal scale needs either Postgres checkpoints or LangGraph Platform. Add `langgraph.json` + a Postgres saver if multi-instance durable state is a goal.

---

## What can be improved (quality / harness lens)

1. **Replace the custom checkpointer — highest-impact durability fix.** `backend/checkpoints.py` subclasses `MemorySaver` and **pickles the entire checkpoint state into a single SQLite row on every write**. Problems: O(full-state) write amplification, reaches into `MemorySaver` internals (`self.storage/writes/blobs` — breaks on a LangGraph upgrade), `pickle.loads` of an on-disk blob (security smell), and it's not multi-instance safe. The LangGraph guidance is to use the official `langgraph.checkpoint.sqlite.SqliteSaver` (single instance) or `PostgresSaver` (production). Swap to those and delete the bespoke saver.

2. **Stream graph turns.** `run_tutor_turn` uses `.invoke()`. For chat UX, add `.stream()/astream` (`stream_mode="updates"` for steps, `"messages"` for tokens). Low effort, better perceived latency.

3. **Tracing polish (LangSmith).** `config.py:configure_langsmith()` sets the **legacy** `LANGCHAIN_TRACING_V2`/`LANGCHAIN_PROJECT`; prefer the modern `LANGSMITH_TRACING`/`LANGSMITH_PROJECT` the SDK reads natively. Also add `@traceable` to the key deterministic impls (assess / grade / retrieve) so traces show tool-level spans, not just the LangGraph layer.

4. **Avoid import-time side effects.** `graph.py` runs `tutor_graph = build_tutor_graph()` at module import, which opens/creates the SQLite checkpoint DB on import. Both harness skills flag this. Wrap construction in a lazy factory (`functools.lru_cache`) so importing `backend.graph` stays cheap and side-effect-free.

5. **MCP tool robustness + parity.** (a) Wrap tool bodies so an unexpected impl exception returns a structured error instead of a raw traceback to the client. (b) `tutor_submit_answer` text drops the `evidence` list and `proficiency_delta` that the impl payload carries — surface them for app/MCP parity. (c) `tutor_get_next_exercise` prints `Rubric:` then `Choices:` then the rubric points, so the label is separated from its points — reorder.

6. **Test/CI isolation.** Smoke and demo scripts write `mcp-smoke-learner`, `demo-learner`, `api-smoke-learner` into the **live** `data/` store. Point them at a temp `TUTOR_DATA_DIR` so gates don't mutate real state. (`data/` is gitignored, so this is hygiene, not a leak.)

7. **Dependency hygiene.** Resolve the `StarletteDeprecationWarning` (httpx/testclient) surfaced by pytest. If adopting the items above, declare the new deps (`langgraph-checkpoint-sqlite`/`-postgres`, `openevals`).

---

## Verification still needed

- **Frontend gates** (could not run here): `npm test`, `npm run build`, `npm run test:e2e` (`frontend/e2e/app.spec.mjs`), `npm audit --audit-level=high`.
- **Consolidated gate** end-to-end: `uv run python scripts/check_all.py` (includes the frontend steps + a backup restore-drill).
- **Secret check:** a populated `.env` (~3.6 KB) exists in the project root — confirm it's gitignored and contains no committed secrets.

---

## Bottom line

Strong, genuinely enterprise-shaped work: all Python gates green, real RBAC + tenant isolation, source-backed everything, corpus immutability enforced, 10 intent-oriented MCP tools with auth. The priorities are: **(1) refresh the stale HANDOFF, (2) make the destructive-reset guard real or remove it, (3) swap the bespoke pickle-into-SQLite checkpointer for the official saver, and (4) add a LangSmith eval harness.** Everything else is polish.
