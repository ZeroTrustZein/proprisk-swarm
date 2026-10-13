"""Comprehensive test suite for PropRisk Swarm domain models and types."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from proprisk_swarm.types import (
    AgentAuditEntry,
    AgentMessage,
    AgentRole,
    AgentTask,
    AnnualCashFlow,
    BaseEntity,
    ChecklistStatus,
    DCFParameters,
    DCFValuationResult,
    DealStatus,
    DeedRecord,
    DeedType,
    DiligenceChecklistItem,
    DocumentChunk,
    EntityType,
    EventPriority,
    EventType,
    FinancingAssumptions,
    GraphEntity,
    GraphRelation,
    HistoricalFinancials,
    IngestionJob,
    IngestionSourceType,
    IngestionStatus,
    KnowledgeGraph,
    LoanAmortizationRow,
    LoanType,
    MemoRecommendation,
    OfferingMemorandum,
    OperatingExpenses,
    PropertyAddress,
    PropertyDeal,
    PropertyPhysical,
    PropertyType,
    RelationType,
    RiskCategory,
    RiskFinding,
    RiskSeverity,
    SECFiling,
    SECFilingType,
    SECRiskMention,
    SECRiskTopic,
    SensitivityMatrix,
    SensitivityScenario,
    SignOff,
    StressScenario,
    SwarmEvent,
    SwarmWorkflowState,
    TaskStatus,
    UnderwritingMemo,
    UnitMix,
    UnitSpec,
    ValuationMetrics,
    generate_uuid,
    utc_now,
)


def test_base_entity():
    entity = BaseEntity()
    assert entity.id is not None
    assert isinstance(entity.created_at, datetime)
    old_updated = entity.updated_at
    entity.touch()
    assert entity.updated_at >= old_updated
    assert generate_uuid() != generate_uuid()
    assert utc_now().tzinfo == timezone.utc


def test_property_models():
    addr = PropertyAddress(
        street="100 Wall Street",
        city="New York",
        state="NY",
        postal_code="10005",
        county="New York",
        apn="APN-00123",
    )
    assert addr.state == "NY"
    assert "Wall Street" in addr.full_address

    with pytest.raises(ValidationError):
        PropertyAddress(
            street="100 Wall Street",
            city="New York",
            state="NEWYORK",  # invalid state length
            postal_code="10005",
            county="New York",
            apn="APN-00123",
        )

    phys = PropertyPhysical(
        gross_square_feet=50000.0,
        rentable_square_feet=45000.0,
        year_built=2015,
        stories=5,
        site_area_acres=1.5,
    )
    assert phys.gross_square_feet == 50000.0

    with pytest.raises(ValidationError):
        # rentable > gross
        PropertyPhysical(
            gross_square_feet=50000.0,
            rentable_square_feet=55000.0,
            year_built=2015,
            site_area_acres=1.5,
        )

    # UnitMix & UnitSpec
    unit = UnitSpec(
        unit_type="2BR",
        count=10,
        square_feet=950.0,
        in_place_rent=2500.0,
        market_rent=2700.0,
        vacant_units=1,
    )
    assert unit.occupied_units == 9
    assert unit.in_place_rent_psf == pytest.approx(2500.0 / 950.0)
    assert unit.market_rent_psf == pytest.approx(2700.0 / 950.0)
    assert unit.monthly_loss_to_lease == (2700.0 - 2500.0) * 9

    with pytest.raises(ValidationError):
        UnitSpec(
            unit_type="2BR",
            count=10,
            square_feet=950.0,
            in_place_rent=2500.0,
            vacant_units=12,  # > count
        )

    mix = UnitMix(items=[unit])
    assert mix.total_units == 10
    assert mix.total_vacant_units == 1
    assert mix.physical_occupancy_rate == 0.9
    assert mix.total_rentable_sqft == 9500.0
    assert mix.total_in_place_monthly_rent == 9 * 2500.0
    assert mix.total_market_monthly_rent == 10 * 2700.0
    assert mix.annual_in_place_rent == 9 * 2500.0 * 12.0
    assert mix.annual_market_rent == 10 * 2700.0 * 12.0
    assert mix.weighted_average_rent_psf == pytest.approx((9 * 2500.0) / 9500.0)

    # UnitMix empty validation and property methods
    mix_empty = UnitMix.model_construct(items=[])
    assert mix_empty.total_units == 0
    assert mix_empty.physical_occupancy_rate == 0.0
    assert mix_empty.weighted_average_rent_psf == 0.0

    # Physical validation errors
    with pytest.raises(ValidationError):
        PropertyPhysical(
            gross_square_feet=50000.0,
            rentable_square_feet=45000.0,
            year_built=2015,
            year_renovated=2010,  # renovated before built
            stories=5,
            site_area_acres=1.5,
        )

    # OperatingExpenses
    opex = OperatingExpenses(
        property_taxes=50000.0,
        insurance=15000.0,
        utilities=10000.0,
        repairs_maintenance=12000.0,
        management_fees=15000.0,
    )
    assert opex.total_opex == 50000.0 + 15000.0 + 10000.0 + 12000.0 + 15000.0
    assert opex.opex_ratio(200000.0) == opex.total_opex / 200000.0
    assert opex.opex_ratio(0.0) == 0.0

    # HistoricalFinancials
    hist = HistoricalFinancials(
        period_label="2024A",
        gross_potential_rent=500000.0,
        vacancy_credit_loss=25000.0,
        concessions=5000.0,
        other_income=10000.0,
        expenses=opex,
    )
    assert hist.effective_gross_income == 480000.0
    assert hist.net_operating_income == 480000.0 - opex.total_opex

    # PropertyDeal
    deal = PropertyDeal(
        title="Apex Tower",
        property_type=PropertyType.OFFICE,
        status=DealStatus.UNDERWRITING,
        address=addr,
        physical=phys,
        unit_mix=mix,
        asking_price=10000000.0,
        target_purchase_price=9500000.0,
        in_place_noi=600000.0,
        sponsor_name="Apex Holdings",
        historical_financials=[hist],
    )
    assert deal.asking_cap_rate == 600000.0 / 10000000.0
    assert deal.target_cap_rate == 600000.0 / 9500000.0
    assert deal.price_per_unit == 9500000.0 / 10
    assert deal.price_per_sqft == 9500000.0 / 45000.0
    assert deal.in_place_cap_rate == deal.target_cap_rate

    # Zero values branch tests for PropertyDeal properties
    deal_uncalc = PropertyDeal.model_construct(
        asking_price=0.0,
        target_purchase_price=0.0,
        in_place_noi=600000.0,
        unit_mix=mix_empty,
        physical=PropertyPhysical.model_construct(rentable_square_feet=0.0),
    )
    assert deal_uncalc.asking_cap_rate == 0.0
    assert deal_uncalc.target_cap_rate == 0.0
    assert deal_uncalc.price_per_unit == 0.0
    assert deal_uncalc.price_per_sqft == 0.0

    # Zero asking price edge case
    with pytest.raises(ValidationError):
        PropertyDeal(
            title="Apex Tower",
            property_type=PropertyType.OFFICE,
            address=addr,
            physical=phys,
            unit_mix=mix,
            asking_price=0.0,
            target_purchase_price=9500000.0,
            in_place_noi=600000.0,
            sponsor_name="Apex Holdings",
        )


def test_financial_models():
    with pytest.raises(ValidationError):
        # interest_only > term
        FinancingAssumptions(
            loan_amount=1000000.0,
            interest_rate=0.05,
            term_years=5,
            interest_only_years=6,
            amortization_years=30,
        )

    with pytest.raises(ValidationError):
        # term > amortization
        FinancingAssumptions(
            loan_amount=1000000.0,
            interest_rate=0.05,
            term_years=35,
            amortization_years=30,
        )

    fa = FinancingAssumptions(
        loan_amount=7000000.0,
        loan_type=LoanType.FIXED_RATE,
        interest_rate=0.065,
        term_years=10,
        amortization_years=30,
        interest_only_years=2,
    )
    assert fa.loan_type == LoanType.FIXED_RATE
    assert fa.monthly_interest_rate == 0.065 / 12.0
    assert fa.origination_fee_amount == 7000000.0 * 0.01
    assert fa.monthly_amortizing_payment() > 0
    assert fa.annual_debt_service(1) == 7000000.0 * 0.065
    assert fa.annual_debt_service(3) == fa.monthly_amortizing_payment() * 12.0

    # zero loan amount / zero rate
    fa_zero = FinancingAssumptions(
        loan_amount=0.0,
        interest_rate=0.0,
    )
    assert fa_zero.monthly_amortizing_payment() == 0.0
    assert fa_zero.annual_debt_service(1) == 0.0

    fa_zerorate = FinancingAssumptions(
        loan_amount=120000.0,
        interest_rate=0.0,
        amortization_years=10,
    )
    assert fa_zerorate.monthly_amortizing_payment() == 1000.0

    cf = AnnualCashFlow(
        year=1,
        potential_gross_revenue=1000000.0,
        vacancy_and_credit_loss=50000.0,
        effective_gross_income=950000.0,
        operating_expenses=350000.0,
        net_operating_income=600000.0,
        capex_reserves=20000.0,
        debt_service=400000.0,
        unlevered_cash_flow=580000.0,
        levered_cash_flow=180000.0,
        ending_loan_balance=6800000.0,
        dscr=1.5,
        debt_yield=600000.0 / 6800000.0,
    )
    assert cf.net_operating_income == 600000.0

    dcf_p = DCFParameters(
        holding_period_years=5,
        exit_cap_rate=0.06,
        discount_rate=0.08,
    )
    assert dcf_p.holding_period_years == 5

    metrics = ValuationMetrics(
        purchase_price=10000000.0,
        equity_invested=3000000.0,
        loan_amount=7000000.0,
        unlevered_irr=0.095,
        levered_irr=0.145,
        equity_multiple=1.75,
        net_present_value=1200000.0,
        in_place_cap_rate=0.06,
        exit_cap_rate=0.065,
        gross_exit_sales_price=12000000.0,
        net_sales_proceeds=11760000.0,
        total_net_profit=2250000.0,
        min_dscr_observed=1.35,
        average_dscr=1.45,
    )
    assert metrics.levered_irr == 0.145

    row = LoanAmortizationRow(
        month=1,
        beginning_balance=1000.0,
        payment=100.0,
        principal=80.0,
        interest=20.0,
        ending_balance=920.0,
    )
    assert row.month == 1

    scen = SensitivityScenario(
        rent_growth_delta_bps=50,
        exit_cap_delta_bps=-25,
        levered_irr=0.16,
        equity_multiple=1.85,
        net_present_value=1500000.0,
    )
    matrix = SensitivityMatrix(
        base_levered_irr=0.145,
        base_equity_multiple=1.75,
        scenarios=[scen],
    )
    assert len(matrix.scenarios) == 1

    res = DCFValuationResult(
        deal_id="deal-1",
        parameters=dcf_p,
        financing=fa,
        annual_cash_flows=[cf],
        metrics=metrics,
        sensitivity=matrix,
        model_checksum="sha256-abc123xyz",
    )
    assert res.deal_id == "deal-1"


def test_agent_models():
    assert AgentRole("swarm_orchestrator") == AgentRole.SWARM_ORCHESTRATOR
    assert AgentRole._missing_("SWARM_ORCHESTRATOR") == AgentRole.SWARM_ORCHESTRATOR
    assert AgentRole._missing_("invalid") is None

    msg = AgentMessage(
        sender_role=AgentRole.INGESTION_COORDINATOR,
        recipient_role=AgentRole.SWARM_ORCHESTRATOR,
        deal_id="deal-1",
        message_text="Ingestion done",
    )
    assert msg.sender_role == AgentRole.INGESTION_COORDINATOR

    task = AgentTask(
        role=AgentRole.MUNICIPAL_DEED_AUDITOR,
        deal_id="deal-1",
        description="Verify parcel conveyance deed history",
    )
    assert task.status == TaskStatus.PENDING

    audit = AgentAuditEntry(
        task_id=task.id,
        role=AgentRole.SEC_DILIGENCE_ANALYST,
        action_taken="parse_10k_risk_factors",
        justification="Checked tenant risk factor disclosures in Item 1A",
        input_hash="hash-123",
        output_summary="Identified single-tenant concentration",
    )
    assert audit.role == AgentRole.SEC_DILIGENCE_ANALYST

    wf = SwarmWorkflowState(
        deal_id="deal-1",
        tasks=[task],
        audit_trail=[audit],
    )
    assert wf.deal_id == "deal-1"
    assert len(wf.tasks) == 1


def test_events_models():
    event = SwarmEvent(
        event_type=EventType.DEAL_CREATED,
        deal_id="deal-1",
        source_role=AgentRole.SWARM_ORCHESTRATOR.value,
        payload={"name": "Deal 1"},
        priority=EventPriority.HIGH,
    )
    assert event.event_type == EventType.DEAL_CREATED
    assert event.priority == EventPriority.HIGH


def test_ingestion_models():
    deed = DeedRecord(
        parcel_number="123-456-789",
        document_number="DOC-2023-01",
        recording_date=date(2023, 1, 1),
        deed_type=DeedType.GENERAL_WARRANTY_DEED,
        grantor="Seller LLC",
        grantee="Buyer LP",
        consideration_amount=5000000.0,
        legal_description="Lot 1 Block 2 Subdivision Plat",
        county_name="Travis",
    )
    assert deed.grantor == "Seller LLC"

    mention = SECRiskMention(
        topic=SECRiskTopic.REFINANCING_RISK,
        excerpt="The company is exposed to SOFR benchmark interest rate fluctuations.",
        item_section="Item 7A. Quantitative and Qualitative Disclosures About Market Risk",
        severity_score=0.75,
        relevance_score=0.90,
    )
    sec = SECFiling(
        accession_number="0001234567-23-000001",
        cik="123456",  # tests zfill validator
        company_name="Reit Corp",
        form_type=SECFilingType.FORM_10K,
        filing_date=date(2023, 2, 15),
        risk_mentions=[mention],
    )
    assert sec.cik == "0000123456"
    assert sec.company_name == "Reit Corp"

    # CIK non-digit error
    with pytest.raises(ValueError):
        SECFiling(
            accession_number="0001234567-23-000001",
            cik="ABC1234567",
            company_name="Reit Corp",
            form_type=SECFilingType.FORM_10K,
            filing_date=date(2023, 2, 15),
        )

    # integer CIK auto stringified
    sec_int_cik = SECFiling(
        accession_number="0001234567-23-000002",
        cik=12345678,  # type: ignore
        company_name="Reit Corp",
        form_type=SECFilingType.FORM_10K,
        filing_date=date(2023, 2, 15),
    )
    assert sec_int_cik.cik == "0012345678"

    with pytest.raises(ValueError):
        SECFiling(
            accession_number="0001234567-23-000001",
            cik="0001234567891",  # > 10 digits
            company_name="Reit Corp",
            form_type=SECFilingType.FORM_10K,
            filing_date=date(2023, 2, 15),
        )

    chunk = DocumentChunk(
        document_id="doc-om-1",
        source_type=IngestionSourceType.OFFERING_MEMORANDUM,
        chunk_index=0,
        page_number=1,
        text_content="Excerpt from OM text",
        token_count=15,
    )
    om = OfferingMemorandum(
        deal_id="deal-1",
        filename="Apex_Tower_OM.pdf",
        file_size_bytes=1024000,
        file_hash="abcde12345sha256",
        page_count=45,
        chunks=[chunk],
    )
    assert om.filename == "Apex_Tower_OM.pdf"

    job = IngestionJob(
        source_type=IngestionSourceType.MUNICIPAL_DEED,
        source_uri="https://recorder.traviscountytx.gov/deeds/DOC-2023-01",
        status=IngestionStatus.COMPLETED,
    )
    assert job.status == IngestionStatus.COMPLETED


def test_knowledge_graph_models():
    node1 = GraphEntity(
        entity_type=EntityType.PROPERTY,
        label="Apex Tower",
    )
    node2 = GraphEntity(
        entity_type=EntityType.SPONSOR,
        label="Apex Sponsor LLC",
    )
    rel = GraphRelation(
        source_id=node2.entity_id,
        target_id=node1.entity_id,
        relation_type=RelationType.OWNS,
    )
    kg = KnowledgeGraph()
    kg.add_entity(node1)
    kg.add_entity(node2)
    kg.add_relation(rel)

    assert len(kg.entities) == 2
    assert len(kg.relations) == 1
    assert kg.get_entity(node1.entity_id) == node1
    assert len(kg.filter_by_type(EntityType.PROPERTY)) == 1
    assert len(kg.get_outgoing_relations(node2.entity_id)) == 1
    assert len(kg.get_incoming_relations(node1.entity_id)) == 1
    assert kg.get_neighbors(node1.entity_id) == [node2.entity_id]
    assert kg.get_neighbors(node2.entity_id) == [node1.entity_id]
    assert len(kg.find_encumbrances(node1.entity_id)) == 0

    enc_rel = GraphRelation(
        source_id=node2.entity_id,
        target_id=node1.entity_id,
        relation_type=RelationType.ENCUMBERS,
    )
    kg.add_relation(enc_rel)
    assert len(kg.find_encumbrances(node1.entity_id)) == 1

    # relation with non-existent source or target
    bad_rel_source = GraphRelation(
        source_id="non-existent",
        target_id=node1.entity_id,
        relation_type=RelationType.OWNS,
    )
    with pytest.raises(KeyError):
        kg.add_relation(bad_rel_source)

    bad_rel_target = GraphRelation(
        source_id=node2.entity_id,
        target_id="non-existent",
        relation_type=RelationType.OWNS,
    )
    with pytest.raises(KeyError):
        kg.add_relation(bad_rel_target)


def test_risk_models():
    assert RiskCategory._missing_("zoning_and_land_use") == RiskCategory.ZONING_AND_LAND_USE
    assert RiskCategory._missing_("invalid") is None
    assert RiskSeverity._missing_("critical") == RiskSeverity.CRITICAL
    assert RiskSeverity._missing_("invalid") is None
    assert MemoRecommendation._missing_("approve_with_conditions") == MemoRecommendation.APPROVE_WITH_CONDITIONS
    assert MemoRecommendation._missing_("invalid") is None

    finding = RiskFinding(
        category=RiskCategory.TITLE_AND_LEGAL,
        severity=RiskSeverity.HIGH,
        title="Easement Encumbrance",
        description="Utility easement traverses buildable area footprint",
        evidence_citation="County deed book 452 page 12",
        impact_summary="Restricts vertical expansion potential",
        confirmed_by_role=AgentRole.MUNICIPAL_DEED_AUDITOR,
    )
    assert finding.severity == RiskSeverity.HIGH

    item = DiligenceChecklistItem(
        category=RiskCategory.PHYSICAL_ENVIRONMENTAL,
        requirement="Phase I ESA completed within past 180 days with no RECs",
        status=ChecklistStatus.PASS,
    )
    assert item.status == ChecklistStatus.PASS

    signoff = SignOff(
        role=AgentRole.CREDIT_RISK_UNDERWRITER,
        recommendation=MemoRecommendation.APPROVE_WITH_CONDITIONS,
        rationale="Loan metrics within covenants subject to debt yield escrow",
    )
    assert signoff.role == AgentRole.CREDIT_RISK_UNDERWRITER

    stress = StressScenario(
        name="Stagflation Shock",
        rent_shock_pct=-0.10,
        resultant_irr=0.08,
        min_dscr_observed=1.1,
    )
    assert stress.name == "Stagflation Shock"
    assert stress.noi_shock_pct == -0.10
    assert stress.resultant_dscr == 1.1

    stress2 = StressScenario(
        name="Rate Shock",
        noi_shock_pct=-0.05,
        cap_rate_expansion_bps=75,
        resultant_dscr=1.2,
        resultant_irr=0.09,
    )
    assert stress2.rent_shock_pct == -0.05
    assert stress2.exit_cap_expansion_bps == 75
    assert stress2.min_dscr_observed == 1.2

    stress3 = StressScenario(
        name="Exit Cap Shock",
        exit_cap_expansion_bps=100,
        resultant_irr=0.07,
        resultant_dscr=1.0,
    )
    assert stress3.cap_rate_expansion_bps == 100

    metrics = ValuationMetrics(
        purchase_price=10000000.0,
        equity_invested=3000000.0,
        loan_amount=7000000.0,
        unlevered_irr=0.095,
        levered_irr=0.145,
        equity_multiple=1.75,
        net_present_value=1200000.0,
        in_place_cap_rate=0.06,
        exit_cap_rate=0.065,
        gross_exit_sales_price=12000000.0,
        net_sales_proceeds=11760000.0,
        total_net_profit=2250000.0,
        min_dscr_observed=1.35,
        average_dscr=1.45,
    )

    memo = UnderwritingMemo(
        deal_id="deal-1",
        deal_title="Apex Tower Underwriting Memo",
        executive_summary="Institutional asset with strong credit tenants and manageable debt profile.",
        recommendation=MemoRecommendation.APPROVE_WITH_CONDITIONS,
        valuation_summary=metrics,
        risk_findings=[finding],
        diligence_checklist=[item],
        sign_offs=[signoff],
    )
    assert memo.recommendation == MemoRecommendation.APPROVE_WITH_CONDITIONS
