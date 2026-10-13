"""Domain models for municipal deeds, SEC EDGAR filings, and OM document ingestion."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from proprisk_swarm.types.base import BaseEntity


class IngestionSourceType(str, Enum):
    """Origin of ingested real estate intelligence."""

    MUNICIPAL_DEED = "municipal_deed"
    SEC_EDGAR = "sec_edgar"
    OFFERING_MEMORANDUM = "offering_memorandum"
    TITLE_REPORT = "title_report"
    ENVIRONMENTAL_ESA = "environmental_esa"
    RENT_ROLL = "rent_roll"


class IngestionStatus(str, Enum):
    """State of an asynchronous ingestion pipeline job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class DeedType(str, Enum):
    """Legal classifications of recorded property deeds."""

    SPECIAL_WARRANTY_DEED = "special_warranty_deed"
    GENERAL_WARRANTY_DEED = "general_warranty_deed"
    QUITCLAIM_DEED = "quitclaim_deed"
    TRUSTEES_DEED = "trustees_deed"
    GRANT_DEED = "grant_deed"
    FORECLOSURE_DEED = "foreclosure_deed"


class DeedRecord(BaseEntity):
    """Recorded municipal conveyance deed from county recorder MCP ingestion."""

    parcel_number: str = Field(..., min_length=3, description="Assessor parcel number (APN)")
    document_number: str = Field(
        ..., min_length=1, description="Official county instrument / book & page"
    )
    recording_date: date = Field(..., description="Date document was officially recorded")
    deed_type: DeedType = Field(
        default=DeedType.SPECIAL_WARRANTY_DEED, description="Deed legal structure"
    )
    grantor: str = Field(..., min_length=2, description="Selling or conveying entity")
    grantee: str = Field(..., min_length=2, description="Purchasing or acquiring entity")
    consideration_amount: float = Field(
        ..., ge=0.0, description="Recorded transaction dollar amount"
    )
    transfer_tax: float = Field(
        default=0.0, ge=0.0, description="Documentary transfer tax assessed"
    )
    legal_description: str = Field(
        ..., min_length=5, description="Metes and bounds or subdivision lot parcel text"
    )
    county_name: str = Field(..., min_length=2, description="Jurisdiction of recordation")
    source_url: Optional[str] = Field(default=None, description="Direct URL or archive URI")
    verified: bool = Field(
        default=False, description="Whether record has cross-validated title hash"
    )


class SECFilingType(str, Enum):
    """SEC EDGAR reporting form types relevant to sponsor/tenant diligence."""

    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_S11 = "S-11"
    FORM_DEF14A = "DEF 14A"


class SECRiskTopic(str, Enum):
    """Extracted risk categories from SEC disclosure analysis."""

    TENANT_CONCENTRATION = "tenant_concentration"
    LITIGATION = "litigation"
    REFINANCING_RISK = "refinancing_risk"
    LEASE_TERMINATION = "lease_termination"
    ENVIRONMENTAL_LIABILITY = "environmental_liability"
    LIQUIDITY_GOING_CONCERN = "liquidity_going_concern"


class SECRiskMention(BaseModel):
    """Specific risk extraction from an SEC EDGAR filing."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: SECRiskTopic = Field(..., description="Classified risk domain")
    excerpt: str = Field(..., min_length=10, description="Raw quoted excerpt from filing")
    item_section: str = Field(..., description="Filing section (e.g. 'Item 1A. Risk Factors')")
    severity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized risk severity rating"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Correlation to subject property/sponsor"
    )


class SECFiling(BaseEntity):
    """Ingested SEC filing for sponsor or anchor tenant credit scrutiny."""

    accession_number: str = Field(
        ..., min_length=10, description="SEC EDGAR unique accession number"
    )
    cik: str = Field(..., min_length=10, max_length=10, description="Central Index Key (10 digits)")
    company_name: str = Field(..., min_length=2, description="Entity reporting to the SEC")
    form_type: SECFilingType = Field(..., description="Regulatory disclosure form")
    filing_date: date = Field(..., description="Public filing acceptance date")
    period_end_date: Optional[date] = Field(
        default=None, description="Fiscal report period closing date"
    )
    report_url: Optional[str] = Field(default=None, description="EDGAR HTML/TXT document endpoint")
    risk_mentions: List[SECRiskMention] = Field(
        default_factory=list, description="Extracted credit and diligence risk flags"
    )

    @field_validator("cik", mode="before")
    @classmethod
    def validate_cik(cls, v: Any) -> str:
        """Validate that CIK is zero-padded 10 digits."""
        if not isinstance(v, str):
            v = str(v)
        stripped = v.strip()
        if not stripped.isdigit():
            raise ValueError(f"CIK must contain digits only: {v}")
        if len(stripped) > 10:
            raise ValueError(f"CIK cannot exceed 10 digits: {v}")
        return stripped.zfill(10)


class DocumentChunk(BaseEntity):
    """Text chunk from offering memorandum or report for hybrid RAG."""

    document_id: str = Field(..., description="Parent document identifier")
    source_type: IngestionSourceType = Field(..., description="Ingestion source classifier")
    chunk_index: int = Field(..., ge=0, description="Ordinal index within document")
    page_number: int = Field(..., ge=1, description="Source page number")
    text_content: str = Field(..., min_length=1, description="Segment text content")
    token_count: int = Field(..., ge=0, description="Estimated or exact token count")
    embedding: Optional[List[float]] = Field(
        default=None, description="Dense vector embedding representation"
    )


class OfferingMemorandum(BaseEntity):
    """Broker Offering Memorandum (OM) ingested for hybrid vector-graph diligence."""

    deal_id: str = Field(..., description="Associated target deal identifier")
    filename: str = Field(..., min_length=1, description="Original uploaded filename")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    file_hash: str = Field(..., min_length=8, description="SHA256 content verification hash")
    page_count: int = Field(..., ge=1, description="Total document pages")
    brokerage_firm: Optional[str] = Field(default=None, description="Listing broker agency")
    publication_date: Optional[date] = Field(default=None, description="Offering publication date")
    claimed_asking_price: Optional[float] = Field(
        default=None, ge=0.0, description="OM listed price"
    )
    claimed_pro_forma_noi: Optional[float] = Field(
        default=None, description="OM projected Net Operating Income"
    )
    claimed_cap_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Broker advertised cap rate"
    )
    claimed_occupancy: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Broker claimed occupancy"
    )
    executive_summary: Optional[str] = Field(
        default=None, description="Synthesized property investment thesis"
    )
    chunks: List[DocumentChunk] = Field(
        default_factory=list, description="Extracted and embedded text passages"
    )


class IngestionJob(BaseEntity):
    """Audit record of an autonomous ingestion batch or task."""

    source_type: IngestionSourceType = Field(..., description="Target source category")
    status: IngestionStatus = Field(
        default=IngestionStatus.PENDING, description="Current batch state"
    )
    source_uri: str = Field(..., description="Source location, query parameter, or file path")
    items_ingested: int = Field(default=0, ge=0, description="Total entities or records produced")
    errors: List[str] = Field(
        default_factory=list, description="Failures and exceptions recorded during run"
    )
    started_at: Optional[datetime] = Field(default=None, description="Job execution start time")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion time")

