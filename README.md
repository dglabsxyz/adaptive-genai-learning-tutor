# Adaptive GenAI Learning Tutor

A production-ready, AI-powered adaptive learning platform demonstrating enterprise-grade GenAI security, deep agent orchestration, and pedagogically-grounded tutoring.

---

## Project Overview

This project showcases a complete end-to-end implementation of an adaptive learning system that:

1. **Assesses learner knowledge** through diagnostic conversations
2. **Generates personalized learning paths** based on knowledge gaps
3. **Creates contextual exercises** grounded in curated source material
4. **Grades responses** with deterministic rubrics and optional LLM coaching
5. **Tracks progress** with persistent state and spaced repetition

The tutor is backed by a research corpus (`genai_research/`) covering Generative AI topics: RAG, vector databases, prompt engineering, AI agents, MCP, and more.

---

## Architecture Highlights

### Deep Agent Orchestration

The `/chat` endpoint is powered by a **Deep Agent** built on the [`deepagents`](https://github.com/langchain-ai/deepagents) framework:

```
                    ┌─────────────────────────────────────────┐
                    │           Orchestrator Agent            │
                    │  - Plans tasks (write_todos)            │
                    │  - Delegates to specialists             │
                    │  - Human-in-the-loop gates              │
                    └──────────────┬──────────────────────────┘
                                   │
         ┌─────────────┬───────────┼───────────┬─────────────┐
         ▼             ▼           ▼           ▼             ▼
   ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
   │Diagnostic│ │   Path    │ │Exercise │ │ Grader  │ │  Memory  │
   │  Agent   │ │ Planner   │ │ Author  │ │ Critic  │ │  Store   │
   └──────────┘ └───────────┘ └─────────┘ └─────────┘ └──────────┘
```

- **Isolated contexts** per subagent for focused tool access
- **On-demand skills** loaded dynamically
- **Cross-session memory** via `/memories/` store
- **Checkpointed state** with explicit resume API

### Multi-Tenant Security

- JWT/OIDC authentication with RS256+ algorithms only (HS256 blocked)
- Per-tenant memory namespace isolation
- Per-user daily token budgets
- Fixed-window rate limiting by action type
- HMAC-SHA256 state integrity protection
- Comprehensive audit logging

### Source-Grounded Learning

All tutor responses cite their sources:

```json
{
  "answer": "RAG retrieves relevant documents using vector similarity...",
  "sources": [
    {
      "title": "RAG Fundamentals",
      "path": "genai_research/topics/rag/topic_summary.json",
      "citations": ["https://arxiv.org/abs/2005.11401"]
    }
  ],
  "grounding_score": 0.92
}
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11+, Pydantic |
| **Agent Framework** | deepagents (LangChain/LangGraph) |
| **LLM Provider** | Qwen (DashScope) / Deterministic fallback |
| **Vector Search** | Local sparse embeddings / pgvector |
| **State Management** | SQLite / PostgreSQL checkpoints |
| **Frontend** | Vite + React + Tailwind CSS |
| **MCP Server** | FastMCP for enterprise tool integration |
| **Deployment** | Railway / Docker / Supabase |

---

## Key Features Demo

### 1. Diagnostic Assessment

The tutor evaluates learner knowledge across topic areas:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-tutor-user-id: demo-learner" \
  -d '{"learner_id": "demo-learner", "message": "I want to learn AI agents"}'
```

Response includes skill assessment:
```json
{
  "skills": {
    "rag": {"level": "developing", "confidence": 0.7},
    "mcp": {"level": "exposure", "confidence": 0.5}
  }
}
```

### 2. Personalized Learning Path

```bash
curl http://localhost:8000/path/demo-learner
```

Returns a sequenced study plan grounded in the corpus.

### 3. Exercise Generation & Grading

```bash
# Generate an exercise
curl -X POST http://localhost:8000/exercise \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "demo-learner", "topic": "rag"}'

# Submit an answer
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "demo-learner", "exercise_id": "...", "answer": "..."}'
```

### 4. Progress Tracking

```bash
curl http://localhost:8000/progress/demo-learner
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/dglabsxyz/adaptive-genai-learning-tutor.git
cd adaptive-genai-learning-tutor

# Install Python dependencies
uv sync

# Install frontend dependencies
cd tutor-ui && npm install && cd ..

# Copy environment template
cp .env.example .env
```

### Running Locally

```bash
# Terminal 1: Backend
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd tutor-ui && npm run dev
```

Open:
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Running Tests

```bash
# All tests
uv run pytest

# Full check suite
uv run python scripts/check_all.py
```

---

## Project Structure

```
├── backend/                 # FastAPI application
│   ├── main.py             # App entry, middleware, routes
│   ├── agent.py            # Deep agent orchestration
│   ├── agent_tools.py      # Subagent tool definitions
│   ├── corpus.py           # Source document management
│   ├── auth.py             # JWT/OIDC authentication
│   ├── input_filter.py     # Prompt injection detection
│   ├── token_budget.py     # Per-user token limits
│   ├── state_integrity.py  # HMAC state protection
│   └── ...
├── tutor-ui/               # React frontend
│   └── src/
│       ├── App.jsx         # Main application
│       ├── TutorChat.jsx   # Chat interface
│       └── ...
├── mcp_server/             # MCP tool server
│   └── server.py           # FastMCP implementation
├── genai_research/         # Knowledge corpus
│   └── topics/             # Topic summaries and citations
├── tests/                  # Test suite
├── scripts/                # Operational utilities
└── docs/                   # Additional documentation
```

---

## Security Architecture

This project implements enterprise-grade security following three OWASP frameworks:

### Frameworks Applied

| Framework | Version | Focus |
|-----------|---------|-------|
| **OWASP Top 10 Web** | 2025 | Traditional web security |
| **OWASP Top 10 LLM** | 2025 | LLM-specific vulnerabilities |
| **OWASP Agentic AI** | 2026 | Multi-agent security |

### Key Security Controls

| Control | Implementation |
|---------|----------------|
| **Prompt Injection Defense** | 30+ regex patterns in `input_filter.py` |
| **JWT Security** | RS256+ only, HS256 blocked (WEB-023) |
| **Memory Isolation** | Per-tenant namespace prefixes (AGT-006) |
| **Token Budgets** | Daily per-user limits (LLM-029) |
| **State Integrity** | HMAC-SHA256 signatures (AGT-008) |
| **Audit Logging** | Security event tracking (WEB-009) |
| **Rate Limiting** | Per-action fixed windows |

### Security Testing

Run your own OWASP security audit using the provided prompt:

```bash
# Use OWASP_Security_Audit_Prompt.md with Claude Code or similar
```

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## MCP Server Integration

The tutor exposes tools via Model Context Protocol for enterprise AI assistants:

```bash
# Run MCP server
uv run python mcp_server/server.py

# Smoke test
uv run python mcp_server/server.py --smoke
```

### Available Tools

| Tool | Role | Description |
|------|------|-------------|
| `tutor_search_course_material` | All | Search the knowledge corpus |
| `tutor_assess_skills` | All | Run diagnostic assessment |
| `tutor_get_next_exercise` | All | Generate personalized exercise |
| `tutor_submit_answer` | All | Submit and grade answer |
| `tutor_view_progress` | All | View learner progress |
| `tutor_recommend_path` | All | Get personalized path |
| `tutor_review_cohort_progress` | Educator+ | Cohort analytics |
| `tutor_assign_learning_path` | Educator+ | Assign paths to learners |
| `tutor_audit_source_grounding` | Admin | Verify citation quality |
| `tutor_escalate_learning_gap` | Admin | Flag systemic gaps |

---

## Environment Variables

### Required for Deep Agent

```bash
QWEN_API_KEY=your-dashscope-api-key
```

### Optional Configuration

```bash
# Environment
TUTOR_ENV=local                    # local | production

# Authentication
TUTOR_AUTH_MODE=local              # local | jwt | oidc
TUTOR_AUTH_JWT_PUBLIC_KEY=...      # RS256 public key
TUTOR_AUTH_ISSUER=https://...      # JWT issuer
TUTOR_AUTH_AUDIENCE=adaptive-tutor # JWT audience

# Rate Limiting
TUTOR_RATE_LIMIT_ENABLED=true
TUTOR_TOKEN_BUDGET_DAILY_LIMIT=100000

# Persistence
TUTOR_REPOSITORY_BACKEND=json      # json | supabase
TUTOR_VECTOR_PROVIDER=local        # local | pgvector

# Tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=adaptive-tutor
```

---

## Deployment

### Railway

```bash
railway up
```

See `railway.json` and `Procfile` for configuration.

### Docker

```bash
docker build -t adaptive-tutor .
docker run -p 8000:8000 adaptive-tutor
```

---

## Further Reading

- [Deployment Guide](docs/deployment.md) - Production deployment details
- [Rebuild From Scratch](docs/REBUILD_FROM_SCRATCH.md) - Deep agent architecture
- [SECURITY.md](SECURITY.md) - Security policy and reporting
- [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook) - Agentic AI security reference

---

## License

MIT License - See LICENSE file for details.

---

## Acknowledgments

- [OWASP Foundation](https://owasp.org/) for security frameworks
- [LangChain](https://langchain.com/) for deepagents framework
- [Anthropic](https://anthropic.com/) for Claude Code security audit assistance
