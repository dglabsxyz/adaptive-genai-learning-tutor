# Build the Adaptive GenAI Tutor as a Deep Agent — from scratch

This is the walkthrough the judges (and any student) can follow to rebuild the tutor's
agent layer from zero. It mirrors the course's **GTM Deep Agent** tutorial, but instead of
drafting marketing content it runs an adaptive tutoring loop grounded in a real research
corpus, and instead of a notebook it lives in this repo so you can `git clone` and run it.

It uses the **`deepagents`** framework — LangChain's batteries-included agent layer on
LangGraph. You *configure* an orchestrator and subagents; planning, delegation, the
filesystem tools, and the human-in-the-loop machinery come for free.

## Architecture at a glance

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
                    └──────┬─┘  └──────┬───┘  └────┬─────┘  └──┬────────┘
                           └───────────┴─────┬─────┴───────────┘
                                  ┌──────────▼──────────┐
                                  │   SHARED STATE      │
                                  │ files + todos       │
                                  └─────────────────────┘
   Grounding: genai_research corpus   ·   Memory: Store (/memories/, cross-session)
   Model: Qwen (DashScope, OpenAI-compatible)   ·   Tracing: LangSmith
```

| Deep Agents concept | Where it lives here |
|---|---|
| **Planning** | orchestrator calls `write_todos` (free from deepagents) |
| **Subagents** | `backend/agent.py`: `diagnostic`, `path-planner`, `exercise-author`, `grader-critic` |
| **Isolated context** | each subagent is a fresh `task` run with its own tools + prompt |
| **Skills (progressive disclosure)** | `backend/skills/*/SKILL.md` (socratic-tutoring, exercise-design, feedback-style) |
| **Deterministic validation** | grading/mastery are computed in code, not judged by the LLM |
| **Memory** | `/memories/` via a `Store` (learner notes survive across sessions) |
| **Human-in-the-loop** | `commit_progress` runs behind `interrupt_on` approval |
| **Runaway protection** | `recursion_limit` in `backend/agent_runtime.py` |

## Prerequisites

- Python **3.12+** and [uv](https://docs.astral.sh/uv/)
- A **Qwen / DashScope** API key (`QWEN_API_KEY`) — the agent needs a real tool-calling model
- Optional: a **LangSmith** key (`LANGSMITH_API_KEY` + `LANGSMITH_WORKSPACE_ID`) to see the traces
- The `genai_research/` corpus (already in this repo) — the tutor's grounding

```bash
uv sync
cp .env.example .env   # then fill in QWEN_API_KEY (+ LangSmith if you want traces)
```

---

## Step 1 — Dependencies

The agent layer adds `deepagents` and the langchain 1.0 stack on top of the existing
FastAPI/corpus backend (`pyproject.toml`):

```toml
requires-python = ">=3.12,<3.14"
dependencies = [
    "deepagents>=0.6.10",
    "langchain>=1.0,<2.0",
    "langchain-core>=1.0,<2.0",
    "langchain-openai>=1.0",   # ChatOpenAI, pointed at the DashScope endpoint
    "langgraph>=1.0",
    # ... fastapi, httpx, pydantic, langsmith, mcp, etc.
]
```

## Step 2 — Ground the agent

`backend/grounding/genai_tutor.md` holds the brand/domain facts: the mission, the ten skill
topics, the mastery model, what the corpus contains, and the non-negotiable grounding rules
(retrieve before teaching; never invent; grading is deterministic). It is injected verbatim
into the orchestrator prompt — the same pattern as the course's `gen_academy.md`.

## Step 3 — Write the skills (progressive disclosure)

A skill is a `SKILL.md` directory with YAML frontmatter (`name` + `description`). The agent
sees only the description until it decides the skill is relevant, then `read_file`s the body.
We ship three (`backend/skills/`):

- `socratic-tutoring` — diagnose first, teach from cited sources, ask before telling
- `exercise-design` — pick the type by mastery, write a checkable rubric, ground every point
- `feedback-style` — report the deterministic verdict, show covered/missed, name one next step

## Step 4 — Tools: the LLM drafts, code validates

`backend/agent_tools.py` exposes **context-bound** tools. The underlying `*_impl` functions are
learner- and tenant-scoped, but the LLM must never supply (or hallucinate) a learner id or a
tenant UUID — so the wrappers read those from a per-request context variable
(`set_agent_context`) and expose only the semantic arguments:

- `search_course_material(query, k)` — corpus retrieval with citations (every subagent gets it)
- `assess_skills(goal)` / `view_progress()` — diagnostic reads
- `recommend_path(goal)` — ordered, prerequisite-aware plan
- `next_exercise(skill, …)` — author + persist one exercise
- `grade_answer(answer, exercise_id)` — **deterministic** grade + mastery update (code, not LLM)
- `commit_progress(summary)` — the consequential write, gated by human approval

## Step 5 — Backends: files + cross-session memory

`backend/agent.py` wires a `CompositeBackend` (deepagents):

```python
CompositeBackend(
    default=FilesystemBackend(root_dir=AGENT_HOME, virtual_mode=True),  # /diagnostics, /plans, …
    routes={"/memories/": StoreBackend(namespace=lambda ctx: ("tutor",))},  # cross-session
)
```

`virtual_mode=True` confines the filesystem to `root_dir` and serves `/skills/` from it
(materialized from `backend/skills/`). A **checkpointer** (`backend/checkpoints.py`) holds
per-thread state and is required for the human-in-the-loop gate.

## Step 6 — Define the subagents

Each subagent is a dict — a name, a description (the orchestrator reads this to decide *when* to
delegate), a focused system prompt, its own tools, and the skills it may load. They are
stateless, so instructions must be complete. Note the division of labour: each only gets the
tools it needs (clean tools = clean context).

## Step 7 — Assemble the deep agent

```python
create_deep_agent(
    model=ChatOpenAI(model="qwen-plus", base_url=DASHSCOPE, api_key=QWEN_API_KEY),
    system_prompt=ORCHESTRATOR_PROMPT,           # grounding injected here
    tools=[view_progress, commit_progress],
    subagents=[DIAGNOSTIC, PATH_PLANNER, EXERCISE_AUTHOR, GRADER_CRITIC],
    backend=backend, store=InMemoryStore(), skills=["/skills/"],
    interrupt_on={"commit_progress": True},      # HITL gate
    checkpointer=build_checkpointer(),
)
```

## Step 8 — Serve it

`backend/agent_runtime.py` gives the FastAPI app the same `run_tutor_turn` / `resume_tutor_turn`
contract the old graph had, so `/chat` and `/chat/resume` in `backend/main.py` are unchanged on
the wire. It sets the request's learner/tenant context, invokes the agent on a thread, and
formats either an `interrupt` (awaiting approval) or a final `message`. The old hand-built graph
(`backend/graph.py`) is now a thin deprecation shim.

## Step 9 — See it in LangSmith

Set `LANGSMITH_TRACING=true` and `LANGSMITH_PROJECT=adaptive-tutor-deep-agent`. Every run uploads
a nested trace tree: the orchestrator at the top, each `task` delegation as a child span, and the
full subagent trajectory (LLM + tool calls) nested inside — i.e. exactly *which subagent ran which
tool*. Generate a rich demo set:

```bash
LANGSMITH_TRACING=true uv run python scripts/generate_demo_traces.py
```

Then open the `adaptive-tutor-deep-agent` project in the LangSmith dashboard and walk the tree.

## Step 10 — Run + test

```bash
# Talk to the agent over HTTP
uv run uvicorn backend.main:app --reload      # POST /chat {"learner_id","message"}

# Offline gates (no model calls; agent wiring is tested without an LLM)
uv run pytest -q
```

## Recap

You rebuilt a multi-agent tutor with almost no plumbing: an orchestrator that **plans** and
**delegates**, four **subagents** with isolated context and focused tools, **skills** loaded on
demand, a **composite backend** (disk + Store memory), a **human-in-the-loop** gate on the
consequential write, deterministic grading the model can't overrule, and `recursion_limit` as the
backstop — all traced to LangSmith.

**Where to take it next:** swap `InMemoryStore` for a `PostgresStore`, give the grader-critic a
structured `response_format` so its verdict is machine-readable, or add an answers-driven eval
dataset (`client.evaluate`) over the agent.
