"""Hybrid Graph-RAG subsystem combining dense/lexical retrieval with knowledge graph traversal."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
import numpy as np

from proprisk_swarm.protocols import GraphRAGProtocol
from proprisk_swarm.types.knowledge_graph import (
    EntityType,
    GraphEntity,
    GraphRelation,
    KnowledgeGraph,
    RelationType,
)


class HybridGraphRAG(GraphRAGProtocol):
    """Hybrid Graph-RAG indexing passages and linking entity-relation graphs."""

    def __init__(self, hybrid_alpha: float = 0.6) -> None:
        self.hybrid_alpha = hybrid_alpha
        self._chunks: List[Dict[str, Any]] = []
        self.graph = KnowledgeGraph()

    def _simple_embed(self, text: str, dim: int = 64) -> np.ndarray:
        """Deterministic hash-based dense embedding vector."""
        vec = np.zeros(dim, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        if not words:
            return vec
        for i, word in enumerate(words):
            h = hash(word) % dim
            vec[h] += 1.0 / (1.0 + (i * 0.05))
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def index_document(
        self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Index text chunks into vector/lexical index and extract graph relations."""
        meta = metadata or {}
        cleaned = content.replace("\x00", "").strip()
        if not cleaned:
            return 0

        # Chunk into paragraphs / sentences
        raw_chunks = [c.strip() for c in re.split(r"\n\s*\n|(?<=[.!?])\s+", cleaned) if c.strip()]
        if not raw_chunks:
            raw_chunks = [cleaned]

        chunk_count = 0
        for idx, text in enumerate(raw_chunks):
            chunk_id = f"{doc_id}-chunk-{idx}"
            tokens = set(re.findall(r"\w+", text.lower()))
            embedding = self._simple_embed(text)
            self._chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "text": text,
                "tokens": tokens,
                "embedding": embedding,
                "metadata": meta,
            })
            chunk_count += 1

        # Automatically extract entities for knowledge graph
        self._extract_graph_entities(doc_id, cleaned, meta)
        return chunk_count

    def _extract_graph_entities(self, doc_id: str, text: str, meta: Dict[str, Any]) -> None:
        """Extract basic property and tenant entities from text."""
        prop_id = meta.get("deal_id", doc_id)
        prop_name = meta.get("title", f"Property {doc_id}")

        prop_entity = GraphEntity(
            id=prop_id,
            entity_type=EntityType.PROPERTY,
            name=prop_name,
            properties={"doc_id": doc_id},
        )
        self.graph.add_entity(prop_entity)

        # Check for tenant mentions
        tenant_match = re.search(r"tenant\s+([A-Z][a-zA-Z0-9\s&]+?)(?=[,\.\n]|$)", text, re.IGNORECASE)
        if tenant_match:
            t_name = tenant_match.group(1).strip()
            t_id = f"tenant-{abs(hash(t_name)) % 100000}"
            t_entity = GraphEntity(id=t_id, entity_type=EntityType.TENANT, name=t_name)
            self.graph.add_entity(t_entity)
            self.graph.add_relation(
                GraphRelation(
                    source_id=t_id,
                    target_id=prop_id,
                    relation_type=RelationType.LEASES_TO,
                    confidence=0.85,
                )
            )

        # Check for zoning district
        zoning_match = re.search(r"zone\s+([A-Z0-9\-]+)", text, re.IGNORECASE)
        if zoning_match:
            z_code = zoning_match.group(1).strip()
            z_id = f"zone-{z_code}"
            z_entity = GraphEntity(id=z_id, entity_type=EntityType.ZONING_DISTRICT, name=z_code)
            self.graph.add_entity(z_entity)
            self.graph.add_relation(
                GraphRelation(
                    source_id=z_id,
                    target_id=prop_id,
                    relation_type=RelationType.RESTRICTS,
                    confidence=0.9,
                )
            )

    def query_with_citations(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Perform hybrid dense/lexical retrieval with citation grounding."""
        if not self._chunks:
            return {"query": query, "passages": [], "citations": []}

        q_clean = query.replace("\x00", "").strip()
        q_tokens = set(re.findall(r"\w+", q_clean.lower()))
        q_emb = self._simple_embed(q_clean)

        scored: List[tuple[float, Dict[str, Any]]] = []
        for chk in self._chunks:
            # Lexical Jaccard score
            overlap = len(chk["tokens"].intersection(q_tokens))
            union = len(chk["tokens"].union(q_tokens))
            lex_score = overlap / max(union, 1)

            # Dense cosine similarity
            dense_score = float(np.dot(chk["embedding"], q_emb))

            score = (self.hybrid_alpha * dense_score) + ((1.0 - self.hybrid_alpha) * lex_score)
            scored.append((score, chk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        passages = [
            {
                "chunk_id": item["chunk_id"],
                "doc_id": item["doc_id"],
                "text": item["text"],
                "score": round(score, 4),
            }
            for score, item in top
        ]
        citations = list(dict.fromkeys(item["doc_id"] for _, item in top))

        return {
            "query": query,
            "passages": passages,
            "citations": citations,
            "total_candidates": len(self._chunks),
        }

    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Traverse knowledge graph relations from source entity."""
        visited: Set[str] = set()
        queue = [(entity_id, 0)]
        results: List[Dict[str, Any]] = []

        while queue:
            curr_id, depth = queue.pop(0)
            if curr_id in visited or depth > max_depth:
                continue
            visited.add(curr_id)

            neighbors = self.graph.get_neighbors(curr_id)
            for node, rel in neighbors:
                results.append({
                    "entity_id": node.id,
                    "name": node.name,
                    "type": str(node.entity_type),
                    "relation": str(rel.relation_type),
                    "depth": depth + 1,
                })
                if depth + 1 < max_depth:
                    queue.append((node.id, depth + 1))

        return results
