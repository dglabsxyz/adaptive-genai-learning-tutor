"""LangGraph tutor orchestrator with routing, memory, and interrupt behavior."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from .audit import write_audit_event
from .checkpoints import build_checkpointer
from .stores import exercise_store, learner_store, reset_learner_progress
from .tools import (
    answer_needs_clarification,
    search_course_material_impl,
    tutor_assess_skills_impl,
    tutor_get_next_exercise_impl,
    tutor_recommend_path_impl,
    tutor_submit_answer_impl,
    tutor_view_progress_impl,
)
from .topic_utils import is_vague_goal, resolve_skills

Intent = Literal[
    "diagnose",
    "recommend_path",
    "practice",
    "submit_answer",
    "progress",
    "search_material",
    "reset_progress",
    "reset_declined",
    "other",
]


def _is_affirmative(text: str) -> bool:
    """Decide whether a confirmation reply approves a destructive reset."""
    lowered = text.strip().lower()
    if any(neg in lowered for neg in ["no", "cancel", "stop", "don't", "do not", "nevermind", "never mind"]):
        return False
    return any(
        yes in lowered
        for yes in ["yes", "confirm", "proceed", "go ahead", "reset", "wipe", "delete", "do it", "sure", "ok", "okay"]
    )


class TutorState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    learner_id: str
    tenant_id: str
    intent: Intent
    active_skill: str | None
    active_exercise: dict[str, Any] | None
    response: dict[str, Any] | None
    source_refs: list[dict[str, Any]]


def _last_human_text(state: TutorState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _resume_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("message", "answer", "text", "query", "goal"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
    return str(value).strip()


def classify_intent(text: str) -> Intent:
    lowered = text.lower()
    if any(word in lowered for word in ["progress", "mastery", "how am i doing"]):
        return "progress"
    if any(word in lowered for word in ["answer", "submit", "my response is", "grade this"]):
        return "submit_answer"
    if any(word in lowered for word in ["exercise", "practice", "quiz", "question"]):
        return "practice"
    if any(word in lowered for word in ["study plan", "path", "recommend", "roadmap"]):
        return "recommend_path"
    if any(word in lowered for word in ["search", "source", "course", "material", "citation"]):
        return "search_material"
    if any(word in lowered for word in ["diagnostic", "assess", "learn", "study", "goal"]):
        return "diagnose"
    return "other"


def route_node(state: TutorState) -> TutorState:
    text = _last_human_text(state)
    skills = resolve_skills(text)
    return {
        "intent": classify_intent(text),
        "active_skill": skills[0] if skills else None,
    }


def interrupt_guard_node(state: TutorState) -> TutorState:
    text = _last_human_text(state)
    lowered = text.lower()
    if any(word in lowered for word in ["delete progress", "reset progress", "wipe progress"]):
        write_audit_event(
            "destructive_action_interrupt",
            learner_id=state.get("learner_id") or "demo-learner",
            tenant_id=state.get("tenant_id"),
            outcome="interrupted",
            metadata={"reason": "confirm_destructive_action"},
        )
        resumed = interrupt(
            {
                "reason": "confirm_destructive_action",
                "message": "Resetting progress is destructive. Reply 'yes' to confirm the reset, or 'no' to cancel.",
            }
        )
        if text := _resume_text(resumed):
            decision = "reset_progress" if _is_affirmative(text) else "reset_declined"
            return {"intent": decision, "messages": [HumanMessage(content=text)]}
    if state.get("intent") in {"diagnose", "recommend_path"} and is_vague_goal(text):
        resumed = interrupt(
            {
                "reason": "vague_goal",
                "message": "Which GenAI topic should we focus on first: RAG, AI agents, MCP, prompt engineering, or another corpus topic?",
            }
        )
        if text := _resume_text(resumed):
            return {"messages": [HumanMessage(content=text)]}
    matches = resolve_skills(text)
    if state.get("intent") == "search_material" and len(matches) > 2:
        resumed = interrupt(
            {
                "reason": "ambiguous_reference",
                "message": f"Your reference could match multiple topics: {', '.join(matches)}. Please narrow the search.",
            }
        )
        if text := _resume_text(resumed):
            return {"messages": [HumanMessage(content=text)]}
    if state.get("intent") == "submit_answer":
        profile = learner_store.get(
            state.get("learner_id") or "demo-learner",
            tenant_id=state.get("tenant_id"),
        )
        active_exercise = (
            exercise_store.get(profile.active_exercise_id, tenant_id=state.get("tenant_id"))
            if profile.active_exercise_id
            else None
        )
        if active_exercise and answer_needs_clarification(_answer_text(text), active_exercise.exercise_type):
            resumed = interrupt(
                {
                    "reason": "ambiguous_answer",
                    "message": "Your answer is too ambiguous to grade. Add the main design choices, evidence, or option rationale.",
                    "active_exercise_id": active_exercise.id,
                }
            )
            if text := _resume_text(resumed):
                return {"messages": [HumanMessage(content=text)]}
    return {}


def _answer_text(text: str) -> str:
    lowered = text.lower()
    for marker in ["my answer is", "my response is", "answer:", "submit:"]:
        if marker in lowered:
            index = lowered.index(marker) + len(marker)
            return text[index:].strip()
    return text


def dispatch_node(state: TutorState) -> TutorState:
    learner_id = state.get("learner_id") or "demo-learner"
    tenant_id = state.get("tenant_id")
    text = _last_human_text(state)
    intent = state.get("intent") or "other"
    if intent == "reset_progress":
        result = reset_learner_progress(learner_id, tenant_id=tenant_id)
        response = {"intent": intent, "message": result["message"], "reset": result, "source_refs": []}
        return {
            "response": response,
            "source_refs": [],
            "messages": [AIMessage(content=response["message"])],
        }
    if intent == "reset_declined":
        response = {
            "intent": intent,
            "message": "Reset cancelled. Your progress is unchanged.",
            "source_refs": [],
        }
        return {
            "response": response,
            "source_refs": [],
            "messages": [AIMessage(content=response["message"])],
        }
    if intent == "diagnose":
        diagnostic = tutor_assess_skills_impl(learner_id=learner_id, goal=text, tenant_id=tenant_id)
        plan = tutor_recommend_path_impl(learner_id=learner_id, goal=text, tenant_id=tenant_id)
        response = {
            "intent": intent,
            "message": f"{diagnostic['summary']} I also prepared a source-backed study path.",
            "diagnostic": diagnostic,
            "study_plan": plan,
            "source_refs": diagnostic["source_refs"][:4],
        }
    elif intent == "recommend_path":
        plan = tutor_recommend_path_impl(learner_id=learner_id, goal=text, tenant_id=tenant_id)
        response = {
            "intent": intent,
            "message": "Here is a source-backed study path.",
            "study_plan": plan,
            "source_refs": plan["source_refs"][:4],
        }
    elif intent == "practice":
        exercise_payload = tutor_get_next_exercise_impl(
            learner_id=learner_id,
            skill=state.get("active_skill"),
            goal=text,
            tenant_id=tenant_id,
        )
        response = {
            "intent": intent,
            "message": "Here is your next source-backed exercise.",
            "exercise": exercise_payload,
            "source_refs": exercise_payload["source_refs"],
        }
    elif intent == "submit_answer":
        grading = tutor_submit_answer_impl(
            learner_id=learner_id,
            answer=_answer_text(text),
            tenant_id=tenant_id,
        )
        response = {
            "intent": intent,
            "message": "I graded your answer and updated progress.",
            "grading": grading,
            "source_refs": grading.get("source_refs", []),
        }
    elif intent == "progress":
        response = {
            "intent": intent,
            "message": "Here is the persistent mastery state.",
            "progress": tutor_view_progress_impl(learner_id=learner_id, tenant_id=tenant_id),
        }
    elif intent == "search_material":
        search = search_course_material_impl(query=text, k=5, tenant_id=tenant_id)
        response = {
            "intent": intent,
            "message": "Here are matching source-backed corpus records.",
            "search": search,
            "source_refs": search["source_refs"],
        }
    else:
        search = search_course_material_impl(query=text, k=3, tenant_id=tenant_id)
        response = {
            "intent": intent,
            "message": "I can help with diagnostics, study paths, practice, grading, progress, or corpus search.",
            "search": search,
            "source_refs": search["source_refs"],
        }
    learner_store.append_history(learner_id, {"type": "chat", "intent": intent, "message": text}, tenant_id=tenant_id)
    return {
        "response": response,
        "source_refs": response.get("source_refs", []),
        "messages": [AIMessage(content=response["message"])],
    }


def build_tutor_graph():
    builder = StateGraph(TutorState)
    builder.add_node("route", route_node)
    builder.add_node("interrupt_guard", interrupt_guard_node)
    builder.add_node("dispatch", dispatch_node)
    builder.add_edge(START, "route")
    builder.add_edge("route", "interrupt_guard")
    builder.add_edge("interrupt_guard", "dispatch")
    builder.add_edge("dispatch", END)
    return builder.compile(checkpointer=build_checkpointer())


tutor_graph = build_tutor_graph()


def _thread_config(learner_id: str, thread_id: str | None, tenant_id: str | None) -> tuple[str, str, dict[str, Any]]:
    tenant = tenant_id or "local"
    base_thread_id = thread_id or learner_id
    graph_thread_id = base_thread_id if tenant == "local" else f"{tenant}:{base_thread_id}"
    return tenant, base_thread_id, {"configurable": {"thread_id": graph_thread_id}}


def _format_graph_result(
    result: dict[str, Any] | Any,
    *,
    learner_id: str,
    tenant_id: str,
    thread_id: str,
) -> dict[str, Any]:
    interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
    if interrupts:
        first = interrupts[0]
        value = getattr(first, "value", first)
        return {
            "learner_id": learner_id,
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "needs_clarification": True,
            "interrupt": value,
        }
    response = result.get("response") if isinstance(result, dict) else None
    return {
        "learner_id": learner_id,
        "tenant_id": tenant_id,
        "thread_id": thread_id,
        **(response or {"message": "No tutor response was produced."}),
    }


def run_tutor_turn(
    learner_id: str,
    message: str,
    thread_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    tenant, base_thread_id, config = _thread_config(learner_id, thread_id, tenant_id)
    result = tutor_graph.invoke(
        {"messages": [HumanMessage(content=message)], "learner_id": learner_id, "tenant_id": tenant},
        config=config,
    )
    return _format_graph_result(result, learner_id=learner_id, tenant_id=tenant, thread_id=base_thread_id)


def resume_tutor_turn(
    learner_id: str,
    resume: str | dict[str, Any],
    thread_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    tenant, base_thread_id, config = _thread_config(learner_id, thread_id, tenant_id)
    result = tutor_graph.invoke(Command(resume=resume), config=config)
    return _format_graph_result(result, learner_id=learner_id, tenant_id=tenant, thread_id=base_thread_id)
