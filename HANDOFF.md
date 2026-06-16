# HANDOFF — Adaptive GenAI Learning Tutor (resume guide)

**Status: shipped.** The enterprise build, Qwen integration, LangSmith tracing,
Supabase persistence, and a live Railway deployment are all done and verified
end-to-end (2026-06-15). This doc is written so a new session can pick up cleanly:
it records the live resources, how to connect the browser, what was fixed, the
gotchas that cost time, and the small optional follow-ups that remain.

**Session 2 update (2026-06-15).** Optional follow-ups #3–#5 are now done:
full Supabase schema coverage (answers / study_plans / audit_events now written;
`skill_progress.source_refs` round-trips via migration 003, applied live and
verified by `scripts/verify_supabase_coverage.py`), throwaway learner rows
deleted (only `demo-learner` remains), legacy `.env` names reconciled to the
`TUTOR_*` convention (backward-compat fallbacks kept), an opt-in Postgres graph
checkpointer added, and the Railway builder switched to **Railpack**. Remaining:
the LangSmith demo video (#1) and the Mac-only frontend e2e (#2). **Action
required: `git push` from the Mac to ship the Railpack switch** (see §4/§5).

**Session 3 update (2026-06-16) — Deep-Agent refactor (full replace).** The hand-built
LangGraph brain was replaced with the course's **`deepagents`** framework so the project can be
walked through like the Session 2 "Deep Agent" tutorial. What changed:
- **New agent layer:** `backend/agent.py` (orchestrator + 4 subagents: `diagnostic`,
  `path-planner`, `exercise-author`, `grader-critic`), `backend/agent_tools.py` (context-bound
  tools + HITL `commit_progress`), `backend/agent_runtime.py` (the `/chat` runtime, same response
  contract as before). `backend/grounding/genai_tutor.md` + `backend/skills/{socratic-tutoring,
  exercise-design,feedback-style}/SKILL.md` (progressive disclosure).
- **Full replace:** `/chat` now runs the deep agent and **requires `QWEN_API_KEY`** (no
  deterministic fallback for orchestration). `backend/graph.py` is now a thin deprecation shim
  re-exporting `agent_runtime`.
- **Model fix:** the old default `qwen3.7-plus` is not a real DashScope model; standardized on
  **`qwen-plus`** (verified tool-calling). Settings default updated.
- **Deps bumped:** `langchain>=1.0`, `langchain-core>=1.0`, `langchain-openai`, `deepagents>=0.6.10`,
  `langgraph>=1.0`; **Python floor raised to 3.12** (deepagents needs it). `uv.lock` re-locked.
- **LangSmith:** traces now route to a NEW project **`adaptive-tutor-deep-agent`** (`.env` updated);
  `scripts/generate_demo_traces.py` rewritten to drive the deep agent for the dashboard demo.
- **Tests reworked + green (31 passed offline):** graph-routing/reset/resume graph tests replaced
  with offline deep-agent wiring tests; the rest kept.
- **From-scratch walkthrough:** `docs/REBUILD_FROM_SCRATCH.md` (the GitHub-as-tutorial deliverable).
- **Verified live:** deepagents + Qwen + subagent delegation run end-to-end and a nested trace tree
  lands in `adaptive-tutor-deep-agent` (orchestrator → task → subagent).
- **Do on the Mac (sandbox can't delete/rename files):** optional cleanup
  `git rm backend/graph.py` (it's now just a shim) and
  `git mv tests/test_graph_routing.py tests/test_agent_wiring.py`; then commit + push. Railway
  already has `QWEN_API_KEY`; the next deploy builds the langchain-1.0 + deepagents stack on
  Python 3.12 via Railpack — re-verify `/health` and a `/chat` turn after it builds.

**Session 4 update (2026-06-16) — §8 #1 + #2 done, plus a production-blocking agent loop fixed.**
Implemented the two top-ranked §8 follow-ups and, in the course of verifying them live, found and
fixed a loop that made `/chat` hang/500 on simple inputs. What changed:
- **§8 #2 — `PostgresStore` for `/memories/` (DONE).** New `backend/agent_store.py` mirrors
  `backend/checkpoints.py` (lazy import, manual context-manager entry, idempotent `setup()`, graceful
  fallback). New setting **`TUTOR_AGENT_STORE_BACKEND`** (`memory` default | `postgres`) reuses
  `DATABASE_URL`; `backend/agent.py` now calls `build_store()` instead of `InMemoryStore()`.
  `.env.example` documents it; 5 tests in `tests/test_agent_store_backends.py`. **Note:** like the
  checkpointer, real Postgres persistence needs the optional `postgres` extra installed in the build
  (the default Railway `uv sync` skips extras) — otherwise it logs a warning and falls back to memory.
- **§8 #1 — agent-level LangSmith eval (DONE).** New `scripts/run_agent_eval.py` builds a LangSmith
  dataset **`adaptive-tutor-agent`** (5 cases: goal / exercise / grade / commit / advice) and runs
  `client.evaluate` over `agent_runtime.run_tutor_turn` with two behavioral evaluators
  (`produced_output`, `matches_expected_behavior`). Gated on `QWEN_API_KEY` **and** `LANGSMITH_API_KEY`
  (skips offline, exit 0). Routes the experiment + nested agent traces to `adaptive-tutor-deep-agent`.
  Flags: `--limit N`, `--only <thread>` (e.g. `commit`), `--no-upload` (dry run), `--max-concurrency`.
- **Loop fix (enterprise hardening; was pre-existing, NOT from the two follow-ups).** Root cause: the
  orchestrator + subagents treated the corpus as a filesystem and burned their step budget on
  `ls`/`glob`/`grep`/`read_file` chasing paths from `genai_tutor.md` (e.g. `coverage_report.json`,
  `instructors/`) that don't exist on the agent's virtual FS, looping to `recursion_limit=80`. Fixes:
  (a) reworded `backend/grounding/genai_tutor.md` so corpus categories are clearly *not* files;
  (b) hardened `ORCHESTRATOR_PROMPT` (it **delegates**, does not retrieve; never FS-spelunk; one
  diagnosis/path/exercise/grade per turn then STOP); (c) added `SUBAGENT_FS_GUARDRAIL` to all four
  subagents; (d) `agent_runtime._invoke` now catches `GraphRecursionError` and returns a clean,
  contract-shaped `RECURSION_FALLBACK_MESSAGE` (logged + still traced) instead of a 500/hang.
- **Verified.** Offline gates green: **pytest 38** (was 31; +5 store, +1 prompt-guard, +1
  recursion-fallback), api/corpus/demo/MCP smokes pass, corpus immutable (386 files). Live: the agent
  now **converges** (orchestrator → `view_progress` → `task` → subagent authors a real exercise →
  final answer, ~42 s) and a live experiment **`adaptive-tutor-agent-f19f8822`** landed in
  `adaptive-tutor-deep-agent` with both evaluators at **1.00** (the `commit`/HITL case).
- **Run the FULL 5-example eval on the Mac** (the sandbox caps each shell call at 45 s and a single
  2-subagent "goal" turn exceeds that): `LANGSMITH_TRACING=true TUTOR_REPOSITORY_BACKEND=json uv run
  python scripts/run_agent_eval.py`. The dataset already holds all 5 examples.
- **⚠️ Prod still runs the OLD looping agent.** The loop fix is local only; **push from the Mac + let
  Railway redeploy** before trusting prod `/chat` (today it can hang/500 on simple messages — confirmed
  live: `/chat` returned no response within 40 s while `/health` was fine).
- **Do on the Mac (sandbox can't delete/rename/commit):** commit the new files
  (`backend/agent_store.py`, `scripts/run_agent_eval.py`, `tests/test_agent_store_backends.py`) and the
  edits; the optional §8 #9 cleanup (`git rm backend/graph.py`, `git mv tests/test_graph_routing.py
  tests/test_agent_wiring.py`) is still outstanding.

---

## 0. How to resume (local)

```bash
# from the project root
uv sync                               # installs deps incl. langgraph-checkpoint-sqlite, cairosvg
uv run python scripts/check_all.py    # full backend gate suite (frontend steps need Node)
```

- `.env` is auto-loaded for real runs (uvicorn / MCP / scripts) and skipped under
  pytest so gates stay deterministic.
- **Sandbox note:** the macOS `.venv` cannot be reused from the Linux tool sandbox
  (interpreter mismatch + the mount blocks lockfile removal). In the sandbox, build
  a throwaway env elsewhere: `UV_PROJECT_ENVIRONMENT=/tmp/venv uv sync`, then prefix
  commands with that same var. Long tasks must run **foreground** — background procs
  do not survive across sandbox shell calls (each call is its own PID namespace).

---

## 1. Reusable browser session (Claude in Chrome)

The user is signed into all the dashboards in one Chrome for Testing instance.
**Reuse it — do not open a new browser.**

- **Browser:** `Chrome 4 Testing`
- **deviceId:** `8943f5c6-aac9-4f27-ad17-3c74af143c51` (macOS, local)
- Other connected devices (do NOT use unless asked): `Macbook Chrome`
  (`5479851b-ca29-4074-a66e-040587390055`, macOS), `Browser 1`
  (`0978deea-b091-4999-8358-94c136ba10ff`, Windows).

Connect:

```text
list_connected_browsers                 # confirm 8943f5c6… is present
# (3 browsers are connected — the tooling requires asking the user which one first)
select_browser 8943f5c6-aac9-4f27-ad17-3c74af143c51
tabs_context_mcp { createIfEmpty: true }
navigate <url> ; then get_page_text / read_page
```

**Signed in within that browser:** GitHub (`dglabsxyz`), Railway, Supabase
(OWASP org), LangSmith, Tavily.

**Browser caveats (cost real time last session):**
- **Screenshots time out** on this instance (`Page.captureScreenshot` CDP timeout).
  Drive via `get_page_text`, `read_page` (a11y refs), `find`, and `javascript_tool`
  instead — those all work.
- Programmatic `.click()` is blocked for **popups** (e.g. GitHub/Railway OAuth) and
  for setting some React inputs. For OAuth grants and final "Authorize/Install"
  clicks, hand off to the user. For React inputs, set `.value` via the native
  setter + dispatch `input`/`change` events.

---

## 2. Live resources (IDs + URLs — no secrets here)

**Railway (deployed, healthy):**
- Live URL: **https://adaptive-genai-learning-tutor-production.up.railway.app**
  (`/health`, `/docs`, `/chat`, …). Domain target port **8080**.
- Project `feisty-warmth` = `b8822eef-0333-406a-a98c-09f67a994632`
- Service `adaptive-genai-learning-tutor` = `d9c50342-01d9-496b-8daf-e731a9267061`
- Environment `production` = `8a850a37-00e4-4d7e-8718-0880b041d2d8`
- Builder: **RAILPACK** per `railway.json` (switched from the deprecated NIXPACKS in
  session 2; Railpack has native uv, so `NIXPACKS_UV_VERSION` is no longer required —
  the variable is harmless if left set). **Pending the Mac `git push` + rebuild to go live.**

**GitHub:** `dglabsxyz/adaptive-genai-learning-tutor` (private). Local repo is
initialized with `origin` set; `main` is pushed. `.railwayignore` keeps the upload
to backend + corpus.

**Supabase:** project `igzjdeayqudbjzcchhzx` ("Gen AI Adaptive Learning Tutor",
org `pakooyncnxjtmkvtdhyf` / daniel.gomez@owasp.org, region `us-west-2`).
- Base URL `https://igzjdeayqudbjzcchhzx.supabase.co`.
- 14 tables applied (migration 001); migration **003** adds `skill_progress.source_refs`.
  RLS is enabled on all (the project auto-enables it) with **no policies** — the app uses
  the **service_role** key, which bypasses RLS.
- **Full schema coverage (session 2):** the app now writes `answers` (answer hashed,
  never stored verbatim), `study_plans`, and mirrors `audit_events` (best-effort, gated on
  the Supabase backend, no-op offline) via `backend/enterprise_sink.py`. Migrations are
  applied through the Management API SQL endpoint
  `POST https://api.supabase.com/v1/projects/{ref}/database/query` using the dashboard
  session token — the Studio SQL editor would not mount in the automation browser, but
  that endpoint works headlessly. Re-verify anytime: `uv run python scripts/verify_supabase_coverage.py`.
- Seeded tenant: slug `local`, id **`0507cc0e-4a9f-4468-ab32-b56bd87fc97d`**
  (`TUTOR_LOCAL_TENANT_ID` must be this UUID — the schema's `tenant_id` is a UUID,
  so the default string `"local"` causes a 400).
- The Supabase **MCP** must be connected to the OWASP account to manage this project.

**LangSmith (US region):**
- Workspace (tenant) id **`67b5f775-97d1-4af8-a86f-7f940f1b3429`**, project
  `week3-adaptive-tutor`.
- Traces: https://smith.langchain.com/o/67b5f775-97d1-4af8-a86f-7f940f1b3429/projects/p/8798eb60-95b2-45c2-a5e1-f91a713c2b39
- Experiments: `adaptive-tutor-retrieval`, `adaptive-tutor-grading` (+ datasets).

---

## 3. What was completed this session

1. **LangSmith (was the blocker for the demo video).** The 403 was **not** a bad key
   — the service key just needed its **workspace id**. Fixed in `.env`:
   `LANGSMITH_WORKSPACE_ID`, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=week3-adaptive-tutor`.
   21 trace trees (route → interrupt_guard → dispatch → per-tool spans, incl. vague-goal
   interrupt/resume and the audited reset confirm/decline) plus 2 eval experiments are live.
   Added `scripts/generate_demo_traces.py` (re-run before recording) and `@traceable`
   to the 6 tool impls in `backend/tools.py`. **Demo video material is ready to record.**

2. **Supabase persistence.** Applied `001_enterprise_schema.sql` via MCP, fixed
   `SUPABASE_URL`, confirmed the `service_role` key, set `TUTOR_REPOSITORY_BACKEND=supabase`,
   seeded the `local` tenant, and verified the adapter against the live DB (learner_profiles
   + skill_progress + exercises written with correct tenant scoping). `002_optional_pgvector.sql`
   is **not** applied (only needed for `TUTOR_VECTOR_PROVIDER=pgvector`).

3. **Qwen embedding index.** Fixed the build: the default `QWEN_EMBEDDING_BATCH=10`
   exceeds DashScope's per-request limit for this corpus → set `QWEN_EMBEDDING_BATCH=4`
   (each doc embeds fine alone; batch of the 4 largest is the safe worst case). The dense
   `text-embedding-v4` index (1024-dim, 158 docs) builds with no fallback and scores at
   **parity with TF-IDF** on the 5-query retrieval suite (suite is too small to differentiate).

4. **Frontend gates.** `npm run build`, `npm audit --audit-level=high` (0 vulns), and
   `test:contract` pass. Playwright **e2e** can't run in the Linux sandbox (missing
   Chromium system libs) — run it on the Mac: `cd frontend && npm run test:e2e`.

5. **Railway deploy (from GitHub).** Created the private GitHub repo, pushed, deployed via
   the Railway browser flow, generated the domain (port 8080), set all env vars, and
   **verified live**: `/health` ok, `/chat` 200 with source-backed output, a Supabase write,
   and a LangSmith trace from the deployed app.

---

## 4. Railway gotchas (read before touching the deploy)

- **Variable edits are STAGED.** After changing variables you must click **Deploy**
  ("Apply N changes") or nothing takes effect.
- **Builder is now Railpack** (session 2). Railpack has native uv, so the old
  `NIXPACKS_UV_VERSION` workaround is no longer needed (Nixpacks ran
  `pip install uv==$NIXPACKS_UV_VERSION` and failed with `Invalid requirement: 'uv=='`
  when empty; the var was pinned to `0.11.19`). If you ever revert to NIXPACKS, re-pin it.
  The new optional `postgres` extra is **not** installed by the default Railway build
  (`uv sync` skips extras), so it does not affect the deploy.
- **Secrets must be entered by the user** in Railway → Variables (I can't type secret
  values into fields). Copy each *exactly* from local `.env` — a placeholder/mangled value
  shows as `supabase_enabled:true` in `/health` but then 401s Supabase / 403s LangSmith at runtime.
- The sandbox **cannot run the Railway CLI** (binary download blocked) and the
  `RAILWAY_TOKEN` is read-only (`variableUpsert` → "Not Authorized"). Use the browser.

### Railway env vars (names only — values live in `.env` / dashboard)

Non-secret (safe to set anywhere): `GENAI_RESEARCH_DIR=./genai_research`,
`TUTOR_ENV=production`, `TUTOR_REPOSITORY_BACKEND=supabase`,
`TUTOR_LOCAL_TENANT_ID=0507cc0e-4a9f-4468-ab32-b56bd87fc97d`,
`TUTOR_VECTOR_PROVIDER=local`, `QWEN_EMBEDDING_BATCH=4`,
`SUPABASE_URL=https://igzjdeayqudbjzcchhzx.supabase.co`, `LANGSMITH_TRACING=true`,
`LANGSMITH_PROJECT=week3-adaptive-tutor`,
`LANGSMITH_WORKSPACE_ID=67b5f775-97d1-4af8-a86f-7f940f1b3429`,
`NIXPACKS_UV_VERSION=0.11.19`.

Secret (user pastes the real value): `SUPABASE_KEY` (service_role JWT),
`LANGSMITH_API_KEY`, `QWEN_API_KEY`, `TAVILY_API_KEY`. (`PORT` is injected by Railway.)

---

## 5. Remaining / optional

1. **Record the LangSmith demo video** — material is live (section 2). `scripts/generate_demo_traces.py`
   regenerates the full trace set on demand.
2. **Frontend e2e on the Mac:** `cd frontend && npm install && npm run test:e2e`.
3. ~~Supabase adapter polish~~ **DONE (session 2).** Full schema coverage: `answers`,
   `study_plans`, and `audit_events` are now written, and `skill_progress.source_refs`
   round-trips via migration 003. Verified live by `scripts/verify_supabase_coverage.py`
   (all four checks PASS). Writes are best-effort and gated on the Supabase backend, so the
   json/local path is unchanged and offline-safe.
4. ~~Test data cleanup~~ **DONE (session 2).** `railway-verify3`, `tc-verify`,
   `verify-local-graph`, and `fresh-verify` deleted (FK cascade); only `demo-learner` remains.
5. ~~Optional hardening~~ **DONE (session 2).** Railway builder → **Railpack** (railway.json;
   pending the Mac push to go live); opt-in **Postgres checkpointer** added
   (`TUTOR_GRAPH_CHECKPOINTER_BACKEND=postgres` + `DATABASE_URL`, optional `postgres` extra,
   covered by `tests/test_checkpointer_backends.py`); legacy `.env` names reconciled to
   `TUTOR_*` (dead vars dropped, `APP_ENV`/`CHECKPOINTER_BACKEND`/`SUPABASE_KEY` renamed;
   settings.py keeps backward-compat fallbacks so the live deploy is untouched).

---

## 6. Guardrails (unchanged)

- Do not mutate `genai_research`; do not invent corpus metadata.
- Do not commit secrets — `.env` and the `*apiKey*.csv` are gitignored; the GitHub repo
  was committed with a hardened `.gitignore` (verified no secret files staged).
- Keep local functionality working without Supabase/Railway/paid APIs (Qwen-first,
  deterministic fallback). Cloud integrations stay gated by env vars; flip
  `TUTOR_REPOSITORY_BACKEND=json` for offline/local-only.
- Preserve the demo flow: diagnostic → path → exercise → grade → progress → MCP.
- The user pastes secret values; never transcribe them from dashboards.

---

## 7. Verification

```bash
uv run python scripts/check_all.py          # backend gates (pytest 29, smokes, demo flow)
curl https://adaptive-genai-learning-tutor-production.up.railway.app/health   # live: ok, supabase_enabled:true
```

Live `/chat` smoke (local-auth headers; tenant must be the seeded UUID):

```bash
curl -s -X POST https://adaptive-genai-learning-tutor-production.up.railway.app/chat \
  -H 'Content-Type: application/json' \
  -H 'x-tutor-user-id: demo-learner' \
  -H 'x-tutor-tenant-id: 0507cc0e-4a9f-4468-ab32-b56bd87fc97d' \
  -H 'x-tutor-role: learner' \
  -d '{"learner_id":"demo-learner","message":"I want to learn RAG and AI agents"}'
```

---

## 8. Deep-Agent — next steps & known follow-ups (session 3)

The `/chat` brain is now the `deepagents` orchestrator (see the Session 3 note up top and
`docs/REBUILD_FROM_SCRATCH.md`). Ranked follow-ups for a new session:

1. ~~Agent-level eval dataset~~ **DONE (session 4).** `scripts/run_agent_eval.py` builds the LangSmith
   dataset `adaptive-tutor-agent` (5 message→behavior cases) and runs `client.evaluate` over
   `agent_runtime.run_tutor_turn`; experiment + nested traces route to `adaptive-tutor-deep-agent`.
   Gated on `QWEN_API_KEY` + `LANGSMITH_API_KEY` (skips offline). One live experiment landed
   (`adaptive-tutor-agent-f19f8822`, both evaluators 1.00 on the `commit` case); run the full set on
   the Mac (see the Session 4 note — the sandbox 45 s/call cap can't fit a 2-subagent turn).
2. ~~`PostgresStore` for `/memories/`~~ **DONE (session 4).** `backend/agent_store.py` (`build_store()`)
   swaps `InMemoryStore()` behind **`TUTOR_AGENT_STORE_BACKEND=postgres`** + `DATABASE_URL`, mirroring
   the checkpointer's lazy-import + graceful fallback; `backend/agent.py` now calls it. Covered by
   `tests/test_agent_store_backends.py`. Needs the `postgres` extra installed in the build for real
   persistence (else falls back to memory, same caveat as the checkpointer).
3. **Surface `source_refs` in `/chat` responses.** `agent_runtime._format` returns `source_refs: []`;
   the citations currently live only inside the agent's tool-result messages. Scan the tool messages
   for `source_refs` and populate the structured field so the frontend Sources view works again.
4. **Update the frontend to the new `/chat` contract.** The Vite UI (`frontend/` and `tutor-ui/`) was
   written for the OLD graph response (`intent`, `diagnostic`, `study_plan`). The new shape is
   `{message, source_refs, needs_clarification, interrupt:{action_requests:[…]}}`, and **resume now
   takes `{"decisions":[{"type":"approve"}]}`** (not a string). Update the client + the HITL approve
   flow before demoing the web UI. (Deferred frontend e2e from §5#2 still applies.)
5. **Structured grader verdict.** Give the `grader-critic` subagent a `response_format` so its verdict
   is machine-readable instead of prose.
6. **Expose the agent over MCP.** `mcp_server/server.py` still exposes the raw tutor tools; add an
   `ask_tutor(message)` MCP tool that drives `agent_runtime.run_tutor_turn` for an end-to-end agent
   surface.
7. **Cost / latency.** Each turn is several Qwen calls (planning + delegation + per-subagent), so it is
   slower and more token-heavy than the old deterministic graph. Watch token usage in LangSmith;
   consider a cheaper model for subagents or trimming the orchestrator prompt.
8. **Live integration test.** Add one `@pytest.mark.skipif(no QWEN key)` test that runs a real turn and
   asserts a non-empty `message` + that "save my progress" interrupts on `commit_progress` — complements
   the offline wiring tests in `tests/test_graph_routing.py`.
9. **Optional cleanup you skipped (do on the Mac — the sandbox can't delete/rename):**
   `git rm backend/graph.py` (now just a deprecation shim) and
   `git mv tests/test_graph_routing.py tests/test_agent_wiring.py`.

**Guardrail update:** the old "Qwen-first with deterministic fallback" no longer holds for `/chat` — the
deep agent **requires `QWEN_API_KEY`** (full replace). The offline path is the test suite + the
deterministic tool impls, not a deterministic `/chat`. The demo flow is now
diagnose → path → exercise → grade → **commit (HITL approve)**.

**Status:** deep agent is LIVE in prod (verified; `/chat` returns the new shape). Railway
`LANGSMITH_PROJECT` was updated to **`adaptive-tutor-deep-agent`** (done in the dashboard), so live
traffic and `scripts/generate_demo_traces.py` both trace to that project. Model is **`qwen-plus`**.

### Deep-agent dev notes
- **Sandbox venv:** the repo is now on **langchain 1.0 + deepagents, Python 3.12**. Build a throwaway
  env with `UV_PROJECT_ENVIRONMENT=/tmp/venv2 uv sync` (the macOS `.venv` can't be reused in the Linux
  sandbox). Run tests with `TUTOR_REPOSITORY_BACKEND=json` and no `QWEN_API_KEY` to stay offline (31 pass).
- **Key files:** `backend/agent.py` (orchestrator + 4 subagents + composite backend), `agent_tools.py`
  (context-bound tools via `set_agent_context` + HITL `commit_progress`), `agent_runtime.py` (`/chat`
  runtime), `grounding/genai_tutor.md`, `skills/{socratic-tutoring,exercise-design,feedback-style}/SKILL.md`.
- **Mount limits:** the sandbox mount blocks file **deletion** and `.git/index.lock` removal — all
  commits/pushes happen on the Mac.

---

## 9. Browser / Chrome session (connect to the RIGHT browser)

A new session must reuse the user's signed-in browser — **do not open a new one**.

- **Browser:** `Chrome 4 Testing` — **deviceId `8943f5c6-aac9-4f27-ad17-3c74af143c51`** (macOS, local).
- Other devices that have appeared (do NOT use unless asked): a Windows `Browser 2` /
  `0978deea-b091-4999-8358-94c136ba10ff`.

Connect (Claude in Chrome MCP):
```text
list_connected_browsers            # confirm 8943f5c6… is present
# (when >1 browser is connected the tooling forces an AskUserQuestion to pick one — choose Chrome 4 Testing)
select_browser 8943f5c6-aac9-4f27-ad17-3c74af143c51
tabs_context_mcp { createIfEmpty: true }
navigate <url> ; then get_page_text / read_page / javascript_tool
```

**Signed in within that browser:** GitHub (`dglabsxyz`), Railway, Supabase (OWASP org), LangSmith, Tavily.

**This-session browser findings (save yourself the time):**
- **Screenshots time out** on this instance — drive via `get_page_text`, `read_page`, `find`, and
  `javascript_tool`, never screenshots.
- **Supabase Studio does NOT mount** in this browser (the SQL editor renders an empty shell). Apply DDL
  via the Management API instead: `POST https://api.supabase.com/v1/projects/{ref}/database/query` with
  the dashboard session token from `localStorage['supabase.dashboard.auth.token']` (used in-page; never
  print it). This is how migration 003 was applied.
- **Railway dashboard DOES render**, but fine-grained variable edits via automation are unreliable
  (hover-revealed kebab menus and the Raw Editor don't surface to DOM queries). Project `feisty-warmth`
  URL: `https://railway.com/project/b8822eef-0333-406a-a98c-09f67a994632`; variables deep link:
  `…/service/d9c50342-01d9-496b-8daf-e731a9267061/variables?environmentId=8a850a37-00e4-4d7e-8718-0880b041d2d8`.
  For variable changes, ask the user to do it in the dashboard (the read-only `RAILWAY_TOKEN` returns
  "Not Authorized" for `variableUpsert`).
