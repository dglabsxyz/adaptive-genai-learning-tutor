"""DEPRECATED — superseded by the deep-agent tutor.

The hand-built LangGraph that used to live here (route -> interrupt_guard ->
dispatch, with intent classification and the reset/vague-goal interrupts) has
been fully replaced by the `deepagents` orchestrator in `backend/agent.py`,
driven through `backend/agent_runtime.py`.

This module remains only as a thin compatibility shim re-exporting the request
entry points so older scripts keep importing successfully. New code should import
from `backend.agent_runtime`.

Safe to delete on a machine with filesystem write access:
    git rm backend/graph.py
"""

from __future__ import annotations

from .agent_runtime import resume_tutor_turn, run_tutor_turn

__all__ = ["run_tutor_turn", "resume_tutor_turn"]
