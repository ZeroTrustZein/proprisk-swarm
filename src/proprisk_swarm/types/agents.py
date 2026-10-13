"""Domain models for multi-agent swarm roles, task dispatch, and audit trails."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from proprisk_swarm.types.base import BaseEntity, generate_uuid, utc_now


class AgentRole(str, Enum):
    """Specialized underwriting swarm agent designations."""

    SWARM_ORCHESTRATOR = "swarm_orchestrator"
    INGESTION_COORDINATOR = "ingestion_coordinator"
    MUNICIPAL_DEED_AUDITOR = "municipal_deed_auditor"
    SEC_DILIGENCE_ANALYST = "sec_diligence_analyst"
    MEMORANDUM_RAG_SYNTHESIZER = "memorandum_rag_synthesizer"
    DCF_VALUATION_ENGINEER = "dcf_valuation_engineer"
    CREDIT_RISK_UNDERWRITER = "credit_risk_underwriter"
    INVESTMENT_COMMITTEE_CHAIR = "investment_committee_chair"
    ZONING_LAND_USE_COMPLIANCE = "zoning_land_use_compliance"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_norm = value.lower()
            for member in cls:
                if member.value.lower() == val_norm or member.name.lower() == val_norm:
                    return member
        return None


class AgentState(str, Enum):
    """Real-time lifecycle state of an individual agent worker."""

    IDLE = "idle"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ERROR = "error"


class TaskStatus(str, Enum):
    """Execution status of an assigned agent task."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentTask(BaseEntity):
    """Unit of analytical diligence assigned to an agent."""

    role: AgentRole = Field(..., description="Designated agent role responsible")
    deal_id: str = Field(..., description="Subject property deal identifier")
    description: str = Field(..., min_length=5, description="Specific objective of this analysis")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current execution state")
    input_artifacts: Dict[str, Any] = Field(
        default_factory=dict, description="References to deeds, chunks, parameters"
    )
    output_artifacts: Dict[str, Any] = Field(
        default_factory=dict, description="Generated models, memos, risk findings"
    )
    error_message: Optional[str] = Field(
        default=None, description="Failure reason if status is FAILED"
    )
    execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Processing runtime in milliseconds"
    )


class AgentMessage(BaseModel):
    """Inter-agent communications exchanged over the swarm protocol."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    message_id: str = Field(default_factory=generate_uuid, description="Unique message ID")
    sender_role: AgentRole = Field(..., description="Originating agent")
    recipient_role: Optional[AgentRole] = Field(
        default=None, description="Destination agent role, or None for swarm multicast"
    )
    deal_id: str = Field(..., description="Deal context identifier")
    message_text: str = Field(..., min_length=1, description="Message body or query")
    attachments: Dict[str, Any] = Field(
        default_factory=dict, description="Structured artifact payloads"
    )
    timestamp: Any = Field(default_factory=utc_now, description="Dispatch UTC timestamp")


class AgentAuditEntry(BaseModel):
    """Cryptographic-style provenance log of every autonomous decision."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    entry_id: str = Field(default_factory=generate_uuid, description="Unique audit log entry ID")
    task_id: str = Field(..., description="Associated AgentTask ID")
    role: AgentRole = Field(..., description="Executing agent role")
    action_taken: str = Field(
        ..., min_length=3, description="Specific decision or model calculation performed"
    )
    justification: str = Field(
        ..., min_length=5, description="Rationale, mathematical formula, or source citation"
    )
    input_hash: str = Field(..., description="SHA256 or digest of the inputs consumed")
    output_summary: str = Field(..., description="Brief summary of outputs produced")
    timestamp: Any = Field(default_factory=utc_now, description="Event log timestamp")


class SwarmWorkflowState(BaseEntity):
    """Top-level execution state of the multi-agent diligence pipeline for a deal."""

    deal_id: str = Field(..., description="Subject property deal identifier")
    active_role: Optional[AgentRole] = Field(default=None, description="Currently executing role")
    completed_roles: List[AgentRole] = Field(
        default_factory=list, description="Roles that have signed off on their diligence stages"
    )
    tasks: List[AgentTask] = Field(default_factory=list, description="All assigned tasks")
    audit_trail: List[AgentAuditEntry] = Field(
        default_factory=list, description="Immutable audit log"
    )
    is_terminal: bool = Field(
        default=False, description="Whether workflow reached IC decision or terminal failure"
    )
    final_memo_id: Optional[str] = Field(default=None, description="Generated UnderwritingMemo ID")

