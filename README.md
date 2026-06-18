<div align="center">

# Adaptive GenAI Learning Tutor

**A Deep Agent that helps learners master Generative AI topics through diagnostic assessment, personalized learning paths, grounded exercises, and deterministic grading.**

[![Live Demo](https://img.shields.io/badge/Live_Demo-tutor--ui-10b981?style=for-the-badge&logo=railway&logoColor=white)](https://tutor-ui-production.up.railway.app)
[![API Docs](https://img.shields.io/badge/API_Docs-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://adaptive-genai-learning-tutor-production.up.railway.app/docs)
[![LangSmith](https://img.shields.io/badge/Tracing-LangSmith-1c3c3c?style=for-the-badge&logo=langchain&logoColor=white)](https://smith.langchain.com)

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-deepagents-1c3c3c?style=flat-square&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](https://opensource.org/licenses/MIT)
[![OWASP](https://img.shields.io/badge/Security-OWASP_Audited-green?style=flat-square&logo=owasp&logoColor=white)](SECURITY.md)
[![Tests](https://img.shields.io/badge/Tests-39_Passing-success?style=flat-square&logo=pytest&logoColor=white)](tests/)

*Built for Week 3 of the Mastering Agentic AI Bootcamp | The Gen Academy*

</div>

---

## Live Demo

| | URL |
|---|---|
| **Frontend App** | [https://tutor-ui-production.up.railway.app](https://tutor-ui-production.up.railway.app) |
| **Backend API** | [https://adaptive-genai-learning-tutor-production.up.railway.app](https://adaptive-genai-learning-tutor-production.up.railway.app) |
| **API Docs** | [https://adaptive-genai-learning-tutor-production.up.railway.app/docs](https://adaptive-genai-learning-tutor-production.up.railway.app/docs) |
| **Health Check** | [https://adaptive-genai-learning-tutor-production.up.railway.app/health](https://adaptive-genai-learning-tutor-production.up.railway.app/health) |

---

## The One-Liner (Agent Framework Primer)

> My agent helps **learners** master **Generative AI concepts** in a **web app + MCP interface**, replacing the **hours of unstructured self-study with no feedback loop**. It **diagnoses knowledge gaps, recommends study paths, generates exercises, and grades answers** on its own using **7 tools across 4 specialized subagents**, hands off to a human **before persisting progress changes**, and I'll know it works when a learner can **complete a diagnostic → exercise → grading cycle** in under **5 minutes** with **deterministic, source-cited feedback**.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [The Agent Framework](#the-agent-framework)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Build Journey: Start to Finish](#build-journey-start-to-finish)
5. [Local Development](#local-development)
6. [Railway Deployment](#railway-deployment)
7. [Supabase Integration](#supabase-integration)
8. [LangSmith Tracing](#langsmith-tracing)
9. [Security Hardening (OWASP)](#security-hardening-owasp)
10. [Demo Flow](#demo-flow)
11. [MCP Server Integration](#mcp-server-integration)
12. [What I Learned](#what-i-learned)
13. [Resources](#resources)

---

## Project Overview

This project is my Week 3 submission for the Mastering Agentic AI Bootcamp. I chose to build my own use case: an **Adaptive Learning Tutor** that demonstrates:

- **Multi-agent orchestration** with specialized subagents
- **Stateful graph flows** with checkpointing and resumption
- **Human-in-the-loop gates** for consequential actions
- **Tool failure handling** with graceful degradation
- **Source grounding** - every answer cites the research corpus
- **Deterministic validation** - grading happens in code, not LLM judgment

### Why This Use Case?

Most AI tutors are just chat wrappers. They hallucinate, can't track what you know, and give generic feedback. I wanted to build something that:

1. **Actually assesses** what the learner knows before teaching
2. **Retrieves from a curated corpus** instead of making things up
3. **Grades deterministically** using rubrics, not vibes
4. **Remembers progress** across sessions
5. **Asks for approval** before saving state changes

---

## The Agent Framework

### Agent Goal
Take a learner through a complete learning cycle: diagnose → recommend path → generate exercise → grade answer → track progress.

### Where Do People Use It?
- Web chat interface (Vite + React)
- MCP server for enterprise AI assistants (Claude Desktop, etc.)
- REST API for programmatic access

### What Steps Does It Take?

1. **Diagnostic Assessment** - Understand what the learner wants to learn and evaluate current knowledge
2. **Path Recommendation** - Generate a prerequisite-aware study sequence grounded in the corpus
3. **Exercise Generation** - Author a skill-appropriate exercise with a deterministic rubric
4. **Answer Grading** - Score the response using code-based rubric matching
5. **Progress Commit** - Save the results (with human approval)

### Tools (What It Can Do)

| Tool | Type | Description |
|------|------|-------------|
| `search_course_material` | Read | RAG search over the genai_research corpus |
| `assess_skills` | Read | Evaluate learner's current knowledge level |
| `view_progress` | Read | Retrieve learner's progress and mastery levels |
| `recommend_path` | Read | Generate personalized study sequence |
| `next_exercise` | Write | Author and persist an exercise |
| `grade_answer` | Write | Deterministic grading + mastery update |
| `commit_progress` | Write | Persist progress (HUMAN APPROVAL REQUIRED) |

### Memory
- **Session memory**: Conversation history within a thread
- **Cross-session memory**: `/memories/` store for learner notes and preferences
- **Checkpointed state**: SQLite/Postgres for resumable conversations

### Hard Limits (What It Should Never Do)
- Never invent information not in the corpus
- Never override deterministic grades with LLM judgment
- Never persist progress without human approval
- Never expose other learners' data (tenant isolation)

### Human-in-the-Loop
The `commit_progress` tool is gated by `interrupt_on`. When the agent wants to save progress, it pauses and asks for approval. The learner can review and either approve or reject.

### Error Handling
- Tool failures return structured error messages
- Agent retries with exponential backoff for transient failures
- Graceful degradation to cached/fallback responses
- `recursion_limit` prevents runaway agent loops

### Success Metric
A learner completes diagnostic → exercise → grading with source-cited feedback in under 5 minutes, 8 out of 10 times.

---

## Architecture Deep Dive

### Deep Agent Orchestration

The tutor uses the **deepagents** framework (LangChain's agent layer on LangGraph):

```
                       ┌──────────────────────────────────────┐
   Learner message     │       Tutor Orchestrator Agent       │
        │              │  (plans, delegates, assembles)       │
        └─────────────▶│  write_todos → task → commit_progress│
                       └───┬───────────┬───────────┬──────────┘
                       task│       task│       task│       task│
                    ┌──────▼─┐  ┌──────▼───┐  ┌────▼─────┐  ┌──▼────────┐
                    │diagnos-│  │  path-   │  │ exercise-│  │  grader-  │
                    │  tic   │  │ planner  │  │  author  │  │  critic   │
                    │ assess │  │ recommend│  │  author  │  │ grade     │
                    │ + view │  │  path    │  │ exercise │  │ (determin)│
                    └────────┘  └──────────┘  └──────────┘  └───────────┘
                           │           │            │              │
                           └───────────┴────────────┴──────────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │   SHARED STATE      │
                                   │ files + memories    │
                                   └─────────────────────┘
```

### Key Components

| Deep Agents Concept | Implementation |
|---------------------|----------------|
| **Planning** | Orchestrator calls `write_todos` (built into deepagents) |
| **Subagents** | 4 specialists: diagnostic, path-planner, exercise-author, grader-critic |
| **Isolated context** | Each subagent gets only its relevant tools + prompt |
| **Skills** | Progressive disclosure via `SKILL.md` files (socratic-tutoring, exercise-design, feedback-style) |
| **Deterministic validation** | Grading/mastery computed in Python, not LLM |
| **Memory** | `/memories/` via Store (cross-session) |
| **Human-in-the-loop** | `commit_progress` uses `interrupt_on` |
| **Runaway protection** | `recursion_limit` in agent runtime |

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11+, Pydantic |
| **Agent Framework** | deepagents (LangChain + LangGraph) |
| **LLM** | Nebius Token Factory (Llama 3.1 70B) / Qwen-Plus via DashScope |
| **Vector Search** | Local sparse embeddings / pgvector |
| **State** | SQLite locally, PostgreSQL in production |
| **Frontend** | Vite + React + Tailwind CSS |
| **MCP** | FastMCP server for tool exposure |
| **Deployment** | Railway (backend + frontend), Supabase (database) |
| **Tracing** | LangSmith |

---

## Build Journey: Start to Finish

### Phase 1: Foundation (Day 1)

**Goal**: Get a working FastAPI backend with corpus ingestion.

1. **Set up the project structure**
   ```bash
   mkdir adaptive-genai-learning-tutor && cd $_
   uv init
   ```

2. **Built the research corpus** (`genai_research/`)
   - Created topic summaries for RAG, vector databases, prompt engineering, AI agents, MCP, LangSmith, LangGraph, LangChain, evals, and observability
   - Each topic has `topic_summary.json` with content, prerequisites, and citations
   - Used `build_genai_research_corpus.py` to structure and validate

3. **Implemented core backend modules**
   - `backend/corpus.py` - Document loading and management
   - `backend/vector_search.py` - Sparse embeddings and similarity search
   - `backend/learner.py` - Progress tracking and mastery model
   - `backend/exercise.py` - Exercise generation and storage
   - `backend/grading.py` - Deterministic rubric-based grading

4. **Created FastAPI routes**
   - `GET /health` - Health check
   - `GET /progress/{learner_id}` - View progress
   - `POST /chat` - Main conversation endpoint
   - `POST /exercise` - Generate exercise
   - `POST /answer` - Submit and grade answer

5. **Ran locally**
   ```bash
   uv run uvicorn backend.main:app --reload
   # Tested with curl and verified /docs
   ```

### Phase 2: Deep Agent Integration (Day 2)

**Goal**: Replace simple chat with full multi-agent orchestration.

1. **Added deepagents dependency**
   ```toml
   # pyproject.toml
   dependencies = [
       "deepagents>=0.6.10",
       "langchain>=1.0,<2.0",
       "langgraph>=1.0",
       "langchain-openai>=1.0",
   ]
   ```

2. **Created grounding document** (`backend/grounding/genai_tutor.md`)
   - Mission statement
   - Ten skill topics
   - Mastery model (exposure → developing → proficient)
   - Grounding rules (retrieve before teaching, never invent)

3. **Wrote skills** (`backend/skills/`)
   - `socratic-tutoring/SKILL.md` - Diagnose first, teach from sources
   - `exercise-design/SKILL.md` - Match type to mastery, write rubrics
   - `feedback-style/SKILL.md` - Report deterministic verdict, name next step

4. **Implemented agent tools** (`backend/agent_tools.py`)
   - Context-bound wrappers that inject learner/tenant from request
   - LLM never sees or supplies IDs directly

5. **Defined subagents** (`backend/agent.py`)
   ```python
   DIAGNOSTIC = {
       "name": "diagnostic",
       "description": "Assesses learner knowledge and views progress",
       "tools": [search_course_material, assess_skills, view_progress],
       "skills": ["/skills/socratic-tutoring"],
   }
   # ... path-planner, exercise-author, grader-critic
   ```

6. **Assembled the deep agent**
   ```python
   create_deep_agent(
       model=ChatOpenAI(model="qwen-plus", base_url=DASHSCOPE),
       system_prompt=ORCHESTRATOR_PROMPT,
       subagents=[DIAGNOSTIC, PATH_PLANNER, EXERCISE_AUTHOR, GRADER_CRITIC],
       backend=CompositeBackend(...),
       interrupt_on={"commit_progress": True},
       checkpointer=build_checkpointer(),
   )
   ```

7. **Tested the agent loop**
   ```bash
   uv run python scripts/demo_flow.py
   # Verified: diagnostic → path → exercise → grade → commit
   ```

### Phase 3: Frontend Development (Day 2-3)

**Goal**: Build a polished chat interface.

1. **Created Vite + React app** (`tutor-ui/`)
   ```bash
   cd tutor-ui && npm create vite@latest . -- --template react
   npm install
   ```

2. **Implemented components**
   - `TutorChat.jsx` - Main chat interface with streaming
   - `ProgressPanel.jsx` - Visual mastery indicators
   - `ExerciseCard.jsx` - Exercise display and answer submission
   - `SourceCitations.jsx` - Linked references to corpus

3. **Added Tailwind styling**
   ```bash
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

4. **Connected to backend API**
   - Environment variable `VITE_API_URL`
   - Fetch calls to `/chat`, `/progress`, `/exercise`, `/answer`

### Phase 4: Local Deployment & Testing (Day 3)

**Goal**: Verify everything works end-to-end locally.

1. **Environment setup**
   ```bash
   cp .env.example .env
   # Added QWEN_API_KEY
   ```

2. **Ran full test suite**
   ```bash
   uv run pytest                              # 39 tests passing
   uv run python scripts/check_all.py         # All gates green
   uv run python scripts/api_contract_smoke.py
   uv run python scripts/corpus_immutability_check.py
   ```

3. **Manual testing flow**
   - Started backend: `uv run uvicorn backend.main:app --reload`
   - Started frontend: `cd tutor-ui && npm run dev`
   - Completed full learning cycle in browser

### Phase 5: Railway Deployment (Day 3-4)

**Goal**: Deploy backend and frontend to Railway.

1. **Backend service setup**
   - Created `Procfile`:
     ```
     web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - Created `railway.json` with build commands
   - Set environment variables in Railway dashboard:
     - `QWEN_API_KEY`
     - `TUTOR_ENV=production`
     - `TUTOR_CORS_ORIGINS=https://tutor-ui-production.up.railway.app`

2. **Frontend service setup**
   - Created `tutor-ui/server.mjs` for static serving
   - Created `tutor-ui/railway.json`
   - Set `VITE_API_URL` to backend Railway URL

3. **Deployed**
   ```bash
   railway up
   ```

4. **Verified production**
   - Tested `/health` endpoint
   - Ran through full chat flow
   - Checked CORS headers working

### Phase 6: Supabase Integration (Day 4)

**Goal**: Add persistent PostgreSQL storage for production.

1. **Created Supabase project**
   - Set up new project in Supabase dashboard
   - Noted `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`

2. **Applied schema** (`supabase/schema.sql`)
   - `learners` table
   - `exercises` table
   - `progress_events` table
   - `audit_events` table

3. **Optional: pgvector for embeddings**
   ```sql
   -- supabase/migrations/002_optional_pgvector.sql
   create extension if not exists vector;
   create table corpus_embeddings (...);
   create function match_corpus_embeddings (...);
   ```

4. **Updated Railway environment**
   ```bash
   TUTOR_REPOSITORY_BACKEND=supabase
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJ...
   ```

5. **Tested persistence**
   - Created learner, completed exercise
   - Restarted service, verified data persisted

### Phase 7: LangSmith Tracing (Day 4-5)

**Goal**: Full observability into agent behavior.

1. **Configured LangSmith**
   ```bash
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=lsv2_pt_xxx
   LANGSMITH_PROJECT=adaptive-tutor-deep-agent
   ```

2. **Generated demo traces**
   ```bash
   LANGSMITH_TRACING=true uv run python scripts/generate_demo_traces.py
   ```

3. **Explored in dashboard**
   - Viewed nested trace tree
   - Saw orchestrator → subagent delegation
   - Inspected tool calls and responses
   - Identified latency bottlenecks

4. **Key insights from traces**
   - Diagnostic subagent makes 2-3 corpus searches
   - Exercise generation takes longest (LLM drafting)
   - Grading is fast (deterministic)
   - Human-in-the-loop shows as interrupt state

### Phase 8: MCP Server (Day 5)

**Goal**: Expose tutor tools for enterprise AI assistants.

1. **Implemented FastMCP server** (`mcp_server/server.py`)
   ```python
   @server.tool()
   async def tutor_search_course_material(query: str, k: int = 5):
       """Search the GenAI research corpus."""
       return search_impl(query, k)
   ```

2. **Registered tools**
   - `tutor_search_course_material`
   - `tutor_assess_skills`
   - `tutor_get_next_exercise`
   - `tutor_submit_answer`
   - `tutor_view_progress`
   - `tutor_recommend_path`
   - `tutor_review_cohort_progress` (educator+)
   - `tutor_assign_learning_path` (educator+)
   - `tutor_audit_source_grounding` (admin)
   - `tutor_escalate_learning_gap` (admin)

3. **Tested**
   ```bash
   uv run python mcp_server/server.py --smoke
   ```

4. **Created `.mcp.json`** for client discovery

### Phase 9: Security Hardening (Day 5-6)

**Goal**: Production-grade security following OWASP frameworks.

1. **Ran OWASP audit** using Claude Code with custom prompt
   - OWASP Top 10 Web (2025)
   - OWASP Top 10 LLM (2025)
   - OWASP Agentic AI (2026)

2. **Remediated 21 critical/high findings**

   | Finding | Fix |
   |---------|-----|
   | Prompt injection | 30+ regex patterns in `input_filter.py` |
   | JWT HS256 allowed | Blocked symmetric algorithms, RS256+ only |
   | Memory leakage | Per-tenant namespace isolation |
   | Unbounded tokens | Daily per-user token budgets |
   | State tampering | HMAC-SHA256 signatures |
   | Missing audit logs | Security event tracking |
   | Wildcard CORS | Production validation |

3. **Created security documentation**
   - `SECURITY.md` - Vulnerability reporting
   - `.github/dependabot.yml` - Automated dependency updates

4. **Verified all tests pass**
   ```bash
   uv run pytest  # 39 tests passing
   ```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) package manager

### Quick Start

```bash
# Clone
git clone https://github.com/dglabsxyz/adaptive-genai-learning-tutor.git
cd adaptive-genai-learning-tutor

# Backend
uv sync
cp .env.example .env
# Edit .env: add QWEN_API_KEY

# Frontend
cd tutor-ui && npm install && cd ..

# Run
uv run uvicorn backend.main:app --reload  # Terminal 1
cd tutor-ui && npm run dev                 # Terminal 2
```

### URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Run Tests
```bash
uv run pytest
uv run python scripts/check_all.py
```

---

## Railway Deployment

### Backend Service

1. Create new Railway project
2. Add service from GitHub repo
3. Set environment variables:
   ```
   QWEN_API_KEY=your-key
   TUTOR_ENV=production
   TUTOR_AUTH_MODE=local  # or jwt/oidc for production
   TUTOR_CORS_ORIGINS=https://your-frontend.railway.app
   ```
4. Deploy

### Frontend Service

1. Add another service pointing to `tutor-ui/`
2. Set environment variables:
   ```
   VITE_API_URL=https://your-backend.railway.app
   ```
3. Deploy

---

## Supabase Integration

### Setup

1. Create Supabase project
2. Run schema migration:
   ```sql
   -- From supabase/schema.sql
   ```
3. Add to Railway environment:
   ```
   TUTOR_REPOSITORY_BACKEND=supabase
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJ...
   ```

### Optional: pgvector

For production-grade vector search:
```sql
-- supabase/migrations/002_optional_pgvector.sql
```

Set `TUTOR_VECTOR_PROVIDER=pgvector` and `TUTOR_VECTOR_TENANT_ID`.

---

## LangSmith Tracing

### Configuration

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_xxx
LANGSMITH_PROJECT=adaptive-tutor-deep-agent
```

### What You'll See

1. **Orchestrator traces** - Top-level agent decisions
2. **Subagent delegation** - `task` calls to specialists
3. **Tool invocations** - Each search, grade, commit
4. **Interrupt states** - Human-in-the-loop pauses
5. **Token usage** - Per-call and cumulative

### Generate Demo Traces

```bash
LANGSMITH_TRACING=true uv run python scripts/generate_demo_traces.py
```

Then explore in the [LangSmith dashboard](https://smith.langchain.com).

---

## Security Hardening (OWASP)

This project was audited against three OWASP frameworks:

| Framework | Version | Findings Remediated |
|-----------|---------|---------------------|
| OWASP Top 10 Web | 2025 | 8 |
| OWASP Top 10 LLM | 2025 | 7 |
| OWASP Agentic AI | 2026 | 6 |

### Key Security Controls

| Control | File | Description |
|---------|------|-------------|
| Prompt injection defense | `input_filter.py` | 30+ regex patterns |
| JWT security | `settings.py`, `auth.py` | RS256+ only, HS256 blocked |
| Memory isolation | `agent.py` | Per-tenant namespace prefixes |
| Token budgets | `token_budget.py` | Daily per-user limits |
| State integrity | `state_integrity.py` | HMAC-SHA256 signatures |
| Audit logging | `audit.py` | Security event tracking |
| Rate limiting | `rate_limit.py` | Per-action fixed windows |

### Run Your Own Audit

Use the included `OWASP_Security_Audit_Prompt.md` with Claude Code or similar.

See also: [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook)

---

## Demo Flow

### Complete Learning Cycle

1. **Start a conversation**
   ```
   User: "I want to learn about RAG and AI agents"
   ```

2. **Agent runs diagnostic**
   - Searches corpus for RAG and agent topics
   - Assesses current knowledge level
   - Returns skill assessment

3. **Request a learning path**
   ```
   User: "What should I study first?"
   ```
   - Agent recommends prerequisite-aware sequence
   - Each topic links to corpus sources

4. **Generate an exercise**
   ```
   User: "Give me an exercise on RAG"
   ```
   - Exercise-author subagent creates question
   - Rubric is deterministic, grounded in corpus

5. **Submit answer**
   ```
   User: "I would retrieve relevant documents using vector similarity,
          ground the answer in source snippets with citations..."
   ```

6. **Receive graded feedback**
   - Deterministic rubric matching
   - Score with covered/missed criteria
   - Source citations for learning more

7. **Approve progress commit**
   - Human-in-the-loop gate
   - Review what will be saved
   - Approve or reject

---

## MCP Server Integration

### Run the Server

```bash
uv run python mcp_server/server.py
```

### Smoke Test

```bash
uv run python mcp_server/server.py --smoke
```

### Available Tools

| Tool | Role | Description |
|------|------|-------------|
| `tutor_search_course_material` | All | Search the GenAI corpus |
| `tutor_assess_skills` | All | Run diagnostic |
| `tutor_get_next_exercise` | All | Generate exercise |
| `tutor_submit_answer` | All | Submit and grade |
| `tutor_view_progress` | All | View progress |
| `tutor_recommend_path` | All | Get study path |
| `tutor_review_cohort_progress` | Educator+ | Cohort analytics |
| `tutor_assign_learning_path` | Educator+ | Assign paths |
| `tutor_audit_source_grounding` | Admin | Verify citations |
| `tutor_escalate_learning_gap` | Admin | Flag gaps |

---

## What I Learned

### Technical Insights

1. **Subagent isolation matters** - Giving each subagent only its relevant tools prevents confusion and reduces hallucination
2. **Deterministic validation is key** - Letting code grade (not LLM) makes the system trustworthy
3. **Human-in-the-loop is simple with deepagents** - Just set `interrupt_on` for consequential tools
4. **LangSmith traces are invaluable** - Without them, debugging multi-agent flows is impossible
5. **pgvector is production-ready** - The Supabase integration was smooth

### Process Insights

1. **Start with the framework** - Filling out the agent framework first saved hours of confusion
2. **Test locally first** - Railway deploys take time; catch issues locally
3. **Security isn't optional** - The OWASP audit found real vulnerabilities I would have shipped

### What I'd Do Differently

1. **Add evals earlier** - Should have built a test dataset from day 1
2. **Use structured outputs** - Would make grader-critic responses machine-readable
3. **Add voice** - ElevenLabs integration would make this more accessible

---

## Resources

### Project Links
- [GitHub Repository](https://github.com/dglabsxyz/adaptive-genai-learning-tutor)
- [OWASP Security Audit Prompt](OWASP_Security_Audit_Prompt.md)
- [Security Policy](SECURITY.md)

### External References
- [deepagents Documentation](https://github.com/langchain-ai/deepagents)
- [LangSmith](https://smith.langchain.com)
- [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook)
- [Railway Deployment](https://railway.app)
- [Supabase](https://supabase.com)

---

## License

MIT License - See LICENSE file for details.

---

*Built for Week 3 of the Mastering Agentic AI Bootcamp | The Gen Academy*
