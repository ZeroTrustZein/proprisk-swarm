"""Tests for Valuation Engine subsystem."""

from __future__ import annotations

import pytest
from proprisk_swarm.protocols import ValuationEngineProtocol
from proprisk_swarm.types.risk import MemoRecommendation
from proprisk_swarm.valuation.engine import ValuationEngine


def test_valuation_engine_protocol_conformance():
    """Verify ValuationEngine satisfies ValuationEngineProtocol."""
    engine = ValuationEngine()
    assert isinstance(engine, ValuationEngineProtocol)


def test_compute_dcf_metrics():
    """Verify DCF metrics: NPV, IRR, Equity Multiple, and DSCR."""
    engine = ValuationEngine()
    purchase_price = 10000000.0
    cash_flows = [650000.0, 675000.0, 700000.0, 725000.0, 750000.0]

    dcf = engine.compute_dcf(
        purchase_price=purchase_price,
        cash_flows=cash_flows,
        discount_rate=0.085,
        terminal_cap_rate=0.06,
    )

    assert dcf["purchase_price"] == purchase_price
    assert dcf["exit_valuation"] == round(750000.0 / 0.06, 2)
    assert dcf["unlevered_irr"] > 0.05
    assert dcf["levered_irr"] > 0.05
    assert dcf["equity_multiple"] > 1.0
    assert dcf["debt_service_coverage_ratio"] > 1.0
    assert dcf["debt_yield"] > 0.05


def test_compute_sensitivity_matrix():
    """Verify 2D sensitivity matrix generation over cap rates and growth."""
    engine = ValuationEngine()
    purchase_price = 10000000.0
    cash_flows = [600000.0, 620000.0, 640000.0, 660000.0, 680000.0]

    matrix = engine.compute_sensitivity_matrix(
        purchase_price=purchase_price,
        base_cash_flows=cash_flows,
        cap_rates=[0.05, 0.06],
        noi_growth_rates=[0.02, 0.04],
    )

    assert matrix.base_irr > 0.0
    assert len(matrix.grid) == 2  # 2 growth rows
    assert len(matrix.grid[0]) == 2  # 2 cap rate columns


def test_synthesize_investment_memo_recommendations():
    """Verify memo recommendations based on hurdle rates."""
    engine = ValuationEngine()

    # Approved scenario
    approved_val = {
        "unlevered_irr": 0.14,
        "equity_multiple": 1.75,
        "debt_service_coverage_ratio": 1.45,
        "npv": 1500000.0,
        "exit_valuation": 12000000.0,
        "gross_sales_proceeds": 12000000.0,
        "net_sales_proceeds": 11760000.0,
    }
    memo_app = engine.synthesize_investment_memo("DEAL-APP", approved_val)
    assert memo_app["recommendation"] == MemoRecommendation.APPROVED.value
    assert memo_app["overall_risk_score"] < 30.0

    # Conditional approval scenario
    cond_val = {
        "unlevered_irr": 0.09,
        "equity_multiple": 1.35,
        "debt_service_coverage_ratio": 1.20,
    }
    memo_cond = engine.synthesize_investment_memo("DEAL-COND", cond_val)
    assert memo_cond["recommendation"] == MemoRecommendation.CONDITIONAL_APPROVAL.value

    # Rejected scenario
    rej_val = {
        "unlevered_irr": 0.03,
        "equity_multiple": 0.95,
        "debt_service_coverage_ratio": 0.90,
    }
    memo_rej = engine.synthesize_investment_memo("DEAL-REJ", rej_val)
    assert memo_rej["recommendation"] == MemoRecommendation.REJECTED.value
    assert memo_rej["overall_risk_score"] > 60.0
