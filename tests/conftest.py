"""Pytest fixtures for PropRisk Swarm testing."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional

import pytest
from click.testing import CliRunner

from proprisk_swarm.config import PropRiskSettings
from proprisk_swarm.types.agents import (
    AgentRole,
)
from proprisk_swarm.types.events import (
    EventPriority,
    EventType,
    SwarmEvent,
)
from proprisk_swarm.types.financial import (
    AnnualCashFlow,
    DCFParameters,
    DCFValuationResult,
    FinancingAssumptions,
    LoanType,
    SensitivityMatrix,
    SensitivityScenario,
    ValuationMetrics,
)
from proprisk_swarm.types.ingestion import (
    DeedRecord,
    DeedType,
    DocumentChunk,
    IngestionSourceType,
    OfferingMemorandum,
    SECFiling,
    SECFilingType,
    SECRiskMention,
    SECRiskTopic,
)
from proprisk_swarm.types.knowledge_graph import (
    EntityType,
    GraphEntity,
    GraphRelation,
    KnowledgeGraph,
    RelationType,
)
from proprisk_swarm.types.property import (
    DealStatus,
    HistoricalFinancials,
    OperatingExpenses,
    PropertyAddress,
    PropertyDeal,
    PropertyPhysical,
    PropertyType,
    UnitMix,
    UnitSpec,
)
from proprisk_swarm.types.risk import (
    ChecklistStatus,
    DiligenceChecklistItem,
    MemoRecommendation,
    RiskCategory,
    RiskFinding,
    RiskSeverity,
    SignOff,
    StressScenario,
    UnderwritingMemo,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Fixture providing Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def default_settings() -> PropRiskSettings:
    """Fixture providing fresh default settings."""
    return PropRiskSettings()


class MockAgent:
    """Mock implementation of AgentProtocol."""

    def __init__(self, agent_id: str = "agent-001", role: str = "deed-auditor") -> None:
        self._id = agent_id
        self._role = role

    @property
    def agent_id(self) -> str:
        return self._id

    @property
    def role_name(self) -> str:
        return self._role

    def execute_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "result": f"Executed by {self._role}"}

    def can_handle(self, task_type: str) -> bool:
        return task_type == "deed_audit"


class MockMCPServer:
    """Mock implementation of MCPServerProtocol."""

    def __init__(self, server_name: str = "deeds-mcp") -> None:
        self._name = server_name

    @property
    def server_name(self) -> str:
        return self._name

    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": "fetch_deed", "description": "Fetch deed by parcel number"}]

    def list_resources(self) -> List[Dict[str, Any]]:
        return [{"uri": "mcp://deeds/parcels", "name": "Parcel Registry"}]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"tool": name, "result": "mock_record"}


class MockIngestionPipeline:
    """Mock implementation of IngestionPipelineProtocol."""

    def ingest_document(
        self, source_path: str, source_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        return "job-uuid-12345"

    def parse_payload(self, raw_data: bytes, document_type: str) -> Dict[str, Any]:
        return {"doc_type": document_type, "size": len(raw_data)}


class MockGraphRAG:
    """Mock implementation of GraphRAGProtocol."""

    def index_document(
        self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        return len(content.split())

    def query_with_citations(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        return {"query": query, "citations": ["doc-1#p4"], "answer": "Grounded answer."}

    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        return [{"entity_id": "sponsor-01", "relation": "OWNS"}]


class MockValuationEngine:
    """Mock implementation of ValuationEngineProtocol."""

    def compute_dcf(
        self,
        purchase_price: float,
        cash_flows: List[float],
        discount_rate: float,
        terminal_cap_rate: float,
    ) -> Dict[str, Any]:
        return {
            "npv": sum(cash_flows) - purchase_price,
            "levered_irr": 0.165,
            "equity_multiple": 1.95,
        }

    def synthesize_investment_memo(
        self, deal_id: str, valuation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"deal_id": deal_id, "recommendation": "BUY"}


class MockEventBus:
    """Mock implementation of EventBusProtocol."""

    def __init__(self) -> None:
        self.published: List[tuple[str, Dict[str, Any]]] = []
        self.handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.published.append((event_type, payload))
        for handler in self.handlers.get(event_type, []):
            handler(payload)

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.handlers.setdefault(event_type, []).append(handler)


@pytest.fixture
def mock_agent() -> MockAgent:
    return MockAgent()


@pytest.fixture
def mock_mcp_server() -> MockMCPServer:
    return MockMCPServer()


@pytest.fixture
def mock_ingestion_pipeline() -> MockIngestionPipeline:
    return MockIngestionPipeline()


@pytest.fixture
def mock_graph_rag() -> MockGraphRAG:
    return MockGraphRAG()


@pytest.fixture
def mock_valuation_engine() -> MockValuationEngine:
    return MockValuationEngine()


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    return MockEventBus()


# -------------------------------------------------------------------------
# Domain Model Fixtures
# -------------------------------------------------------------------------


@pytest.fixture
def sample_address() -> PropertyAddress:
    """Standard property address."""
    return PropertyAddress(
        street="401 Congress Ave",
        unit_or_suite="Suite 1500",
        city="Austin",
        state="tx",
        postal_code="78701",
        county="Travis",
        apn="01-0203-0405-0000",
        latitude=30.2672,
        longitude=-97.7431,
    )


@pytest.fixture
def sample_unit_mix() -> UnitMix:
    """Multifamily 100-unit mix."""
    return UnitMix(
        items=[
            UnitSpec(
                unit_type="1B/1B",
                count=60,
                square_feet=750.0,
                in_place_rent=1600.0,
                market_rent=1800.0,
                vacant_units=3,
            ),
            UnitSpec(
                unit_type="2B/2B",
                count=40,
                square_feet=1100.0,
                in_place_rent=2200.0,
                market_rent=2450.0,
                vacant_units=2,
            ),
        ]
    )


@pytest.fixture
def sample_physical() -> PropertyPhysical:
    """Building physical specifications."""
    return PropertyPhysical(
        gross_square_feet=95000.0,
        rentable_square_feet=89000.0,
        year_built=2018,
        year_renovated=2023,
        site_area_acres=2.5,
        stories=5,
        parking_spaces=120,
        zoning_code="CBD-MF",
        flood_zone="X",
    )


@pytest.fixture
def sample_operating_expenses() -> OperatingExpenses:
    """Detailed annual opex schedule."""
    return OperatingExpenses(
        property_taxes=280000.0,
        insurance=95000.0,
        utilities=110000.0,
        repairs_maintenance=85000.0,
        management_fees=75000.0,
        payroll=130000.0,
        marketing_leasing=25000.0,
        general_admin=35000.0,
        capex_reserve=35000.0,
    )


@pytest.fixture
def sample_historical_financials(
    sample_operating_expenses: OperatingExpenses,
) -> HistoricalFinancials:
    """T12 historical performance."""
    return HistoricalFinancials(
        period_label="T12",
        gross_potential_rent=2200000.0,
        vacancy_credit_loss=110000.0,
        concessions=25000.0,
        other_income=85000.0,
        expenses=sample_operating_expenses,
    )


@pytest.fixture
def sample_deal(
    sample_address: PropertyAddress,
    sample_physical: PropertyPhysical,
    sample_unit_mix: UnitMix,
    sample_historical_financials: HistoricalFinancials,
) -> PropertyDeal:
    """Complete subject CRE deal record."""
    return PropertyDeal(
        id="deal-atx-001",
        title="The Travis Ridge Residences",
        property_type=PropertyType.MULTIFAMILY,
        status=DealStatus.UNDERWRITING,
        address=sample_address,
        physical=sample_physical,
        unit_mix=sample_unit_mix,
        asking_price=26000000.0,
        target_purchase_price=24500000.0,
        in_place_noi=1280000.0,
        sponsor_name="Apex Capital Partners",
        broker_name="Eastdil Secured",
        target_closing_date=date(2026, 11, 15),
        historical_financials=[sample_historical_financials],
    )


@pytest.fixture
def sample_deed() -> DeedRecord:
    """Sample municipal recorded conveyance deed."""
    return DeedRecord(
        parcel_number="01-0203-0405-0000",
        document_number="DOC-2022-0987654",
        recording_date=date(2022, 6, 15),
        deed_type=DeedType.SPECIAL_WARRANTY_DEED,
        grantor="Hill Country Holdings LP",
        grantee="Apex Capital Partners LLC",
        consideration_amount=21500000.0,
        transfer_tax=21500.0,
        legal_description="Lot 4, Block B, Austin Downtown Subdivision No. 2",
        county_name="Travis",
        source_url="https://recorder.traviscountytx.gov/deed/DOC-2022-0987654",
        verified=True,
    )


@pytest.fixture
def sample_sec_filing() -> SECFiling:
    """Sample SEC 10-K filing."""
    return SECFiling(
        accession_number="0001234567-26-000012",
        cik="0001234567",
        company_name="Apex REIT Management Corp",
        form_type=SECFilingType.FORM_10K,
        filing_date=date(2026, 3, 1),
        period_end_date=date(2025, 12, 31),
        report_url="https://www.sec.gov/edgar/data/1234567/000123456726000012.txt",
        risk_mentions=[
            SECRiskMention(
                topic=SECRiskTopic.REFINANCING_RISK,
                excerpt="The company holds $45M of floating debt subject to SOFR reset in Q4 2026.",
                item_section="Item 1A. Risk Factors",
                severity_score=0.75,
                relevance_score=0.88,
            )
        ],
    )


@pytest.fixture
def sample_document_chunk() -> DocumentChunk:
    """Sample embedded document chunk from offering memorandum."""
    return DocumentChunk(
        document_id="om-travis-001",
        source_type=IngestionSourceType.OFFERING_MEMORANDUM,
        chunk_index=3,
        page_number=12,
        text_content="Travis Ridge features a 100-unit mix with strong loss-to-lease recapture opportunity.",
        token_count=18,
        embedding=[0.012, -0.045, 0.089, 0.033],
    )


@pytest.fixture
def sample_offering_memorandum(sample_document_chunk: DocumentChunk) -> OfferingMemorandum:
    """Sample broker offering memorandum."""
    return OfferingMemorandum(
        deal_id="deal-atx-001",
        filename="Travis_Ridge_OM_Confidential.pdf",
        file_size_bytes=14502800,
        file_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        page_count=48,
        brokerage_firm="Eastdil Secured",
        publication_date=date(2026, 8, 1),
        claimed_asking_price=26000000.0,
        claimed_pro_forma_noi=1420000.0,
        claimed_cap_rate=0.0546,
        claimed_occupancy=0.95,
        executive_summary="Premier Class A multifamily community in Austin core.",
        chunks=[sample_document_chunk],
    )


@pytest.fixture
def sample_knowledge_graph() -> KnowledgeGraph:
    """Sample interconnected diligence knowledge graph."""
    kg = KnowledgeGraph()
    p = GraphEntity(
        entity_id="prop-001",
        entity_type=EntityType.PROPERTY,
        label="The Travis Ridge Residences",
        properties={"apn": "01-0203-0405-0000"},
    )
    s = GraphEntity(
        entity_id="spon-001",
        entity_type=EntityType.SPONSOR,
        label="Apex Capital Partners",
        properties={"cik": "0001234567"},
    )
    lender = GraphEntity(
        entity_id="lend-001",
        entity_type=EntityType.LENDER,
        label="MetLife Real Estate Debt",
        properties={"facility_type": "Senior Mortgage"},
    )
    kg.add_entity(p)
    kg.add_entity(s)
    kg.add_entity(lender)

    kg.add_relation(
        GraphRelation(
            source_id="spon-001",
            target_id="prop-001",
            relation_type=RelationType.OWNS,
            weight=1.0,
        )
    )
    kg.add_relation(
        GraphRelation(
            source_id="lend-001",
            target_id="prop-001",
            relation_type=RelationType.ENCUMBERS,
            weight=0.95,
            properties={"original_lien_amount": 16000000.0},
        )
    )
    return kg


@pytest.fixture
def sample_financing() -> FinancingAssumptions:
    """Sample senior acquisition financing."""
    return FinancingAssumptions(
        loan_amount=15925000.0,
        loan_type=LoanType.FIXED_RATE,
        interest_rate=0.0625,
        term_years=7,
        amortization_years=30,
        interest_only_years=2,
        origination_fee_pct=0.01,
        exit_fee_pct=0.005,
        min_dscr_covenant=1.25,
        max_ltv_covenant=0.65,
    )


@pytest.fixture
def sample_dcf_params() -> DCFParameters:
    """Sample underwriting parameters."""
    return DCFParameters(
        holding_period_years=5,
        exit_cap_rate=0.0575,
        discount_rate=0.09,
        annual_rent_growth=0.03,
        annual_opex_growth=0.025,
        general_inflation_rate=0.025,
        disposition_cost_pct=0.015,
    )


@pytest.fixture
def sample_valuation_metrics() -> ValuationMetrics:
    """Sample return metrics output."""
    return ValuationMetrics(
        purchase_price=24500000.0,
        equity_invested=8950000.0,
        unlevered_irr=0.114,
        levered_irr=0.168,
        equity_multiple=2.12,
        net_present_value=3250000.0,
        in_place_cap_rate=0.0522,
        exit_cap_rate=0.0575,
        gross_exit_sales_price=29800000.0,
        net_sales_proceeds=13900000.0,
        total_net_profit=10034000.0,
        min_dscr_observed=1.31,
        average_dscr=1.44,
    )


@pytest.fixture
def sample_dcf_result(
    sample_dcf_params: DCFParameters,
    sample_financing: FinancingAssumptions,
    sample_valuation_metrics: ValuationMetrics,
) -> DCFValuationResult:
    """Sample audit-ready DCF valuation result artifact."""
    cash_flows = [
        AnnualCashFlow(
            year=1,
            potential_gross_revenue=2300000.0,
            vacancy_and_credit_loss=115000.0,
            effective_gross_income=2185000.0,
            operating_expenses=870000.0,
            net_operating_income=1315000.0,
            capex_reserves=35000.0,
            debt_service=995312.5,
            unlevered_cash_flow=1280000.0,
            levered_cash_flow=284687.5,
            ending_loan_balance=15925000.0,
            dscr=1.32,
            debt_yield=0.0825,
        )
    ]
    sensitivity = SensitivityMatrix(
        base_levered_irr=0.168,
        base_equity_multiple=2.12,
        scenarios=[
            SensitivityScenario(
                rent_growth_delta_bps=-50,
                exit_cap_delta_bps=25,
                levered_irr=0.142,
                equity_multiple=1.89,
                net_present_value=2100000.0,
            )
        ],
    )
    return DCFValuationResult(
        deal_id="deal-atx-001",
        parameters=sample_dcf_params,
        financing=sample_financing,
        annual_cash_flows=cash_flows,
        metrics=sample_valuation_metrics,
        sensitivity=sensitivity,
        model_checksum="sha256:d8a9f029348b0a1d",
    )


@pytest.fixture
def sample_risk_findings() -> List[RiskFinding]:
    """Sample identified diligence risks."""
    return [
        RiskFinding(
            category=RiskCategory.TITLE_AND_LEGAL,
            severity=RiskSeverity.MEDIUM,
            title="Utility Easement Encroachment",
            description="Municipal water line easement runs within 10 feet of Building 3 foundation.",
            evidence_citation="Deed DOC-2022-0987654 Schedule B-II",
            impact_summary="Minor title exception, requires title policy endorsement.",
            proposed_mitigation="Obtain ALTA 9 comprehensive title endorsement.",
            confirmed_by_role=AgentRole.MUNICIPAL_DEED_AUDITOR,
        ),
        RiskFinding(
            category=RiskCategory.REFINANCING_DEBT,
            severity=RiskSeverity.HIGH,
            title="Sponsor SOFR Floating Debt Exposure",
            description="Parent entity faces $45M SOFR reset in Q4 2026 across sister assets.",
            evidence_citation="SEC Form 10-K Accession 0001234567-26-000012 Item 1A",
            impact_summary="Potential liquidity draw at sponsor balance sheet level.",
            proposed_mitigation="Require ring-fenced single-purpose entity (SPE) with warm-body guarantor carve-outs.",
            confirmed_by_role=AgentRole.SEC_DILIGENCE_ANALYST,
        ),
    ]


@pytest.fixture
def sample_memo(
    sample_valuation_metrics: ValuationMetrics, sample_risk_findings: List[RiskFinding]
) -> UnderwritingMemo:
    """Sample completed investment committee memorandum."""
    return UnderwritingMemo(
        deal_id="deal-atx-001",
        deal_title="The Travis Ridge Residences",
        executive_summary="Recommendation to acquire Travis Ridge at $24.5M basis (5.22% in-place cap rate, 16.8% levered IRR).",
        recommendation=MemoRecommendation.APPROVE_WITH_CONDITIONS,
        valuation_summary=sample_valuation_metrics,
        risk_findings=sample_risk_findings,
        diligence_checklist=[
            DiligenceChecklistItem(
                category=RiskCategory.TITLE_AND_LEGAL,
                requirement="Clean chain of title from last arm's length sale",
                status=ChecklistStatus.PASS,
                comments="Grantor matches recorded deed",
                citation_reference="DOC-2022-0987654",
            )
        ],
        stress_scenarios=[
            StressScenario(
                name="Severe Stagflation",
                rent_shock_pct=-0.05,
                vacancy_shock_pct=0.05,
                opex_shock_pct=0.08,
                exit_cap_expansion_bps=50,
                resultant_irr=0.118,
                min_dscr_observed=1.19,
                covenant_breached=False,
            )
        ],
        conditions_precedent=[
            "Receipt of clean Phase I ESA with no Recognized Environmental Conditions (RECs)",
            "ALTA title policy endorsement without standard survey exceptions",
        ],
        sign_offs=[
            SignOff(
                role=AgentRole.INVESTMENT_COMMITTEE_CHAIR,
                recommendation=MemoRecommendation.APPROVE_WITH_CONDITIONS,
                rationale="Compelling core-plus risk/return profile meeting target IRR hurdles.",
            )
        ],
    )


@pytest.fixture
def sample_swarm_event() -> SwarmEvent:
    """Sample dispatch event."""
    return SwarmEvent(
        event_type=EventType.DEED_AUDIT_COMPLETED,
        deal_id="deal-atx-001",
        source_role=AgentRole.MUNICIPAL_DEED_AUDITOR.value,
        target_role=AgentRole.CREDIT_RISK_UNDERWRITER.value,
        priority=EventPriority.NORMAL,
        payload={"verified": True, "encumbrances_found": 1},
    )

