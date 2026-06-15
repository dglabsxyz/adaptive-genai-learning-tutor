from uuid import uuid4

from backend.tools import (
    TUTOR_TOOLS,
    tutor_assess_skills_impl,
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
    tutor_view_progress_impl,
)


def test_langchain_tools_are_registered():
    names = {tool.name for tool in TUTOR_TOOLS}

    assert {
        "search_course_material",
        "tutor_assess_skills",
        "tutor_get_next_exercise",
        "tutor_submit_answer",
        "tutor_view_progress",
        "tutor_recommend_path",
    } <= names


def test_grading_updates_persistent_progress():
    learner_id = f"test-{uuid4()}"
    tutor_assess_skills_impl(learner_id, "I want to learn AI agents", answers=[])
    before = tutor_view_progress_impl(learner_id)["progress"]["RAG"]["attempts"]
    exercise = tutor_get_next_exercise_impl(learner_id, skill="RAG")["exercise"]

    grade = tutor_submit_answer_impl(
        learner_id,
        "I would retrieve with embeddings from a vector index, ground the answer in source citations, preserve unknown fields instead of inventing, and evaluate faithfulness with tests.",
        exercise_id=exercise["id"],
    )
    after = tutor_view_progress_impl(learner_id)["progress"]["RAG"]

    assert grade["score"] >= 0.75
    assert after["attempts"] == before + 1
    assert after["correct_streak"] >= 1
    assert after["source_refs"]
    assert grade["mastery_update"]["evidence"]


def test_learning_flows_prioritize_topic_or_course_sources():
    learner_id = f"test-{uuid4()}"
    plan = tutor_recommend_path_impl(learner_id, "I want to learn AI agents")
    rag_module = next(module for module in plan["modules"] if module["skill"] == "RAG")
    exercise = tutor_get_next_exercise_impl(learner_id, skill="RAG")["exercise"]

    assert rag_module["source_refs"][0]["record_type"] in {"topic", "course", "coverage", "research_index"}
    assert exercise["source_refs"][0]["record_type"] in {"topic", "course", "coverage", "research_index"}


def test_exercise_type_variants_include_multiple_choice():
    learner_id = f"test-{uuid4()}"
    exercise = tutor_get_next_exercise_impl(
        learner_id,
        skill="MCP",
        exercise_type="multiple_choice",
    )["exercise"]

    assert exercise["exercise_type"] == "multiple_choice"
    assert exercise["choices"]
    assert exercise["answer_key"] == ["B"]


def test_ambiguous_answer_does_not_update_attempts():
    learner_id = f"test-{uuid4()}"
    exercise = tutor_get_next_exercise_impl(learner_id, skill="RAG")["exercise"]
    before = tutor_view_progress_impl(learner_id)["progress"]["RAG"]["attempts"]

    grade = tutor_submit_answer_impl(learner_id, "maybe", exercise_id=exercise["id"])
    after = tutor_view_progress_impl(learner_id)["progress"]["RAG"]["attempts"]

    assert grade["needs_clarification"] is True
    assert after == before


def test_partial_credit_grading_explains_mastery_update():
    learner_id = f"test-{uuid4()}"
    tutor_assess_skills_impl(learner_id, "I want to learn AI agents", answers=[])
    exercise = tutor_get_next_exercise_impl(learner_id, skill="RAG")["exercise"]

    grade = tutor_submit_answer_impl(
        learner_id,
        "I would retrieve relevant records with vector search and use the evidence to answer.",
        exercise_id=exercise["id"],
    )

    assert 0 < grade["score"] < 1
    assert grade["covered_points"]
    assert grade["missed_points"]
    assert grade["mastery_update"]["status_reason"]
