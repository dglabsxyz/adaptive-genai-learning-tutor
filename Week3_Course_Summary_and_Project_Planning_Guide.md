# Mastering Agentic AI — Week 3 Course Summary & Project Planning Guide

> **Source repository:** `https://github.com/The-Gen-Academy/Mastering-Agentic-AI-Week3/tree/main`  
> **Scope:** This document distills the Week 3 course material into a single planning reference for building the Week 3 project. It covers LangGraph fundamentals, high-level agent construction, multi-agent composition, Deep Agents, and the Model Context Protocol (MCP).

---

## How to Use This Guide

Use this document in three passes:

1. **Orient** with Sections 1-2 to understand the Week 3 arc and the shared mental models.
2. **Study the source projects** in Sections 3-5 to see how each pattern is implemented in the repository.
3. **Plan and validate your own project** with Sections 7-10, which turn the course content into architecture decisions, build steps, acceptance criteria, and demo checks.

The guide is based on the repository READMEs, notebooks, policy documents, skills, MCP server code, FastAPI backend, React demo, and PRD. It intentionally separates **course facts** from **project planning recommendations** so you can trace each build decision back to a Week 3 artifact.

---

## 1. Course Overview

Week 3 is the implementation-heavy midpoint of the Mastering Agentic AI certification. The objective is to move from *understanding* agents to *building* real agentic systems using LangGraph, LangChain, Deep Agents, and MCP. The repository is organized around two major learning tracks:

- **Session 1:** Build agents directly in LangGraph, then simplify with LangChain `create_agent`, then compose multiple agents.
- **Session 2:** Build higher-level agent systems with Deep Agents and expose application capabilities through MCP.

The throughline is practical architecture: tools, state, routing, persistence, human approval, retrieval, subagents, and interoperability.

### 1.1 Learning Objectives

By the end of Week 3, you should be able to:

1. Build a **ReAct agent from scratch** in LangGraph (tools → state → nodes → edges → loops).
2. Use LangChain’s **`create_agent`** to assemble the same logic with less boilerplate.
3. Add **human-in-the-loop** behavior using `interrupt()` and middleware approval gates.
4. Persist state across turns using **checkpointers** and `thread_id`.
5. Compose multiple agents into a **router-pattern multi-agent workflow**.
6. Implement **agentic RAG** by exposing a retriever as a tool.
7. Use the **Deep Agents** framework to build orchestrator + specialist subagent systems.
8. Design and expose **MCP servers** that translate human intent into API actions.
9. Connect MCP servers to LangChain agents and Claude Code over stdio.
10. Reason about trade-offs between raw API CRUD and intent-oriented MCP tool design.
11. Translate the course patterns into a scoped project plan with tools, state, routing, persistence, tests, and a demo script.

### 1.2 Session Map

| Session | Folder | Main Artifact | Topic |
|---|---|---|---|
| Session 1 | `Session1/langgraph/` | 3 Jupyter notebooks | LangGraph: ReAct, `create_agent`, multi-agent workflows |
| Session 2 | `Session2/Deep Agent/` | `gtm_deep_agent.ipynb` | Deep Agents: planning, subagents, skills, memory |
| Session 2 | `Session2/MCP Basics/` | `mcp_server.py`, `mcp_client.py` | MCP fundamentals: FastMCP + LangChain client |
| Session 2 | `Session2/MCP Demo/` | Full-stack course platform | MCP in practice: intent layer over a CRUD API |

### 1.3 Repository Projects at a Glance

| Project | Primary Pattern | What to Reuse in Your Project |
|---|---|---|
| Employee Time-Off Assistant | Manual ReAct loop | Tool docstrings, `GraphState`, `reason_node`, `action_node`, conditional back-edge, interrupts |
| Employee Assistant with Expenses | Router-pattern multi-agent graph | Intent classifier, compiled subgraphs as nodes, policy retrieval tool, fallback node |
| GTM Deep Agent | Orchestrator + specialist subagents | Planning with todos, delegated specialist contexts, shared artifact files, skills, long-term memory |
| MCP Basics Support Agent | Minimal MCP server/client | FastMCP tools/resources/prompts, stdio launch, LangChain MCP adapter |
| MCP Course Platform | Intent layer over real app | Fuzzy human-reference resolution, guarded writes, formatted tool output, visible UI proof |

### 1.4 Recommended Week 3 Project Shape

A strong Week 3 project should demonstrate at least one complete agentic workflow, not just isolated tool calls. A practical target is:

- **One user-facing assistant domain** with a concrete job to be done.
- **Three to six tools** split across reads, writes, clarification, and retrieval.
- **One persistence strategy** for conversation state, even if the prototype uses `InMemorySaver`.
- **One safety gate** using either `interrupt()` or `HumanInTheLoopMiddleware`.
- **One composition layer**: either a router graph, a Deep Agents orchestrator, or an MCP server that turns app operations into intent tools.
- **One demo script** showing a normal path, a missing-information path, a guarded action, and a graceful failure.

---

## 2. Core Concepts & Mental Models

### 2.1 What Is an Agent?

The course repeatedly emphasizes:

> **The LLM never executes anything.** It emits a structured *request* to call a tool. Your code executes the function and feeds the result back. The agent is the LLM plus the surrounding loop.

An agentic system is therefore:
- **A loop** (reason → act → observe → repeat)
- **Stateful** (the conversation history persists across turns)
- **Tool-augmented** (the model can call external functions)
- **Pausable** (can stop for human input and resume)

### 2.2 Chains vs. Graphs

| Chain | Graph |
|---|---|
| Fixed sequence of steps | Steps can loop, branch, pause |
| Number of tool calls known up front | Number of tool calls emerges at runtime |
| Simple, predictable | Flexible, controllable |
| Use case: one-shot transformations | Use case: agents, workflows, HITL |

The back-edge (`action_node → reason_node`) is the reason LangGraph exists: it lets an agent take as many turns as the task requires.

### 2.3 From ReAct to Multi-Agent

The progression of the course mirrors how production systems are built:

```text
ReAct (manual) → create_agent (high-level) → multi-agent composition → Deep Agents (batteries-included) → MCP (interop layer)
```

Each layer hides more boilerplate but preserves the same underlying ideas: state, tools, routing, and persistence.

### 2.4 Design Decisions Repeated Across the Repo

| Decision | Course Pattern | Planning Question |
|---|---|---|
| Tool boundary | Python functions, retrievers, MCP tools | What should the model be allowed to ask code to do? |
| State boundary | `GraphState`, `MessagesState`, checkpointers, Store | What must survive across nodes, turns, pauses, or sessions? |
| Control boundary | Conditional edges, routers, middleware, Deep Agents task delegation | Who decides the next step: code, classifier, orchestrator, or human? |
| Knowledge boundary | Policy docs, grounding file, skills, resources | What context should be retrieved or loaded only when needed? |
| Safety boundary | `interrupt()`, approval middleware, guarded MCP writes | What actions need clarification, approval, or refusal? |
| Product boundary | FastAPI CRUD vs. MCP intent tools | What should be exposed to users or AI clients, and at what abstraction level? |

The most important project habit is to name these boundaries before coding. That makes it easier to decide whether a feature belongs in a tool, a node, a subagent prompt, middleware, a backend API, or an MCP server.

---

## 3. Session 1: LangGraph — Building Agents, From Scratch to Multi-Agent

### 3.1 Project: Employee Assistant

The running example is an **Employee Assistant** that handles two request types:
- **Time-off requests** — check balance, book leave, ask for missing dates.
- **Expense reimbursements** — search company policy docs via RAG, submit claims.

### 3.2 Notebook 1 — ReAct Agent from Scratch

**File:** `1_Langgraph_React_Agent.ipynb`

This notebook builds a hand-wired ReAct agent so every piece is visible before abstraction hides it.

#### 3.2.1 Tools

- Decorated with `@tool`.
- The **docstring is part of the prompt** — it tells the model when and how to call the tool.
- Example tools:
  - `get_time_off_balance(user_id: str) -> int`
  - `process_time_off(user_id, start_date, end_date) -> dict`
  - `get_additional_info_from_human(message: str) -> str` (interrupt-based)

> **Key takeaway:** Vague docstrings produce wrong arguments. Be explicit about formats (e.g., `YYYY-MM-DD`).

**Prototype limitation to remember:** the notebook tools are stubs. `get_time_off_balance` always returns `10`, so repeated bookings do not actually decrement a database-backed balance. For a project, keep the agent loop but replace stub tools with real storage or explicit mock state.

#### 3.2.2 Graph State

```python
class GraphState(TypedDict):
    chat_history: Annotated[list[AnyMessage], add_messages]
    user_id: Optional[str]
```

- `add_messages` is a **reducer**: it appends messages instead of replacing the list.
- It is message-ID-aware, so it deduplicates messages that flow through twice (important after interrupts).
- Fields without reducers use last-write-wins semantics.

#### 3.2.3 Nodes

- **`reason_node`**: assembles system prompt + chat history, calls the LLM, appends the `AIMessage`.
- **`action_node`**: reads `tool_calls` from the last AI message, invokes each tool, appends `ToolMessage` results.

The shared prompt in `langraph_prompts.py` injects both `todays_date` and `user_id`. That is what lets the model resolve relative dates such as "tomorrow" into concrete `YYYY-MM-DD` arguments and act on behalf of the correct user.

#### 3.2.4 Edges & Routing

```text
START → reason_node
reason_node ──(tool_calls?)──→ action_node ──→ reason_node  (loop back)
        └─(no tool_calls)────→ END
```

- Fixed edges always go from A → B.
- Conditional edges call a router function that inspects state and returns the next node name.

#### 3.2.5 Human-in-the-Loop with Interrupts

- `interrupt(message)` suspends the entire graph at that line.
- The message surfaces under `__interrupt__` in the stream.
- Resume with `Command(resume={"user_message": "..."})`.
- **Critical contract:** the tool reads `interrupt_result["user_message"]`, so the resume payload must match that shape.

#### 3.2.6 Checkpointers & Persistence

- `InMemorySaver()` keeps snapshots in RAM — good for notebooks, lost on restart.
- Production: swap for Postgres, Redis, or SQLite checkpointer; no other code changes.
- `thread_id` keys the conversation. Resuming under a different `thread_id` finds nothing.
- Re-running with the same `thread_id` **continues** the conversation (surprising the first time).

> **Idempotency warning:** on resume, the interrupted node restarts from the top. Keep code before the interrupt read-only or safely repeatable.

---

### 3.3 Notebook 2 — `create_agent` + Middleware

**File:** `2_Langchain_CreateAgent.ipynb`

#### 3.3.1 `create_agent` Is a Pre-Assembled LangGraph

`create_agent(model, tools, system_prompt, checkpointer=...)` replaces:
- `StateGraph`
- `add_node` / `add_edge`
- `bind_tools`
- `compile`

It gives the same ReAct loop with less code.

#### 3.3.2 Standard Interrupts

The same `interrupt()` and `Command(resume=...)` pattern works inside `create_agent`.

#### 3.3.3 Middleware

- `HumanInTheLoopMiddleware` hooks into the agent loop at defined points.
- Use case: require approval before dangerous tools run (e.g., `process_time_off`).
- `interrupt_on` maps tool names to permission flags.
- Conceptually similar to HTTP middleware: inspect/modify state as it flows through.

> **Key takeaway:** Middleware lets you add gates without changing the agent implementation.

---

### 3.4 Notebook 3 — Multi-Agent Workflow

**File:** `3_Multi_Agent_Workflow.ipynb`

#### 3.4.1 Architecture: Router Pattern

```text
User message ──▶ Intent Classifier (structured output)
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   time_off_agent    expense_agent      fallback_node
```

- **Router pattern:** a cheap classifier picks one branch; exactly one specialist handles the request.
- **Supervisor pattern (alternative):** an LLM manager dynamically delegates and loops between workers. More flexible, harder to control.

#### 3.4.2 Intent Classification

- Pydantic model with `Literal[...]` forces one of a fixed set of intents.
- `llm.with_structured_output(IntentClassification)` returns a validated Python object.
- Always include an `"other"` intent for graceful fallback.

#### 3.4.3 Reusing Agents as Nodes

A compiled graph (including one from `create_agent`) can be added to a parent `StateGraph` with `add_node`.

- The parent owns persistence.
- The sub-agents inherit the parent checkpointer automatically.
- Common state keys (e.g., `messages`) flow through with zero glue code.

#### 3.4.4 Agentic RAG for Expense Policy

- Policy documents (`policies/equipment.md`, `meals.md`, `travel.md`) are embedded into an `InMemoryVectorStore`.
- `search_expense_policy(query)` is exposed as a tool.
- The agent decides when to retrieve, then answers grounded in the retrieved excerpts.
- `submit_expense` mocks a claims system with auto-approval limits.

#### 3.4.5 Interrupts Through the Parent Graph

Interrupts raised deep inside a sub-agent surface cleanly through the parent graph. Resume at the parent level with `Command(resume=...)`.

### 3.5 Session 1 Planning Implications

For a Week 3 project, Session 1 gives you the minimum production-shaped skeleton:

- Start with a manual ReAct graph if you need to understand or customize control flow.
- Use `create_agent` once the model-tool loop is conventional and you want less boilerplate.
- Add a router when user intents are distinct enough that one specialist should own each request.
- Keep a fallback route for unsupported requests so the assistant does not improvise outside its domain.
- Treat RAG as a tool the agent can choose, not as a mandatory pre-step, when retrieval is only sometimes needed.
- Pass checkpointers at the parent graph in composed systems, and test interrupt/resume from the top-level entry point.

---

## 4. Session 2: Deep Agents — GTM Content Assistant

### 4.1 Project: GTM Deep Agent

**File:** `Session2/Deep Agent/gtm_deep_agent.ipynb`

**Use case:** draft a LinkedIn post and a marketing email for The Gen Academy, using an orchestrator + specialist subagents. Draft-only — nothing is actually published.

### 4.2 Architecture

```text
Campaign brief ──▶ GTM Orchestrator Agent
                         │
        ┌────────────────┼────────────────┬──────────┐
        ▼                ▼                ▼          ▼
    research      linkedin writer    email writer   critic
    (web search)  (LI skill)         (email skill)  (linters)
        └────────────────┴────────────────┘          │
                         ▼                           │
                   SHARED STATE (files + todos) ◀────┘
```

### 4.3 Key Concepts Demonstrated

| Concept | Description |
|---|---|
| **Planning** | `write_todos` breaks the brief into discrete steps. |
| **Subagent delegation** | `task` calls specialists, each with isolated context. |
| **Shared state** | Filesystem + todos are shared; message histories are isolated. |
| **Skills** | `SKILL.md` files loaded on demand for progressive disclosure. |
| **Cross-session memory** | `/memories/*` persists via a `Store`. |
| **Human-in-the-loop** | `publish_post` pauses for approval. |
| **Runaway protection** | `recursion_limit` caps the agent loop. |
| **Deterministic validation** | `linkedin_post_linter` and `email_linter` check hard constraints the LLM may miss. |

### 4.4 Grounding

- Brand facts are scraped into `grounding/gen_academy.md`.
- The agent is instructed to honor the grounding and not invent claims.
- The Gen Academy ICP: AI-curious professionals through experienced engineers.
- Tone: direct, energetic, outcome-focused — *“Ship real work. Land real opportunities.”*
- Optional web search via Tavily can supplement the grounding, but the durable brand facts live in the repository file.

### 4.5 Skills

Skills are `SKILL.md` files with YAML frontmatter (`name`, `description`). The agent sees only the description until it decides the skill is relevant, then loads the full body.

- **`linkedin-style/SKILL.md`**: hook-first, 600–1,200 chars, one CTA, 3–5 hashtags, max 3 emojis.
- **`email-style/SKILL.md`**: subject < 50 chars, 80–150 word body, exactly one CTA, mobile-first.

### 4.6 Persistence Backends

A `CompositeBackend` routes by path:

- `/memories/*` → `StoreBackend` (cross-session memory)
- Everything else → `FilesystemBackend` (`/research`, `/drafts`, `/final`)

### 4.7 Specialist Subagents

Each subagent is a configuration dict with:
- Name + description (orchestrator uses this to decide delegation)
- Focused system prompt
- Own tools (clean separation: researcher gets web search, writers get linters)
- Own skills (loaded on demand)

### 4.8 Human Approval Gate

- `interrupt_on={"publish_post": True}` pauses before the simulated publish.
- Approve, reject with feedback, or edit arguments, then resume with `Command`.

### 4.9 Thread State vs. Long-Term Memory

- A new thread = fresh message history.
- `/memories/` lives in the `Store`, so a brand-new thread can still recall saved brand voice.

### 4.10 Deep Agents Planning Implications

Use Deep Agents when your project benefits from an orchestrator that plans, delegates, and assembles artifacts. It is especially useful for multi-output work such as research reports, GTM assets, onboarding packs, or analyst briefs.

Plan these pieces explicitly:

- **Subagent roster:** each specialist needs a crisp name, description, prompt, tool list, and skill list.
- **Artifact contract:** decide what files subagents should read/write, such as `/research`, `/drafts`, `/final`, and `/memories`.
- **Validation tools:** enforce measurable requirements with code, not model self-judgment.
- **Approval gate:** put simulated or real outbound actions behind `interrupt_on`.
- **Memory policy:** decide what belongs in thread-local messages versus long-term `Store` memory.

---

## 5. Session 2: MCP — Model Context Protocol

### 5.1 What Is MCP?

The **Model Context Protocol** is an open standard for connecting AI assistants to tools, resources, and prompts. It lets an AI client discover and call tools exposed by a server without knowing the server’s internals.

### 5.2 MCP Basics

**Files:** `Session2/MCP Basics/mcp_server.py`, `mcp_client.py`

#### 5.2.1 Server

A FastMCP server exposes:
- **Tools**: `get_return_policy()`, `get_current_date()`, `get_product_details(order_id)`
- **Resources**: `config://support-hours`, `docs://faq/{topic}`
- **Prompts**: `support_reply(customer_message)`, `summarize_order(order_id)`

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Langgraph_MCP_Server")

@mcp.tool()
def get_return_policy() -> str:
    """Provide the return policy for the product"""
    return "You can return the product within 30 days..."
```

#### 5.2.2 Client

A LangChain agent launches the server as a subprocess and loads its tools via `langchain-mcp-adapters`:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({
    "support": {
        "command": "uv",
        "args": ["run", "python", "mcp_server.py"],
        "transport": "stdio",
    }
})
tools = await client.get_tools()
agent = create_agent(model=llm, tools=tools, system_prompt="...")
```

#### 5.2.3 Inspector

Use `uv run mcp dev mcp_server.py` to browse tools, resources, and prompts in a browser-based UI.

---

### 5.3 MCP Demo: Course Platform

**Files:** `Session2/MCP Demo/` (full-stack app)

#### 5.3.1 System Architecture

```text
React (Vite, :5173) ──GET──▶ FastAPI (:8000) ◀──HTTP── MCP Server (FastMCP)
                                  │                          ▲ stdio
                           data/curriculum.json          Claude Code
```

- **One writer path:** only FastAPI touches the JSON file.
- **MCP transport:** stdio — Claude Code launches the server as a subprocess.
- **Live UI:** React polls every 2 seconds, so MCP-driven changes appear automatically.

#### 5.3.2 Data Model

Single source of truth: `data/curriculum.json`

```text
Course
 └─ weeks[]
     ├─ number, title, start_date, end_date
     └─ items[]
         ├─ id, title, type, date, start_time, end_time, timezone
         ├─ optional, completed
         └─ resources[]
             ├─ id, label, kind (link|text), url|text
```

Item types are constrained to `live_session`, `office_hours`, `guest_lecture`, `topic_group`, `project`, and `reading`. Resource kinds are `link` or `text`; a `link` resource with `url: null` is displayed as a visible "not published yet" placeholder in the UI.

#### 5.3.3 REST API (CRUD)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/curriculum` | Full course tree |
| GET | `/weeks/{n}` | One week |
| GET | `/items/{id}` | One item |
| GET | `/items?week=&type=&date=` | Filtered listing |
| PATCH | `/items/{id}` | Update item |
| POST | `/items/{id}/resources` | Add resource |
| PATCH | `/items/{id}/resources/{rid}` | Update resource |
| DELETE | `/items/{id}/resources/{rid}` | Delete resource |

#### 5.3.4 MCP Toolset (Intent Layer)

The MCP server is deliberately **not** a 1:1 mapping of the REST API. It exposes 4 intent-oriented tools:

| Tool | Intent | Internal behavior |
|---|---|---|
| `get_schedule(week?)` | "Show me what's happening in Week 2" | Filtered GET → chronological digest |
| `get_session_details(session)` | "Get me the slides link for the NVIDIA lecture" | Fuzzy-resolve name → item details + resources |
| `publish_recording(session, recording_url)` | "The recording for Live Session 1 is up" | Resolve → validate past date → add/update Recording resource |
| `whats_next()` | "What should I focus on?" | Join today's date + schedule + completion state |

#### 5.3.5 MCP Design Principles

1. **Intent over endpoints** — tool names should sound like user sentences.
2. **Human references, not IDs** — accept "the NVIDIA lecture"; fuzzy-match titles.
3. **Formatted summaries, not raw JSON** — return compact markdown.
4. **Domain rules live in the tool** — e.g., recordings only attach to past sessions.
5. **Conversational errors** — error strings go into the model context; write them to recover gracefully.
6. **Portability** — logic baked into the tool yields consistent behavior across clients.

#### 5.3.6 Fuzzy Name Resolution

The server scores references with:
- Exact title match
- `SequenceMatcher` similarity
- Token overlap (e.g., "nvidia lecture" hits the NVIDIA guest lecture)
- Digit-pair checking so "session 1" does not resolve to "session 2"
- Ambiguity detection: if two items score similarly, ask for clarification.

#### 5.3.7 Claude Code Integration

Registered via `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "course-platform": {
      "command": "uv",
      "args": ["run", "python", "<absolute-path-to-project>/mcp_server/mcp_server.py"],
      "env": { "UV_PROJECT": "<absolute-path-to-project>" }
    }
  }
}
```

> **Gotcha:** GUI clients may spawn the server from `/`, so `UV_PROJECT` or `--directory` is required for `uv run` to find `pyproject.toml`.

The checked-in `.mcp.json` is a concrete local registration file and may contain the original author's absolute path. When cloning or reusing the demo, replace those paths with your own project path before relying on auto-launch.

### 5.4 MCP Planning Implications

Use MCP when your project has an application or data source that should be available to AI clients beyond a single notebook. The best MCP tools are product-level operations, not backend implementation details.

When designing an MCP layer:

- Start from user sentences, then name tools after those intents.
- Keep raw CRUD in the backend API and expose higher-level MCP tools over it.
- Accept human references and resolve them internally, returning clarification prompts when ambiguous.
- Put domain invariants in write tools, especially rules the backend intentionally does not enforce.
- Return markdown or concise text summaries that can be read directly by a user and by the model.
- Make local setup portable by handling working-directory and `uv` path assumptions.

---

## 6. Technology Stack

### 6.1 Python Environment

- **Package manager:** `uv` (Astral)
- **Python version:** ≥ 3.12 for the LangGraph, Deep Agent, and MCP Basics subprojects; ≥ 3.11 for the MCP Course Demo.
- **Virtual env:** `.venv` managed by `uv sync`

### 6.2 Core Libraries

| Library | Version/Range | Used In |
|---|---|---|
| `langchain` | 1.x | All notebooks and MCP client |
| `langchain-core` | 1.x | Messages, tools, runnables |
| `langchain-openai` | ≥ 1.3 | LLM and embeddings |
| `langgraph` | 1.x | Graphs, checkpointers |
| `langsmith` | ≥ 0.3 | Tracing |
| `deepagents` | ≥ 0.6.10 | Deep Agent tutorial |
| `langchain-tavily` | ≥ 0.2.18 | Web search tool |
| `mcp` | ≥ 1.2 | MCP server/client |
| `langchain-mcp-adapters` | ≥ 0.3 | Bridge MCP tools to LangChain |
| `fastapi` / `uvicorn` | ≥ 0.115 / ≥ 0.32 | MCP Demo backend |
| `httpx` | ≥ 0.27 | HTTP client in MCP server |
| `python-dotenv` | ≥ 1.2.2 | Env loading |

### 6.3 Frontend (MCP Demo)

- React 18 + Vite
- Node 18+ / npm for the local demo workflow
- Pure CSS (no component library)
- Polling-based live updates

### 6.4 External Services

- **OpenAI API** — required for `gpt-4o` and embeddings.
- **Tavily** — optional, used only in the Deep Agent web search tool.
- **LangSmith** — optional tracing.

---

## 7. Project Planning Guide

Use this section to plan your own Week 3 project.

### 7.1 Planning Canvas

Fill this in before writing code. It forces the major Week 3 design decisions into the open.

| Decision | Your Answer | Course Reference |
|---|---|---|
| Primary user | Who is asking for help? | Employee assistant, student/instructor personas |
| Core job | What outcome should the assistant complete? | Time off, expenses, GTM drafts, course admin |
| Intent set | What 2-4 request types should be routed or delegated? | `time_off`, `expense_reimbursement`, `other` |
| Data sources | What docs, APIs, files, or stores are needed? | Policy markdown, grounding file, curriculum JSON |
| Tools | Which reads, writes, retrieval calls, and human questions are exposed? | `@tool`, retriever tools, FastMCP tools |
| State | What must persist across turns or nodes? | `GraphState`, `MessagesState`, checkpointers |
| Safety gates | Which actions require clarification or approval? | `interrupt()`, `HumanInTheLoopMiddleware`, guarded MCP writes |
| Composition | Manual graph, `create_agent`, router, Deep Agents, or MCP? | Notebooks 1-3, GTM Deep Agent, MCP Demo |
| Demo proof | What visible result shows the system worked? | Stream trace, file output, React UI update |

### 7.2 Suggested Deliverables

A complete Week 3 project should include:

- A short README explaining the domain, setup, and demo script.
- A runnable agent or MCP server with clear entry points.
- A small dataset or fixture set so the demo works without hidden services.
- Tool docstrings that describe when to use each tool and what arguments mean.
- At least one transcript, trace, screenshot, or UI state change proving the workflow.
- Notes on limitations, especially any in-memory stores, stub tools, or simulated actions.

### 7.3 Step 1: Choose a Domain

Pick a small, real-world assistant domain with:
- A clear user goal (e.g., book time off, submit expenses, publish course content).
- 2–3 distinct task types (so you can practice routing or subagent delegation).
- At least one data source that benefits from RAG (policies, docs, knowledge base).
- At least one action that should require human approval.

**Ideas from the course:**
- Employee assistant (time-off + expenses)
- Course-platform admin (schedule + resources)
- GTM content assistant (LinkedIn + email)
- IT support assistant (KB search + ticket creation)

Good scope test: the project should be too complex for a single deterministic function but small enough to demo in under 5 minutes.

### 7.4 Step 2: Define Tools

For each task, list:
- **Read tools** (fetch data)
- **Write tools** (change state)
- **Human tools** (interrupt for missing info)
- **RAG tools** (search documents)

Apply the docstring rule: a developer who only sees the docstring should know exactly what arguments to pass.

Tool design checklist:

- Name the tool as an action the model can understand, such as `search_expense_policy` or `publish_recording`.
- Use typed arguments and constrained values where possible.
- Put formatting requirements in the docstring, such as dates in `YYYY-MM-DD`.
- Make write tools return confirmation plus the changed identifier or visible result.
- Return recoverable errors in plain language so the model can ask a better follow-up.

### 7.5 Step 3: Design State

Use `TypedDict` with `Annotated[...]` reducers:

```python
class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: Optional[str]
    intent: Optional[str]
```

- Use `add_messages` for message lists.
- Add fields only when they need to persist across nodes.
- Keep `thread_id` separate from `user_id` in real applications. The notebook equates them only to simplify the demo.
- Put durable business data in tools/backends, not in chat history.

### 7.6 Step 4: Build the ReAct Loop

Start manually (Notebook 1) so you understand every piece:
1. Define tools.
2. Define state.
3. Implement `reason_node` and `action_node`.
4. Wire edges with a conditional router.
5. Compile and test.

Then refactor to `create_agent` (Notebook 2) to reduce boilerplate.

Use the manual loop when you need custom routing, inspection, or teaching clarity. Use `create_agent` when your workflow is a standard model-tools loop and you want to focus on tools, prompts, and safety.

### 7.7 Step 5: Add Human-in-the-Loop

Identify where the agent might be wrong or destructive:
- Missing required information → use `interrupt()` inside a tool.
- Dangerous write operations → use `HumanInTheLoopMiddleware` with `interrupt_on`.
- Final publish/sensitive actions → wrap the tool and require explicit approval.

### 7.8 Step 6: Add Persistence

- Use `InMemorySaver` for prototyping.
- Plan the production checkpointer early (Postgres / Redis / SQLite).
- Decide your `thread_id` strategy: one per conversation, not one per user.
- Document what is intentionally volatile. In the repo, vector stores and checkpointers are in-memory for workshop convenience.

### 7.9 Step 7: Compose Multi-Agent

If you have distinct task types:
- Build a **router** (intent classifier + conditional edges).
- Or build a **supervisor** (LLM manager delegates dynamically).
- Reuse compiled agents as nodes in a parent graph.
- Pass the checkpointer once at the parent level.

### 7.10 Step 8: Add Agentic RAG

- Collect domain documents.
- Chunk and embed them into a vector store.
- Expose retrieval as a tool.
- The agent decides when to search and answers from retrieved context.
- Include source metadata in retrieved documents so answers can explain where policy came from.

### 7.11 Step 9: Explore Deep Agents

If your project fits an orchestrator + specialists pattern:
- Use `deepagents` to configure planning, delegation, and shared filesystem state.
- Define specialist subagents with isolated tools and prompts.
- Add `SKILL.md` style guides for channel-specific outputs.
- Use a `Store` for cross-session memory.

### 7.12 Step 10: Add an MCP Layer

For interoperability with AI assistants (Claude Code, Claude Desktop, Codex):
- Wrap your backend with a FastMCP server.
- Design 3–5 intent-oriented tools, not a 1:1 CRUD mapping.
- Accept human references and fuzzy-match them.
- Return formatted summaries and conversational errors.
- Register the server in `.mcp.json` or the client’s config.

### 7.13 Choose the Right Architecture

| Project Need | Best Fit | Why |
|---|---|---|
| Learn internals or customize the loop | Manual LangGraph | Maximum control over state, nodes, and edges |
| Simple tool-using assistant | `create_agent` | Less boilerplate, same ReAct behavior |
| Distinct task categories | Router-pattern graph | Predictable one-specialist routing and easy fallback |
| Multi-output artifact workflow | Deep Agents | Built-in planning, delegation, files, skills, memory |
| Let external AI clients operate your app | MCP server | Portable intent layer over local/backend capabilities |

### 7.14 Demo and Evaluation Plan

Prepare four demo prompts before presenting:

| Scenario | What It Should Prove |
|---|---|
| Happy path | The assistant completes a normal request end-to-end. |
| Missing information | The graph pauses, asks a useful question, and resumes correctly. |
| Guarded write | A sensitive action requires approval or refuses invalid input. |
| Out-of-domain or ambiguous request | The system falls back, clarifies, or returns a recoverable error. |

For evaluation, start lightweight:

- Inspect LangSmith traces or graph streams to confirm tool order.
- Unit-test deterministic helpers such as fuzzy resolution, date checks, policy caps, and linters.
- Re-run the same `thread_id` to confirm memory behavior, then switch IDs to confirm isolation.
- Reset fixtures before demos so repeated runs are predictable.

---

## 8. Common Patterns & Anti-Patterns

### 8.1 Do

- **Write precise docstrings** — they are prompts.
- **Use `add_messages`** for conversation state.
- **Pass `thread_id`** consistently; separate it from `user_id` in production.
- **Keep code before `interrupt()` idempotent.**
- **Return formatted text** from MCP tools, not raw JSON.
- **Include an `"other"` intent** in classifiers.
- **Validate domain rules inside MCP tools**, not just the API.
- **Use `recursion_limit`** as a safety backstop.
- **Document prototype shortcuts** such as stub tools, in-memory stores, simulated publishing, and seed data.
- **Reset demo fixtures** before reruns when the workflow mutates local data.

### 8.2 Avoid

- **Guessing missing information** — interrupt and ask.
- **1:1 CRUD-to-MCP mappings** — design for intent.
- **Tool names that expose IDs** — use human references.
- **Mixing sync and async carelessly** in Playwright / MCP contexts.
- **Committing API keys** — `.env` and `.venv` are gitignored for a reason.
- **Relying on in-memory stores in production** — plan persistence early.
- **Hard-coding another user's absolute path** in MCP client config — replace local registrations after cloning.
- **Letting the model validate hard limits by itself** — use deterministic checks for dates, budgets, character counts, and domain constraints.

---

## 9. Checklists

### 9.1 Before Coding

- [ ] Domain and user stories defined
- [ ] Architecture chosen: manual LangGraph, `create_agent`, router, Deep Agents, MCP, or a combination
- [ ] Tool list drafted with docstrings
- [ ] State schema designed
- [ ] Data fixtures or domain documents identified
- [ ] Human approval / clarification points named
- [ ] Persistence strategy chosen
- [ ] API keys loaded in `.env`

### 9.2 During Development

- [ ] ReAct loop works end-to-end
- [ ] Interrupt/resume tested
- [ ] Multi-turn memory verified with same `thread_id`
- [ ] RAG tool retrieves relevant excerpts
- [ ] Dangerous actions gated
- [ ] Fallback path handles unsupported or ambiguous requests
- [ ] Deterministic helper logic has focused tests or reproducible examples

### 9.3 Before Demo

- [ ] Setup commands are documented and tested from a fresh terminal
- [ ] Happy-path prompt completes without manual patching
- [ ] Missing-information prompt pauses and resumes correctly
- [ ] Guard rails refuse or pause invalid/destructive actions conversationally
- [ ] UI, CLI, trace, file artifact, or backend state visibly reflects writes
- [ ] Demo data can be reset to a known state

### 9.4 MCP-Specific Checklist

- [ ] Server launches over stdio from the configured client
- [ ] Tool names describe user intent rather than backend endpoints
- [ ] Human references are resolved without requiring raw IDs
- [ ] Read tools return compact formatted summaries
- [ ] Write tools validate domain rules and return recoverable errors
- [ ] `.mcp.json` or client config uses portable paths for the local environment

---

## 10. Extension Ideas

1. **Persistent checkpointer** — swap `InMemorySaver` for Postgres.
2. **Real policy PDFs** — replace markdown stubs with chunked PDF RAG.
3. **Supervisor pattern** — replace the router with an LLM manager that can loop between specialists.
4. **Real outbound actions** — connect `publish_post` to LinkedIn / email APIs behind HITL.
5. **Evaluation** — add LangSmith datasets and evaluators for agent outputs.
6. **Streaming UI** — stream graph events to a web frontend.
7. **Multi-client MCP** — register the same server in Claude Desktop, Codex, and Claude Code.
8. **Auth & multi-tenancy** — add user scoping to backend and MCP tools.

---

## 11. Reference: File-by-File Map

| File | What It Teaches |
|---|---|
| `Session1/langgraph/1_Langgraph_React_Agent.ipynb` | Manual ReAct: tools, state, nodes, edges, interrupts, checkpointers |
| `Session1/langgraph/2_Langchain_CreateAgent.ipynb` | `create_agent`, standard interrupts, middleware approval gates |
| `Session1/langgraph/3_Multi_Agent_Workflow.ipynb` | Router pattern, structured intent classification, agentic RAG, subgraphs |
| `Session1/langgraph/langraph_prompts.py` | Shared system prompt with date injection |
| `Session1/langgraph/policies/*.md` | Mock policy docs for RAG |
| `Session2/Deep Agent/gtm_deep_agent.ipynb` | Deep Agents: planning, subagents, skills, composite backends, memory |
| `Session2/Deep Agent/skills/*.md` | SKILL.md format for progressive disclosure |
| `Session2/Deep Agent/grounding/gen_academy.md` | Brand grounding document |
| `Session2/MCP Basics/mcp_server.py` | FastMCP tools, resources, prompts |
| `Session2/MCP Basics/mcp_client.py` | MultiServerMCPClient + LangChain agent |
| `Session2/MCP Demo/backend/main.py` | Plain FastAPI CRUD over JSON file |
| `Session2/MCP Demo/backend/storage.py` | Atomic file writes with temp file + rename |
| `Session2/MCP Demo/mcp_server/mcp_server.py` | Intent-oriented MCP layer, fuzzy resolution |
| `Session2/MCP Demo/frontend/src/App.jsx` | React viewer with polling |
| `Session2/MCP Demo/PRD.md` | Full product/design rationale |
| `Session2/MCP Demo/.mcp.json` | Claude Code stdio registration |

---

## 12. Resources & Documentation

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **LangChain Docs:** https://python.langchain.com/
- **LangSmith Docs:** https://docs.smith.langchain.com/
- **MCP Spec:** https://modelcontextprotocol.io/
- **FastMCP:** https://github.com/modelcontextprotocol/python-sdk
- **uv:** https://docs.astral.sh/uv/
- **The Gen Academy:** https://thegenacademy.com

---

## 13. Final Takeaways

1. **Agents are loops, not single calls.** The value of LangGraph is the controlled back-edge between reasoning and acting.
2. **State and persistence are first-class.** Interrupts, multi-turn memory, and debugging all depend on checkpointers.
3. **Composition is the superpower.** Compiled graphs can be dropped into larger graphs as nodes.
4. **Intent beats CRUD.** A well-designed MCP layer speaks in human terms and embeds domain rules.
5. **Progressive disclosure matters.** Skills, grounding, and isolated subagent contexts keep each specialist focused.
6. **Human-in-the-loop is not an afterthought.** Design approval gates and interrupt points from the start.

Use these principles as the foundation for your Week 3 project.
