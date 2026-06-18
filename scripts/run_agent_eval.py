"""Agent-level LangSmith evaluation for the deep-agent tutor.

Where ``scripts/run_evals.py`` (backed by ``backend/evaluation.py``) evaluates the
*deterministic tutor tools* offline, this script evaluates the *whole deep agent*:
it builds a small LangSmith dataset of ``(message -> expected behavior)`` and runs
``client.evaluate`` over ``backend.agent_runtime.run_tutor_turn``. Because the
target drives the real orchestrator + subagents over Qwen, the experiment lands an
**experiment row next to the nested agent traces** in LangSmith — so a judge can
open one project and see both "how the agent behaved on a fixed set" and "which
subagent ran which tool" for each example.

Behavior checks (deliberately behavioral, not exact-match, since the agent is an
LLM): every turn must produce output, "respond" turns return a non-empty message
without interrupting, and the "save my progress" turn must trip the human-in-the-
loop ``commit_progress`` gate (``needs_clarification`` + a commit action request).

Gating (mirrors the offline-gate convention):
- No Qwen key  -> SKIP, exit 0 (the offline gates run this without keys).
- No LangSmith key -> SKIP, exit 0 (can't build a dataset / experiment).
- Both present -> run live; the experiment + traces land in LANGSMITH_PROJECT
  (default ``adaptive-tutor-deep-agent``).

Run (needs QWEN_API_KEY + LANGSMITH_API_KEY + LANGSMITH_WORKSPACE_ID in .env):

    LANGSMITH_TRACING=true TUTOR_REPOSITORY_BACKEND=json \
        uv run python scripts/run_agent_eval.py

Useful flags: ``--limit N`` (evaluate only the first N examples), ``--no-upload``
(dry-run: run the agent + evaluators but don't create an experiment row),
``--max-concurrency N`` (default 1 — sequential is gentlest on Qwen rate limits and
keeps each example on its own agent thread).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
# Route tracing + the experiment to the deep-agent project so the experiment row
# sits next to the agent's nested traces. Set before importing the agent.
os.environ["LANGSMITH_TRACING"] = "true"
os.environ.setdefault("LANGSMITH_PROJECT", "adaptive-tutor-deep-agent")

DATASET_NAME = "adaptive-tutor-agent"
LEARNER = "agent-eval"
TENANT = os.environ.get("TUTOR_LOCAL_TENANT_ID", "local")
# Unique per-process suffix so each run starts every example on a fresh agent
# thread (no checkpoint/interrupt state leaking in from a previous run).
RUN_NONCE = time.strftime("%Y%m%d-%H%M%S")


def _has_qwen_key() -> bool:
    return bool(os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"))


def _has_langsmith_key() -> bool:
    return bool(os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"))


# ---------------------------------------------------------------------------
# Dataset: (message -> expected behavior) across the tutoring pipeline + HITL.
# ---------------------------------------------------------------------------
AGENT_EVAL_DATASET: list[dict] = [
    {
        "inputs": {
            "message": "I want to learn RAG and AI agents. Diagnose me and plan a study path.",
            "thread": "goal",
        },
        "outputs": {"behavior": "respond"},
    },
    {
        "inputs": {"message": "Give me one exercise on RAG.", "thread": "exercise"},
        "outputs": {"behavior": "respond"},
    },
    {
        "inputs": {
            "message": (
                "My answer: retrieve relevant corpus snippets with embeddings and vector search, "
                "ground the answer in those source citations, keep missing fields uncertain, and "
                "evaluate retrieval quality plus answer faithfulness."
            ),
            "thread": "grade",
        },
        "outputs": {"behavior": "respond"},
    },
    {
        "inputs": {"message": "This looks good — please save my progress for this session.", "thread": "commit"},
        "outputs": {"behavior": "interrupt_commit"},
    },
    {
        "inputs": {"message": "What should I focus on first to become production-ready?", "thread": "advice"},
        "outputs": {"behavior": "respond"},
    },
]


# ---------------------------------------------------------------------------
# Target: the real deep agent under test.
# ---------------------------------------------------------------------------
def agent_target(inputs: dict) -> dict:
    """Run one tutor turn and normalize the observable behavior for evaluators."""
    from backend.agent_runtime import run_tutor_turn

    thread = f"agent-eval-{inputs.get('thread', 't')}-{RUN_NONCE}"
    result = run_tutor_turn(LEARNER, inputs["message"], thread_id=thread, tenant_id=TENANT)

    actions: list[str] = []
    if result.get("needs_clarification"):
        for req in (result.get("interrupt") or {}).get("action_requests", []) or []:
            if isinstance(req, dict):
                actions.append(req.get("name") or req.get("action") or "?")
    return {
        "message": (result.get("message") or "").strip(),
        "needs_clarification": bool(result.get("needs_clarification")),
        "interrupt_actions": actions,
    }


# ---------------------------------------------------------------------------
# Evaluators: (inputs, outputs, reference_outputs) -> {key, score}.
# ---------------------------------------------------------------------------
def produced_output(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Every turn must yield something: a message or a pending action request."""
    ok = bool(outputs.get("message")) or bool(outputs.get("interrupt_actions"))
    return {"key": "produced_output", "score": 1.0 if ok else 0.0}


def matches_expected_behavior(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Respond turns answer without interrupting; the commit turn trips the HITL gate."""
    expected = (reference_outputs or {}).get("behavior", "respond")
    if expected == "interrupt_commit":
        ok = bool(outputs.get("needs_clarification")) and any(
            "commit" in (action or "") for action in outputs.get("interrupt_actions", [])
        )
    else:  # "respond"
        ok = (not outputs.get("needs_clarification")) and bool(outputs.get("message"))
    return {"key": "matches_expected_behavior", "score": 1.0 if ok else 0.0}


EVALUATORS = [produced_output, matches_expected_behavior]


def _ensure_dataset(client) -> None:
    """Create the dataset + examples once; reuse it by name on later runs."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        return
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Agent-level behavior set for the deep-agent tutor (message -> expected behavior).",
    )
    client.create_examples(
        dataset_id=dataset.id,
        examples=[{"inputs": ex["inputs"], "outputs": ex["outputs"]} for ex in AGENT_EVAL_DATASET],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N examples")
    parser.add_argument("--only", default=None, help="Evaluate only the example with this 'thread' label (e.g. commit)")
    parser.add_argument("--no-upload", action="store_true", help="Dry run: run the agent + evaluators but create no experiment")
    parser.add_argument("--max-concurrency", type=int, default=1, help="Parallel examples (default 1)")
    args = parser.parse_args()

    if not _has_qwen_key():
        print("SKIP run_agent_eval: QWEN_API_KEY (or DASHSCOPE_API_KEY) not set — the deep agent needs it. Offline gate no-op.")
        return 0
    if not _has_langsmith_key():
        print("SKIP run_agent_eval: LANGSMITH_API_KEY not set — cannot build the dataset/experiment. Offline gate no-op.")
        return 0

    # Configure tracing now that we know we're running live.
    from backend.config import configure_langsmith

    configure_langsmith()

    from langsmith import Client

    client = Client()
    _ensure_dataset(client)

    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    if args.only:
        examples = [ex for ex in examples if (ex.inputs or {}).get("thread") == args.only]
    if args.limit is not None:
        examples = examples[: args.limit]
    upload = not args.no_upload

    project = os.environ.get("LANGSMITH_PROJECT", "adaptive-tutor-deep-agent")
    print(
        f"Running agent eval: {len(examples)} example(s), upload={upload}, "
        f"max_concurrency={args.max_concurrency} -> project '{project}'"
    )

    experiment = client.evaluate(
        agent_target,
        data=examples,
        evaluators=EVALUATORS,
        experiment_prefix=DATASET_NAME,
        max_concurrency=args.max_concurrency,
        upload_results=upload,
    )

    # Summarize pass rates without requiring pandas.
    totals: dict[str, list[float]] = {}
    for row in experiment:
        for res in (row.get("evaluation_results", {}) or {}).get("results", []) or []:
            score = getattr(res, "score", None)
            if score is not None:
                totals.setdefault(res.key, []).append(float(score))
    print("\nResults:")
    for key, scores in totals.items():
        mean = sum(scores) / len(scores) if scores else 0.0
        print(f"  {key}: {mean:.2f} mean over {len(scores)} example(s)")

    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers

        wait_for_all_tracers()
    except Exception:  # pragma: no cover - flushing is best-effort
        pass

    name = getattr(experiment, "experiment_name", DATASET_NAME)
    print(f"\nDone. Experiment '{name}' and its agent traces are in LangSmith project '{project}'.")
    # Non-zero exit if either evaluator regressed below a perfect score.
    all_scores = [s for scores in totals.values() for s in scores]
    passed = all(s == 1.0 for s in all_scores) if all_scores else True
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
