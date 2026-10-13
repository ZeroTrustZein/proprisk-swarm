"""Event schema and dispatch contracts for asynchronous multi-agent coordination."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from proprisk_swarm.types.base import generate_uuid, utc_now


class EventType(str, Enum):
    """Event taxonomy triggering agent actions across the diligence lifecycle."""

    DEAL_CREATED = "deal.created"
    MUNICIPAL_DEED_INGESTED = "ingestion.deed.completed"
    DEED_AUDIT_COMPLETED = "audit.deed.completed"
    SEC_FILING_INGESTED = "ingestion.sec.completed"
    SEC_DISCLOSURE_FLAGGED = "audit.sec.flagged"
    MEMORANDUM_INGESTED = "ingestion.memorandum.completed"
    RAG_SYNTHESIS_COMPLETED = "rag.synthesis.completed"
    GRAPH_LINK_CREATED = "graph.link.created"
    DCF_VALUATION_STARTED = "valuation.dcf.started"
    DCF_VALUATION_COMPLETED = "valuation.dcf.completed"
    SENSITIVITY_COMPLETED = "valuation.sensitivity.completed"
    RISK_FINDING_REGISTERED = "risk.finding.registered"
    UNDERWRITING_MEMO_GENERATED = "memo.underwriting.generated"
    IC_DECISION_RECORDED = "ic.decision.recorded"
    AGENT_ERROR_ENCOUNTERED = "agent.error.encountered"


class EventPriority(str, Enum):
    """Urgency level governing event queue dispatch order."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SwarmEvent(BaseModel):
    """Immutable event payload propagated across the swarm messaging bus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(default_factory=generate_uuid, description="Unique event identifier")
    event_type: Union[EventType, str] = Field(..., description="Categorical event topic")
    deal_id: str = Field(..., description="Subject property deal identifier")
    correlation_id: str = Field(
        default_factory=generate_uuid, description="Distributed tracing correlation key"
    )
    source_role: str = Field(..., description="Agent role or subsystem emitting event")
    target_role: Optional[str] = Field(
        default=None, description="Specific target agent role if unicast, or None for broadcast"
    )
    priority: EventPriority = Field(
        default=EventPriority.NORMAL, description="Dispatch priority level"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Structured event payload data"
    )
    errors: List[str] = Field(
        default_factory=list, description="Diagnostic error stack traces if applicable"
    )
    timestamp: Any = Field(default_factory=utc_now, description="Event emission UTC timestamp")
