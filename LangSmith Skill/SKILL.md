---
name: langsmith-harness
description: Observe, evaluate, query, or manage LangSmith workspaces from an automation harness. Use when you need to configure LangSmith tracing, create or query datasets, run evaluations and experiments, inspect traces/runs, manage prompts, record feedback, connect the official LangSmith MCP server, or automate LangSmith UI workflows when no SDK/API path exists.
---

# LangSmith Harness

Use this skill to work with LangSmith from code, agent runtimes, MCP clients, or UI automation. Choose the lightest entry point that proves the behavior:

1. **SDK/API** - trace applications, query runs, manage datasets, run evaluations, prompts, and feedback. Prefer this for most work.
2. **MCP** - expose LangSmith workspace data to an agent through the official LangSmith MCP server.
3. **Browser UI** - automate LangSmith only for workflows that have no SDK/API path, such as visual review or one-off UI checks.

Prefer SDK calls over browser automation. Browser automation against LangSmith can expose trace data in screenshots, downloads, logs, or storage state.

---

## 1. SDK setup

Use this when tracing, evaluating, querying runs, managing datasets, working with prompts, or logging feedback.

### 1.1 Prerequisites

```bash
pip install -U langsmith langchain-core httpx pytest pytest-asyncio python-dotenv
```

Install provider packages only when the harness calls models, for example `openai`, `langchain-openai`, or `openevals`.

The async examples use the `@pytest.mark.asyncio` marker. Alternatively, enable auto mode once so async tests run without per-test markers:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
```

### 1.2 Environment

```bash
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=langsmith-harness
LANGSMITH_JUDGE_MODEL=openai:gpt-4.1   # provider:model for openevals judges (Section 3.3)
# Optional when using non-default regions, self-hosted LangSmith, or multi-workspace keys:
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=...
```

Load `.env` before constructing clients or model wrappers:

```python
from dotenv import load_dotenv

load_dotenv()
```

### 1.3 Client health check

```python
from langsmith import Client


client = Client()
# An invalid key or endpoint raises here; a successful call returns a list.
projects = list(client.list_projects(limit=1))
assert isinstance(projects, list)
```

### 1.4 Setup gotchas

- **Tracing flag**: set `LANGSMITH_TRACING=true` before importing or constructing LangChain/LangGraph objects when relying on automatic tracing.
- **Project routing**: traces land in `LANGSMITH_PROJECT`, a `project_name` argument, or the active tracing context.
- **Workspace routing**: set `LANGSMITH_WORKSPACE_ID` when one API key can access multiple workspaces.
- **Regional/self-hosted endpoints**: set `LANGSMITH_ENDPOINT` to the API base URL; do not append `/api/v1`.
- **Secrets**: never commit API keys, profile files, browser storage state, trace exports, or screenshots containing trace payloads.

---

## 2. Tracing harness

Use tracing to inspect inputs, outputs, model calls, tool calls, latency, token usage, and nested run trees.

### 2.1 Trace plain Python

```python
from langsmith import traceable


@traceable(run_type="chain", name="qa_pipeline")
def qa_pipeline(inputs: dict) -> dict:
    question = inputs["question"]
    return {"answer": f"Received: {question}"}


result = qa_pipeline({"question": "What is LangSmith?"})
assert result["answer"]
```

`@traceable` also wraps async callables; the run is traced when you await them:

```python
import pytest

from langsmith import traceable


@traceable(run_type="chain", name="qa_pipeline_async")
async def qa_pipeline_async(inputs: dict) -> dict:
    return {"answer": f"Received: {inputs['question']}"}


@pytest.mark.asyncio
async def test_async_trace():
    result = await qa_pipeline_async({"question": "smoke"})
    assert result["answer"]
```

### 2.2 Trace within an explicit context

Use a tracing context when tests need to override project, client, or enabled state.

```python
import langsmith as ls


client = ls.Client()

with ls.tracing_context(client=client, project_name="langsmith-harness", enabled=True):
    result = qa_pipeline({"question": "smoke"})
```

### 2.3 Query recent traces

```python
from datetime import datetime, timedelta, timezone
from langsmith import Client


client = Client()
runs = list(
    client.list_runs(
        project_name="langsmith-harness",
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        is_root=True,
        limit=10,
    )
)
assert all(run.id for run in runs)
```

### 2.4 REST query fallback

Prefer the SDK. Use REST for non-Python clients or wire-level debugging. The query endpoint is `POST /runs/query` (the same endpoint `list_runs` uses) and returns an object with `runs` and pagination `cursors`.

```python
import os

import httpx


headers = {"x-api-key": os.environ["LANGSMITH_API_KEY"]}
if os.getenv("LANGSMITH_WORKSPACE_ID"):
    headers["x-tenant-id"] = os.environ["LANGSMITH_WORKSPACE_ID"]

resp = httpx.post(
    f"{os.getenv('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com')}/runs/query",
    headers=headers,
    json={"project_name": "langsmith-harness", "is_root": True, "limit": 5},
    timeout=30,
)
resp.raise_for_status()
assert "runs" in resp.json()
```

### 2.5 Tracing gotchas

- **Missing traces**: confirm `LANGSMITH_TRACING=true`, project name, workspace ID, and endpoint before debugging app code.
- **Ingestion delay**: traces can take a few seconds to appear; poll briefly in smoke tests.
- **Root vs child runs**: use `is_root=True` for trace-level queries and omit it when inspecting child spans.
- **High volume**: filter by time, project, run type, tags, or FQL instead of exporting unbounded traces.

---

## 3. Datasets and evaluations

Use evaluations to compare target behavior against dataset examples with deterministic or model-judged evaluators.

### 3.1 Create a dataset

```python
from langsmith import Client


client = Client()
dataset = client.create_dataset(
    dataset_name="qa-smoke",
    description="Small QA regression set.",
)

client.create_examples(
    dataset_id=dataset.id,
    examples=[
        {
            "inputs": {"question": "Which country is Mount Kilimanjaro in?"},
            "outputs": {"answer": "Tanzania"},
        },
        {
            "inputs": {"question": "What is 2 + 2?"},
            "outputs": {"answer": "4"},
        },
    ],
)
```

### 3.2 Run a deterministic evaluation

```python
from langsmith import Client


client = Client()


def target(inputs: dict) -> dict:
    return {"answer": inputs["question"]}


def contains_reference(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    expected = reference_outputs["answer"].lower()
    return expected in outputs["answer"].lower()


experiment = client.evaluate(
    target,
    data="qa-smoke",
    evaluators=[contains_reference],
    experiment_prefix="qa-smoke",
    max_concurrency=2,
)
print(experiment)
```

### 3.3 Run an LLM-as-judge evaluation

Use `openevals` when judging open-ended text. Keep model names configurable via `LANGSMITH_JUDGE_MODEL` (a `provider:model` string such as `openai:gpt-4.1`).

```bash
pip install -U openevals openai
```

```python
import os

from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT


judge = create_llm_as_judge(
    prompt=CORRECTNESS_PROMPT,
    model=os.environ["LANGSMITH_JUDGE_MODEL"],  # e.g. "openai:gpt-4.1"
    feedback_key="correctness",
)


def correctness(inputs: dict, outputs: dict, reference_outputs: dict):
    return judge(inputs=inputs, outputs=outputs, reference_outputs=reference_outputs)


Client().evaluate(
    target,
    data="qa-smoke",
    evaluators=[correctness],
    experiment_prefix="qa-judge",
    max_concurrency=2,
)
```

### 3.4 Evaluation gotchas

- **Target shape**: target functions receive dataset `inputs` and should return a dict; evaluators must match that output shape.
- **Reference outputs**: deterministic correctness checks need examples with `outputs`; exploratory datasets may omit them.
- **Concurrency**: set `max_concurrency` to avoid provider or LangSmith rate limits.
- **Async targets**: use `await client.aevaluate(...)` when the target or evaluators are async, instead of the sync `evaluate`.
- **Local-only dry runs**: use `upload_results=False` when validating evaluator logic without creating an experiment.
- **Dataset identity**: use dataset IDs for stable automation and names for quick local workflows.

---

## 4. Prompts and feedback

Use the SDK for prompt versioning and feedback instead of UI automation whenever possible.

### 4.1 Push and pull prompts

```python
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client


client = Client()
prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")

url = client.push_prompt("qa-brief-answer", object=prompt)
print(url)

production_prompt = client.pull_prompt("qa-brief-answer:production")
```

### 4.2 Log feedback

```python
from langsmith import Client


client = Client()
# Pass a real run id, e.g. one returned by client.list_runs(...).
client.create_feedback(
    run_id="<run-id>",
    key="user_score",
    score=1,
    comment="Useful answer.",
)
```

### 4.3 Prompts and feedback gotchas

- **Prompt package**: use the `langsmith` SDK for prompt management; `langchainhub` is deprecated.
- **Tags over commits**: pull prompts by tags like `:production` when release channels matter.
- **Prompt cache**: pulled prompts may be cached in process; disable or bypass cache when testing fresh edits.
- **Feedback target**: attach feedback to the root run for whole-answer quality or a child run for a specific retrieval/tool/model step.

---

## 5. MCP harness

Use MCP when an agent needs workspace data such as runs, traces, datasets, experiments, prompts, or billing.

### 5.1 Prefer LangSmith Remote MCP when available

Use Remote MCP for OAuth-based access when the MCP client supports OAuth 2.1 with Dynamic Client Registration.

Cloud endpoints follow the LangSmith host for the region:

- `https://smith.langchain.com/api/mcp`
- `https://eu.smith.langchain.com/api/mcp`
- `https://apac.smith.langchain.com/api/mcp`
- `https://aws.smith.langchain.com/api/mcp`

Self-hosted LangSmith v0.15 or later uses:

- `https://<your-langsmith-host>/api/mcp`

```json
{
  "mcpServers": {
    "LangSmith Remote MCP": {
      "url": "https://smith.langchain.com/api/mcp"
    }
  }
}
```

If the client cannot complete the OAuth flow, use the LangSmith CLI or the standalone MCP server below.

### 5.2 Use the standalone MCP server when OAuth is unavailable

Use the standalone server for clients without Remote MCP OAuth support, self-hosted LangSmith before v0.15, custom regions, or environments where a separate server is required.

```bash
pip install -U uv
uvx langsmith-mcp-server
```

Client config:

```json
{
  "mcpServers": {
    "LangSmith MCP": {
      "command": "/path/to/uvx",
      "args": ["langsmith-mcp-server"],
      "env": {
        "LANGSMITH_API_KEY": "${LANGSMITH_API_KEY}",
        "LANGSMITH_WORKSPACE_ID": "${LANGSMITH_WORKSPACE_ID}",
        "LANGSMITH_ENDPOINT": "${LANGSMITH_ENDPOINT}"
      }
    }
  }
}
```

### 5.3 MCP tool surface

Common tools exposed by the official server:

| Area | Tools |
|------|-------|
| Runs / projects | `fetch_runs`, `list_projects` |
| Threads | `get_thread_history` |
| Datasets | `list_datasets`, `list_examples`, `read_dataset`, `read_example` |
| Prompts | `list_prompts`, `get_prompt_by_name` |
| Experiments | `list_experiments` |
| Billing | `get_billing_usage` |

The exact set depends on the server version and the API key's scope; write actions (pushing prompts, running experiments) may require extra permissions. Call the client's tool-list method to see what your server actually exposes.

### 5.4 MCP gotchas

- **Scope**: MCP can expose sensitive inputs, outputs, prompts, and billing data; use least-privilege API keys and workspace IDs.
- **Pagination**: large `fetch_runs` and `get_thread_history` responses use character-budget pagination; request subsequent `page_number` values.
- **Remote vs standalone**: Remote MCP uses OAuth; standalone hosted/local MCP uses headers or environment variables.
- **Client compatibility**: clients that do not implement the required OAuth resource flow may need the standalone MCP server or LangSmith CLI.
- **Self-hosting**: use `https://<host>/api/mcp` for self-hosted v0.15+ Remote MCP; set `LANGSMITH_ENDPOINT` for standalone server deployments.

---

## 6. Browser UI harness

Use browser automation only when no SDK/API/MCP route exists or when validating the UI itself.

### 6.1 Prerequisites

```bash
pip install -U playwright pytest
playwright install chromium
```

### 6.2 Stored-auth smoke test

Create storage state interactively once, keep it out of version control, then reuse it for UI checks.

```python
# test_langsmith_ui.py
import os

from playwright.sync_api import expect, sync_playwright


BASE_URL = os.getenv("LANGSMITH_UI_URL", "https://smith.langchain.com")
ORG_SLUG = os.getenv("LANGSMITH_ORG_SLUG", "default")
STATE_PATH = os.getenv("LANGSMITH_STORAGE_STATE", "langsmith_state.json")


def test_projects_page_loads():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(storage_state=STATE_PATH)
            page = context.new_page()
            page.goto(f"{BASE_URL}/o/{ORG_SLUG}")
            expect(page.get_by_text("Projects").first).to_be_visible(timeout=20000)
        finally:
            browser.close()
```

### 6.3 Browser gotchas

- **SSO/MFA**: avoid automating login in tests; reuse stored auth state.
- **Trace data**: do not commit screenshots, downloads, videos, traces, or storage state.
- **Selectors**: prefer accessible roles/text and resilient waits; UI internals can change.
- **Fresh data**: newly ingested traces may lag in the UI; poll or wait before asserting.

---

## 7. Choosing an entry point

| Task shape | Recommended entry point |
|------------|-------------------------|
| Trace an app or chain | SDK tracing |
| Query recent runs or root traces | SDK `list_runs` |
| Export high-volume traces | Bulk export, not ad hoc loops |
| Create datasets or examples | SDK dataset methods |
| Run offline experiments | SDK `client.evaluate` |
| Manage prompt versions | SDK prompt methods |
| Log user or evaluator feedback | SDK `create_feedback` |
| Let an agent inspect LangSmith | Official LangSmith MCP server |
| Validate visual UI behavior | Playwright with stored auth |

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `401 Unauthorized` | Missing, expired, or wrong API key | Rotate key and check env/profile |
| `403 Forbidden` | Key lacks access to the target workspace | Use a key for that workspace and set `LANGSMITH_WORKSPACE_ID` / `x-tenant-id` |
| Traces in wrong workspace | Multi-workspace key without workspace ID | Set `LANGSMITH_WORKSPACE_ID` |
| Traces in wrong project | Missing or stale project env | Set `LANGSMITH_PROJECT` or tracing context |
| No traces appear | Tracing disabled or import order issue | Set `LANGSMITH_TRACING=true` before app setup |
| `404` on self-hosted endpoint | Endpoint includes a versioned suffix | Remove `/api/v1` from `LANGSMITH_ENDPOINT` |
| `429` rate limited | Too many runs/queries or high eval concurrency | Back off and lower `max_concurrency` |
| Evaluation fails with key errors | Evaluator expects a different output shape | Align target outputs and evaluator parameters |
| `openevals` judge errors on the model | Bare model name passed | Use a `provider:model` string (e.g. `openai:gpt-4.1`) |
| Async tests are skipped or warn "coroutine was never awaited" | pytest-asyncio not active | Mark tests `@pytest.mark.asyncio` or set `asyncio_mode = auto` |
| MCP response too large | Missing pagination or broad filters | Pass limits, filters, and page numbers |
| Browser test stuck at login | Storage state expired | Re-authenticate and regenerate local state |

---

## 9. References

- LangSmith account and API keys: https://docs.langchain.com/langsmith/create-account-api-key
- Trace LangChain apps: https://docs.langchain.com/langsmith/trace-with-langchain
- Trace with the REST API: https://docs.langchain.com/langsmith/trace-with-api
- Query traces: https://docs.langchain.com/langsmith/export-traces
- Evaluation quickstart: https://docs.langchain.com/langsmith/evaluation-quickstart
- Define evaluation targets: https://docs.langchain.com/langsmith/define-target-function
- openevals (LLM-as-judge evaluators): https://github.com/langchain-ai/openevals
- Manage prompts programmatically: https://docs.langchain.com/langsmith/manage-prompts-programmatically
- LangSmith Remote MCP: https://docs.langchain.com/langsmith/langsmith-remote-mcp
- LangSmith MCP server: https://docs.langchain.com/langsmith/langsmith-mcp-server
- Browser automation with Playwright: https://playwright.dev/python/
