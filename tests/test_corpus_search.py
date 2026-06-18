from backend.corpus import load_corpus_documents
from backend.tools import search_course_material_impl


def test_corpus_loader_reads_required_record_types():
    docs = load_corpus_documents()
    record_types = {doc.metadata["record_type"] for doc in docs}

    assert {"research_index", "coverage", "topic", "course", "instructor"} <= record_types
    assert len(docs) >= 150
    assert all(doc.metadata["path"].startswith("genai_research/") for doc in docs)


def test_source_search_returns_source_refs():
    payload = search_course_material_impl("RAG retrieval augmented generation vector databases", k=3)

    assert payload["results"]
    assert payload["source_refs"]
    assert all(ref["path"].startswith("genai_research/") for ref in payload["source_refs"])
    assert any("RAG" in ref["title"] or "Rag" in ref["title"] for ref in payload["source_refs"])

