"""Optional pgvector-backed retrieval adapter."""

from __future__ import annotations

import hashlib
import math
import uuid
from collections import Counter
from typing import Any

from .corpus import CorpusDocument, load_corpus_documents
from .models import SearchHit, SourceRef, utc_now
from .repositories.supabase import SupabaseREST
from .settings import get_settings
from .vector_store import _rank_score, _snippet, _tokenize

PGVECTOR_DIMENSIONS = 1536


def _embedding_vector(text: str, dimensions: int = PGVECTOR_DIMENSIONS) -> list[float]:
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * dimensions
    counts = Counter(tokens)
    values = [0.0] * dimensions
    for token, count in counts.items():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = -1.0 if digest[4] % 2 else 1.0
        values[index] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [round(value / norm, 6) for value in values]


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in values) + "]"


def _checksum(documents: list[CorpusDocument]) -> str:
    checksum = hashlib.sha256()
    for doc in documents:
        checksum.update(doc.id.encode("utf-8"))
        checksum.update(str(doc.metadata.get("path") or "").encode("utf-8"))
        checksum.update(doc.content.encode("utf-8"))
    return checksum.hexdigest()


def _deterministic_uuid(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, ":".join(parts)))


class PGVectorIndex:
    """Supabase/pgvector retrieval provider with the LocalVectorIndex interface."""

    def __init__(self, client: SupabaseREST | None = None):
        self.settings = get_settings()
        if not self.settings.supabase_enabled:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for pgvector retrieval")
        self.client = client or SupabaseREST(self.settings)
        self.tenant_id = self.settings.supabase_vector_tenant_id or self.settings.local_tenant_id
        self.metadata: dict[str, Any] = {}
        self.vector_index_id: str | None = None

    def _index_ids(self, documents: list[CorpusDocument]) -> tuple[str, str, str]:
        corpus_checksum = _checksum(documents)
        corpus_version_id = _deterministic_uuid("corpus", self.tenant_id, corpus_checksum)
        vector_index_id = _deterministic_uuid("pgvector", self.tenant_id, corpus_checksum)
        return corpus_checksum, corpus_version_id, vector_index_id

    def build(self, documents: list[CorpusDocument] | None = None) -> None:
        docs = documents or load_corpus_documents()
        corpus_checksum, corpus_version_id, vector_index_id = self._index_ids(docs)
        now = utc_now()
        self.client.upsert(
            "corpus_versions",
            [
                {
                    "id": corpus_version_id,
                    "tenant_id": self.tenant_id,
                    "corpus_checksum": corpus_checksum,
                    "document_count": len(docs),
                    "file_count": len({doc.metadata.get("path") for doc in docs}),
                    "metadata": {"provider": "pgvector_hash_embedding"},
                    "created_at": now,
                }
            ],
            "tenant_id,corpus_checksum",
        )
        self.client.upsert(
            "vector_indexes",
            [
                {
                    "id": vector_index_id,
                    "tenant_id": self.tenant_id,
                    "corpus_version_id": corpus_version_id,
                    "provider": "pgvector_hash_embedding",
                    "index_checksum": corpus_checksum,
                    "document_count": len(docs),
                    "metadata": {"dimensions": PGVECTOR_DIMENSIONS},
                    "built_at": now,
                }
            ],
            "id",
        )
        rows: list[dict[str, Any]] = []
        for doc in docs:
            metadata = doc.metadata
            rows.append(
                {
                    "tenant_id": self.tenant_id,
                    "vector_index_id": vector_index_id,
                    "source_id": metadata["source_id"],
                    "record_type": metadata["record_type"],
                    "slug": metadata.get("slug"),
                    "title": metadata.get("title") or "Untitled corpus record",
                    "path": metadata.get("path") or "",
                    "content": doc.content,
                    "embedding": _vector_literal(_embedding_vector(doc.content)),
                    "metadata": metadata,
                    "created_at": now,
                }
            )
            if len(rows) >= 50:
                self.client.upsert("corpus_embeddings", rows, "tenant_id,vector_index_id,source_id")
                rows = []
        if rows:
            self.client.upsert("corpus_embeddings", rows, "tenant_id,vector_index_id,source_id")
        self.vector_index_id = vector_index_id
        self.metadata = {
            "built_at": now,
            "document_count": len(docs),
            "corpus_checksum": corpus_checksum,
            "provider": "pgvector_hash_embedding",
            "vector_index_id": vector_index_id,
            "dimensions": PGVECTOR_DIMENSIONS,
        }

    def load(self) -> bool:
        docs = load_corpus_documents()
        corpus_checksum, _, vector_index_id = self._index_ids(docs)
        rows = self.client.get(
            "vector_indexes",
            {
                "tenant_id": f"eq.{self.tenant_id}",
                "id": f"eq.{vector_index_id}",
                "select": "*",
                "limit": "1",
            },
        )
        if not rows:
            return False
        row = rows[0]
        self.vector_index_id = vector_index_id
        self.metadata = {
            "built_at": row.get("built_at"),
            "document_count": row.get("document_count") or len(docs),
            "corpus_checksum": corpus_checksum,
            "provider": row.get("provider") or "pgvector_hash_embedding",
            "vector_index_id": vector_index_id,
            **(row.get("metadata") or {}),
        }
        return True

    def save(self) -> None:
        return None

    def ensure(self, rebuild: bool = False) -> None:
        if rebuild or not self.load():
            self.build()

    def search(
        self,
        query: str,
        k: int = 5,
        record_type: str | None = None,
        preferred_record_types: list[str] | tuple[str, ...] | None = None,
    ) -> list[SearchHit]:
        self.ensure()
        match_count = max(k, 1) * 5
        rows = self.client.rpc(
            "match_corpus_embeddings",
            {
                "query_embedding": _vector_literal(_embedding_vector(query)),
                "match_count": match_count,
                "record_type_filter": record_type,
                "vector_index_id_filter": self.vector_index_id,
                "tenant_id_filter": self.tenant_id,
            },
        )
        preferred = set(preferred_record_types or [])
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            metadata = row.get("metadata") or {}
            if record_type and row.get("record_type") != record_type:
                continue
            raw_score = max(0.0, float(row.get("score") or 0.0))
            score = _rank_score(raw_score, {**metadata, "record_type": row.get("record_type")}, query, preferred)
            if score <= 0:
                continue
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits: list[SearchHit] = []
        for score, row in scored[: max(k, 1)]:
            metadata = row.get("metadata") or {}
            source_ref = SourceRef(
                source_id=row["source_id"],
                record_type=row["record_type"],
                slug=row.get("slug"),
                title=row.get("title") or "Untitled corpus record",
                path=row.get("path") or "",
                citations=metadata.get("citations") or [],
                snippet=_snippet(row.get("content") or "", query),
                last_researched_at=metadata.get("last_researched_at"),
            )
            hits.append(
                SearchHit(
                    score=round(score, 4),
                    source_ref=source_ref,
                    summary=source_ref.snippet or "",
                    metadata=metadata,
                )
            )
        return hits
