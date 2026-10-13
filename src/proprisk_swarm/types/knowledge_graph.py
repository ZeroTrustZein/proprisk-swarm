"""Domain models for property diligence entity-relationship knowledge graph."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from proprisk_swarm.types.base import BaseEntity, generate_uuid


class EntityType(str, Enum):
    """Categorical taxonomy of nodes in the CRE knowledge graph."""

    PROPERTY = "property"
    PARCEL = "parcel"
    OWNER_ENTITY = "owner_entity"
    SPONSOR = "sponsor"
    GUARANTOR = "guarantor"
    TENANT = "tenant"
    LENDER = "lender"
    LIEN_HOLDER = "lien_holder"
    BROKER = "broker"
    MUNICIPALITY = "municipality"


class RelationType(str, Enum):
    """Semantic edges connecting real estate entities."""

    OWNS = "owns"
    LEASES_TO = "leases_to"
    ENCUMBERS = "encumbers"
    GUARANTEES = "guarantees"
    FINANCED_BY = "financed_by"
    SITUATED_IN = "situated_in"
    MANAGED_BY = "managed_by"
    ADJACENT_TO = "adjacent_to"
    AFFILIATED_WITH = "affiliated_with"


class GraphEntity(BaseModel):
    """A node in the diligence graph representing a legal or physical object."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    entity_id: str = Field(default_factory=generate_uuid, description="Unique node identifier")
    entity_type: EntityType = Field(..., description="Taxonomy classification")
    label: str = Field(..., min_length=1, description="Human readable name or title")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction certainty rating"
    )
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary typed metadata")


class GraphRelation(BaseModel):
    """A directed, weighted edge representing a legal or contractual relationship."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    relation_id: str = Field(default_factory=generate_uuid, description="Unique edge identifier")
    source_id: str = Field(..., description="Source node entity_id")
    target_id: str = Field(..., description="Target node entity_id")
    relation_type: RelationType = Field(..., description="Semantic relation")
    weight: float = Field(default=1.0, ge=0.0, description="Edge weight or relation confidence")
    citation_doc_id: Optional[str] = Field(
        default=None, description="Document chunk or filing reference ID"
    )
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship metadata")


class KnowledgeGraph(BaseEntity):
    """In-memory or serializable knowledge graph for multi-agent deal diligence."""

    entities: Dict[str, GraphEntity] = Field(
        default_factory=dict, description="Entities indexed by entity_id"
    )
    relations: List[GraphRelation] = Field(
        default_factory=list, description="All directed relations"
    )

    def add_entity(self, entity: GraphEntity) -> None:
        """Insert or overwrite an entity node."""
        self.entities[entity.entity_id] = entity
        self.touch()

    def add_relation(self, relation: GraphRelation) -> None:
        """Insert a relation edge after verifying existence of both endpoints."""
        if relation.source_id not in self.entities:
            raise KeyError(f"Source entity {relation.source_id} not found in graph")
        if relation.target_id not in self.entities:
            raise KeyError(f"Target entity {relation.target_id} not found in graph")
        self.relations.append(relation)
        self.touch()

    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Retrieve entity by ID."""
        return self.entities.get(entity_id)

    def filter_by_type(self, entity_type: EntityType) -> List[GraphEntity]:
        """Return all entities matching a specific type."""
        return [e for e in self.entities.values() if e.entity_type == entity_type]

    def get_outgoing_relations(self, entity_id: str) -> List[GraphRelation]:
        """Return all edges starting from the specified entity."""
        return [r for r in self.relations if r.source_id == entity_id]

    def get_incoming_relations(self, entity_id: str) -> List[GraphRelation]:
        """Return all edges terminating at the specified entity."""
        return [r for r in self.relations if r.target_id == entity_id]

    def get_neighbors(self, entity_id: str) -> List[str]:
        """Return all unique entity IDs directly linked in either direction."""
        neighbors = set()
        for r in self.relations:
            if r.source_id == entity_id:
                neighbors.add(r.target_id)
            elif r.target_id == entity_id:
                neighbors.add(r.source_id)
        return sorted(list(neighbors))

    def find_encumbrances(self, property_entity_id: str) -> List[GraphRelation]:
        """Return liens, mortgages, or encumbrances against a property."""
        return [
            r
            for r in self.relations
            if r.target_id == property_entity_id and r.relation_type == RelationType.ENCUMBERS
        ]

