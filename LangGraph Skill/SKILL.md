---
name: langgraph-harness
description: Invoke, test, debug, or expose LangGraph graphs from an automation harness. Use when you need to call local or deployed LangGraph apps through in-process graph.invoke/graph.stream, the LangGraph SDK or REST APIs, MCP tools, browser/UI automation, persistence/checkpointing, streaming, interrupts, or LangSmith tracing.
---

# LangGraph Harness

Use this skill to drive a LangGraph app from code or automation. Choose the lightest entry point that proves the behavior:

1. **In-process** - import the compiled graph and call `invoke`, `ainvoke`, `stream`, or `astream`. Best for unit tests and local debugging.
2. **LangGraph API server** - call a local `langgraph dev` server or deployed Agent Server with the LangGraph SDK or REST.
3. **MCP** - expose a graph as an MCP tool, or give a LangGraph-backed agent MCP tools.
4. **Browser/UI automation** - drive a real UI only when DOM, auth, or browser-agent behavior matters.

Prefer in-process tests for graph logic. Use the API server when validating deployment packaging, thread persistence, remote auth, or client behavior.

---

## 1. In-process harness

Use this when the repository contains a compiled graph and the task does not need network or deployment behavior.

### 1.1 Prerequisites

```bash
pip install -U langgraph pytest pytest-asyncio python-dotenv
```

Install provider packages only when the graph actually calls a model, for example `langchain-openai`.

The examples below use the explicit `@pytest.mark.asyncio` marker. Alternatively, enable auto mode once so async tests run without per-test markers:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
```

### 1.2 Minimal graph

The example graph stays LLM-free so it is deterministic and free to run in tests. Add a model node only when the behavior under test needs one.

```python
# graph.py
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    answer: str


def answer_node(state: State) -> dict[str, str]:
    return {"answer": f"LangGraph received: {state['question']}"}


builder = StateGraph(State)
builder.add_node("answer", answer_node)
builder.add_edge(START, "answer")
builder.add_edge("answer", END)

graph = builder.compile()
```

### 1.3 Direct tests

```python
# test_graph.py
import pytest

from graph import graph


def test_graph_invoke():
    result = graph.invoke({"question": "What is LangGraph?"})
    assert result["answer"].strip()


@pytest.mark.asyncio
async def test_graph_ainvoke():
    result = await graph.ainvoke({"question": "What is 2+2?"})
    assert "answer" in result


def test_graph_stream_updates():
    chunks = list(graph.stream({"question": "Ping"}, stream_mode="updates"))
    assert chunks
    assert any("answer" in update for chunk in chunks for update in chunk.values())
```

### 1.4 Persistence and threads

Use a checkpointer when tests need conversation continuity, time travel, interrupts, or resume behavior. Read the persisted state back with `get_state`.

```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "test-thread-1"}}

graph.invoke({"question": "Remember this"}, config=config)
graph.invoke({"question": "Continue"}, config=config)

snapshot = graph.get_state(config)
assert snapshot.values["answer"]  # latest state on the thread
```

For production, use a durable checkpointer such as Postgres (`langgraph.checkpoint.postgres.PostgresSaver`) instead of `InMemorySaver`.

### 1.5 Interrupts and resume

Human-in-the-loop graphs pause at `interrupt(...)` and resume with `Command(resume=...)`. Both require a checkpointer and a stable thread ID.

```python
# interrupt_graph.py
from langgraph.types import Command, interrupt


def review_node(state: State) -> dict[str, str]:
    decision = interrupt({"question": state["question"]})  # pauses the run here
    return {"answer": f"Human said: {decision}"}


builder = StateGraph(State)
builder.add_node("review", review_node)
builder.add_edge(START, "review")
builder.add_edge("review", END)
graph = builder.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "review-1"}}
graph.invoke({"question": "Ship it?"}, config=config)   # runs up to the interrupt
assert graph.get_state(config).next == ("review",)      # paused, awaiting input

final = graph.invoke(Command(resume="approved"), config=config)
assert final["answer"] == "Human said: approved"
```

### 1.6 In-process gotchas

- **State updates**: nodes should return partial state updates, not mutate the input state in place.
- **Thread IDs**: persistence requires a `configurable.thread_id`; using a new thread ID starts a separate state history.
- **Interrupts**: interrupt/resume flows require both a checkpointer and a stable thread ID; resume with `Command(resume=...)`, not a fresh input dict.
- **Streaming**: `stream_mode="updates"` is usually best for node-level assertions; `values` is best for final-state assertions; `messages` or `messages-tuple` is for LLM tokens.
- **Recursion**: graph loops need a stop condition or a configured `recursion_limit`.

---

## 2. LangGraph API server harness

Use this when validating `langgraph.json`, local Agent Server behavior, SDK clients, thread persistence, auth, or deployed runs.

### 2.1 Prerequisites

```bash
# Python >= 3.11 is required by the LangGraph CLI / local Agent Server.
pip install -U "langgraph-cli[inmem]" langgraph-sdk httpx pytest python-dotenv
```

### 2.2 Application config

Create `langgraph.json` at the app root:

```json
{
  "dependencies": ["."],
  "graphs": {
    "qa": "./graph.py:graph"
  },
  "env": ".env"
}
```

The graph key, `qa` above, is the assistant ID used by SDK and REST calls. The `graphs` value can point to a compiled graph or to a function that creates one.

Start the local server:

```bash
langgraph dev
```

By default, the local API is available at `http://127.0.0.1:2024` and the generated API docs at `/docs`.

### 2.3 SDK client harness

Prefer the LangGraph SDK over hand-written REST clients unless the task is specifically about wire-level behavior. For a deployed (remote) server, pass `api_key` as well.

```python
# test_langgraph_server.py
import os

import pytest
from langgraph_sdk import get_sync_client


BASE_URL = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:2024")
ASSISTANT_ID = os.getenv("LANGGRAPH_ASSISTANT_ID", "qa")


@pytest.fixture
def client():
    # api_key is unused for local `langgraph dev`; required for deployed servers.
    return get_sync_client(url=BASE_URL, api_key=os.getenv("LANGSMITH_API_KEY"))


def test_threadless_stream(client):
    chunks = list(
        client.runs.stream(
            None,
            ASSISTANT_ID,
            input={"question": "What is LangGraph?"},
            stream_mode="values",
        )
    )
    data = [chunk.data for chunk in chunks if chunk.data]
    assert data
    assert any(isinstance(item, dict) and "answer" in item for item in data)


def test_threaded_run_persists(client):
    thread = client.threads.create()
    thread_id = thread["thread_id"]
    chunks = list(
        client.runs.stream(
            thread_id,
            ASSISTANT_ID,
            input={"question": "Keep this on a thread"},
            stream_mode="updates",
        )
    )
    assert chunks
```

### 2.4 REST smoke harness

Use REST directly for endpoint debugging, non-Python clients, or SSE parsing.

```python
# test_langgraph_rest.py
import json
import os

import httpx


BASE_URL = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:2024")
ASSISTANT_ID = os.getenv("LANGGRAPH_ASSISTANT_ID", "qa")


def sse_json(lines):
    for line in lines:
        if line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
            if data and data != "[DONE]":
                yield json.loads(data)


def test_stateless_rest_stream():
    payload = {
        "assistant_id": ASSISTANT_ID,
        "input": {"question": "What is LangGraph?"},
        "stream_mode": "values",
    }
    with httpx.stream("POST", f"{BASE_URL}/runs/stream", json=payload, timeout=60) as resp:
        assert resp.status_code == 200
        events = list(sse_json(resp.iter_lines()))
    assert events
```

For threaded REST runs, create a thread with `POST /threads`, then stream with `POST /threads/{thread_id}/runs/stream`.

### 2.5 API server gotchas

- **Port drift**: current `langgraph dev` defaults to `127.0.0.1:2024`, not older examples that use `8123`.
- **Assistant ID**: use the graph key from `langgraph.json` as the SDK/REST assistant ID; do not send a separate `graph_id` unless a specific API requires it.
- **Remote auth**: deployed servers reject unauthenticated calls — pass `api_key` to `get_sync_client` (or an `x-api-key` header for REST).
- **Threadless vs threaded**: pass `None` as `thread_id` for stateless SDK runs; create a thread when persistence matters.
- **Streaming shape**: stream modes include `updates`, `values`, `messages` or SDK `messages-tuple`, `custom`, and `debug`; choose assertions for the mode.
- **Local server storage**: `langgraph dev` uses in-memory storage for development. Use LangSmith Deployment or persistent storage for production.
- **Packaging**: install the project in editable mode or list the right local package in `dependencies` so the server can import the graph.

---

## 3. MCP harness

Use this when a graph should be callable by an MCP client, or when a LangGraph-backed agent should call MCP tools.

### 3.1 Prerequisites

```bash
pip install -U langgraph langchain langchain-openai langchain-mcp-adapters mcp
```

### 3.2 Expose a graph as an MCP tool

The imported `graph` must be compiled with a checkpointer for the `thread_id` argument below to persist (see 1.4); without one, the thread ID is accepted but has no effect.

```python
# mcp_server.py
from graph import graph
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("langgraph-qa")


@mcp.tool()
async def ask_question(question: str, thread_id: str = "default") -> str:
    """Ask the QA graph a question."""
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke({"question": question}, config=config)
    return str(result.get("answer", result))


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 3.3 Consume MCP tools from a LangGraph-backed agent (recommended)

`MultiServerMCPClient` is the current high-level client. It manages one or many servers and returns LangChain-ready tools from `get_tools()`.

```python
# mcp_agent.py
import os
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            "args": [str(Path(__file__).with_name("math_server.py"))],
            "transport": "stdio",
        },
        # "remote": {"url": "https://example.com/mcp", "transport": "streamable_http"},
    }
)


async def run_agent(question: str):
    tools = await client.get_tools()
    # create_agent needs a "provider:model" string (e.g. openai:gpt-4.1) or a model instance.
    agent = create_agent(os.environ["LANGCHAIN_AGENT_MODEL"], tools=tools)
    return await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]}
    )
```

### 3.4 Alternative: single stdio server with an explicit session

Use the low-level client for direct control of one stdio session. Keep the session open while the agent uses the tools.

```python
# mcp_agent_lowlevel.py
import os
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


server_params = StdioServerParameters(
    command="python",
    args=[str(Path(__file__).with_name("math_server.py"))],
)


async def run_agent(question: str):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_agent(os.environ["LANGCHAIN_AGENT_MODEL"], tools=tools)
            return await agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]}
            )
```

In LangGraph API server deployments, expose an async graph factory in `langgraph.json` so MCP clients and tools are initialized during graph creation rather than at import time.

### 3.5 MCP checklist

- [ ] Compile the graph before exposing it as a tool.
- [ ] Return a specific field from the graph state instead of the full state unless the caller needs all fields.
- [ ] Type-hint every MCP tool argument.
- [ ] Use stable absolute paths for stdio server commands.
- [ ] Prefer `MultiServerMCPClient` + `get_tools()`; drop to an explicit `ClientSession` only when you need a persistent session.
- [ ] Keep any explicit MCP session open through tool use.
- [ ] Prefer `streamable_http` transport for remote services; stdio is best for local tools.

### 3.6 MCP gotchas

- **Closed sessions**: do not return an agent that depends on tools loaded from an already-closed `ClientSession`; `MultiServerMCPClient` avoids this by managing sessions per call.
- **Transport failures vs tool failures**: MCP tool execution errors can be surfaced to the model, while transport/session failures should fail the harness.
- **Stateful tools**: pass `thread_id` or checkpoint config explicitly when a tool invokes a persistent graph.
- **Server stdout**: MCP stdio servers must reserve stdout for protocol messages; send logs to stderr.

---

## 4. Browser and UI harness

Use browser automation only when the task depends on a rendered UI, authenticated browser state, screenshots, or live navigation.

### 4.1 Browser agent

```bash
pip install -U browser-use python-dotenv uv
uvx browser-use install
```

`ChatBrowserUse` calls the hosted Browser Use model and requires `BROWSER_USE_API_KEY` (see Section 5). To use your own provider instead, pass a different LLM (e.g. `from browser_use.llm import ChatOpenAI`).

```python
# browser_agent.py
import asyncio

from browser_use import Agent, ChatBrowserUse
from dotenv import load_dotenv


load_dotenv()


async def run(task: str):
    agent = Agent(task=task, llm=ChatBrowserUse())
    return await agent.run(max_steps=30)


if __name__ == "__main__":
    result = asyncio.run(run("Go to http://localhost:3000 and report the page title"))
    print(result)
```

### 4.2 UI test backed by LangGraph

Create test state through the LangGraph API, then drive the UI that uses the same thread.

```python
# test_ui.py
import os

from langgraph_sdk import get_sync_client
from playwright.sync_api import expect, sync_playwright


UI_BASE = os.getenv("UI_BASE", "http://localhost:3000")
API_BASE = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:2024")


def test_chat_thread():
    api = get_sync_client(url=API_BASE)
    thread = api.threads.create()
    thread_id = thread["thread_id"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(f"{UI_BASE}/chat?thread={thread_id}")
            page.fill("[data-testid='message-input']", "What is LangGraph?")
            page.click("[data-testid='send-button']")
            assistant = page.locator("[data-testid='assistant-message']").first
            expect(assistant).to_be_visible(timeout=20000)
            assert assistant.inner_text().strip()
        finally:
            browser.close()
```

### 4.3 Browser gotchas

- **Installers**: Browser Use and Playwright have separate browser install steps.
- **API key**: `ChatBrowserUse` needs `BROWSER_USE_API_KEY`; a missing key surfaces as an auth error, not an import error.
- **Timing**: prefer Playwright locators and explicit waits over sleeps.
- **Thread mismatch**: ensure the UI and setup API point to the same LangGraph deployment.
- **Cost**: browser agents can make many model calls; set `max_steps` and narrow the task.
- **Traces**: capture screenshots or Playwright traces on failure when debugging UI regressions.

---

## 5. Shared environment

Keep secrets in environment variables or a local `.env` file that is excluded from version control.

```bash
OPENAI_API_KEY=...
LANGCHAIN_AGENT_MODEL=openai:gpt-4.1   # provider:model for create_agent (Section 3)
LANGSMITH_API_KEY=...                  # also used as api_key for deployed SDK/REST calls
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=langgraph-harness
LANGGRAPH_API_URL=http://127.0.0.1:2024
LANGGRAPH_ASSISTANT_ID=qa
BROWSER_USE_API_KEY=...                # required by ChatBrowserUse (Section 4)
```

Load `.env` before constructing models, clients, or browser agents:

```python
from dotenv import load_dotenv

load_dotenv()
```

LangSmith tracing captures prompts and responses; treat traces as sensitive and keep `LANGSMITH_PROJECT` scoped to non-production data when testing.

Recommended packages for a broad harness environment:

```text
langgraph
langgraph-sdk
langchain
langchain-core
langchain-openai
langchain-mcp-adapters
mcp
langgraph-cli[inmem]
httpx
pytest
pytest-asyncio
playwright
python-dotenv
# browser-use   # optional: only for the Section 4 browser agent
```

---

## 6. Choosing an entry point

| Task shape | Recommended entry point |
|------------|-------------------------|
| Unit-test graph logic | In-process graph calls |
| Validate streaming state or tokens | In-process stream or SDK stream |
| Validate `langgraph.json` packaging | Local `langgraph dev` server |
| Call a deployed graph | LangGraph SDK |
| Debug REST or non-Python clients | REST/SSE harness |
| Share graph as a tool | MCP server |
| Give agent external MCP tools | MCP client in a graph/agent factory |
| Validate a LangGraph-backed frontend | Playwright UI test plus API setup |
| Navigate a live page autonomously | Browser Use agent |

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ModuleNotFoundError` in `langgraph dev` | Project package is not installed or missing from `dependencies` | Run `pip install -e .` or fix `langgraph.json` |
| `langgraph dev` refuses to start | Python < 3.11 or `inmem` extra not installed | Use Python >= 3.11 and `pip install "langgraph-cli[inmem]"` |
| `404` from run endpoints | Wrong base URL, assistant ID, or path | Check `http://127.0.0.1:2024/docs` and the graph key in `langgraph.json` |
| `401` / `403` from a deployed server | Missing or wrong API key | Pass `api_key` to the client (or `x-api-key` header for REST) |
| Stream chunks are empty | Wrong stream mode or filtering metadata only | Try `values` or `updates` and inspect raw chunk events |
| `GraphRecursionError` | Loop without a stop condition | Add a terminating edge/condition or raise `recursion_limit` in config |
| State is not persisted | Threadless run or no checkpointer | Create a thread and compile with a checkpointer |
| Interrupt does not resume | Missing checkpointer or wrong thread ID | Resume with the same thread and `Command(resume=...)` |
| `create_agent` cannot infer the model | Bare model name passed | Use a `provider:model` string (e.g. `openai:gpt-4.1`) or a model instance |
| Async tests are skipped or warn "coroutine was never awaited" | pytest-asyncio not active | Mark tests `@pytest.mark.asyncio` or set `asyncio_mode = auto` |
| MCP agent fails after setup | Tools were loaded from a closed session | Invoke the agent inside the MCP session or use `MultiServerMCPClient` |
| Browser import fails | Installed the wrong package or skipped browser install | Install `browser-use` and run `uvx browser-use install` |
| UI test hangs | UI and API use different thread/server state | Verify `UI_BASE`, `LANGGRAPH_API_URL`, and thread propagation |

---

## 8. References

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph local server: https://docs.langchain.com/oss/python/langgraph/local-server
- LangGraph application structure: https://docs.langchain.com/oss/python/langgraph/application-structure
- LangGraph streaming: https://docs.langchain.com/oss/python/langgraph/streaming
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- Human-in-the-loop / interrupts: https://docs.langchain.com/oss/python/langgraph/add-human-in-the-loop
- create_agent reference: https://reference.langchain.com/python/langchain/agents/factory/create_agent
- LangChain MCP adapters: https://github.com/langchain-ai/langchain-mcp-adapters
- LangSmith Deployment streaming API: https://docs.langchain.com/langsmith/streaming
- Browser Use quickstart: https://docs.browser-use.com/open-source/quickstart
- Playwright Python: https://playwright.dev/python/
