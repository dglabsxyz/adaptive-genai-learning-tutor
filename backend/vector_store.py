"""Small local embedding and vector search implementation.

This is intentionally dependency-light: it builds sparse TF-IDF style vectors
from the local corpus and persists them as JSON under data/. It is not a
semantic model, but it is a real local embedding space and enough for a
reliable MVP.
"""

from __future__ import annotations

import json
import math
import re
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from .config import VECTOR_INDEX_PATH, ensure_data_dir
from .corpus import CorpusDocument, load_corpus_documents
from .models import SearchHit, SourceRef, utc_now

TOKEN_RE = re.compile(r"[a-z0-9]+")

QUERY_EXPANSIONS = {
    "rag": "retrieval augmented generation vector database embeddings grounding citations",
    "mcp": "model context protocol server tools resources prompts",
    "agents": "agent tool use state memory routing langgraph orchestration",
    "agentic": "agents tool use state memory routing langgraph orchestration",
    "evals": "evaluation safety grading assessment quality",
}

LEARNING_RECORD_TYPE_WEIGHTS = {
    "topic": 1.28,
    "course": 1.18,
    "coverage": 1.05,
    "research_index": 1.0,
    "instructor": 0.72,
}


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    expanded = [lowered]
    for key, extra in QUERY_EXPANSIONS.items():
        if key in lowered:
            expanded.append(extra)
    return TOKEN_RE.findall(" ".join(expanded))


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    numerator = sum(value * right.get(key, 0.0) for key, value in left.items())
    return numerator


def _normalize(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm == 0:
        return vector
    return {key: value / norm for key, value in vector.items()}


def _snippet(content: str, query: str, limit: int = 320) -> str:
    query_terms = set(_tokenize(query))
    sentences = re.split(r"(?<=[.!?])\s+|\n+", content)
    best = ""
    best_score = -1
    for sentence in sentences:
        terms = set(_tokenize(sentence))
        score = len(query_terms & terms)
        if score > best_score and sentence.strip():
            best = sentence.strip()
            best_score = score
    if not best:
        best = content.strip()
    return best[:limit].rstrip()


def _rank_score(raw_score: float, metadata: dict[str, Any], query: str, preferred_record_types: set[str]) -> float:
    """Bias learning flows toward topic/course records without hiding other evidence."""
    if raw_score <= 0:
        return 0.0
    record_type = metadata.get("record_type")
    score = raw_score
    if preferred_record_types:
        score *= LEARNING_RECORD_TYPE_WEIGHTS.get(record_type, 1.0)
    title_terms = set(_tokenize(str(metadata.get("title") or "")))
    slug_terms = set(_tokenize(str(metadata.get("slug") or "")))
    query_terms = set(_tokenize(query))
    if query_terms:
        overlap = len(query_terms & (title_terms | slug_terms))
        if overlap:
            score *= 1.0 + min(0.25, overlap * 0.08)
    if record_type in preferred_record_types:
        score *= 1.08
    return score


class LocalVectorIndex:
    def __init__(self, index_path: Path = VECTOR_INDEX_PATH):
        self.index_path = index_path
        self.documents: list[dict[str, Any]] = []
        self.idf: dict[str, float] = {}
        self.vectors: list[dict[str, float]] = []
        self.metadata: dict[str, Any] = {}

    def build(self, documents: list[CorpusDocument] | None = None) -> None:
        docs = documents or load_corpus_documents()
        doc_tokens = [_tokenize(doc.content) for doc in docs]
        doc_count = len(doc_tokens)
        dfs: Counter[str] = Counter()
        for tokens in doc_tokens:
            dfs.update(set(tokens))
        self.idf = {
            token: math.log((1 + doc_count) / (1 + df)) + 1.0
            for token, df in dfs.items()
        }
        self.documents = [doc.model_dump() for doc in docs]
        self.vectors = [self._embed_tokens(tokens) for tokens in doc_tokens]
        checksum = hashlib.sha256()
        for doc in docs:
            checksum.update(doc.id.encode("utf-8"))
            checksum.update(str(doc.metadata.get("path") or "").encode("utf-8"))
            checksum.update(doc.content.encode("utf-8"))
        self.metadata = {
            "built_at": utc_now(),
            "document_count": len(docs),
            "corpus_checksum": checksum.hexdigest(),
            "provider": "local_sparse_tfidf",
        }

    def _embed_tokens(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        if not counts:
            return {}
        total = sum(counts.values())
        weighted = {
            token: (count / total) * self.idf.get(token, 1.0)
            for token, count in counts.items()
        }
        return _normalize(weighted)

    def embed_query(self, query: str) -> dict[str, float]:
        return self._embed_tokens(_tokenize(query))

    def save(self) -> None:
        ensure_data_dir()
        payload = {
            "version": 1,
            "index_metadata": self.metadata,
            "documents": self.documents,
            "idf": self.idf,
            "vectors": self.vectors,
        }
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> bool:
        if not self.index_path.exists():
            return False
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.documents = payload.get("documents", [])
        self.idf = payload.get("idf", {})
        self.vectors = payload.get("vectors", [])
        self.metadata = payload.get("index_metadata", {})
        return bool(self.documents and self.vectors)

    def ensure(self, rebuild: bool = False) -> None:
        if rebuild or not self.load():
            self.build()
            self.save()

    def search(
        self,
        query: str,
        k: int = 5,
        record_type: str | None = None,
        preferred_record_types: list[str] | tuple[str, ...] | None = None,
    ) -> list[SearchHit]:
        self.ensure()
        query_vector = self.embed_query(query)
        preferred = set(preferred_record_types or [])
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc, vector in zip(self.documents, self.vectors, strict=False):
            metadata = doc["metadata"]
            if record_type and metadata.get("record_type") != record_type:
                continue
            score = _rank_score(_cosine(query_vector, vector), metadata, query, preferred)
            if score <= 0:
                continue
            scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits: list[SearchHit] = []
        for score, doc in scored[: max(k, 1)]:
            metadata = doc["metadata"]
            snippet = _snippet(doc["content"], query)
            source_ref = SourceRef(
                source_id=metadata["source_id"],
                record_type=metadata["record_type"],
                slug=metadata.get("slug"),
                title=metadata.get("title") or "Untitled corpus record",
                path=metadata.get("path") or "",
                citations=metadata.get("citations") or [],
                snippet=snippet,
                last_researched_at=metadata.get("last_researched_at"),
            )
            hits.append(
                SearchHit(
                    score=round(score, 4),
                    source_ref=source_ref,
                    summary=snippet,
                    metadata=metadata,
                )
            )
        return hits
