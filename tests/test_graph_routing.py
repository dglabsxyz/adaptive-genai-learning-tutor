from uuid import uuid4

from backend.graph import classify_intent, run_tutor_turn
from backend.tools import tutor_get_next_exercise_impl


def test_router_classifies_core_intents():
    assert classify_intent("I want to learn AI agents") == "diagnose"
    assert classify_intent("recommend a study plan for RAG") == "recommend_path"
    assert classify_intent("give me a practice exercise") == "practice"
    assert classify_intent("show my progress") == "progress"
    assert classify_intent("search sources about MCP") == "search_material"


def test_graph_runs_diagnostic_turn():
    learner_id = f"graph-{uuid4()}"
    response = run_tutor_turn(learner_id, "I want to learn AI agents", thread_id=learner_id)

    assert response["intent"] == "diagnose"
    assert "diagnostic" in response
    assert "study_plan" in response
    assessment = response["diagnostic"]["assessment"]
    statuses = {item["skill"]: item["status"] for item in assessment}
    assert statuses["RAG"] == "developing"
    assert statuses["MCP"] == "exposure"


def test_graph_interrupts_ambiguous_answer_with_active_exercise():
    learner_id = f"graph-{uuid4()}"
    tutor_get_next_exercise_impl(learner_id, skill="RAG")

    response = run_tutor_turn(learner_id, "answer: maybe", thread_id=learner_id)

    assert response["needs_clarification"] is True
    assert response["interrupt"]["reason"] == "ambiguous_answer"
