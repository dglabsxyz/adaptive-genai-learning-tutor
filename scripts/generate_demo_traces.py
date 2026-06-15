"""Generate a rich set of LangSmith traces for the agent demo video.

Exercises the real LangGraph tutor graph end to end so every turn produces a
trace tree (route -> interrupt_guard -> dispatch, with per-tool spans from the
@traceable impls in backend/tools.py). Covers the normal pipeline plus the two
human-in-the-loop interrupts (vague goal, destructive reset) and both the
confirm and decline branches of the audited reset.

Run:
    LANGSMITH_TRACING=true uv run python scripts/generate_demo_traces.py

Requires a working LANGSMITH_API_KEY + LANGSMITH_WORKSPACE_ID in .env (see HANDOFF).
Traces land in the LANGSMITH_PROJECT project (default: week3-adaptive-tutor).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure tracing is on for this process before importing the graph.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "true"

from backend.config import configure_langsmith  # noqa: E402

configure_langsmith()

from backend.graph import resume_tutor_turn, run_tutor_turn  # noqa: E402


GRADE_ANSWER = (
    "I would retrieve relevant local corpus records with embeddings and vector "
    "search, ground the answer in source snippets and citations, preserve "
    "uncertainty for missing fields, and evaluate answer faithfulness plus "
    "retrieval quality."
)


def _flag(result: dict) -> str:
    if result.get("needs_clarification"):
        interrupt = result.get("interrupt") or {}
        reason = interrupt.get("reason") if isinstance(interrupt, dict) else None
        return f"INTERRUPT ({reason or 'needs_clarification'})"
    return f"intent={result.get('intent')}"


def turn(label: str, learner: str, message: str, thread: str) -> dict:
    result = run_tutor_turn(learner, message, thread_id=thread)
    print(f"  {label}: run '{message[:48]}' -> {_flag(result)}")
    return result


def resume(label: str, learner: str, answer: str, thread: str) -> dict:
    result = resume_tutor_turn(learner, answer, thread_id=thread)
    print(f"  {label}: resume '{answer[:32]}' -> {_flag(result)}")
    return result


def main() -> None:
    print("Scenario A - full pipeline (diagnose -> path -> exercise -> grade -> progress)")
    turn("A1", "ls-demo", "I want to learn AI agents and RAG", "trace-pipeline")
    turn("A2", "ls-demo", "Give me an exercise on RAG", "trace-pipeline")
    turn("A3", "ls-demo", f"My answer is: {GRADE_ANSWER}", "trace-pipeline")
    turn("A4", "ls-demo", "Show my progress", "trace-pipeline")

    print("Scenario B - vague-goal interrupt + resume")
    turn("B1", "ls-demo-vague", "Help me learn", "trace-vague")
    resume("B2", "ls-demo-vague", "RAG", "trace-vague")

    print("Scenario C - destructive reset: confirm (audited)")
    turn("C1", "ls-demo-reset", "Please reset progress", "trace-reset-yes")
    resume("C2", "ls-demo-reset", "yes", "trace-reset-yes")

    print("Scenario D - destructive reset: decline")
    turn("D1", "ls-demo-reset2", "Please reset progress", "trace-reset-no")
    resume("D2", "ls-demo-reset2", "no", "trace-reset-no")

    # Force the background tracer to flush before the process exits.
    from langchain_core.tracers.langchain import wait_for_all_tracers

    wait_for_all_tracers()
    project = os.environ.get("LANGSMITH_PROJECT", "week3-adaptive-tutor")
    print(f"\nDone. Traces flushed to LangSmith project '{project}'.")


if __name__ == "__main__":
    main()
