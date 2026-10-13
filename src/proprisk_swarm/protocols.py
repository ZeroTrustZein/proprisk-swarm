"""Core architectural protocols and interfaces for PropRisk Swarm."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol for specialized autonomous swarm agents."""

    @property
    def agent_id(self) -> str:
        """Unique identifier for the agent."""
        ...

    @property
    def role_name(self) -> str:
        """Functional role label."""
        ...

    def execute_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute assigned underwriting diligence task."""
        ...

    def can_handle(self, task_type: str) -> bool:
        """Check whether the agent supports the requested task."""
        ...


@runtime_checkable
class MCPServerProtocol(Protocol):
    """Protocol for Model Context Protocol (MCP) data source servers."""

    @property
    def server_name(self) -> str:
        """Name of the MCP server endpoint."""
        ...

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return available structured tool definitions."""
        ...

    def list_resources(self) -> List[Dict[str, Any]]:
        """Return catalog of accessible data resources."""
        ...

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke MCP tool call with arguments."""
        ...


@runtime_checkable
class IngestionPipelineProtocol(Protocol):
    """Protocol for external data ingestion from deeds, SEC filings, and zoning."""

    def ingest_document(
        self, source_path: str, source_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Ingest raw legal or financial document and return job ID."""
        ...

    def parse_payload(self, raw_data: bytes, document_type: str) -> Dict[str, Any]:
        """Parse binary payload into structured property record."""
        ...


@runtime_checkable
class GraphRAGProtocol(Protocol):
    """Protocol for Hybrid Graph-RAG knowledge indexing and citation grounding."""

    def index_document(
        self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Index text into vector store and extract entity-relation triples."""
        ...

    def query_with_citations(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Perform hybrid retrieval returning grounded passages with citations."""
        ...

    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Traverse knowledge graph relations from source entity."""
        ...


@runtime_checkable
class ValuationEngineProtocol(Protocol):
    """Protocol for DCF modeling and audit-ready memo synthesis."""

    def compute_dcf(
        self,
        purchase_price: float,
        cash_flows: List[float],
        discount_rate: float,
        terminal_cap_rate: float,
    ) -> Dict[str, Any]:
        """Calculate DCF metrics: NPV, Unlevered IRR, Levered IRR, and Equity Multiple."""
        ...

    def synthesize_investment_memo(
        self, deal_id: str, valuation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assemble audit-ready investment committee memorandum."""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol for event-driven swarm orchestration."""

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event across the swarm message bus."""
        ...

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for specific event type."""
        ...
