"""Input sanitization and prompt injection detection.

Centralizes all input validation for user messages before they reach the LLM.
Addresses: LLM-001, LLM-002, LLM-003, LLM-004, AGT-001, AGT-002, AGT-009
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("backend.input_filter")

# Maximum allowed message length (characters)
MAX_MESSAGE_LENGTH = 10_000

# Patterns that indicate prompt injection attempts
# These are case-insensitive regex patterns
INJECTION_PATTERNS = [
    # Direct instruction override attempts
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"ignore\s+(all\s+)?above\s+instructions?",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?(your\s+)?instructions?",
    r"forget\s+everything",
    r"override\s+(your\s+)?(system\s+)?prompt",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*you\s+are\s+now",
    # Role manipulation
    r"you\s+are\s+now\s+(a\s+)?dan",
    r"you\s+are\s+now\s+(a\s+)?different",
    r"pretend\s+(to\s+be|you\s+are)\s+(a\s+)?",
    r"act\s+as\s+(if\s+you\s+are|a)",
    r"roleplay\s+as",
    r"simulate\s+(being|a)",
    # System prompt extraction
    r"(show|reveal|display|print|output|repeat)\s+(me\s+)?(your|the)\s+(system\s+)?prompt",
    r"(show|reveal|display|print|output|repeat)\s+(me\s+)?(your|the)\s+instructions?",
    r"what\s+(are|is)\s+your\s+(system\s+)?prompt",
    r"what\s+(are|is)\s+your\s+instructions?",
    r"(tell|give)\s+me\s+your\s+(system\s+)?prompt",
    r"repeat\s+(everything|all)\s+(you\s+were\s+told|above)",
    # Grounding bypass
    r"(don'?t|do\s+not)\s+(need\s+to\s+)?cite",
    r"(don'?t|do\s+not)\s+(need\s+to\s+)?ground",
    r"skip\s+(the\s+)?grounding",
    r"ignore\s+(the\s+)?grounding",
    r"without\s+(any\s+)?citations?",
    r"no\s+need\s+(for|to)\s+sources?",
    # Tool manipulation
    r"call\s+commit_progress\s+(immediately|now|right\s+away)",
    r"execute\s+tool\s+",
    r"run\s+function\s+",
    r"invoke\s+\w+\s*\(",
    # Filesystem access attempts (for corpus guardrail bypass)
    r"(read|access|open|cat|grep)\s+(the\s+)?/",
    r"(read|access|open)\s+file\s+",
    r"filesystem\s+access",
    r"you\s+can\s+access\s+(the\s+)?filesystem",
    # Jailbreak patterns
    r"jailbreak",
    r"bypass\s+(your\s+)?(safety|security|restrictions?)",
    r"(disable|turn\s+off)\s+(your\s+)?(safety|security|filters?)",
    r"do\s+anything\s+now",
    r"maximum\s+freedom\s+mode",
]

# Compiled patterns for efficiency
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# Patterns for sensitive data requests (phishing via clarification)
SENSITIVE_DATA_PATTERNS = [
    r"(what\s+is|tell\s+me|give\s+me)\s+your\s+(api\s+)?key",
    r"(what\s+is|tell\s+me|give\s+me)\s+your\s+password",
    r"(what\s+is|tell\s+me|give\s+me)\s+your\s+secret",
    r"(what\s+is|tell\s+me|give\s+me)\s+your\s+token",
    r"(what\s+is|tell\s+me|give\s+me)\s+your\s+credentials?",
]

_COMPILED_SENSITIVE = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_DATA_PATTERNS]


@dataclass
class FilterResult:
    """Result of input filtering."""

    allowed: bool
    message: str  # Original or sanitized message
    violations: list[str]  # List of detected violations
    truncated: bool = False


def detect_injection(text: str) -> list[str]:
    """Detect prompt injection patterns in text.

    Returns list of matched pattern descriptions.
    """
    violations = []
    for i, pattern in enumerate(_COMPILED_PATTERNS):
        if pattern.search(text):
            # Return a generic description, not the exact pattern (for security)
            violations.append(f"injection_pattern_{i + 1}")
    return violations


def detect_sensitive_request(text: str) -> list[str]:
    """Detect requests for sensitive information."""
    violations = []
    for i, pattern in enumerate(_COMPILED_SENSITIVE):
        if pattern.search(text):
            violations.append(f"sensitive_request_{i + 1}")
    return violations


def sanitize_message(message: str) -> FilterResult:
    """Sanitize user message before passing to LLM.

    This is the main entry point for input filtering.

    Returns:
        FilterResult with:
        - allowed: True if message passes all checks
        - message: The (possibly truncated) message
        - violations: List of detected issues
        - truncated: True if message was truncated
    """
    if not message or not isinstance(message, str):
        return FilterResult(allowed=True, message="", violations=[])

    violations = []
    truncated = False

    # Check length
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH]
        truncated = True
        violations.append("message_truncated")
        logger.warning("Message truncated from %d to %d characters", len(message), MAX_MESSAGE_LENGTH)

    # Detect injection attempts
    injection_violations = detect_injection(message)
    violations.extend(injection_violations)

    # Detect sensitive data requests
    sensitive_violations = detect_sensitive_request(message)
    violations.extend(sensitive_violations)

    # Log violations for security monitoring
    if violations:
        logger.warning(
            "Input filter detected violations: %s (message_preview=%s)",
            violations,
            message[:100] + "..." if len(message) > 100 else message,
        )

    # Block message if injection detected
    if injection_violations:
        return FilterResult(
            allowed=False,
            message=message,
            violations=violations,
            truncated=truncated,
        )

    return FilterResult(
        allowed=True,
        message=message,
        violations=violations,
        truncated=truncated,
    )


def filter_tool_parameter(param_name: str, value: Any) -> tuple[bool, Any]:
    """Filter a tool parameter value.

    Used to validate parameters before subagent delegation.

    Returns:
        (is_valid, sanitized_value)
    """
    if value is None:
        return True, value

    if isinstance(value, str):
        # Check for injection in string parameters
        result = sanitize_message(value)
        if not result.allowed:
            logger.warning("Tool parameter %s rejected: %s", param_name, result.violations)
            return False, None
        return True, result.message

    # For other types, pass through (could add more validation)
    return True, value


def filter_clarification_question(question: str) -> FilterResult:
    """Filter clarification questions to prevent phishing.

    Addresses AGT-031: Request clarification weaponization.
    """
    if not question or not isinstance(question, str):
        return FilterResult(allowed=False, message="", violations=["empty_question"])

    violations = []

    # Check for sensitive data requests
    sensitive = detect_sensitive_request(question)
    if sensitive:
        violations.extend(sensitive)
        return FilterResult(
            allowed=False,
            message=question,
            violations=violations,
        )

    # Check length
    if len(question) > 500:
        question = question[:500]
        violations.append("question_truncated")

    return FilterResult(
        allowed=True,
        message=question,
        violations=violations,
    )


# Allowlist of valid goal/skill topics (for parameter validation)
VALID_SKILL_TOPICS = {
    "llm",
    "llms",
    "large language model",
    "large language models",
    "prompt engineering",
    "prompting",
    "rag",
    "retrieval augmented generation",
    "retrieval-augmented generation",
    "agents",
    "agent",
    "agentic",
    "mcp",
    "model context protocol",
    "evals",
    "evaluation",
    "evaluations",
    "safety",
    "ai safety",
    "fine-tuning",
    "fine tuning",
    "finetuning",
    "embeddings",
    "vector",
    "vectors",
    "langchain",
    "langgraph",
    "deepagents",
    "genai",
    "generative ai",
    "generative-ai",
}


def is_valid_learning_goal(goal: str) -> bool:
    """Check if a goal appears to be about GenAI learning.

    Addresses AGT-004: Out-of-domain request handling.
    """
    if not goal:
        return False

    goal_lower = goal.lower()

    # Check for any valid topic mention
    for topic in VALID_SKILL_TOPICS:
        if topic in goal_lower:
            return True

    # Check for learning-related keywords combined with AI/ML terms
    learning_keywords = {"learn", "study", "understand", "master", "practice", "teach", "help me with"}
    ai_keywords = {"ai", "ml", "model", "neural", "deep learning", "machine learning"}

    has_learning = any(kw in goal_lower for kw in learning_keywords)
    has_ai = any(kw in goal_lower for kw in ai_keywords)

    return has_learning and has_ai
