"""Retrieval + grading evaluation harness (LangSmith-compatible).

Closes REVIEW item 4: the project had in-app citation/retrieval reports but no
dataset-driven regression evaluation. This module defines small datasets,
deterministic targets (the real tutor functions), and evaluators that score
them. It runs fully offline by default; when a LangSmith key is configured it
can upload the run as an experiment via ``langsmith.Client.evaluate``.

Design:
- No network or model calls at import time.
- The targets are the deterministic tutor functions, so offline runs are
  reproducible and safe in CI even without the Qwen or LangSmith keys.
"""

from __future__ import annotations

from typing import Any, Callable

from .tools import (
    search_course_material_impl,
    tutor_get_next_exercise_impl,
    tutor_submit_answer_impl,
)

LEARNING_RECORD_TYPES = ("topic", "course", "coverage", "research_index")

EVAL_TENANT = "eval-harness"

# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

# ``topic`` is a substring expected to appear in at least one returned title.
RETRIEVAL_DATASET: list[dict[str, Any]] = [
    {"inputs": {"query": "retrieval augmented generation"}, "reference_outputs": {"topic": "rag"}},
    {"inputs": {"query": "model context protocol"}, "reference_outputs": {"topic": "mcp"}},
    {"inputs": {"query": "ai agents tool use"}, "reference_outputs": {"topic": "ai agents"}},
    {"inputs": {"query": "prompt engineering"}, "reference_outputs": {"topic": "prompt engineering"}},
    {"inputs": {"query": "ai safety and evaluation"}, "reference_outputs": {"topic": "eval"}},
]

# "strong" answers should grade well; vague ones should be flagged as needing
# clarification. The deterministic grader is keyword/rubric based, so the
# reliable "strong" case is the multiple-choice path with its canonical answer.
GRADING_DATASET: list[dict[str, Any]] = [
    {
        "inputs": {
            "skill": "RAG",
            "exercise_type": "multiple_choice",
            "answer": "B. Retrieve local topic and course records, cite the source refs, and keep missing metadata unknown.",
        },
        "reference_outputs": {"outcome": "graded_strong"},
    },
    {
        "inputs": {"skill": "RAG", "exercise_type": "short_answer", "answer": "idk maybe"},
        "reference_outputs": {"outcome": "needs_clarification"},
    },
]


# ---------------------------------------------------------------------------
# Targets (the real tutor under test)
# ---------------------------------------------------------------------------

def retrieval_target(inputs: dict[str, Any]) -> dict[str, Any]:
    payload = search_course_material_impl(query=inputs["query"], k=5, tenant_id=EVAL_TENANT)
    results = payload.get("results", [])
    return {
        "top_record_type": results[0]["record_type"] if results else None,
        "titles": [r["title"].lower() for r in results],
        "result_count": len(results),
    }


def grading_target(inputs: dict[str, Any]) -> dict[str, Any]:
    learner_id = f"eval-{inputs['skill'].lower().replace(' ', '-')}-{inputs.get('exercise_type', 'short')}"
    exercise = tutor_get_next_exercise_impl(
        learner_id=learner_id,
        skill=inputs["skill"],
        exercise_type=inputs.get("exercise_type", "short_answer"),
        tenant_id=EVAL_TENANT,
    )
    result = tutor_submit_answer_impl(
        learner_id=learner_id,
        answer=inputs["answer"],
        exercise_id=exercise["exercise"]["id"],
        tenant_id=EVAL_TENANT,
    )
    if result.get("needs_clarification"):
        return {"outcome": "needs_clarification", "verdict": None, "score": None}
    return {"outcome": "graded", "verdict": result.get("verdict"), "score": result.get("score")}


# ---------------------------------------------------------------------------
# Evaluators (inputs, outputs, reference_outputs) -> {key, score}
# ---------------------------------------------------------------------------

def retrieval_top_is_learning_record(inputs, outputs, reference_outputs) -> dict[str, Any]:
    ok = outputs.get("top_record_type") in LEARNING_RECORD_TYPES
    return {"key": "top_is_learning_record", "score": 1.0 if ok else 0.0}


def retrieval_finds_expected_topic(inputs, outputs, reference_outputs) -> dict[str, Any]:
    expected = reference_outputs["topic"].lower()
    found = any(expected in title for title in outputs.get("titles", []))
    return {"key": "finds_expected_topic", "score": 1.0 if found else 0.0}


def grading_matches_expected_outcome(inputs, outputs, reference_outputs) -> dict[str, Any]:
    expected = reference_outputs["outcome"]
    if expected == "graded_strong":
        ok = outputs.get("outcome") == "graded" and outputs.get("verdict") in {"strong", "partial"}
    else:
        ok = outputs.get("outcome") == expected
    return {"key": "matches_expected_outcome", "score": 1.0 if ok else 0.0}


SUITES: dict[str, dict[str, Any]] = {
    "retrieval": {
        "dataset": RETRIEVAL_DATASET,
        "target": retrieval_target,
        "evaluators": [retrieval_top_is_learning_record, retrieval_finds_expected_topic],
    },
    "grading": {
        "dataset": GRADING_DATASET,
        "target": grading_target,
        "evaluators": [grading_matches_expected_outcome],
    },
}


def run_offline(suite_names: list[str] | None = None) -> dict[str, Any]:
    """Run the evaluators locally and return per-suite pass rates. No network."""
    names = suite_names or list(SUITES)
    report: dict[str, Any] = {"suites": {}, "passed": True}
    for name in names:
        suite = SUITES[name]
        target: Callable = suite["target"]
        rows: list[dict[str, Any]] = []
        scores: list[float] = []
        for example in suite["dataset"]:
            outputs = target(example["inputs"])
            example_scores = {}
            for evaluator in suite["evaluators"]:
                result = evaluator(example["inputs"], outputs, example.get("reference_outputs", {}))
                example_scores[result["key"]] = result["score"]
                scores.append(result["score"])
            rows.append({"inputs": example["inputs"], "scores": example_scores})
        mean = round(sum(scores) / len(scores), 3) if scores else 0.0
        report["suites"][name] = {"mean_score": mean, "n": len(suite["dataset"]), "rows": rows}
        if mean < 1.0:
            report["passed"] = False
    return report


def run_langsmith(suite_names: list[str] | None = None, upload: bool = True) -> dict[str, Any]:
    """Run the suites through LangSmith's evaluate(). Requires a LangSmith key.

    Falls back to offline if langsmith is unavailable or not configured.
    """
    from .settings import get_settings

    settings = get_settings()
    if not settings.langsmith_api_key:
        return {"mode": "offline_fallback", "reason": "no LANGSMITH_API_KEY", **run_offline(suite_names)}
    try:
        from langsmith import Client
    except Exception:
        return {"mode": "offline_fallback", "reason": "langsmith not installed", **run_offline(suite_names)}

    client = Client()
    names = suite_names or list(SUITES)
    experiments = {}
    for name in names:
        suite = SUITES[name]
        dataset_name = f"adaptive-tutor-{name}"
        try:
            dataset = client.create_dataset(dataset_name=dataset_name)
            client.create_examples(
                dataset_id=dataset.id,
                examples=[
                    {"inputs": ex["inputs"], "outputs": ex.get("reference_outputs", {})}
                    for ex in suite["dataset"]
                ],
            )
        except Exception:
            dataset_name = dataset_name  # dataset likely already exists; reuse by name
        experiment = client.evaluate(
            suite["target"],
            data=dataset_name,
            evaluators=suite["evaluators"],
            experiment_prefix=f"adaptive-tutor-{name}",
            upload_results=upload,
            max_concurrency=2,
        )
        experiments[name] = str(experiment)
    return {"mode": "langsmith", "experiments": experiments}
