"""Tests for Hybrid Graph-RAG subsystem."""

from __future__ import annotations

import pytest
from proprisk_swarm.protocols import GraphRAGProtocol
from proprisk_swarm.rag.hybrid_rag import HybridGraphRAG


def test_graph_rag_protocol_conformance():
    """Verify HybridGraphRAG satisfies GraphRAGProtocol."""
    rag = HybridGraphRAG()
    assert isinstance(rag, GraphRAGProtocol)


def test_index_document_and_query():
    """Verify indexing text chunks, hybrid retrieval, and citation grounding."""
    rag = HybridGraphRAG(hybrid_alpha=0.6)

    doc_text = (
        "Austin Tower is a premier Class A multifamily asset located in downtown Austin. "
        "The primary tenant Whole Foods Market signed a 15-year net lease. "
        "The property sits in zone CBD with permissible commercial and residential uses."
    )
    chunks_indexed = rag.index_document(
        doc_id="DOC-AUSTIN",
        content=doc_text,
        metadata={"deal_id": "DEAL-AUSTIN", "title": "Austin Tower"},
    )
    assert chunks_indexed >= 1

    # Query matching tenant
    res = rag.query_with_citations("Who is the primary tenant?", top_k=3)
    assert len(res["passages"]) > 0
    assert "DOC-AUSTIN" in res["citations"]
    assert res["total_candidates"] >= 1

    # Empty index query
    empty_rag = HybridGraphRAG()
    empty_res = empty_rag.query_with_citations("random query")
    assert empty_res["passages"] == []
    assert empty_res["citations"] == []


def test_knowledge_graph_extraction_and_traversal():
    """Verify entity extraction and relation traversal."""
    rag = HybridGraphRAG()
    text = "Property Tower A has tenant Apex Logistics and lies in zone IND-1."
    rag.index_document("DOC-1", text, metadata={"deal_id": "DEAL-1", "title": "Tower A"})

    # Check graph entities
    assert len(rag.graph.entities) >= 2

    # Traverse relations from DEAL-1
    neighbors = rag.get_related_entities("DEAL-1")
    assert len(neighbors) >= 1
    names = [n["name"] for n in neighbors]
    assert any("Apex" in name or "IND-1" in name for name in names)


def test_index_document_empty_or_null():
    """Verify handling of empty or blank document indexing."""
    rag = HybridGraphRAG()
    assert rag.index_document("DOC-EMPTY", "   \x00   ") == 0
