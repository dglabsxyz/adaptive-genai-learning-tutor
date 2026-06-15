"""Qwen embedding index must fall back to TF-IDF when no key is configured."""

from backend.corpus import load_corpus_documents
from backend.qwen_vector_store import QwenVectorIndex


def test_qwen_index_falls_back_to_tfidf_without_key(tmp_path):
    index = QwenVectorIndex(index_path=tmp_path / "idx.json")
    docs = load_corpus_documents()[:12]
    index.build(documents=docs)  # no QWEN_API_KEY under pytest -> fallback path
    index.save()

    assert index.metadata.get("qwen_fallback") is True
    assert index.metadata.get("provider") == "local_sparse_tfidf"

    hits = index.search("retrieval augmented generation", k=3)
    assert hits  # offline search still works
