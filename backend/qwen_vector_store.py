"""Dense corpus embedding index backed by Qwen ``text-embedding-v4``.

Selected with ``TUTOR_VECTOR_PROVIDER=qwen``. It reuses ``LocalVectorIndex``'s
ranking, snippeting, and hit-construction, but embeds documents and queries with
Qwen instead of sparse TF-IDF. Dense vectors are stored as ``{index: value}``
dicts so the inherited cosine/search/save/load all work unchanged.

"Use Qwen first, fall back to local whenever needed": if the Qwen API is
unavailable at build time, it transparently builds the TF-IDF index instead, so
the app never loses search. Build it with ``scripts/rebuild_index.py``.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from . import llm_provider
from .config import VECTOR_INDEX_PATH
from .corpus import CorpusDocument, load_corpus_documents
from .models import utc_now
from .settings import get_settings
from .vector_store import LocalVectorIndex, _normalize

QWEN_PROVIDER_TAG = "qwen_text_embedding_v4"


def _dense_to_dict(vector: list[float]) -> dict[str, float]:
    return _normalize({str(i): value for i, value in enumerate(vector) if value})


class QwenVectorIndex(LocalVectorIndex):
    def __init__(self, index_path: Path = VECTOR_INDEX_PATH):
        super().__init__(index_path=index_path)
        self._dense = False

    def build(self, documents: list[CorpusDocument] | None = None) -> None:
        docs = documents or load_corpus_documents()
        try:
            vectors = llm_provider.embed([doc.content for doc in docs])
        except llm_provider.LLMUnavailable:
            # Fall back to the local sparse index; search keeps working offline.
            super().build(documents=docs)
            self._dense = False
            self.metadata = {**self.metadata, "provider": "local_sparse_tfidf", "qwen_fallback": True}
            return
        self.documents = [doc.model_dump() for doc in docs]
        self.vectors = [_dense_to_dict(vector) for vector in vectors]
        self.idf = {}
        self._dense = True
        checksum = hashlib.sha256()
        for doc in docs:
            checksum.update(doc.id.encode("utf-8"))
            checksum.update(doc.content.encode("utf-8"))
        settings = get_settings()
        self.metadata = {
            "built_at": utc_now(),
            "document_count": len(docs),
            "corpus_checksum": checksum.hexdigest(),
            "provider": QWEN_PROVIDER_TAG,
            "embedding_model": settings.qwen_embedding_model,
            "dimensions": len(vectors[0]) if vectors else 0,
        }

    def load(self) -> bool:
        ok = super().load()
        self._dense = self.metadata.get("provider") == QWEN_PROVIDER_TAG
        return ok

    def embed_query(self, query: str) -> dict[str, float]:
        if not self._dense:
            return super().embed_query(query)
        try:
            vector = llm_provider.embed([query])[0]
        except llm_provider.LLMUnavailable:
            return {}  # search will return no hits rather than crash
        return _dense_to_dict(vector)
