---
name: langchain-harness
description: Invoke, test, or embed LangChain applications from an automation harness. Use when you need to call LangChain chains, agents, or runnables in-process or over HTTP; write pytest harnesses for them; consume or expose MCP tools; automate LangChain-backed browser flows or UIs; configure LangSmith tracing; or debug LangChain harness failures.
---

# LangChain Harness

Use this skill to drive a LangChain app from code or automation. Choose the lightest entry point that proves the behavior:

1. **In-process** - import the local chain, runnable, or agent and call it directly. Best for unit tests and fast debugging.
2. **HTTP API** - call an existing service, custom FastAPI route, or legacy LangServe route.
3. **MCP** - consume MCP tools from LangChain, or expose a LangChain runnable as an MCP tool.
4. **Browser automation** - drive a real UI or browser agent only when DOM behavior matters.

For new services, prefer a custom FastAPI app or the LangGraph Platform API over LangServe. LangServe still works for existing simple-runnable deployments but is in maintenance mode (community bug-fixes only, no new features), and LangGraph Platform is its recommended successor — so do not choose LangServe for greenfield work unless explicitly asked.

---

## 1. In-process harness

Use this when the LangChain object is available in the repository and the task does not require network, auth, or deployment behavior.

### 1.1 Prerequisites

```bash
pip install -U langchain langchain-openai langchain-core pytest pytest-asyncio python-dotenv
```

The examples below use the explicit `@pytest.mark.asyncio` marker. Alternatively, enable auto mode once so async tests run without per-test markers:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
```

### 1.2 Minimal chain

Construct the model lazily inside a factory rather than at import time. This keeps network calls and env lookups out of the import path (see 1.4), so the module can be imported — and collected by pytest — even when no API key is set.

```python
# app_chain.py
import functools
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


@functools.lru_cache(maxsize=1)
def build_chain():
    """Build the chain once. Env is read here, not at import time."""
    model = ChatOpenAI(model=os.environ["OPENAI_MODEL"], temperature=0)
    prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")
    return prompt | model
```

### 1.3 Direct test harness

```python
# test_app_chain.py
import pytest

from app_chain import build_chain


def message_text(value) -> str:
    """Normalize a str, an AIMessage (.content as str OR list of blocks),
    or a dict payload into plain text before asserting."""
    if isinstance(value, str):
        return value
    content = getattr(value, "content", None)
    if content is None and isinstance(value, dict):
        content = value.get("content") or value.get("answer")
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # modern multimodal / tool-call content blocks
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(value if content is None else content)


@pytest.mark.asyncio
async def test_chain_answer():
    result = await build_chain().ainvoke({"question": "What is LangChain?"})
    assert message_text(result).strip()
```

### 1.4 In-process gotchas

- **Import side effects**: keep model construction, env loading, and network calls out of module import paths — wrap them in a factory (as in 1.2) so imports stay cheap and failure-free.
- **Model determinism**: use `temperature=0` or deterministic prompts for assertions.
- **Secrets**: require API keys from the environment; never hard-code them in fixtures.
- **Message shape**: normalize strings, `AIMessage.content` (which may be a string *or* a list of content blocks), and dict payloads before asserting.

---

## 2. HTTP API harness

Use this when a LangChain application exposes a service boundary that must be tested over HTTP.

### 2.1 Custom FastAPI server

Prefer this pattern for new, simple harness APIs because it is explicit and easy to secure.

```bash
pip install -U fastapi uvicorn langchain langchain-openai langchain-core python-dotenv
```

```python
# server.py
import functools
import json
import os

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class InvokeRequest(BaseModel):
    question: str


class InvokeResponse(BaseModel):
    answer: str


def message_text(value) -> str:
    if isinstance(value, str):
        return value
    content = getattr(value, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, str) or (isinstance(block, dict) and block.get("type") == "text")
        ]
        return "".join(parts)
    return str(value)


@functools.lru_cache(maxsize=1)
def get_chain():
    """Lazily build the chain so `from server import app` works without env
    (e.g. to read /openapi.json); env is required only when a route runs."""
    return ChatPromptTemplate.from_template("Answer briefly: {question}") | ChatOpenAI(
        model=os.environ["OPENAI_MODEL"], temperature=0
    )


app = FastAPI(title="LangChain Harness API")


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    result = await get_chain().ainvoke({"question": req.question})
    return InvokeResponse(answer=message_text(result))


@app.post("/stream")
async def stream(req: InvokeRequest):
    async def events():
        async for chunk in get_chain().astream({"question": req.question}):
            text = message_text(chunk)
            if text:
                yield f"data: {json.dumps({'content': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

Run it:

```bash
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

### 2.2 HTTP client harness

```python
# test_api.py
import json

import httpx
import pytest


BASE = "http://127.0.0.1:8000"


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE, timeout=30) as client:
        yield client


def sse_payloads(lines):
    for line in lines:
        if line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
            if data == "[DONE]":
                break
            yield json.loads(data)


def test_invoke(client):
    resp = client.post("/invoke", json={"question": "What is LangChain?"})
    assert resp.status_code == 200
    assert resp.json()["answer"].strip()


def test_stream(client):
    with client.stream("POST", "/stream", json={"question": "Count 1 to 3"}) as stream:
        chunks = [event["content"] for event in sse_payloads(stream.iter_lines())]
    assert "".join(chunks).strip()
```

### 2.3 Legacy LangServe route

Use this only for an existing LangServe app or a compatibility check. For a modern remote runnable, deploy on LangGraph Platform and call it with `RemoteGraph` instead of LangServe's `RemoteRunnable`.

```bash
pip install -U "langserve[server]>=0.3" fastapi uvicorn langchain-openai
```

```python
# langserve_server.py
import os

from fastapi import FastAPI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langserve import add_routes


model = ChatOpenAI(model=os.environ["OPENAI_MODEL"], temperature=0)
prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")
chain = prompt | model

app = FastAPI(title="Legacy LangServe API")
add_routes(app, chain, path="/chain")
```

LangServe adds these common endpoints for a route like `path="/chain"`:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chain/invoke` | Invoke once |
| POST | `/chain/batch` | Invoke multiple inputs |
| POST | `/chain/stream` | Stream output |
| POST | `/chain/stream_log` | Stream output and intermediate logs |
| POST | `/chain/astream_events` | Stream runnable events |
| GET | `/chain/input_schema` | Read input JSON schema |
| GET | `/chain/output_schema` | Read output JSON schema |
| GET | `/chain/config_schema` | Read config JSON schema |
| GET | `/chain/playground/` | Open the generated playground |

Raw HTTP requests must wrap input in the `input` key:

```python
def output_text(payload) -> str:
    output = payload.get("output", payload)
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        return str(output.get("content") or output.get("kwargs", {}).get("content") or output)
    return str(output)


def test_langserve_invoke(client):
    resp = client.post("/chain/invoke", json={"input": {"question": "What is LangChain?"}})
    assert resp.status_code == 200
    assert output_text(resp.json()).strip()
```

### 2.4 HTTP gotchas

- **422 responses**: inspect `/input_schema`; send exactly the shape the runnable expects.
- **Root 404**: LangServe does not define `/` by default; check `/docs`, `/chain/input_schema`, or `/chain/playground/`.
- **Streaming**: treat streams as Server-Sent Events, parse only `data:` lines, and stop on the `[DONE]` sentinel.
- **Pydantic**: use LangServe `>=0.3` if the project uses Pydantic 2.
- **Auth and CORS**: add explicit FastAPI auth/CORS middleware; do not expose playgrounds or trace links publicly by accident.

---

## 3. MCP harness

Use this when a LangChain agent must call MCP tools, or when a LangChain runnable should be made available to an MCP client.

### 3.1 Prerequisites

```bash
pip install -U langchain-mcp-adapters mcp langgraph langchain langchain-openai
```

### 3.2 Consume MCP servers from LangChain (recommended)

`MultiServerMCPClient` is the current high-level entry point. It manages one or many servers, handles sessions for you, and returns LangChain-ready tools from `get_tools()`.

```python
# mcp_client.py
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


async def run_agent():
    tools = await client.get_tools()
    # create_agent needs a "provider:model" string (e.g. openai:gpt-4.1) or a model instance.
    agent = create_agent(os.environ["LANGCHAIN_AGENT_MODEL"], tools=tools)
    return await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What is 7^12?"}]}
    )
```

Run it with `asyncio.run(run_agent())`.

### 3.3 Alternative: single stdio server with an explicit session

Use the low-level client when you need direct control of one stdio session (for example, to keep custom context open across calls).

```python
# mcp_client_lowlevel.py
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


async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_agent(os.environ["LANGCHAIN_AGENT_MODEL"], tools=tools)
            return await agent.ainvoke(
                {"messages": [{"role": "user", "content": "What is 7^12?"}]}
            )
```

### 3.4 Expose a LangChain chain as an MCP server

```python
# mcp_server.py
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("langchain-summarizer")
chain = ChatPromptTemplate.from_template("Summarize: {text}") | ChatOpenAI(
    model=os.environ["OPENAI_MODEL"], temperature=0
)


@mcp.tool()
async def summarize(text: str) -> str:
    """Summarize text with the configured LangChain model."""
    response = await chain.ainvoke({"text": text})
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 3.5 MCP checklist

- [ ] Use absolute or repo-stable paths for stdio server commands.
- [ ] Prefer `MultiServerMCPClient` + `get_tools()`; drop to an explicit `ClientSession` only when you need a persistent session.
- [ ] When using the low-level client, await `session.initialize()` before loading tools and keep the session open for the full agent invocation.
- [ ] Pass `create_agent` a `provider:model` string (or a model instance) and `tools=` as a keyword.
- [ ] Type-hint every `@mcp.tool()` argument so MCP can derive schemas.
- [ ] Prefer `stdio` for local servers and `streamable_http` (or `sse`) for remote servers.
- [ ] Add client timeouts around long-running tools.

### 3.6 MCP gotchas

- **Protocol errors**: MCP uses JSON-RPC; malformed output on stdout can close the session.
- **Tool errors**: distinguish tool execution failures from transport/session failures. `MultiServerMCPClient` returns tool errors as messages by default — set `handle_tool_errors=False` to raise instead.
- **Async mismatch**: use async MCP tools for async chains; sync tools can block the event loop.
- **Name collisions**: keep tool names unique, or enable server-name prefixing on the client.

---

## 4. Browser harness

Use this only when the task requires a real browser, UI state, screenshots, or browser-agent behavior.

### 4.1 Browser agent

```bash
pip install -U browser-use python-dotenv uv
# Current Browser Use docs install Chromium through the project CLI:
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
    return await agent.run()


if __name__ == "__main__":
    result = asyncio.run(run("Go to http://localhost:3000 and report the page title"))
    print(result)
```

### 4.2 UI testing harness

Use Playwright directly when LangChain is the backend and the harness owns the UI interactions.

```bash
pip install -U playwright pytest
playwright install chromium
```

```python
# test_ui.py
from playwright.sync_api import expect, sync_playwright


BASE = "http://localhost:3000"


def test_chat_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(f"{BASE}/chat")
            page.fill("[data-testid='message-input']", "Hello LangChain")
            page.click("[data-testid='send-button']")
            assistant = page.locator("[data-testid='assistant-message']").first
            expect(assistant).to_be_visible(timeout=15000)
            assert assistant.inner_text().strip()
        finally:
            browser.close()
```

### 4.3 Browser gotchas

- **Installers**: `browser-use` and Playwright have separate browser install steps.
- **API key**: `ChatBrowserUse` needs `BROWSER_USE_API_KEY`; a missing key surfaces as an auth error, not an import error.
- **Timing**: prefer locators and explicit waits over `sleep`.
- **Headless blocks**: use headed mode only in test environments you control.
- **Session cleanup**: close browsers in `finally` blocks or fixture teardowns.
- **Cost**: browser agents can make many model calls; constrain task scope and assertions.

---

## 5. Shared environment

Keep secrets in local environment variables or a local `.env` file that is excluded from version control. Note the two model variables differ: `ChatOpenAI` takes a bare model name, while `create_agent` takes a `provider:model` string.

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1                   # bare model name for ChatOpenAI
LANGCHAIN_AGENT_MODEL=openai:gpt-4.1   # provider:model for create_agent (Section 3)
BROWSER_USE_API_KEY=...                # required by ChatBrowserUse (Section 4)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=langchain-harness
# LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
# LANGSMITH_WORKSPACE_ID=...
```

Load `.env` before constructing models (or before calling a factory that constructs them):

```python
from dotenv import load_dotenv

load_dotenv()
```

LangSmith tracing captures prompts and responses; treat traces as sensitive and keep `LANGSMITH_PROJECT` scoped to non-production data when testing.

Recommended packages for a general-purpose harness virtual environment:

```text
langchain
langchain-core
langchain-openai
langchain-mcp-adapters
langgraph
mcp
fastapi
uvicorn
httpx
pytest
pytest-asyncio
playwright
python-dotenv
# browser-use         # optional: only for the Section 4 browser agent
# langserve[server]   # optional: only for legacy LangServe routes (Section 2.3)
```

---

## 6. Choosing an entry point

| Task shape | Recommended entry point |
|------------|-------------------------|
| Unit-test a local chain or agent | In-process |
| Call a deployed service | HTTP API |
| Maintain an existing LangServe app | Legacy LangServe |
| Tool-calling interoperability | MCP |
| Validate a web frontend | Playwright UI test |
| Let an agent navigate a live page | Browser agent |
| Batch regression checks | In-process or HTTP + pytest |

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `OPENAI_API_KEY not found` | Env not loaded before model construction | Call `load_dotenv()` first or export env vars in the shell |
| `422 Unprocessable Entity` | Input schema mismatch | Inspect schema endpoint or local model type and send exact keys |
| LangServe `/` returns 404 | No root route is defined | Use `/docs`, `/chain/input_schema`, or define a root route |
| Stream has no parsed chunks | Harness parsed every line as JSON, or never stopped on the sentinel | Parse only `data:` SSE lines and break on `data: [DONE]` |
| `create_agent` cannot infer the model | Bare model name passed | Use a `provider:model` string (e.g. `openai:gpt-4.1`) or a model instance |
| MCP server exits immediately | Bad command, missing env, or stderr-only failure | Run server command manually and inspect stderr |
| Browser agent import fails | Wrong package name | Install `browser-use`, not `langchain-browser-use` |
| `ChatBrowserUse` auth error | `BROWSER_USE_API_KEY` not set | Set the key in `.env` or pass a different LLM |
| Async tests are skipped or warn "coroutine was never awaited" | pytest-asyncio not active | Mark tests `@pytest.mark.asyncio` or set `asyncio_mode = auto` |
| No LangSmith traces | Legacy env vars or disabled tracing | Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` |

---

## 8. References

- LangChain docs: https://docs.langchain.com/oss/python/langchain/overview
- create_agent reference: https://reference.langchain.com/python/langchain/agents/factory/create_agent
- LangGraph Platform (LangServe successor): https://docs.langchain.com/langgraph-platform
- LangServe legacy repository: https://github.com/langchain-ai/langserve
- LangChain MCP adapters: https://github.com/langchain-ai/langchain-mcp-adapters
- MultiServerMCPClient reference: https://reference.langchain.com/python/langchain-mcp-adapters/client/MultiServerMCPClient
- LangSmith tracing: https://docs.langchain.com/langsmith/trace-with-langchain
- Browser Use quickstart: https://docs.browser-use.com/open-source/quickstart
- MCP spec: https://modelcontextprotocol.io/
- Playwright Python: https://playwright.dev/python/
