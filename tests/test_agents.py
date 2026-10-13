"""Tests for Diligence Swarm Agents and Orchestration subsystem."""

from __future__ import annotations

from pathlib import Path
import pytest
from click.testing import CliRunner

from proprisk_swarm.agents.base import BaseAgent
from proprisk_swarm.agents.specialized import (
    CreditRiskUnderwriterAgent,
    DCFValuationAgent,
    MunicipalDeedAuditorAgent,
    SecDiligenceAnalystAgent,
    ZoningComplianceAgent,
)
from proprisk_swarm.agents.orchestrator import SwarmOrchestrator
from proprisk_swarm.cli import cli
from proprisk_swarm.protocols import AgentProtocol
from proprisk_swarm.types.agents import AgentRole, AgentState


def test_agent_protocol_conformance():
    """Verify all specialized agents satisfy AgentProtocol."""
    agents = [
        MunicipalDeedAuditorAgent(),
        SecDiligenceAnalystAgent(),
        ZoningComplianceAgent(),
        DCFValuationAgent(),
        CreditRiskUnderwriterAgent(),
        SwarmOrchestrator(),
    ]
    for agent in agents:
        assert isinstance(agent, AgentProtocol)
        assert len(agent.agent_id) > 0
        assert len(agent.role_name) > 0


def test_base_agent_can_handle_and_error():
    """Verify task matching and execution error capture in BaseAgent."""
    class DummyAgent(BaseAgent):
        def _process(self, payload: dict) -> dict:
            if payload.get("fail"):
                raise RuntimeError("Deliberate failure")
            return {"ok": True}

    agent = DummyAgent(role=AgentRole.SWARM_ORCHESTRATOR, supported_tasks=["audit.task", "review"])
    assert agent.can_handle("audit.task") is True
    assert agent.can_handle("audit_task") is True
    assert agent.can_handle("review") is True
    assert agent.can_handle("other") is False

    # Success
    res = agent.execute_task({"fail": False})
    assert res["ok"] is True
    assert agent.state == AgentState.COMPLETED

    # Failure
    fail_res = agent.execute_task({"fail": True})
    assert fail_res["status"] == "error"
    assert "Deliberate failure" in fail_res["error"]
    assert agent.state == AgentState.ERROR


def test_specialized_agents_execution():
    """Verify execution of individual specialized agents."""
    deed_agent = MunicipalDeedAuditorAgent()
    deed_res = deed_agent.execute_task({"parcel_id": "P-99", "county": "Travis"})
    assert deed_res["status"] == "success"
    assert len(deed_res["deeds"]) >= 1

    sec_agent = SecDiligenceAnalystAgent()
    sec_res = sec_agent.execute_task({"cik": "0001", "tenant_name": "Anchor"})
    assert sec_res["status"] == "success"
    assert "risk_factors" in sec_res

    zoning_agent = ZoningComplianceAgent()
    zoning_res = zoning_agent.execute_task({"zone_code": "CBD", "proposed_gfa": 100000.0, "lot_area_sqft": 20000.0})
    assert zoning_res["status"] == "success"
    assert zoning_res["is_far_compliant"] is True

    val_agent = DCFValuationAgent()
    val_res = val_agent.execute_task({"target_purchase_price": 5000000.0, "in_place_noi": 350000.0})
    assert val_res["status"] == "success"
    assert val_res["valuation"]["unlevered_irr"] > 0

    memo_agent = CreditRiskUnderwriterAgent()
    memo_res = memo_agent.execute_task({"deal_id": "DEAL-T", "valuation": val_res["valuation"]})
    assert memo_res["status"] == "success"
    assert "memo" in memo_res


def test_swarm_orchestrator_pipeline_and_validation():
    """Verify SwarmOrchestrator runs end-to-end and returns cleaned/validated package."""
    orchestrator = SwarmOrchestrator()
    res = orchestrator.run_diligence_pipeline(
        deal_id="DEAL-AUSTIN-1",
        deal_payload={
            "title": "Austin Retail Center \x00",
            "target_purchase_price": 12500000.0,
            "in_place_noi": 800000.0,
            "anchor_tenant": "HEB Grocery",
            "zone_code": "CBD",
        },
    )

    assert res["status"] == "completed"
    assert res["is_valid"] is True
    pkg = res["package"]
    assert pkg["deal_id"] == "DEAL-AUSTIN-1"
    assert pkg["deal"]["title"] == "Austin Retail Center"
    assert len(pkg["deeds"]) >= 1
    assert "memo" in pkg


def test_cli_underwrite_live_execution(tmp_path: Path):
    """Verify CLI underwrite with --execute and --export-sql."""
    runner = CliRunner()
    store_file = tmp_path / "store.json"
    sql_file = tmp_path / "deal_export.sql"

    result = runner.invoke(
        cli,
        [
            "underwrite",
            "--deal-id", "DEAL-CLI-LIVE",
            "--asking-price", "8000000",
            "--holding-period", "5",
            "--execute",
            "--store-path", str(store_file),
            "--export-sql", str(sql_file),
        ],
    )

    assert result.exit_code == 0
    assert "Swarm underwriting completed successfully" in result.output
    assert sql_file.exists()
    sql_content = sql_file.read_text(encoding="utf-8")
    assert "PostgreSQL Deal Export for: DEAL-CLI-LIVE" in sql_content
    assert "CREATE TABLE IF NOT EXISTS public.deals" in sql_content
    assert "INSERT INTO public.deals" in sql_content
