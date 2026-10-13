"""Domain models for risk assessment, diligence checklists, and investment committee memos."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from proprisk_swarm.types.agents import AgentRole
from proprisk_swarm.types.base import BaseEntity, generate_uuid, utc_now
from proprisk_swarm.types.financial import ValuationMetrics


class RiskCategory(str, Enum):
    """Categorical classification of CRE deal risks."""

    TITLE_AND_LEGAL = "title_and_legal"
    TENANT_CREDIT = "tenant_credit"
    PHYSICAL_ENVIRONMENTAL = "physical_environmental"
    ENVIRONMENTAL = "environmental"
    ZONING_AND_LAND_USE = "zoning_and_land_use"
    MARKET_MACRO = "market_macro"
    REFINANCING_DEBT = "refinancing_debt"
    OPERATIONAL_EXPENSE = "operational_expense"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_norm = value.lower()
            for member in cls:
                if member.value.lower() == val_norm or member.name.lower() == val_norm:
                    return member
        return None


class RiskSeverity(str, Enum):
    """Risk severity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_norm = value.lower()
            for member in cls:
                if member.value.lower() == val_norm or member.name.lower() == val_norm:
                    return member
        return None


class RiskFinding(BaseModel):
    """Specific diligence anomaly or flagged vulnerability."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    finding_id: str = Field(
        default_factory=generate_uuid, description="Unique risk finding identifier"
    )
    category: RiskCategory = Field(..., description="Subject risk domain")
    severity: RiskSeverity = Field(..., description="Assessed impact severity")
    title: str = Field(..., min_length=3, description="Concise risk header")
    description: str = Field(..., min_length=10, description="Detailed explanation of finding")
    evidence_citation: str = Field(
        ..., min_length=5, description="Filing excerpt, deed record, or OM chunk citation"
    )
    impact_summary: str = Field(..., description="Anticipated economic or legal downside")
    proposed_mitigation: Optional[str] = Field(
        default=None, description="Proposed covenant or escrow remedy"
    )
    confirmed_by_role: AgentRole = Field(..., description="Agent role verifying the risk")


class ChecklistStatus(str, Enum):
    """Diligence compliance verification state."""

    PASS = "pass"
    FAIL = "fail"
    REQUIRES_REVIEW = "requires_review"
    WAIVED = "waived"


class DiligenceChecklistItem(BaseModel):
    """Itemized diligence compliance item."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    item_id: str = Field(default_factory=generate_uuid, description="Item identifier")
    category: RiskCategory = Field(..., description="Category group")
    requirement: str = Field(..., min_length=5, description="Required diligence standard")
    status: ChecklistStatus = Field(
        default=ChecklistStatus.REQUIRES_REVIEW, description="Compliance status"
    )
    comments: Optional[str] = Field(default=None, description="Agent notes or explanation")
    citation_reference: Optional[str] = Field(default=None, description="Document verification key")


class StressScenario(BaseModel):
    """Downside underwriting scenario test."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str = Field(..., min_length=3, description="Scenario label (e.g. 'Stagflation Shock')")
    rent_shock_pct: float = Field(
        default=0.0, description="Gross rent haircut percentage (-0.10 is -10%)"
    )
    noi_shock_pct: float = Field(default=0.0, description="Net operating income haircut percentage")
    vacancy_shock_pct: float = Field(default=0.0, ge=0.0, description="Additional vacancy surge")
    opex_shock_pct: float = Field(default=0.0, ge=0.0, description="Operational expense increase")
    exit_cap_expansion_bps: int = Field(
        default=0, ge=0, description="Terminal cap expansion in basis points"
    )
    cap_rate_expansion_bps: int = Field(
        default=0, ge=0, description="Cap rate expansion in basis points"
    )
    resultant_irr: float = Field(..., description="Downside levered IRR")
    min_dscr_observed: float = Field(default=0.0, ge=0.0, description="Lowest DSCR under stress")
    resultant_dscr: float = Field(default=0.0, ge=0.0, description="Downside resultant DSCR")
    covenant_breached: bool = Field(
        default=False, description="Whether lender DSCR/LTV covenants fail"
    )

    @model_validator(mode="before")
    @classmethod
    def _sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "resultant_dscr" in data and "min_dscr_observed" not in data:
                data["min_dscr_observed"] = data["resultant_dscr"]
            elif "min_dscr_observed" in data and "resultant_dscr" not in data:
                data["resultant_dscr"] = data["min_dscr_observed"]

            if "cap_rate_expansion_bps" in data and "exit_cap_expansion_bps" not in data:
                data["exit_cap_expansion_bps"] = data["cap_rate_expansion_bps"]
            elif "exit_cap_expansion_bps" in data and "cap_rate_expansion_bps" not in data:
                data["cap_rate_expansion_bps"] = data["exit_cap_expansion_bps"]

            if "noi_shock_pct" in data and "rent_shock_pct" not in data:
                data["rent_shock_pct"] = data["noi_shock_pct"]
            elif "rent_shock_pct" in data and "noi_shock_pct" not in data:
                data["noi_shock_pct"] = data["rent_shock_pct"]
        return data


class MemoRecommendation(str, Enum):
    """Investment Committee final recommendation action."""

    STRONGLY_RECOMMEND = "strongly_recommend"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REVISE_TERMS = "revise_terms"
    REJECT = "reject"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_norm = value.lower()
            for member in cls:
                if member.value.lower() == val_norm or member.name.lower() == val_norm:
                    return member
        return None


class SignOff(BaseModel):
    """Formal sign-off by an underwriting swarm agent."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    role: Union[AgentRole, str] = Field(..., description="Voting agent role")
    recommendation: Union[MemoRecommendation, str] = Field(..., description="Agent vote")
    rationale: str = Field(..., min_length=5, description="Sign-off explanation")
    timestamp: Any = Field(default_factory=utc_now, description="Sign-off timestamp")


class UnderwritingMemo(BaseEntity):
    """Audit-ready Investment Committee Memorandum synthesizing all diligence."""

    deal_id: str = Field(..., description="Subject property deal identifier")
    deal_title: str = Field(..., min_length=3, description="Deal title")
    executive_summary: str = Field(..., min_length=20, description="Executive narrative and thesis")
    recommendation: MemoRecommendation = Field(..., description="Swarm consensus recommendation")
    valuation_summary: ValuationMetrics = Field(
        ..., description="Key financial underwriting numbers"
    )
    risk_findings: List[RiskFinding] = Field(default_factory=list, description="All flagged risks")
    diligence_checklist: List[DiligenceChecklistItem] = Field(
        default_factory=list, description="Itemized compliance findings"
    )
    stress_scenarios: List[StressScenario] = Field(
        default_factory=list, description="Downside stress test results"
    )
    conditions_precedent: List[str] = Field(
        default_factory=list, description="Required terms before closing"
    )
    sign_offs: List[SignOff] = Field(
        default_factory=list, description="Autonomous agent committee votes"
    )
