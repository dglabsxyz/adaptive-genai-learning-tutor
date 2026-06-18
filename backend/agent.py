"""The Adaptive GenAI Learning Tutor as a Deep Agent.

This replaces the hand-built LangGraph (`backend/graph.py`) with the
`deepagents` framework taught in the course: an orchestrator that plans
(`write_todos`) and delegates (`task`) to specialist subagents, each with
isolated context, focused tools, and on-demand skills (progressive disclosure).
Shared state is the filesystem + a Store for cross-session `/memories/`; a
human-in-the-loop gate guards the consequential `commit_progress` write.

Full-replace mode: a real tool-calling model is required (Qwen via the DashScope
OpenAI-compatible endpoint). There is no deterministic fallback for orchestration.
"""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from deepagents.middleware.filesystem import FilesystemPermission
from langchain_openai import ChatOpenAI

from . import agent_tools
from .agent_tools import get_memory_namespace
from .agent_store import build_store
from .checkpoints import build_checkpointer
from .settings import get_settings

PKG_DIR = Path(__file__).resolve().parent
GROUNDING = (PKG_DIR / "grounding" / "genai_tutor.md").read_text(encoding="utf-8")
SKILLS_SOURCES = ["/skills/"]  # resolved against the FilesystemBackend root_dir


def _build_model() -> ChatOpenAI:
    settings = get_settings()
    if not settings.qwen_api_key:
        raise RuntimeError(
            "The deep-agent tutor requires QWEN_API_KEY (DashScope). "
            "Set it in .env or the deployment environment."
        )
    return ChatOpenAI(
        model=settings.qwen_llm_model,
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.qwen_timeout_seconds,
    )


def _agent_home() -> Path:
    """Runtime workspace that holds the agent's skills + scratch artifacts.

    Skills are the repo source-of-truth under ``backend/skills``; we materialize
    them into the backend root so the FilesystemBackend can serve ``/skills/``.
    """
    home = get_settings().data_dir / "agent_workspace"
    skills_dst = home / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    src = PKG_DIR / "skills"
    if src.exists():
        for skill_dir in src.iterdir():
            if skill_dir.is_dir():
                shutil.copytree(skill_dir, skills_dst / skill_dir.name, dirs_exist_ok=True)
    return home


def _backend() -> CompositeBackend:
    # AGT-020, AGT-021: Memory namespace must be isolated per tenant+learner.
    # The namespace callback is invoked during each request with context set by
    # set_agent_context() before the agent runs. This prevents cross-session
    # memory poisoning and cross-tenant data leakage.
    return CompositeBackend(
        default=FilesystemBackend(root_dir=str(_agent_home()), virtual_mode=True),
        routes={"/memories/": StoreBackend(namespace=get_memory_namespace)},
    )


# Corpus lockdown — deepagents filesystem permission rules (a tool-level security
# guarantee, inherited by every subagent). The orchestrator and its specialists may
# READ only their skills, shared memories, and offloaded tool results; every other
# read (ls / glob / grep / read_file) is denied. The course corpus therefore cannot be
# reached through the filesystem at all — the ONLY way to get course content is the
# `search_course_material` tool. This structurally eliminates the intermittent
# "couldn't locate the genai_research corpus" dead-end: there are no corpus paths to
# spelunk, so the model (and subagents) must use the retrieval tool. Writes stay open —
# memories and large-result offload depend on them, and writes never caused the dead-end.
_FS_READABLE = [
    "/skills/**", "/skills",
    "/memories/**", "/memories",
    "/large_tool_results/**", "/large_tool_results",
]
FS_PERMISSIONS = [
    FilesystemPermission(operations=["read", "write"], paths=_FS_READABLE, mode="allow"),
    FilesystemPermission(operations=["read"], paths=["/**", "/*", "/"], mode="deny"),
]


# --- Subagents (each stateless; instructions must be complete) --------------
# Appended to every subagent prompt: the corpus is reached via search_course_material,
# NOT the filesystem. Without this, the model spends its step budget exploring the
# virtual filesystem (ls/glob/grep/read_file) for corpus paths that don't exist and
# loops to the recursion limit. The file tools are only for skills + shared memories.
SUBAGENT_FS_GUARDRAIL = (
    " IMPORTANT: course material is available ONLY by calling the `search_course_material` tool — call "
    "it directly; the corpus is NOT on the filesystem. Never use `ls`, `glob`, `grep`, or `read_file` to "
    "look for topics, courses, instructors, or corpus files (those paths do not exist and will error). "
    "The filesystem holds only your skills under `/skills/` and shared notes under `/memories/`. Do your "
    "job by calling your tools, then return your result — do not explore the filesystem."
)

DIAGNOSTIC = {
    "name": "diagnostic",
    "description": "Assesses the learner's current mastery for a goal. Use first for a new goal.",
    "system_prompt": (
        "Load the 'socratic-tutoring' skill. Call view_progress to see current mastery, then "
        "assess_skills(goal) using source-backed probes (search_course_material as needed). "
        "Return a short diagnosis: per-skill status for the goal and the 1-2 weakest prerequisites."
        + SUBAGENT_FS_GUARDRAIL
    ),
    "tools": agent_tools.SUBAGENT_TOOLSETS["diagnostic"],
    "skills": SKILLS_SOURCES,
}

PATH_PLANNER = {
    "name": "path-planner",
    "description": "Builds an ordered, prerequisite-aware study path for a goal. Use after diagnosis.",
    "system_prompt": (
        "Load the 'socratic-tutoring' skill. Call recommend_path(goal) and ground each module with "
        "search_course_material. Return the ordered path with one-line rationale per module and citations."
        + SUBAGENT_FS_GUARDRAIL
    ),
    "tools": agent_tools.SUBAGENT_TOOLSETS["path_planner"],
    "skills": SKILLS_SOURCES,
}

EXERCISE_AUTHOR = {
    "name": "exercise-author",
    "description": "Authors ONE source-backed exercise for a skill, calibrated to mastery.",
    "system_prompt": (
        "Load the 'exercise-design' skill and follow it strictly. Use search_course_material to ground "
        "the exercise, then call next_exercise(skill=...). Return the exercise prompt, its expected points, "
        "and the source references. Do not reveal the answer key."
        + SUBAGENT_FS_GUARDRAIL
    ),
    "tools": agent_tools.SUBAGENT_TOOLSETS["exercise_author"],
    "skills": SKILLS_SOURCES,
}

GRADER_CRITIC = {
    "name": "grader-critic",
    "description": "Grades a submitted answer deterministically and explains the result. Use when the learner answers.",
    "system_prompt": (
        "Load the 'feedback-style' skill. Call grade_answer(answer, exercise_id) — the score and verdict "
        "are computed by code; never overrule them. Then explain covered vs missed rubric points, cite a "
        "source to close any gap, and name exactly one next step. CRITICAL: NEVER state mastery percentages, "
        "proficiency numbers, or skill levels that are not returned verbatim from the grade_answer tool. "
        "The UI renders the tool's mastery_update field; any percentages you invent will contradict it. If "
        "mastery_update is missing or you are unsure of the number, say 'see your progress dashboard' instead "
        "of guessing a percentage."
        + SUBAGENT_FS_GUARDRAIL
    ),
    "tools": agent_tools.SUBAGENT_TOOLSETS["grader_critic"],
    "skills": SKILLS_SOURCES,
}

ORCHESTRATOR_PROMPT = f"""You are the Adaptive GenAI Learning Tutor: an orchestrator that helps a learner
go from where they are to production-ready on generative-AI engineering.

You are grounded in the course corpus below. Honor it; never invent courses, instructors,
statistics, or citations beyond it or what a tool returns.

{GROUNDING}

How you work each turn — first call write_todos to plan, then COMPLETE the task by calling your tools.
You hold the tutor tools directly (search_course_material, assess_skills, recommend_path, next_exercise,
grade_answer) — use them to act. You MAY also delegate a richer, isolated treatment to a specialist
subagent with `task`, but calling the tools yourself is the reliable path; prefer it. Never begin a turn
by exploring the filesystem.
- New or restated goal → call assess_skills(goal), then recommend_path(goal), grounding with
  search_course_material. (You may instead delegate to 'diagnostic' then 'path-planner'.)
- Learner is ready to practice (or asks for an exercise) → call next_exercise(skill=...) for ONE
  exercise, using search_course_material first to ground it. (Or delegate to 'exercise-author'.)
- Learner submits an answer → call grade_answer(answer, exercise_id) and explain the result. (Or
  delegate to 'grader-critic'.)
- At a natural stopping point, or when the learner asks to save/finish → call commit_progress with a
  one-line summary. This is gated by human approval; wait for it.
- Missing or too-vague request (no clear goal or skill to act on — e.g. "help me get better", "I want to
  improve") → you MUST call the `request_clarification` tool with ONE specific question and then stop. Do
  NOT ask the clarifying question in plain prose — always use the `request_clarification` tool so the turn
  pauses for the learner's answer. Never guess missing details.
- Off-topic request (anything not about learning generative-AI engineering) → politely decline in one
  sentence, say what you CAN help with (diagnose level, plan a path, practice, track progress), and do
  not delegate or call other tools.

Tools and filesystem — read carefully:
- Course content is reached ONLY through the `search_course_material` tool (which you and your subagents
  hold) — it is NOT on your working filesystem. NEVER use `ls`, `glob`, `grep`, `read_file`, or
  `write_file` to look for topics, courses, or instructors — those corpus paths do not exist and the
  calls will error. When you need course material, call `search_course_material`.
- ACTUALLY CALL your tools. Never end a turn by only describing what you are about to do (e.g. "let me
  use the task tool to search…" or "I'll author an exercise…") — emit the tool call instead. A reply
  that narrates a plan without calling the tool is a failed turn.
- Your working filesystem holds only `/skills/` (skills you may load) and `/memories/` (durable
  learner notes for future sessions). That is the only thing the file tools are for.
- One step per turn: once you have the result (from a tool call or a delegation), STOP and write your
  reply. Do not repeat the same call or loop — at most one diagnosis, one path, one exercise, or one
  grade per turn.

Subagents share the filesystem and todos but not message history, so give each complete instructions.
You may save a durable learner note to /memories/ (e.g. preferred pace, recurring gaps) for future sessions.
Keep your own replies concise, specific, and encouraging; always end with the single best next step.

CRITICAL — Mastery numbers: NEVER state percentages, proficiency scores, or mastery levels unless they come
verbatim from a tool response (view_progress, grade_answer). The UI renders mastery from those tool outputs;
any percentages you invent will contradict the UI and confuse the learner. If unsure or the tool didn't return
a number, say 'see your progress dashboard' instead of guessing."""


@lru_cache(maxsize=1)
def build_tutor_agent():
    """Build (once) and return the compiled deep-agent tutor."""
    return create_deep_agent(
        model=_build_model(),
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            # The orchestrator holds the tutor tools directly so it can complete a turn
            # even when it doesn't emit a `task` delegation (Qwen does so only
            # probabilistically). Subagents remain available via `task` for richer flows.
            agent_tools.search_course_material,
            agent_tools.assess_skills,
            agent_tools.recommend_path,
            agent_tools.next_exercise,
            agent_tools.grade_answer,
            agent_tools.view_progress,
            agent_tools.commit_progress,
            agent_tools.request_clarification,
        ],
        subagents=[DIAGNOSTIC, PATH_PLANNER, EXERCISE_AUTHOR, GRADER_CRITIC],
        backend=_backend(),
        store=build_store(),
        skills=SKILLS_SOURCES,
        permissions=FS_PERMISSIONS,
        interrupt_on={"commit_progress": True},
        checkpointer=build_checkpointer(),
    )
