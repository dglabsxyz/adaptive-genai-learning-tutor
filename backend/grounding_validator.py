"""Post-generation citation and grounding validation.

LLM-026, AGT-029: Validates that agent responses include proper citations
from the corpus and flags potential hallucinations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("backend.grounding_validator")

# Patterns for detecting citations in agent responses
CITATION_PATTERNS = [
    # [1], [2], etc.
    r'\[(\d+)\]',
    # (Source: ...)
    r'\(Source:\s*([^)]+)\)',
    # According to <title>
    r'According to (?:the )?"?([^"]+)"?',
    # From <title> or <path>
    r'From (?:the )?(?:course |material )?"?([^"]+)"?',
    # As mentioned in
    r'As mentioned in (?:the )?"?([^"]+)"?',
    # Based on <source>
    r'Based on (?:the )?"?([^"]+)"?',
]


@dataclass
class GroundingResult:
    """Result of grounding validation."""

    is_grounded: bool
    citation_count: int
    source_refs_present: bool
    confidence: float  # 0.0 to 1.0
    warnings: list[str] = field(default_factory=list)
    citations_found: list[str] = field(default_factory=list)


def count_inline_citations(text: str) -> tuple[int, list[str]]:
    """Count and extract inline citations from response text."""
    citations = []
    for pattern in CITATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        citations.extend(matches)
    return len(citations), citations


def validate_source_refs(source_refs: list[dict[str, Any]] | None) -> tuple[bool, int]:
    """Validate that source_refs are present and properly structured."""
    if not source_refs:
        return False, 0

    valid_count = 0
    for ref in source_refs:
        if not isinstance(ref, dict):
            continue
        # A valid source ref should have at least a title or path
        if ref.get("title") or ref.get("path") or ref.get("source_id"):
            valid_count += 1

    return valid_count > 0, valid_count


def validate_grounding(
    message: str,
    source_refs: list[dict[str, Any]] | None = None,
    *,
    require_citations: bool = True,
    min_citations: int = 1,
) -> GroundingResult:
    """Validate that a response is properly grounded with citations.

    Args:
        message: The agent's response text
        source_refs: Structured source references from the response
        require_citations: Whether to require inline citations
        min_citations: Minimum number of citations required

    Returns:
        GroundingResult with validation details
    """
    warnings = []
    citations_found = []

    # Check for inline citations in text
    inline_count, inline_citations = count_inline_citations(message)
    citations_found.extend(inline_citations)

    # Check structured source refs
    refs_valid, refs_count = validate_source_refs(source_refs)

    # Calculate grounding confidence
    total_citations = inline_count + refs_count
    has_citations = total_citations >= min_citations

    if not has_citations and require_citations:
        warnings.append(
            f"Response has {total_citations} citations (minimum: {min_citations})"
        )

    if not refs_valid and source_refs is not None:
        warnings.append("Source references are present but may be malformed")

    # Check for potential hallucination indicators
    hallucination_phrases = [
        "I believe",
        "I think",
        "in my opinion",
        "generally speaking",
        "it's commonly known",
        "everyone knows",
        "obviously",
        "clearly",
    ]
    message_lower = message.lower()
    for phrase in hallucination_phrases:
        if phrase in message_lower:
            warnings.append(f"Potential unsupported claim marker: '{phrase}'")
            break

    # Calculate confidence
    confidence = 0.0
    if refs_valid and refs_count >= min_citations:
        confidence = min(1.0, 0.5 + (refs_count * 0.1))
    elif inline_count >= min_citations:
        confidence = min(1.0, 0.3 + (inline_count * 0.1))
    elif total_citations > 0:
        confidence = 0.2

    is_grounded = has_citations or (refs_valid and refs_count > 0)

    if not is_grounded:
        logger.warning(
            "Response failed grounding validation: %d citations, %d source_refs",
            inline_count,
            refs_count,
        )

    return GroundingResult(
        is_grounded=is_grounded,
        citation_count=total_citations,
        source_refs_present=refs_valid,
        confidence=confidence,
        warnings=warnings,
        citations_found=citations_found,
    )


def validate_response(
    response: dict[str, Any],
    *,
    strict: bool = False,
) -> tuple[bool, GroundingResult]:
    """Validate a complete agent response for grounding.

    Args:
        response: The full response dict with 'message' and 'source_refs'
        strict: If True, reject responses that fail validation

    Returns:
        (should_allow, grounding_result)
    """
    message = response.get("message", "")
    source_refs = response.get("source_refs")

    # Skip validation for blocked or error responses
    if response.get("blocked") or response.get("error"):
        return True, GroundingResult(
            is_grounded=True,
            citation_count=0,
            source_refs_present=False,
            confidence=1.0,
        )

    # Skip validation for clarification requests
    if response.get("needs_clarification"):
        return True, GroundingResult(
            is_grounded=True,
            citation_count=0,
            source_refs_present=False,
            confidence=1.0,
        )

    result = validate_grounding(message, source_refs)

    if strict and not result.is_grounded:
        logger.error(
            "Strict grounding validation failed: confidence=%.2f, citations=%d",
            result.confidence,
            result.citation_count,
        )
        return False, result

    return True, result
