# Adaptive GenAI Learning Tutor — Web App (`tutor-ui`)

The production frontend for the Adaptive GenAI Learning Tutor. **Vite + React 18 +
React Router + TanStack Query + Tailwind.** It is fully wired to the FastAPI backend —
no mock data.

## What it does

| Page | Backend it uses |
|------|-----------------|
| **Dashboard** | `GET /progress/{learner}`, `GET /health` |
| **Tutor Chat** (flagship) | `POST /chat` + `POST /chat/resume` — the deep agent, with the human-in-the-loop **approve/decline** gate and source citations |
| **Diagnostic** | `POST /diagnostic` |
| **Study Plan** | `POST /study-plan` |
| **Practice (Exercise)** | `POST /exercise`, `POST /answer` (rubric grade, mastery update) |
| **My Progress** | `GET /progress/{learner}` (+ chart), `GET …/export`, `POST …/reset` |
| **Course Catalog / Resources** | `GET /sources/search`, `GET /health` corpus stats |
| **Professor** (educator/admin) | `GET /cohort/progress`, `GET /cohort/interventions`, `GET /admin/*` |

Identity (learner id + role) is sent on every request via `x-tutor-user-id` /
`x-tutor-tenant-id` / `x-tutor-role` headers and is editable from the top bar (the
**role switcher** gates the Professor + admin views).

## Run locally

```bash
cd tutor-ui
npm install
cp .env.example .env      # defaults to a local backend at http://localhost:8000
npm run dev               # http://127.0.0.1:5173
```

Start the backend in another terminal (`uv run uvicorn backend.main:app --reload --port 8000`).
A local backend serves permissive CORS, so the dev server works out of the box.

To point the dev UI at the **deployed** backend, set `VITE_API_URL` in `.env` to the
Railway backend URL — but note you must then add `http://localhost:5173` to the backend's
`TUTOR_CORS_ORIGINS` (prod CORS is closed by default).

## Configuration (`.env`, all `VITE_*`)

| Var | Purpose |
|-----|---------|
| `VITE_API_URL` | Backend base URL (build-time; Vite inlines it). |
| `VITE_TUTOR_TENANT_ID` | `x-tutor-tenant-id`. Must be the seeded UUID for the Supabase-backed backend. |
| `VITE_TUTOR_LEARNER_ID` / `VITE_TUTOR_ROLE` | Default demo learner + role. |
| `VITE_REQUEST_TIMEOUT_MS` | Client timeout (default 90s; agent chat turns are slow). |

## Build / serve

```bash
npm run build     # -> dist/
npm start         # serves dist/ on :PORT (default 8080) with SPA fallback (server.mjs)
```

## Deploy (Railway, second service)

The backend and this SPA are **two services in the same Railway project**.

1. New service → deploy from the same GitHub repo → set **Root Directory = `tutor-ui`**.
   `railway.json` here builds with `npm install && npm run build` and starts `node server.mjs`.
2. Set service variables: `VITE_API_URL = <backend URL>` (and `VITE_TUTOR_TENANT_ID` = seeded UUID).
   `VITE_*` are read at **build** time.
3. Generate a domain for this service.
4. On the **backend** service, set `TUTOR_CORS_ORIGINS = <this SPA's https origin>` and redeploy,
   otherwise the browser blocks the cross-origin API calls.

## Architecture

```
src/
  config.js              env + defaults
  api/
    client.js            fetch wrapper: identity headers, timeout, ApiError
    endpoints.js         one function per backend route
    useApi.js            binds the current identity to every endpoint
    mappers.js           backend payloads -> component shapes
  context/
    SessionContext.jsx   learner id / tenant / role (persisted)
    ThemeContext, ToastContext
  components/            Sidebar, TopBar (identity switcher + health), PageStates, …
  pages/                 one file per route (all wired to the API)
```
