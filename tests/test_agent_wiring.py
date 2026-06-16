"""Offline wiring tests for the deep-agent tutor.

Replaces the old hand-built-graph routing tests. These run without an LLM: they
check the orchestrator/subagent wiring, that the context-bound tools refuse to
act without a learner context (and resolve correctly with one), that the model
factory requires a Qwen key, and that the grounding + skills assets exist.

Rename suggestion on your machine: `git mv tests/test_graph_routing.py tests/test_agent_wiring.py`.
"""

from uuid import uuid4

import pytest
from langgraph.errors import GraphRecursionError

from backend import agent, agent_runtime, agent_tools
from backend.settings import get_settings


def test_orchestrator_grounded_and_subagents_defined():
    specs = [agent.DIAGNOSTIC, agent.PATH_PLANNER, agent.EXERCISE_AUTHOR, agent.GRADER_CRITIC]
    assert {s["name"] for s in specs} == {"diagnostic", "path-planner", "exercise-author", "grader-critic"}
    # grounding is injected into the orchestrator prompt
    assert "corpus" in agent.ORCHESTRATOR_PROMPT.lower()
    # each subagent has focused tools and the skills source
    for spec in specs:
        assert spec["tools"], f"{spec['name']} has no tools"
        assert spec["skills"] == ["/skills/"]


def test_orchestrator_prompt_guards_against_filesystem_corpus_spelunking():
    # Regression guard for the loop fix: the orchestrator must be told the corpus is
    # reached only via search_course_material/subagents, never via filesystem tools.
    prompt = agent.ORCHESTRATOR_PROMPT
    assert "search_course_material" in prompt
    assert "read_file" in prompt and "glob" in prompt and "grep" in prompt
    # and the same guardrail is reinforced in the grounding asset
    grounding = (agent.PKG_DIR / "grounding" / "genai_tutor.md").read_text(encoding="utf-8")
    assert "not files" in grounding.lower() or "not be on" in grounding.lower() or "do not exist" in grounding.lower()


def test_recursion_limit_degrades_gracefully(monkeypatch):
    # When the agent exhausts its step budget, run_tutor_turn returns a clean,
    # contract-shaped reply (not a raised GraphRecursionError / 500) and restores context.
    class _Looping:
        def invoke(self, *args, **kwargs):
            raise GraphRecursionError("Recursion limit of 80 reached without hitting a stop condition.")

    monkeypatch.setattr(agent_runtime, "build_tutor_agent", lambda: _Looping())

    result = agent_runtime.run_tutor_turn("loop-learner", "do something huge", tenant_id="local")

    assert result["message"] == agent_runtime.RECURSION_FALLBACK_MESSAGE
    assert result["learner_id"] == "loop-learner"
    assert result["source_refs"] == []
    # per-request context was reset even though the turn errored internally
    assert agent_tools._agent_ctx.get().get("learner_id") is None


def test_context_bound_tools_require_and_use_context():
    # No context -> refuse rather than guess a learner/tenant.
    agent_tools._agent_ctx.set({"learner_id": None, "tenant_id": None})
    with pytest.raises(RuntimeError):
        agent_tools.view_progress.invoke({})

    # With context -> resolves to that learner (json backend, offline).
    learner_id = f"wire-{uuid4()}"
    token = agent_tools.set_agent_context(learner_id, "tenant-wire")
    try:
        out = agent_tools.view_progress.invoke({})
        assert out["learner_id"] == learner_id
    finally:
        agent_tools.reset_agent_context(token)


def test_model_factory_requires_qwen_key(monkeypatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            agent._build_model()
    finally:
        get_settings.cache_clear()


def test_grounding_and_skills_assets_present():
    assert (agent.PKG_DIR / "grounding" / "genai_tutor.md").exists()
    for name in ("socratic-tutoring", "exercise-design", "feedback-style"):
        assert (agent.PKG_DIR / "skills" / name / "SKILL.md").exists()
