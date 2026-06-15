# Railway deploy runbook

The sandbox can't run the Railway CLI (its binary download is blocked) and this
folder isn't a git repo, so the actual deploy has to run from **your Mac** (CLI)
or via **GitHub**. Everything else is prepared: `railway.json` (NIXPACKS +
`uv run uvicorn`), `Procfile`, `.python-version` (3.13), and `.railwayignore`
(ships only the backend + `genai_research` corpus). Your `RAILWAY_TOKEN` already
authenticates (account token).

## Path A — CLI from your Mac (recommended; no GitHub needed)

```bash
npm i -g @railway/cli
railway login                      # opens browser; or: export RAILWAY_API_TOKEN=<account token>
cd "/Users/dgomez/Week 3 Project"
railway init                       # name it e.g. gen-ai-adaptive-tutor
railway up                         # uploads local code (honors .railwayignore) and builds
railway domain                     # generate a public URL
# then open https://<generated-domain>/health  -> expect {"status":"ok"} (or 200)
```

## Path B — GitHub

```bash
cd "/Users/dgomez/Week 3 Project"
git init && git add . && git commit -m "Adaptive GenAI tutor"
# create a repo on GitHub and push, then:
#   Railway dashboard -> New -> Deploy from GitHub Repo -> pick the repo
```
`.env` is gitignored (secrets stay local); `genai_research` is **not** ignored, so
the corpus is included.

## Environment variables to set on the service

Set these in the Railway dashboard (Service -> Variables) or with
`railway variables --set KEY=value`. `PORT` is injected by Railway automatically.

Non-secret:

```
GENAI_RESEARCH_DIR=./genai_research
TUTOR_ENV=production
TUTOR_REPOSITORY_BACKEND=json          # set to "supabase" once the service_role key is in
TUTOR_VECTOR_PROVIDER=local            # or "qwen"
QWEN_EMBEDDING_BATCH=4
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=week3-adaptive-tutor
LANGSMITH_WORKSPACE_ID=67b5f775-97d1-4af8-a86f-7f940f1b3429
SUPABASE_URL=https://igzjdeayqudbjzcchhzx.supabase.co
```

Secret (paste the values yourself — never commit them):

```
QWEN_API_KEY=...
LANGSMITH_API_KEY=...
TAVILY_API_KEY=...
SUPABASE_KEY=...            # service_role key (only if TUTOR_REPOSITORY_BACKEND=supabase)
```

## Notes

- Health check is `/health` (already in `railway.json`).
- NIXPACKS auto-detects Python 3.13 + `uv` from `.python-version` and `uv.lock`.
- The corpus (~386 files) ships with the build; first request builds the local
  vector index under the ephemeral `data/` dir.
- If you'd rather I create the empty project and set the **non-secret** variables
  for you via the Railway API from here, say so — you'd still run `railway up`
  from your Mac for the code upload and set the secret variables yourself.
