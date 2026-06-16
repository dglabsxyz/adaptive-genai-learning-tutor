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
from langchain_openai import ChatOpenAI

from . import agent_tools
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
    return CompositeBackend(
        default=FilesystemBackend(root_dir=str(_agent_home()), virtual_mode=True),
        routes={"/memories/": StoreBackend(namespace=lambda ctx: ("tutor",))},
    )


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
        "source to close any gap, and name exactly one next step."
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

How you work each turn — begin by calling write_todos to plan, then delegate to specialists with
`task` based on the conversation state. Never begin a turn by exploring the filesystem.
- New or restated goal → delegate to 'diagnostic', then 'path-planner'.
- Learner is ready to practice (or asks for an exercise) → delegate to 'exercise-author' for ONE exercise.
- Learner submits an answer → delegate to 'grader-critic' to grade and give feedback.
- At a natural stopping point, or when the learner asks to save/finish → call commit_progress with a
  one-line summary. This is gated by human approval; wait for it.

Tools and filesystem — read carefully:
- Course content lives behind the `search_course_material` tool, which your SUBAGENTS hold — it is NOT
  on your working filesystem, and you do not retrieve or cite it yourself. To use any topic, course, or
  instructor, DELEGATE to a specialist (it will search and cite). NEVER use `ls`, `glob`, `grep`,
  `read_file`, or `write_file` to look for course material — those corpus paths do not exist on your
  filesystem and the calls will error; an empty or "path_not_found" result means "delegate", not "try
  another path".
- Your working filesystem holds only `/skills/` (skills you may load) and `/memories/` (durable
  learner notes for future sessions). That is the only thing the file tools are for.
- One step per turn: after you have delegated and received the specialist's result (or directly
  answered a simple question), STOP and write your reply. Do not re-run the same delegation or keep
  calling tools in a loop — at most one diagnosis, one path, one exercise, or one grade per turn.

Subagents share the filesystem and todos but not message history, so give each complete instructions.
You may save a durable learner note to /memories/ (e.g. preferred pace, recurring gaps) for future sessions.
Keep your own replies concise, specific, and encouraging; always end with the single best next step."""


@lru_cache(maxsize=1)
def build_tutor_agent():
    """Build (once) and return the compiled deep-agent tutor."""
    return create_deep_agent(
        model=_build_model(),
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[agent_tools.view_progress, agent_tools.commit_progress],
        subagents=[DIAGNOSTIC, PATH_PLANNER, EXERCISE_AUTHOR, GRADER_CRITIC],
        backend=_backend(),
        store=build_store(),
        skills=SKILLS_SOURCES,
        interrupt_on={"commit_progress": True},
        checkpointer=build_checkpointer(),
    )
