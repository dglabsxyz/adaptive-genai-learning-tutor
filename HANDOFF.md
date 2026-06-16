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
