"""Comprehensive test suite for PropRisk Swarm scaffolding."""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from proprisk_swarm import __author__, __version__, get_settings
from proprisk_swarm.cli import cli
from proprisk_swarm.config import PropRiskSettings
from proprisk_swarm.protocols import (
    AgentProtocol,
    EventBusProtocol,
    GraphRAGProtocol,
    IngestionPipelineProtocol,
    MCPServerProtocol,
    ValuationEngineProtocol,
)


def test_package_metadata():
    """Verify package version and author attributes."""
    assert __version__ == "0.1.0"
    assert __author__ == "Zein"


def test_settings_defaults(default_settings: PropRiskSettings):
    """Verify standard default configuration values."""
    assert default_settings.project_name == "proprisk-swarm"
    assert default_settings.version == "0.1.0"
    assert default_settings.log_level == "INFO"

    # MCP servers
    assert default_settings.mcp.deeds_port == 8201
    assert default_settings.mcp.sec_port == 8202
    assert default_settings.mcp.zoning_port == 8203

    # RAG settings
    assert default_settings.rag.vector_dimension == 1536
    assert default_settings.rag.embedding_model == "text-embedding-3-small"
    assert default_settings.rag.hybrid_alpha == 0.6
    assert default_settings.rag.graph_enabled is True

    # Swarm settings
    assert default_settings.swarm.max_concurrent_agents == 6
    assert default_settings.swarm.task_timeout_seconds == 120
    assert default_settings.swarm.strict_audit_mode is True

    # Valuation defaults
    assert default_settings.valuation.default_holding_period_years == 5
    assert default_settings.valuation.default_discount_rate == 0.085
    assert default_settings.valuation.default_exit_cap_rate == 0.0575


def test_settings_from_env():
    """Verify settings overrides from environment variables."""
    env_overrides = {
        "PROPRISK_LOG_LEVEL": "DEBUG",
        "PROPRISK_MCP_DEEDS_PORT": "9001",
        "PROPRISK_VECTOR_DIMENSION": "3072",
        "PROPRISK_MAX_CONCURRENT_AGENTS": "12",
    }
    with patch.dict(os.environ, env_overrides):
        settings = PropRiskSettings.from_env()
        assert settings.log_level == "DEBUG"
        assert settings.mcp.deeds_port == 9001
        assert settings.rag.vector_dimension == 3072
        assert settings.swarm.max_concurrent_agents == 12


def test_get_settings_singleton():
    """Verify get_settings returns identical cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_agent_protocol_conformance():
    """Verify mock agent implements AgentProtocol."""

    class MockAgent:
        @property
        def agent_id(self) -> str:
            return "agent-001"

        @property
        def role_name(self) -> str:
            return "Mock Underwriter"

        def execute_task(self, task_payload):
            return {"status": "success", "result": 42}

        def can_handle(self, task_type: str) -> bool:
            return task_type == "underwriting"

    agent = MockAgent()
    assert isinstance(agent, AgentProtocol)
    assert agent.agent_id == "agent-001"
    assert agent.can_handle("underwriting") is True
    assert agent.can_handle("marketing") is False


def test_mcp_server_protocol_conformance():
    """Verify mock MCP server implements MCPServerProtocol."""

    class MockMCPServer:
        @property
        def server_name(self) -> str:
            return "municipal-deeds"

        def list_tools(self):
            return [{"name": "get_deed", "description": "Fetch deed by APN"}]

        def list_resources(self):
            return [{"uri": "deeds://travis-county", "name": "Travis County Deeds"}]

        def call_tool(self, name: str, arguments):
            return {"status": "ok", "name": name, "echo": arguments}

    server = MockMCPServer()
    assert isinstance(server, MCPServerProtocol)
    assert len(server.list_tools()) == 1
    assert server.call_tool("get_deed", {"apn": "123"})["echo"] == {"apn": "123"}


def test_ingestion_pipeline_protocol_conformance():
    """Verify ingestion pipeline implements IngestionPipelineProtocol."""

    class MockIngestion:
        def ingest_document(self, source_path: str, source_type: str, metadata=None) -> str:
            return f"job-{source_type}-001"

        def parse_payload(self, raw_data: bytes, document_type: str):
            return {"parsed_bytes": len(raw_data), "doc_type": document_type}

    pipeline = MockIngestion()
    assert isinstance(pipeline, IngestionPipelineProtocol)
    assert pipeline.ingest_document("/tmp/deed.pdf", "deed") == "job-deed-001"
    assert pipeline.parse_payload(b"hello", "deed")["parsed_bytes"] == 5


def test_graph_rag_protocol_conformance():
    """Verify GraphRAG pipeline implements GraphRAGProtocol."""

    class MockGraphRAG:
        def index_document(self, doc_id: str, content: str, metadata=None) -> int:
            return 3

        def query_with_citations(self, query: str, top_k: int = 5):
            return {"query": query, "passages": [], "citations": []}

        def get_related_entities(self, entity_id: str, max_depth: int = 2):
            return [{"entity_id": "sponsor-1", "relation": "OWNS"}]

    rag = MockGraphRAG()
    assert isinstance(rag, GraphRAGProtocol)
    assert rag.index_document("doc-1", "sample") == 3
    assert len(rag.get_related_entities("prop-1")) == 1


def test_valuation_engine_protocol_conformance():
    """Verify valuation engine implements ValuationEngineProtocol."""

    class MockValuation:
        def compute_dcf(self, purchase_price, cash_flows, discount_rate, terminal_cap_rate):
            return {
                "npv": 1000000.0,
                "unlevered_irr": 0.12,
                "levered_irr": 0.16,
                "equity_multiple": 1.85,
            }

        def synthesize_investment_memo(self, deal_id: str, valuation_data):
            return {"deal_id": deal_id, "recommendation": "APPROVED"}

    engine = MockValuation()
    assert isinstance(engine, ValuationEngineProtocol)
    metrics = engine.compute_dcf(10_000_000, [500_000] * 5, 0.08, 0.06)
    assert metrics["levered_irr"] == 0.16


def test_event_bus_protocol_conformance():
    """Verify event bus implements EventBusProtocol."""

    class MockEventBus:
        def __init__(self):
            self.events = []

        def publish(self, event_type: str, payload):
            self.events.append((event_type, payload))

        def subscribe(self, event_type: str, handler):
            pass

    bus = MockEventBus()
    assert isinstance(bus, EventBusProtocol)
    bus.publish("deal.created", {"deal_id": "deal-1"})
    assert len(bus.events) == 1


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def test_cli_version_flag(cli_runner: CliRunner):
    """Verify CLI --version output."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in _strip_ansi(result.output)


def test_cli_help(cli_runner: CliRunner):
    """Verify CLI --help shows core commands."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    clean_out = _strip_ansi(result.output)
    assert "status" in clean_out
    assert "mcp-servers" in clean_out
    assert "underwrite" in clean_out
    assert "export-sql" in clean_out
    assert "validate-export" in clean_out


def test_cli_status(cli_runner: CliRunner):
    """Verify CLI status displays system configuration."""
    result = cli_runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    clean_out = _strip_ansi(result.output)
    assert "proprisk-swarm" in clean_out
    assert "8201" in clean_out
    assert "8202" in clean_out
    assert "8203" in clean_out


def test_cli_mcp_servers(cli_runner: CliRunner):
    """Verify CLI mcp-servers lists diligence server endpoints."""
    result = cli_runner.invoke(cli, ["mcp-servers"])
    assert result.exit_code == 0
    clean_out = _strip_ansi(result.output)
    assert "Municipal Deeds" in clean_out
    assert "SEC EDGAR" in clean_out
    assert "Municipal Zoning" in clean_out


def test_cli_underwrite(cli_runner: CliRunner):
    """Verify CLI underwrite initial run."""
    result = cli_runner.invoke(
        cli,
        ["underwrite", "--deal-id", "deal-austin-multifamily", "--asking-price", "25000000"],
    )
    assert result.exit_code == 0
    clean_out = _strip_ansi(result.output)
    assert "deal-austin-multifamily" in clean_out
    assert "25,000,000.00" in clean_out
    assert "Scaffold pipeline execution initialized successfully" in clean_out


def test_cli_no_args(cli_runner: CliRunner):
    """Verify CLI without arguments displays banner."""
    result = cli_runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "PropRisk Swarm" in _strip_ansi(result.output)


def test_cli_main_entrypoint(monkeypatch):
    """Verify CLI direct main execution exit code."""
    with patch("sys.argv", ["proprisk", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            cli()
        assert exc_info.value.code == 0


def test_subpackages_import():
    """Verify all submodules import cleanly."""
    import proprisk_swarm.cli
    import proprisk_swarm.config
    import proprisk_swarm.protocols
    import proprisk_swarm.storage
    import proprisk_swarm.types

    assert proprisk_swarm.config is not None
    assert proprisk_swarm.protocols is not None
    assert proprisk_swarm.cli is not None
    assert proprisk_swarm.storage is not None
    assert proprisk_swarm.types is not None
