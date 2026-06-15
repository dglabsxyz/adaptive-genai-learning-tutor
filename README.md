# Adaptive GenAI Learning Tutor

Local-first MVP of a source-backed GenAI tutor over `genai_research`.

## What Runs Locally

- FastAPI backend with tutor endpoints.
- Read-only ingestion of `genai_research`.
- Local sparse embeddings plus JSON vector search under `data/vector_index.json`.
- Typed settings, request IDs, structured logs, local auth/RBAC headers, optional JWT/OIDC auth, rate limits, and append-only audit events.
- JSON repository interfaces by default, with an optional Supabase REST repository path.
- LangChain tools for search, diagnostics, exercises, grading, progress, and recommendations.
- LangGraph router with SQLite-backed checkpoints, explicit resume API, and interrupt guards.
- LangSmith tracing support through environment variables.
- Vite React tutor workspace with Learner, Educator, Admin, and Sources modes.
- FastMCP server exposing learner tools plus enterprise intent tools over the same state.

## Setup

```bash
uv sync
cd frontend
npm install
```

Copy environment defaults if useful:

```bash
cp .env.example .env
```

No secrets are required for the local MVP.

## Environment Variables

- `GENAI_RESEARCH_DIR`: optional override for the corpus path. Defaults to `./genai_research`.
- `TUTOR_DATA_DIR`: optional override for local learner, exercise, and vector data. Defaults to `./data`.
- `TUTOR_ENV`: `local` by default. Set to `production` to remove wildcard CORS defaults.
- `TUTOR_AUTH_MODE`: `local` by default. Local mode accepts `x-tutor-user-id`, `x-tutor-tenant-id`, and `x-tutor-role` headers. Use `jwt` or `oidc` for production Bearer-token validation.
- `TUTOR_AUTH_JWT_SECRET` / `TUTOR_AUTH_JWT_PUBLIC_KEY`: signing material for `TUTOR_AUTH_MODE=jwt`.
- `TUTOR_AUTH_ISSUER` and `TUTOR_AUTH_AUDIENCE`: issuer/audience checks for JWT or OIDC tokens.
- `TUTOR_OIDC_DISCOVERY_URL` or `TUTOR_OIDC_JWKS_URL`: OIDC key discovery. JWKS responses are cached for key rotation.
- `TUTOR_AUTH_USER_CLAIM`, `TUTOR_AUTH_TENANT_CLAIM`, `TUTOR_AUTH_ROLE_CLAIM`: token claim paths used to build the tutor session.
- `TUTOR_AUTH_REQUIRE_TENANT_CLAIM`: require a tenant claim. Defaults to true in production.
- `TUTOR_GRAPH_CHECKPOINTER_BACKEND`: `sqlite` by default. Set `memory` only for throwaway tests.
- `TUTOR_RATE_LIMIT_ENABLED`: enables per-tenant/user fixed-window limits. Defaults to `true`.
- `TUTOR_RATE_LIMIT_BACKEND`: `sqlite` by default. Set `memory` only for throwaway tests.
- `TUTOR_RATE_LIMIT_CHAT`, `TUTOR_RATE_LIMIT_EXERCISE`, `TUTOR_RATE_LIMIT_ANSWER`, `TUTOR_RATE_LIMIT_SOURCE_SEARCH`, `TUTOR_RATE_LIMIT_MCP_TOOL`: per-window limits for high-volume actions.
- `TUTOR_REPOSITORY_BACKEND`: `json` by default. Set to `supabase` only with Supabase env vars.
- `TUTOR_VECTOR_PROVIDER`: `local` by default. Set to `pgvector` only after applying the optional pgvector migration.
- `TUTOR_VECTOR_TENANT_ID`: Supabase tenant UUID used for corpus embeddings when `TUTOR_VECTOR_PROVIDER=pgvector`.
- `TUTOR_LLM_PROVIDER`: `deterministic` by default.
- `LANGSMITH_TRACING`: set to `true` to enable LangSmith-compatible tracing.
- `LANGSMITH_API_KEY`: LangSmith API key.
- `LANGSMITH_PROJECT`: project name, for example `adaptive-genai-learning-tutor`.
- `SUPABASE_URL`: optional production persistence setting.
- `SUPABASE_SERVICE_ROLE_KEY`: optional production persistence setting.
- `VITE_API_URL`: frontend API URL. Defaults to `http://localhost:8000`.

## Run

Backend:

```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Open:

- Backend health: `http://127.0.0.1:8000/health`
- Frontend: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

## Test and Checks

```bash
uv run pytest
uv run python scripts/api_contract_smoke.py
uv run python scripts/corpus_immutability_check.py
uv run python scripts/demo_flow.py
uv run python mcp_server/server.py --smoke
cd frontend && npm test
cd frontend && npm run test:e2e
cd frontend && npm run build
cd frontend && npm audit --audit-level=high
```

The demo script proves diagnostic, path recommendation, exercise generation, answer grading, progress persistence, and shared state for MCP.

Run the consolidated local gate:

```bash
uv run python scripts/check_all.py
```

Operational scripts:

```bash
uv run python scripts/rebuild_index.py
uv run python scripts/export_state.py
uv run python scripts/backup_state.py --restore-drill
uv run python scripts/restore_state.py --input data/state_export.json --dry-run
uv run python scripts/migrate_json_to_postgres.py
uv run python scripts/review_scheduler.py
```

## Demo Flow

1. In the frontend chat, send `I want to learn AI agents.`
2. Confirm the diagnostic marks RAG as developing and MCP as exposure.
3. Click `Path` to refresh the source-backed study plan.
4. Click `Exercise` to generate a RAG exercise.
5. Submit an answer such as:

```text
I would retrieve relevant local corpus records with embeddings and vector search, ground the answer in source snippets and citations, preserve uncertainty for missing fields, and evaluate answer faithfulness plus retrieval quality.
```

6. Check the grade, updated progress, and visible source references.
7. Click the progress refresh button or call `GET /progress/demo-learner`.
8. Run an MCP tool such as `tutor_view_progress` for `demo-learner`; it reads the same local state.

Interrupted chat turns return `needs_clarification: true` with a `thread_id`. Resume the same checkpoint with:

```bash
curl -X POST http://127.0.0.1:8000/chat/resume \
  -H 'Content-Type: application/json' \
  -H 'x-tutor-user-id: demo-learner' \
  -H 'x-tutor-tenant-id: local' \
  -H 'x-tutor-role: learner' \
  -d '{"learner_id":"demo-learner","thread_id":"demo-learner","resume":{"answer":"Retrieve, cite, preserve unknowns, and evaluate faithfulness."}}'
```

## MCP

Run the MCP server:

```bash
uv run python mcp_server/server.py
```

Run a reproducible smoke check without launching an MCP client:

```bash
uv run python mcp_server/server.py --smoke
```

Tools exposed:

- `tutor_search_course_material`
- `tutor_assess_skills`
- `tutor_get_next_exercise`
- `tutor_submit_answer`
- `tutor_view_progress`
- `tutor_recommend_path`
- `tutor_review_cohort_progress`
- `tutor_assign_learning_path`
- `tutor_audit_source_grounding`
- `tutor_escalate_learning_gap`

MCP tools accept optional `tenant_id`, `user_id`, and `role` arguments. Learner role calls are scoped to their own `learner_id`; educator/admin calls can use cohort and governance tools.

The root `.mcp.json` registers the server for MCP-capable clients that support project config files.

## Optional Railway

`railway.json` and `Procfile` run the FastAPI backend. Set required environment variables in Railway, especially `GENAI_RESEARCH_DIR` if the corpus path differs and any LangSmith/Supabase values you choose to enable.

## Optional Supabase

Local JSON storage is the default. `backend/supabase_store.py` only enables Supabase when env vars are present, and `supabase/schema.sql` sketches production tables plus pgvector. The app does not require Supabase for local demos.

The production schema snapshot is in `supabase/schema.sql`; migration files live under `supabase/migrations/`. The pgvector table and `match_corpus_embeddings` RPC are intentionally optional and should only be applied when `TUTOR_VECTOR_PROVIDER=pgvector`.

Deployment notes and the environment matrix are in `docs/deployment.md`.
