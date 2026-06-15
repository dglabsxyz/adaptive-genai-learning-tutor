"""Topic resolution helpers for learner intents."""

from __future__ import annotations

import re

from .models import SKILL_TOPICS

ALIASES = {
    "llm": "LLMs",
    "llms": "LLMs",
    "large language model": "LLMs",
    "large language models": "LLMs",
    "prompt": "prompt engineering",
    "prompting": "prompt engineering",
    "context": "context engineering",
    "retrieval": "RAG",
    "retrieval augmented generation": "RAG",
    "vector database": "RAG",
    "vector search": "RAG",
    "agent": "AI agents",
    "agents": "AI agents",
    "agentic": "AI agents",
    "tool use": "AI agents",
    "model context protocol": "MCP",
    "mcp": "MCP",
    "coding": "AI coding",
    "code": "AI coding",
    "vibe coding": "AI coding",
    "safety": "AI safety and evaluation",
    "eval": "AI safety and evaluation",
    "evals": "AI safety and evaluation",
    "evaluation": "AI safety and evaluation",
    "fine tuning": "fine-tuning",
    "finetuning": "fine-tuning",
    "multimodal": "multimodal AI",
}

AGENT_PATH = [
    "LLMs",
    "prompt engineering",
    "context engineering",
    "RAG",
    "AI agents",
    "MCP",
    "AI safety and evaluation",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("-", " ")).strip()


def resolve_skills(text: str) -> list[str]:
    normalized = normalize_text(text)
    matches: list[str] = []
    for skill in SKILL_TOPICS:
        if normalize_text(skill) in normalized:
            matches.append(skill)
    for alias, skill in ALIASES.items():
        if alias in normalized and skill not in matches:
            matches.append(skill)
    if "AI agents" in matches:
        for skill in ["RAG", "MCP"]:
            if skill not in matches:
                matches.append(skill)
    return matches


def skill_path_for_goal(goal: str) -> list[str]:
    matches = resolve_skills(goal)
    if "AI agents" in matches:
        return AGENT_PATH
    if "RAG" in matches:
        return ["LLMs", "prompt engineering", "context engineering", "RAG", "AI safety and evaluation"]
    if "MCP" in matches:
        return ["LLMs", "AI agents", "MCP", "AI safety and evaluation"]
    if matches:
        return matches
    return ["LLMs", "prompt engineering", "RAG"]


def is_vague_goal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(phrase in normalized for phrase in ["learn ai", "study genai", "help me learn"]) and not resolve_skills(text)

