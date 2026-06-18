# Deployment Runbook

## Local

```bash
uv sync
cd frontend && npm install
uv run python scripts/check_all.py
```

Run services:

```bash
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

Local defaults:

| Setting | Value |
|---|---|
| `TUTOR_ENV` | `local` |
| `TUTOR_AUTH_MODE` | `local` |
| `TUTOR_GRAPH_CHECKPOINTER_BACKEND` | `sqlite` |
| `TUTOR_RATE_LIMIT_BACKEND` | `sqlite` |
| `TUTOR_REPOSITORY_BACKEND` | `json` |
| `TUTOR_VECTOR_PROVIDER` | `local` |
| `TUTOR_LLM_PROVIDER` | `deterministic` |

## Staging

Use JSON persistence only for temporary preview environments. For shared staging, set:

```bash
TUTOR_ENV=staging
TUTOR_AUTH_MODE=jwt
TUTOR_AUTH_ISSUER=https://issuer.example
TUTOR_AUTH_AUDIENCE=adaptive-tutor-staging
TUTOR_AUTH_JWT_PUBLIC_KEY=...
TUTOR_CORS_ORIGINS=https://your-staging-frontend.example
TUTOR_GRAPH_CHECKPOINTER_BACKEND=sqlite
TUTOR_RATE_LIMIT_ENABLED=true
TUTOR_REPOSITORY_BACKEND=supabase
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

For OIDC staging, use `TUTOR_AUTH_MODE=oidc` plus `TUTOR_OIDC_DISCOVERY_URL` or `TUTOR_OIDC_JWKS_URL`. Apply `supabase/schema.sql`. Apply `supabase/migrations/002_optional_pgvector.sql` only when `TUTOR_VECTOR_PROVIDER=pgvector`, and set `TUTOR_VECTOR_TENANT_ID` to a seeded tenant UUID.

Required checks:

```bash
uv run python scripts/check_all.py
uv run python scripts/rebuild_index.py
uv run python scripts/export_state.py --output data/staging_backup.json
uv run python scripts/backup_state.py --restore-drill --output-dir data/backups/staging
```

## Production

Set explicit origins and keep local mock identity disabled at the edge or replaced with a production identity provider:

```bash
TUTOR_ENV=production
TUTOR_AUTH_MODE=oidc
TUTOR_AUTH_ISSUER=https://issuer.example
TUTOR_AUTH_AUDIENCE=adaptive-tutor
TUTOR_OIDC_DISCOVERY_URL=https://issuer.example/.well-known/openid-configuration
TUTOR_AUTH_REQUIRE_TENANT_CLAIM=true
TUTOR_CORS_ORIGINS=https://your-production-frontend.example
TUTOR_GRAPH_CHECKPOINTER_BACKEND=sqlite
TUTOR_RATE_LIMIT_ENABLED=true
TUTOR_RATE_LIMIT_BACKEND=sqlite
TUTOR_REPOSITORY_BACKEND=supabase
TUTOR_VECTOR_PROVIDER=local
TUTOR_LLM_PROVIDER=deterministic
```

Operational checks:

- Confirm `/health`, `/admin/integrations`, `/admin/index-status`, and `/admin/source-quality`.
- Schedule `scripts/backup_state.py --restore-drill --output-dir <backup-location>` for JSON/local deployments and keep at least 30 days of backups.
- For Supabase/Postgres, enable managed point-in-time recovery or daily backups in the provider, then run a restore drill into a disposable staging project before each production release.
- Use `scripts/restore_state.py --input <backup.json> --dry-run` before restoring local JSON state; a pre-restore copy is created automatically on real restores.
- Rebuild the local index with `scripts/rebuild_index.py` after corpus updates.
- Keep `genai_research` read-only; runtime state must remain under `TUTOR_DATA_DIR` or Supabase.
