"""Corpus versioning, source quality, and citation audit helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import CORPUS_DIR
from .corpus import corpus_stats, load_corpus_documents
from .dependencies import get_vector_index
from .models import SourceRef, utc_now

CORE_RETRIEVAL_TOPICS = [
    "LLMs",
    "prompt engineering",
    "context engineering",
    "RAG",
    "AI agents",
    "MCP",
    "AI safety and evaluation",
]


def corpus_file_inventory(corpus_dir: Path = CORPUS_DIR) -> list[dict[str, Any]]:
    files = sorted(path for path in corpus_dir.rglob("*.json") if path.is_file())
    inventory: list[dict[str, Any]] = []
    for path in files:
        rel = path.relative_to(corpus_dir).as_posix()
        content = path.read_bytes()
        inventory.append(
            {
                "path": str(Path("genai_research") / rel),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return inventory


def corpus_version_metadata(corpus_dir: Path = CORPUS_DIR) -> dict[str, Any]:
    inventory = corpus_file_inventory(corpus_dir)
    checksum = hashlib.sha256()
    for item in inventory:
        checksum.update(item["path"].encode("utf-8"))
        checksum.update(item["sha256"].encode("utf-8"))
    stats = corpus_stats(corpus_dir)
    return {
        "generated_at": utc_now(),
        "corpus_dir": str(corpus_dir),
        "file_count": len(inventory),
        "document_count": stats["document_count"],
        "by_type": stats["by_type"],
        "corpus_checksum": checksum.hexdigest(),
    }


def index_status() -> dict[str, Any]:
    index = get_vector_index()
    return {
        "ready": bool(index.documents and index.vectors),
        "index_path": str(index.index_path),
        "document_count": len(index.documents),
        "metadata": index.metadata,
    }


def source_quality_report(corpus_dir: Path = CORPUS_DIR) -> dict[str, Any]:
    docs = load_corpus_documents(corpus_dir)
    missing_citations: list[dict[str, str | None]] = []
    missing_researched_at: list[dict[str, str | None]] = []
    by_type: dict[str, int] = {}
    for doc in docs:
        metadata = doc.metadata
        record_type = metadata.get("record_type") or "unknown"
        by_type[record_type] = by_type.get(record_type, 0) + 1
        descriptor = {
            "source_id": metadata.get("source_id"),
            "record_type": record_type,
            "title": metadata.get("title"),
            "path": metadata.get("path"),
        }
        if not metadata.get("citations"):
            missing_citations.append(descriptor)
        if metadata.get("last_researched_at") is None:
            missing_researched_at.append(descriptor)
    return {
        "generated_at": utc_now(),
        "document_count": len(docs),
        "by_type": by_type,
        "missing_citations_count": len(missing_citations),
        "missing_last_researched_at_count": len(missing_researched_at),
        "missing_citations": missing_citations[:25],
        "missing_last_researched_at": missing_researched_at[:25],
    }


def collect_source_refs(payload: Any) -> list[SourceRef]:
    refs: list[SourceRef] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        if value.get("source_id") and value.get("path") and value.get("title"):
            try:
                refs.append(SourceRef.model_validate(value))
            except ValueError:
                pass
        for nested in value.values():
            visit(nested)

    visit(payload)
    deduped: dict[str, SourceRef] = {}
    for ref in refs:
        deduped[ref.source_id] = ref
    return list(deduped.values())


def citation_audit(payload: Any) -> dict[str, Any]:
    refs = collect_source_refs(payload)
    return {
        "has_source_refs": bool(refs),
        "source_ref_count": len(refs),
        "missing_citations": [ref.model_dump() for ref in refs if not ref.citations],
        "missing_paths": [ref.model_dump() for ref in refs if not ref.path],
        "unknown_researched_at_count": len([ref for ref in refs if ref.last_researched_at is None]),
    }


def retrieval_evaluation_report(topics: list[str] | None = None) -> dict[str, Any]:
    index = get_vector_index()
    results = []
    for topic in topics or CORE_RETRIEVAL_TOPICS:
        hits = index.search(f"{topic} course topic source evaluation", k=5, preferred_record_types=("topic", "course"))
        refs = [hit.source_ref for hit in hits]
        results.append(
            {
                "topic": topic,
                "hit_count": len(hits),
                "has_topic_or_course": any(ref.record_type in {"topic", "course"} for ref in refs),
                "top_refs": [ref.model_dump() for ref in refs[:3]],
            }
        )
    return {"generated_at": utc_now(), "results": results}


def write_corpus_version_file(output_path: Path) -> dict[str, Any]:
    payload = corpus_version_metadata()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
