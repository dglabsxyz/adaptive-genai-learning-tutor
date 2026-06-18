"""Run the local tutor demo flow without the frontend."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.tools import (
    tutor_assess_skills_impl,
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
    tutor_view_progress_impl,
)


def main() -> None:
    learner_id = "demo-learner"
    goal = "I want to learn AI agents."
    print("1. Learner:", goal)
    diagnostic = tutor_assess_skills_impl(
        learner_id,
        goal,
        answers=["I know agents can call tools, but RAG and MCP are still fuzzy."],
    )
    print("2. Diagnostic:", diagnostic["summary"])
    for item in diagnostic["assessment"]:
        if item["skill"] in {"RAG", "MCP"}:
            print(f"   - {item['skill']}: {item['status']} ({item['proficiency']})")

    plan = tutor_recommend_path_impl(learner_id, goal)
    print(f"3. Study plan modules: {len(plan['modules'])}")
    for module in plan["modules"][:4]:
        print(f"   {module['order']}. {module['skill']} -> {module['milestone']}")

    exercise_payload = tutor_get_next_exercise_impl(learner_id, goal=goal)
    exercise = exercise_payload["exercise"]
    print("4. Exercise:", exercise["prompt"])

    answer = (
        "I would retrieve relevant local corpus records with embeddings and vector search, "
        "ground the generated answer in source snippets and citations, preserve uncertainty "
        "for missing fields, and evaluate answer faithfulness plus retrieval quality."
    )
    grade = tutor_submit_answer_impl(learner_id, answer, exercise_id=exercise["id"])
    print(f"5. Grade: {grade['score']} ({grade['verdict']})")
    print("6. Updated progress:", tutor_view_progress_impl(learner_id)["progress"][exercise["skill"]])
    print("7. MCP uses the same data files under data/learners.json and data/exercises.json.")


if __name__ == "__main__":
    main()
