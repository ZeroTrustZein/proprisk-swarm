"""Tests for MCP Services subsystem."""

from __future__ import annotations

import pytest
from proprisk_swarm.mcp.deeds import MunicipalDeedsMCP
from proprisk_swarm.mcp.sec import SecFilingsMCP
from proprisk_swarm.mcp.zoning import ZoningOrdinanceMCP
from proprisk_swarm.mcp.registry import MCPRegistry
from proprisk_swarm.protocols import MCPServerProtocol


def test_mcp_servers_conformance():
    """Verify deeds, sec, and zoning servers satisfy MCPServerProtocol."""
    deeds = MunicipalDeedsMCP()
    sec = SecFilingsMCP()
    zoning = ZoningOrdinanceMCP()

    for s in [deeds, sec, zoning]:
        assert isinstance(s, MCPServerProtocol)
        assert len(s.server_name) > 0
        assert len(s.list_tools()) > 0
        assert len(s.list_resources()) > 0


def test_municipal_deeds_mcp_tools():
    """Verify MunicipalDeedsMCP tools: search_deeds, verify_title_chain, check_easements."""
    mcp = MunicipalDeedsMCP()

    # search_deeds
    res = mcp.call_tool("search_deeds", {"parcel_id": "P-123", "county": "Travis"})
    assert res["parcel_id"] == "P-123"
    assert res["count"] >= 1
    assert "deeds" in res

    # verify_title_chain
    res_title = mcp.call_tool("verify_title_chain", {"parcel_id": "P-123"})
    assert res_title["chain_status"] == "clear"
    assert res_title["gaps_found"] is False

    # check_easements
    res_ease = mcp.call_tool("check_easements", {"parcel_id": "P-123"})
    assert "easements" in res_ease
    assert res_ease["has_restrictive_easements"] is False


def test_sec_filings_mcp_tools():
    """Verify SecFilingsMCP tools: fetch_10k_risk_factors, check_tenant_credit, get_reit_covenants."""
    mcp = SecFilingsMCP()

    # fetch_10k_risk_factors
    res_rf = mcp.call_tool("fetch_10k_risk_factors", {"cik": "0001234567", "year": 2023})
    assert res_rf["cik"] == "0001234567"
    assert len(res_rf["risk_factors"]) >= 2

    # check_tenant_credit
    res_tc = mcp.call_tool("check_tenant_credit", {"tenant_name": "Anchor Store"})
    assert res_tc["investment_grade"] is True
    assert res_tc["rating_sp"] == "BBB+"

    # get_reit_covenants
    res_cov = mcp.call_tool("get_reit_covenants", {"cik": "0001234567"})
    assert res_cov["covenant_compliant"] is True


def test_zoning_ordinance_mcp_tools():
    """Verify ZoningOrdinanceMCP tools: get_zoning_classification, verify_far_compliance, check_setbacks."""
    mcp = ZoningOrdinanceMCP()

    # get_zoning_classification
    res_z = mcp.call_tool("get_zoning_classification", {"zone_code": "CBD"})
    assert res_z["zone_code"] == "CBD"
    assert "multifamily" in res_z["permitted_uses"]

    # verify_far_compliance compliant
    res_far = mcp.call_tool(
        "verify_far_compliance",
        {"proposed_gfa": 100000.0, "lot_area_sqft": 20000.0, "max_far": 8.0},
    )
    assert res_far["actual_far"] == 5.0
    assert res_far["is_compliant"] is True
    assert res_far["unused_allowable_gfa"] == 60000.0

    # verify_far_compliance non-compliant
    res_far_fail = mcp.call_tool(
        "verify_far_compliance",
        {"proposed_gfa": 200000.0, "lot_area_sqft": 20000.0, "max_far": 8.0},
    )
    assert res_far_fail["actual_far"] == 10.0
    assert res_far_fail["is_compliant"] is False

    # check_setback_requirements
    res_sb = mcp.call_tool("check_setback_requirements", {"zone_code": "CBD"})
    assert res_sb["rear_setback_ft"] == 10.0


def test_mcp_server_error_handling():
    """Verify unknown tool returns structured error."""
    mcp = MunicipalDeedsMCP()
    res = mcp.call_tool("nonexistent_tool", {})
    assert res["is_error"] is True
    assert "not found" in res["error"]


def test_mcp_registry():
    """Verify MCPRegistry registration, lookup, tool routing, and default factory."""
    reg = MCPRegistry.create_default()
    assert "municipal-deeds" in reg.list_servers()
    assert "sec-filings" in reg.list_servers()
    assert "zoning-ordinances" in reg.list_servers()

    # Route call
    res = reg.call_tool("municipal-deeds", "verify_title_chain", {"parcel_id": "P-1"})
    assert res["chain_status"] == "clear"

    # Route call unknown server
    err_res = reg.call_tool("unknown-server", "tool", {})
    assert err_res["is_error"] is True
