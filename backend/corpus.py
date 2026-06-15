"""Read-only ingestion and normalization for genai_research."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .config import CORPUS_DIR

URL_RE = re.compile(r"https?://[^\s)>\"]+")


class CorpusDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _title_from_slug(slug: str | None, fallback: str) -> str:
    if not slug:
        return fallback
    return slug.replace("-", " ").title()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _collect_citations(value: Any) -> list[str]:
    citations: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"citations", "source_urls"} and isinstance(nested, list):
                citations.extend(str(item) for item in nested if isinstance(item, str))
            elif key in {"course_url", "website", "url"} and isinstance(nested, str):
                citations.append(nested)
            else:
                citations.extend(_collect_citations(nested))
    elif isinstance(value, list):
        for item in value:
            citations.extend(_collect_citations(item))
    elif isinstance(value, str):
        citations.extend(URL_RE.findall(value))
    return _dedupe(citations)


def _flatten_text(value: Any, max_items: int = 24) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_flatten_text(item, max_items=max_items) for item in value[:max_items]]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, nested in value.items():
            text = _flatten_text(nested, max_items=max_items)
            if text and text != "unknown":
                parts.append(f"{key}: {text}")
        return "; ".join(parts)
    return str(value)


def _metadata_for(record_type: str, raw: dict[str, Any], rel_path: str) -> dict[str, Any]:
    slug = (
        raw.get("slug")
        or raw.get("course_slug")
        or raw.get("topic_slug")
        or Path(rel_path).parts[-2]
        if len(Path(rel_path).parts) > 1
        else Path(rel_path).stem
    )
    if record_type == "course":
        title = raw.get("course_name") or raw.get("title") or _title_from_slug(slug, "Unknown course")
        topic_tags = raw.get("topic_tags") or []
        platform = raw.get("platform")
    elif record_type == "topic":
        title = raw.get("topic") or _title_from_slug(slug, "Unknown topic")
        topic_tags = [title, *(raw.get("related_topics") or [])]
        platform = None
    elif record_type == "instructor":
        title = raw.get("name") or _title_from_slug(slug, "Unknown instructor")
        topic_tags = raw.get("topics_taught") or raw.get("expertise_areas") or []
        platform = raw.get("platforms") or []
    elif record_type == "coverage":
        title = "Corpus coverage report"
        slug = "coverage-report"
        topic_tags = [item.get("topic") for item in raw.get("required_topic_coverage", []) if item.get("topic")]
        platform = None
    else:
        title = "Research index"
        slug = "research-index"
        topic_tags = [item.get("topic") for item in raw.get("topics", []) if item.get("topic")]
        platform = None

    return {
        "record_type": record_type,
        "slug": slug,
        "title": title,
        "topic_tags": topic_tags,
        "platform": platform,
        "path": str(Path("genai_research") / rel_path),
        "citations": _collect_citations(raw),
        "last_researched_at": raw.get("last_researched_at") or raw.get("generated_at"),
    }


def _content_for(record_type: str, raw: dict[str, Any], metadata: dict[str, Any]) -> str:
    fields_by_type = {
        "course": [
            "course_name",
            "description",
            "topic_tags",
            "syllabus",
            "target_audience",
            "prerequisites",
            "format",
            "duration",
            "certificate",
            "price",
            "rating",
            "enrollment_status",
            "last_updated",
            "source_records",
        ],
        "topic": [
            "topic",
            "description",
            "related_topics",
            "courses",
            "instructors",
            "sources",
        ],
        "instructor": [
            "name",
            "headline",
            "bio",
            "organization",
            "expertise_areas",
            "topics_taught",
            "audience_levels",
            "teaching_formats",
            "courses",
            "credibility_signals",
        ],
        "coverage": [
            "summary",
            "counts",
            "required_topic_coverage",
            "additional_topics_discovered",
            "platforms_covered",
            "known_limitations",
            "source_quality_notes",
        ],
        "research_index": ["counts", "topics", "courses", "instructors"],
    }
    lines = [
        f"Title: {metadata['title']}",
        f"Record type: {record_type}",
        f"Topic tags: {_flatten_text(metadata.get('topic_tags'))}",
        f"Platform: {_flatten_text(metadata.get('platform'))}",
    ]
    for field in fields_by_type.get(record_type, []):
        if field in raw:
            lines.append(f"{field.replace('_', ' ').title()}: {_flatten_text(raw.get(field))}")
    if metadata.get("citations"):
        lines.append(f"Citations: {'; '.join(metadata['citations'])}")
    return "\n".join(line for line in lines if line)


def _document(record_type: str, raw: dict[str, Any], rel_path: str) -> CorpusDocument:
    metadata = _metadata_for(record_type, raw, rel_path)
    source_id = f"{record_type}:{metadata['slug']}"
    if record_type in {"coverage", "research_index"}:
        source_id = record_type
    metadata["source_id"] = source_id
    return CorpusDocument(
        id=source_id,
        content=_content_for(record_type, raw, metadata),
        metadata=metadata,
    )


def load_corpus_documents(corpus_dir: Path = CORPUS_DIR) -> list[CorpusDocument]:
    """Load required corpus files without mutating genai_research."""
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    documents: list[CorpusDocument] = []
    required = [
        ("research_index", "research_index.json"),
        ("coverage", "coverage_report.json"),
    ]
    for record_type, rel in required:
        path = corpus_dir / rel
        if path.exists():
            documents.append(_document(record_type, _load_json(path), rel))

    for path in sorted(corpus_dir.glob("topics/*/topic_summary.json")):
        rel = path.relative_to(corpus_dir).as_posix()
        documents.append(_document("topic", _load_json(path), rel))
    for path in sorted(corpus_dir.glob("courses/*/course_summary.json")):
        rel = path.relative_to(corpus_dir).as_posix()
        documents.append(_document("course", _load_json(path), rel))
    for path in sorted(corpus_dir.glob("instructors/*/instructor_summary.json")):
        rel = path.relative_to(corpus_dir).as_posix()
        documents.append(_document("instructor", _load_json(path), rel))
    return documents


def corpus_stats(corpus_dir: Path = CORPUS_DIR) -> dict[str, Any]:
    docs = load_corpus_documents(corpus_dir)
    by_type: dict[str, int] = {}
    for doc in docs:
        by_type[doc.metadata["record_type"]] = by_type.get(doc.metadata["record_type"], 0) + 1
    return {
        "corpus_dir": str(corpus_dir),
        "document_count": len(docs),
        "by_type": by_type,
    }

