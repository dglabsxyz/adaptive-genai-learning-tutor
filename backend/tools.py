"""LangChain tools and deterministic local tutor behavior."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import tool
from langsmith import traceable

from .audit import write_audit_event
from .dependencies import get_vector_index
from .enterprise_sink import record_answer, record_study_plan
from .models import EXERCISE_TYPES, Exercise, SearchHit, SourceRef
from .stores import exercise_store, learner_store
from .topic_utils import resolve_skills, skill_path_for_goal

LEARNING_RECORD_TYPES = ("topic", "course", "coverage", "research_index")
EXERCISE_TYPE_SEQUENCE: tuple[EXERCISE_TYPES, ...] = (
    "architecture_scenario",
    "design_critique",
    "implementation_prompt",
    "multiple_choice",
    "short_answer",
)


def _source_refs(hits: list[SearchHit], limit: int = 4) -> list[SourceRef]:
    refs: list[SourceRef] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.source_ref.source_id in seen:
            continue
        refs.append(hit.source_ref)
        seen.add(hit.source_ref.source_id)
        if len(refs) >= limit:
            break
    return refs


def _format_sources(refs: list[SourceRef]) -> list[dict[str, Any]]:
    return [ref.model_dump() for ref in refs]


def _learning_search(query: str, k: int = 5) -> list[SearchHit]:
    return get_vector_index().search(
        query,
        k=k,
        preferred_record_types=LEARNING_RECORD_TYPES,
    )


@traceable(run_type="tool", name="tutor_search_course_material")
def search_course_material_impl(query: str, k: int = 5, tenant_id: str | None = None) -> dict[str, Any]:
    """Return concise source-backed summaries from genai_research."""
    hits = _learning_search(query, k=k)
    summaries = [
        {
            "title": hit.source_ref.title,
            "record_type": hit.source_ref.record_type,
            "path": hit.source_ref.path,
            "score": hit.score,
            "summary": hit.summary,
            "citations": hit.source_ref.citations,
        }
        for hit in hits
    ]
    payload = {
        "query": query,
        "summary": "Found source-backed corpus records." if hits else "No matching corpus records found.",
        "results": summaries,
        "source_refs": _format_sources(_source_refs(hits)),
    }
    write_audit_event(
        "source_search",
        tenant_id=tenant_id,
        metadata={"query_length": len(query), "k": k, "result_count": len(summaries)},
    )
    return payload


@traceable(run_type="tool", name="tutor_assess_skills")
def tutor_assess_skills_impl(
    learner_id: str,
    goal: str,
    answers: list[str] | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Estimate learner skill levels with source-backed diagnostic probes."""
    answers = answers or []
    learner_store.add_goal(learner_id, goal, tenant_id=tenant_id)
    path = skill_path_for_goal(goal)
    context_hits = _learning_search(f"{goal} RAG MCP AI agents prerequisites diagnostic", k=6)
    refs = _source_refs(context_hits)
    combined = " ".join(answers).lower()

    baseline = {
        "LLMs": 0.45,
        "prompt engineering": 0.42,
        "context engineering": 0.28,
        "RAG": 0.42,
        "AI agents": 0.35,
        "MCP": 0.14,
        "AI coding": 0.24,
        "AI safety and evaluation": 0.26,
        "fine-tuning": 0.12,
        "multimodal AI": 0.12,
    }
    answer_boosts = {
        "RAG": ["retrieval", "embedding", "vector", "ground", "source", "citation"],
        "AI agents": ["tool", "state", "memory", "router", "langgraph", "orchestration"],
        "MCP": ["model context protocol", "mcp", "server", "resource", "tool"],
        "AI safety and evaluation": ["eval", "test", "metric", "safety", "grade"],
    }
    assessment: list[dict[str, Any]] = []
    for skill in path:
        score = baseline.get(skill, 0.2)
        for keyword in answer_boosts.get(skill, []):
            if keyword in combined:
                score += 0.04
        score = min(score, 0.82)
        profile = learner_store.update_skill(
            learner_id,
            skill,
            proficiency=score,
            source_refs=refs,
            tenant_id=tenant_id,
        )
        progress = profile.progress[skill]
        assessment.append(
            {
                "skill": skill,
                "proficiency": round(progress.proficiency, 2),
                "status": progress.status,
                "source_refs": _format_sources(progress.source_refs[:3]),
            }
        )

    learner_store.append_history(
        learner_id,
        {"type": "diagnostic", "goal": goal, "skills": [item["skill"] for item in assessment]},
        tenant_id=tenant_id,
    )
    diagnostic_questions = [
        "When would you use RAG instead of fine-tuning?",
        "What state should an AI agent remember between tool calls?",
        "How would you evaluate whether an answer is grounded in retrieved sources?",
    ]
    payload = {
        "learner_id": learner_id,
        "goal": goal,
        "summary": "Diagnostic complete. RAG is developing and MCP is exposure for this learner path."
        if "AI agents" in path
        else "Diagnostic complete.",
        "diagnostic_questions": diagnostic_questions,
        "assessment": assessment,
        "source_refs": _format_sources(refs),
    }
    write_audit_event(
        "diagnostic",
        learner_id=learner_id,
        tenant_id=tenant_id,
        metadata={
            "goal_length": len(goal),
            "answer_count": len(answers),
            "skills": [item["skill"] for item in assessment],
        },
    )
    return payload


@traceable(run_type="tool", name="tutor_recommend_path")
def tutor_recommend_path_impl(learner_id: str, goal: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Build a sequenced study path grounded in corpus records."""
    learner_store.add_goal(learner_id, goal, tenant_id=tenant_id)
    profile = learner_store.get(learner_id, tenant_id=tenant_id)
    modules: list[dict[str, Any]] = []
    all_refs: dict[str, SourceRef] = {}
    for order, skill in enumerate(skill_path_for_goal(goal), start=1):
        hits = _learning_search(f"{skill} course topic summary prerequisites exercises", k=3)
        refs = _source_refs(hits, limit=2)
        for ref in refs:
            all_refs[ref.source_id] = ref
        progress = profile.progress.get(skill)
        status = progress.status if progress else "exposure"
        why = (
            f"Current mastery is {status}; study this before moving deeper into "
            f"{goal}."
        )
        modules.append(
            {
                "order": order,
                "skill": skill,
                "status": status,
                "milestone": f"Explain and apply {skill} in a GenAI tutoring scenario.",
                "estimated_time": "45-90 minutes",
                "review_checkpoint": f"Complete one source-backed {skill} exercise and review missed points.",
                "why": why,
                "source_refs": _format_sources(refs),
            }
        )
    profile.study_plan = modules
    saved = learner_store.save(profile, tenant_id=tenant_id)
    record_study_plan(
        tenant_id=saved.tenant_id,
        learner_id=saved.learner_id,
        goal=goal,
        modules=modules,
    )
    learner_store.append_history(
        learner_id,
        {"type": "study_plan", "goal": goal, "module_count": len(modules)},
        tenant_id=tenant_id,
    )
    payload = {
        "learner_id": learner_id,
        "goal": goal,
        "summary": "Recommended path is ordered by prerequisite depth and current mastery.",
        "modules": modules,
        "source_refs": _format_sources(list(all_refs.values())[:8]),
    }
    write_audit_event(
        "study_plan",
        learner_id=learner_id,
        tenant_id=tenant_id,
        metadata={"goal_length": len(goal), "module_count": len(modules)},
    )
    return payload


def _exercise_blueprint(
    skill: str,
    exercise_type: EXERCISE_TYPES,
) -> tuple[str, list[str], list[str], str, list[str], list[str]]:
    if exercise_type == "multiple_choice":
        return (
            f"Which design choice best supports source-backed tutoring for {skill}?",
            [
                "Select B: retrieve relevant local corpus records, cite them, and preserve unknown fields.",
                "Explain why source-backed retrieval is safer than unsupported generation.",
            ],
            [
                "Look for the option that mentions both retrieval and citations.",
                "Avoid choices that fill in missing metadata.",
            ],
            "Award full credit for option B with a brief source-fidelity rationale. Award partial credit for choosing B without rationale.",
            [
                "A. Generate from memory and add likely course details when metadata is missing.",
                "B. Retrieve local topic/course records, cite source refs, and mark missing metadata as unknown.",
                "C. Prefer instructor bios because they usually contain the richest topical keywords.",
                "D. Skip retrieval when the learner goal is already clear.",
            ],
            ["B"],
        )
    if exercise_type == "design_critique":
        return (
            f"Critique this tutor design for {skill}: it recommends courses from a local corpus, but it hides source refs and fills in missing prices from memory. Name the two highest-risk issues and propose a correction.",
            [
                "Identify hidden or missing source references as a source-fidelity problem.",
                "Identify invented missing metadata as unsafe or unsupported.",
                "Propose showing source refs from topic or course records.",
                "Propose preserving missing fields as null or unknown.",
            ],
            [
                "Separate evidence visibility from metadata integrity.",
                "The correction should be visible to the learner.",
            ],
            "Award partial credit for source visibility, unknown-field preservation, and a concrete UI or backend correction.",
            [],
            [],
        )
    if exercise_type == "implementation_prompt":
        return (
            f"Write pseudocode for a local-first {skill} tutor feature. Include data read boundaries, state updates, source refs, and one test.",
            [
                "Read from genai_research without mutating it.",
                "Persist learner or exercise state under local data storage.",
                "Return source refs with title, record type, path, and citation when available.",
                "Name a focused test for source fidelity, grading, routing, or persistence.",
            ],
            [
                "Keep corpus reads separate from learner writes.",
                "The test should catch a regression, not just import the module.",
            ],
            "Award partial credit for read/write boundaries, state persistence, source ref shape, and a meaningful test.",
            [],
            [],
        )
    if exercise_type == "short_answer":
        return (
            f"In 4-6 sentences, explain how {skill} supports a source-grounded GenAI learning tutor. Include one risk and one review checkpoint.",
            [
                f"Correctly define {skill}.",
                "Connect the concept to the tutor workflow.",
                "Name a source-grounding or uncertainty risk.",
                "Describe an evaluation or review checkpoint.",
            ],
            ["Tie the answer back to course material.", "Mention how the learner would see evidence."],
            "Award partial credit for definition, application, risk, and evaluation.",
            [],
            [],
        )
    if skill == "RAG":
        return (
            "Design a RAG flow for a GenAI learning tutor that must answer only from a local course corpus. Include retrieval, grounding, uncertainty handling, and evaluation.",
            [
                "Retrieve relevant corpus records with embeddings or search before answering.",
                "Ground the response in source snippets and citations.",
                "Preserve uncertainty when fields or evidence are missing.",
                "Evaluate both retrieval quality and answer faithfulness.",
            ],
            [
                "Name the retrieval step before generation.",
                "Mention how source references appear to the learner.",
            ],
            "Award partial credit for retrieval, grounding/citations, uncertainty handling, and evaluation.",
            [],
            [],
        )
    if skill == "AI agents":
        return (
            "Sketch an agent workflow for an adaptive tutor. Include the router intent, at least two tools, state that persists, and when the graph should pause for a human.",
            [
                "Classify learner intent before choosing a specialist action.",
                "Use tools for search, assessment, exercises, grading, progress, and recommendations.",
                "Persist learner progress and active exercise state.",
                "Pause for clarification on vague goals, ambiguous answers, or destructive actions.",
            ],
            [
                "Think in graph nodes: route, guard, act.",
                "State is part of the product, not just the chat transcript.",
            ],
            "Award partial credit for routing, tools, persistence, and interrupt behavior.",
            [],
            [],
        )
    if skill == "MCP":
        return (
            "Define three MCP tools for this tutor and explain why they should be intent-oriented rather than raw CRUD endpoints.",
            [
                "Expose tutor_search_course_material, tutor_view_progress, and a practice or grading tool.",
                "Accept human references such as topic names instead of database IDs only.",
                "Return formatted summaries with source references.",
                "Use the same learner state as the local app.",
            ],
            [
                "MCP is the assistant-facing intent layer.",
                "Do not mirror every REST endpoint one-for-one.",
            ],
            "Award partial credit for intent tool design, formatting, citations, and shared state.",
            [],
            [],
        )
    return (
        f"Explain how {skill} supports a source-grounded GenAI learning tutor. Include one risk and one practical evaluation method.",
        [
            f"Correctly define {skill}.",
            "Connect the concept to the tutor workflow.",
            "Name a source-grounding or uncertainty risk.",
            "Describe an evaluation or review checkpoint.",
        ],
        ["Tie the answer back to course material.", "Mention how the learner would see evidence."],
        "Award partial credit for definition, application, risk, and evaluation.",
        [],
        [],
    )


def _default_exercise_type(skill: str) -> EXERCISE_TYPES:
    if skill in {"RAG", "AI agents", "MCP"}:
        return "architecture_scenario"
    return "short_answer"


@traceable(run_type="tool", name="tutor_get_next_exercise")
def tutor_get_next_exercise_impl(
    learner_id: str,
    skill: str | None = None,
    goal: str | None = None,
    exercise_type: EXERCISE_TYPES | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Generate a source-backed exercise at the learner's current level."""
    profile = learner_store.get(learner_id, tenant_id=tenant_id)
    if skill is None:
        path = skill_path_for_goal(goal or "AI agents")
        candidates = [item for item in path if item in profile.progress]
        skill = min(candidates, key=lambda item: profile.progress[item].proficiency) if candidates else "RAG"
        if goal and "AI agents" in skill_path_for_goal(goal):
            skill = "RAG"
    skill_matches = resolve_skills(skill)
    skill = skill_matches[0] if skill_matches else skill
    hits = _learning_search(f"{skill} course topic exercise source", k=4)
    refs = _source_refs(hits)
    progress = profile.progress.get(skill)
    difficulty = progress.status if progress else "developing"
    if difficulty == "exposure":
        difficulty = "developing"
    selected_type = exercise_type or _default_exercise_type(skill)
    if selected_type not in EXERCISE_TYPE_SEQUENCE:
        selected_type = _default_exercise_type(skill)
    prompt, expected_points, hints, rubric, choices, answer_key = _exercise_blueprint(skill, selected_type)
    exercise = Exercise(
        id=exercise_store.create_id(),
        learner_id=learner_id,
        tenant_id=profile.tenant_id,
        skill=skill,
        difficulty=difficulty,  # type: ignore[arg-type]
        exercise_type=selected_type,
        prompt=prompt,
        choices=choices,
        answer_key=answer_key,
        expected_points=expected_points,
        hints=hints,
        rubric=rubric,
        source_refs=refs,
    )
    exercise_store.save(exercise)
    profile.active_exercise_id = exercise.id
    learner_store.save(profile, tenant_id=tenant_id)
    learner_store.append_history(
        learner_id,
        {"type": "exercise_created", "exercise_id": exercise.id, "skill": skill},
        tenant_id=tenant_id,
    )
    payload = {
        "learner_id": learner_id,
        "exercise": exercise.model_dump(),
        "source_refs": _format_sources(refs),
    }
    write_audit_event(
        "exercise_created",
        learner_id=learner_id,
        tenant_id=tenant_id,
        metadata={"exercise_id": exercise.id, "skill": skill, "exercise_type": selected_type},
    )
    return payload


POINT_KEYWORDS = {
    "Retrieve relevant corpus records with embeddings or search before answering.": [
        "retrieve",
        "retrieval",
        "search",
        "embedding",
        "vector",
        "index",
    ],
    "Ground the response in source snippets and citations.": [
        "ground",
        "source",
        "citation",
        "cite",
        "snippet",
        "evidence",
        "context",
    ],
    "Preserve uncertainty when fields or evidence are missing.": [
        "uncertain",
        "unknown",
        "missing",
        "null",
        "unsupported",
        "not invent",
        "hallucination",
    ],
    "Evaluate both retrieval quality and answer faithfulness.": [
        "evaluate",
        "eval",
        "faithful",
        "faithfulness",
        "quality",
        "metric",
        "test",
    ],
}


def answer_needs_clarification(answer: str, exercise_type: str | None = None) -> bool:
    normalized = answer.strip().lower()
    if not normalized:
        return True
    if exercise_type == "multiple_choice" and re.match(r"^[a-d](?:[).:\s]|$)", normalized):
        return False
    vague_markers = {"maybe", "not sure", "idk", "i don't know", "something", "stuff"}
    word_count = len(re.findall(r"[a-z0-9]+", normalized))
    return word_count < 6 or normalized in vague_markers


def _point_is_covered(point: str, answer: str) -> bool:
    normalized = answer.lower()
    keywords = POINT_KEYWORDS.get(point)
    if keywords is None:
        tokens = [token for token in re.findall(r"[a-z0-9]+", point.lower()) if len(token) > 4]
        return len([token for token in tokens if token in normalized]) >= max(1, min(2, len(tokens)))
    return any(keyword in normalized for keyword in keywords)


def _grade_multiple_choice(exercise: Exercise, answer: str) -> tuple[list[str], list[str], float]:
    normalized = answer.strip().lower()
    correct = any(
        normalized == key.lower()
        or normalized.startswith(f"{key.lower()}.")
        or normalized.startswith(f"{key.lower()})")
        or f"option {key.lower()}" in normalized
        for key in exercise.answer_key
    )
    rationale_terms = ["retrieve", "source", "citation", "unknown", "local", "corpus", "evidence"]
    has_rationale = any(term in normalized for term in rationale_terms)
    covered: list[str] = []
    if correct and exercise.expected_points:
        covered.append(exercise.expected_points[0])
    if correct and has_rationale and len(exercise.expected_points) > 1:
        covered.append(exercise.expected_points[1])
    missed = [point for point in exercise.expected_points if point not in covered]
    score = len(covered) / max(1, len(exercise.expected_points))
    return covered, missed, score


@traceable(run_type="tool", name="tutor_submit_answer")
def tutor_submit_answer_impl(
    learner_id: str,
    answer: str,
    exercise_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Grade an answer, explain the result, and persist progress."""
    profile = learner_store.get(learner_id, tenant_id=tenant_id)
    exercise_id = exercise_id or profile.active_exercise_id
    if not exercise_id:
        write_audit_event(
            "answer_submitted",
            learner_id=learner_id,
            tenant_id=tenant_id,
            outcome="needs_clarification",
            metadata={"reason": "no_active_exercise", "answer_length": len(answer)},
        )
        return {
            "learner_id": learner_id,
            "needs_clarification": True,
            "message": "No active exercise found. Ask for a new exercise first.",
            "source_refs": [],
        }
    exercise = exercise_store.get(exercise_id, tenant_id=tenant_id)
    if exercise is None:
        write_audit_event(
            "answer_submitted",
            learner_id=learner_id,
            tenant_id=tenant_id,
            outcome="needs_clarification",
            metadata={"reason": "exercise_not_found", "exercise_id": exercise_id, "answer_length": len(answer)},
        )
        return {
            "learner_id": learner_id,
            "needs_clarification": True,
            "message": f"Exercise {exercise_id} was not found in local state.",
            "source_refs": [],
        }
    if answer_needs_clarification(answer, exercise.exercise_type):
        write_audit_event(
            "answer_submitted",
            learner_id=learner_id,
            tenant_id=tenant_id,
            outcome="needs_clarification",
            metadata={"reason": "ambiguous_answer", "exercise_id": exercise_id, "answer_length": len(answer)},
        )
        return {
            "learner_id": learner_id,
            "exercise_id": exercise_id,
            "needs_clarification": True,
            "message": "The answer is too ambiguous to grade. Add the main design choices you would make.",
            "source_refs": _format_sources(exercise.source_refs),
        }
    before_progress = profile.progress.get(exercise.skill)
    if exercise.exercise_type == "multiple_choice":
        covered, missed, score = _grade_multiple_choice(exercise, answer)
    else:
        covered = [point for point in exercise.expected_points if _point_is_covered(point, answer)]
        missed = [point for point in exercise.expected_points if point not in covered]
        score = len(covered) / max(1, len(exercise.expected_points))
    if score >= 0.75:
        delta = 0.12
        verdict = "strong"
    elif score >= 0.45:
        delta = 0.05
        verdict = "partial"
    else:
        delta = -0.02
        verdict = "needs_review"
    profile = learner_store.update_skill(
        learner_id,
        exercise.skill,
        score_delta=delta,
        source_refs=exercise.source_refs,
        evidence=[
            f"Covered {len(covered)} of {len(exercise.expected_points)} rubric points.",
            *(f"Covered: {point}" for point in covered[:3]),
            *(f"Missed: {point}" for point in missed[:2]),
        ],
        attempted=True,
        correct=score >= 0.75,
        tenant_id=tenant_id,
    )
    learner_store.append_history(
        learner_id,
        {
            "type": "answer_graded",
            "exercise_id": exercise_id,
            "skill": exercise.skill,
            "score": round(score, 2),
        },
        tenant_id=tenant_id,
    )
    record_answer(
        tenant_id=exercise.tenant_id,
        learner_id=learner_id,
        exercise_id=exercise_id,
        answer=answer,
        score=round(score, 4),
        verdict=verdict,
        covered_points=covered,
        missed_points=missed,
    )
    progress = profile.progress[exercise.skill]
    mastery_update = {
        "previous_status": before_progress.status if before_progress else "exposure",
        "new_status": progress.status,
        "proficiency_before": round(before_progress.proficiency, 2) if before_progress else 0.0,
        "proficiency_after": round(progress.proficiency, 2),
        "proficiency_delta": progress.last_change.get("proficiency_delta") if progress.last_change else None,
        "status_reason": progress.status_reason,
        "next_review": progress.next_review,
        "next_review_reason": progress.next_review_reason,
        "evidence": progress.evidence,
    }
    payload = {
        "learner_id": learner_id,
        "exercise_id": exercise_id,
        "skill": exercise.skill,
        "score": round(score, 2),
        "verdict": verdict,
        "covered_points": covered,
        "missed_points": missed,
        "explanation": "The grade is based on overlap with the source-backed rubric, not on unsupported outside claims.",
        "updated_progress": progress.model_dump(),
        "mastery_update": mastery_update,
        "source_refs": _format_sources(exercise.source_refs),
    }
    write_audit_event(
        "answer_submitted",
        learner_id=learner_id,
        tenant_id=tenant_id,
        metadata={
            "exercise_id": exercise_id,
            "skill": exercise.skill,
            "score": round(score, 2),
            "verdict": verdict,
            "answer_length": len(answer),
        },
    )
    payload.update(_maybe_coach_note(exercise.skill, verdict, covered, missed))
    return payload


def _maybe_coach_note(skill: str, verdict: str, covered: list[str], missed: list[str]) -> dict[str, Any]:
    """Optionally add a qwen3.7-plus coaching tip. Deterministic fields are never changed.

    Gated by ``TUTOR_LLM_COACHING`` + provider availability; any failure is
    swallowed so grading always succeeds offline and in tests.
    """
    from .settings import get_settings

    if not get_settings().llm_coaching_enabled:
        return {}
    from . import llm_provider

    if not llm_provider.available():
        return {}
    try:
        note = llm_provider.chat(
            [
                {
                    "role": "system",
                    "content": "You are a concise, encouraging tutor. In at most two sentences, give one specific "
                    "next step. Use only the rubric points provided; do not introduce new facts.",
                },
                {"role": "user", "content": f"Skill: {skill}. Verdict: {verdict}. Covered: {covered}. Missed: {missed}."},
            ],
            max_tokens=120,
        )
    except llm_provider.LLMUnavailable:
        return {}
    return {"coach_note": note.strip(), "coach_model": get_settings().qwen_llm_model}


@traceable(run_type="tool", name="tutor_view_progress")
def tutor_view_progress_impl(learner_id: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Return persistent learner mastery state."""
    profile = learner_store.get(learner_id, tenant_id=tenant_id)
    progress = {
        skill: entry.model_dump()
        for skill, entry in profile.progress.items()
    }
    payload = {
        "learner_id": learner_id,
        "goals": profile.goals,
        "active_exercise_id": profile.active_exercise_id,
        "progress": progress,
        "study_plan": profile.study_plan,
        "updated_at": profile.updated_at,
    }
    write_audit_event("progress_viewed", learner_id=learner_id, tenant_id=tenant_id)
    return payload


@tool
def search_course_material(query: str, k: int = 5) -> dict[str, Any]:
    """Search local genai_research course material and return concise summaries with citations."""
    return search_course_material_impl(query=query, k=k)


@tool
def tutor_assess_skills(
    learner_id: str,
    goal: str,
    answers: list[str] | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Run a source-backed diagnostic assessment for a learner goal."""
    return tutor_assess_skills_impl(learner_id=learner_id, goal=goal, answers=answers, tenant_id=tenant_id)


@tool
def tutor_get_next_exercise(
    learner_id: str,
    skill: str | None = None,
    goal: str | None = None,
    exercise_type: EXERCISE_TYPES | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Create the next source-backed exercise for a learner."""
    return tutor_get_next_exercise_impl(
        learner_id=learner_id,
        skill=skill,
        goal=goal,
        exercise_type=exercise_type,
        tenant_id=tenant_id,
    )


@tool
def tutor_submit_answer(
    learner_id: str,
    answer: str,
    exercise_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Grade a learner answer against a local source-backed exercise rubric."""
    return tutor_submit_answer_impl(
        learner_id=learner_id,
        answer=answer,
        exercise_id=exercise_id,
        tenant_id=tenant_id,
    )


@tool
def tutor_view_progress(learner_id: str, tenant_id: str | None = None) -> dict[str, Any]:
    """View persistent learner progress and current mastery states."""
    return tutor_view_progress_impl(learner_id=learner_id, tenant_id=tenant_id)


@tool
def tutor_recommend_path(learner_id: str, goal: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Recommend a source-backed study path for a learner goal."""
    return tutor_recommend_path_impl(learner_id=learner_id, goal=goal, tenant_id=tenant_id)


TUTOR_TOOLS = [
    search_course_material,
    tutor_assess_skills,
    tutor_get_next_exercise,
    tutor_submit_answer,
    tutor_view_progress,
    tutor_recommend_path,
]
