"""Generate rich LangSmith traces for the deep-agent tutor demo.

Drives the deepagents orchestrator end to end so every turn produces a nested
trace tree in LangSmith: the orchestrator at the top, each `task` delegation as a
child span, and the full subagent trajectory (LLM + tool calls) nested inside —
i.e. exactly "which subagent ran which tool", which a flat message list can't show.

Covers the tutoring pipeline (diagnose -> path -> exercise -> grade) plus the
human-in-the-loop `commit_progress` gate (interrupt -> approve, and a decline).

Run (needs QWEN_API_KEY + LANGSMITH_API_KEY + LANGSMITH_WORKSPACE_ID in .env):
    LANGSMITH_TRACING=true uv run python scripts/generate_demo_traces.py

Traces land in LANGSMITH_PROJECT (default: adaptive-tutor-deep-agent).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ.setdefault("LANGSMITH_PROJECT", "adaptive-tutor-deep-agent")

from backend.config import configure_langsmith  # noqa: E402

configure_langsmith()

from backend.agent_runtime import resume_tutor_turn, run_tutor_turn  # noqa: E402

TENANT = os.environ.get("TUTOR_LOCAL_TENANT_ID", "local")
GRADE_ANSWER = (
    "Retrieve relevant local corpus records with embeddings and vector search, ground the "
    "answer in source snippets and citations, preserve uncertainty for missing fields, and "
    "evaluate retrieval quality plus answer faithfulness."
)


def _flag(result: dict) -> str:
    if result.get("needs_clarification"):
        reqs = (result.get("interrupt") or {}).get("action_requests") or []
        names = ", ".join(r.get("name", "?") for r in reqs if isinstance(r, dict))
        return f"INTERRUPT (awaiting approval: {names or 'action'})"
    return (result.get("message") or "")[:60].replace("\n", " ")


def turn(label: str, learner: str, message: str, thread: str) -> dict:
    result = run_tutor_turn(learner, message, thread_id=thread, tenant_id=TENANT)
    print(f"  {label}: run '{message[:44]}' -> {_flag(result)}")
    return result


def approve(label: str, learner: str, thread: str) -> dict:
    result = resume_tutor_turn(learner, {"decisions": [{"type": "approve"}]}, thread_id=thread, tenant_id=TENANT)
    print(f"  {label}: approve -> {_flag(result)}")
    return result


def main() -> None:
    print("Scenario A - tutoring pipeline (diagnose -> path -> exercise -> grade)")
    turn("A1", "ls-demo", "I want to learn RAG and AI agents. Diagnose me and plan a path.", "trace-pipeline")
    turn("A2", "ls-demo", "Give me one exercise on RAG.", "trace-pipeline")
    turn("A3", "ls-demo", f"My answer: {GRADE_ANSWER}", "trace-pipeline")

    print("Scenario B - human-in-the-loop commit gate (approve)")
    committed = turn("B1", "ls-demo", "Looks good — save my progress for this session.", "trace-pipeline")
    if committed.get("needs_clarification"):
        approve("B2", "ls-demo", "trace-pipeline")

    from langchain_core.tracers.langchain import wait_for_all_tracers

    wait_for_all_tracers()
    project = os.environ.get("LANGSMITH_PROJECT", "adaptive-tutor-deep-agent")
    print(f"\nDone. Deep-agent traces flushed to LangSmith project '{project}'.")


if __name__ == "__main__":
    main()
