"""PropRisk Swarm: Autonomous Multi-Agent Real Estate Underwriting & Risk Platform."""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Zein"

from proprisk_swarm.agents import (
    BaseAgent,
    CreditRiskUnderwriterAgent,
    DCFValuationAgent,
    MunicipalDeedAuditorAgent,
    SecDiligenceAnalystAgent,
    SwarmOrchestrator,
    ZoningComplianceAgent,
)
from proprisk_swarm.config import PropRiskSettings, get_settings
from proprisk_swarm.events import EventBus
from proprisk_swarm.ingestion import IngestionPipeline
from proprisk_swarm.mcp import (
    BaseMCPServer,
    MCPRegistry,
    MunicipalDeedsMCP,
    SecFilingsMCP,
    ZoningOrdinanceMCP,
)
from proprisk_swarm.protocols import (
    AgentProtocol,
    EventBusProtocol,
    GraphRAGProtocol,
    IngestionPipelineProtocol,
    MCPServerProtocol,
    ValuationEngineProtocol,
)
from proprisk_swarm.rag import HybridGraphRAG
from proprisk_swarm.storage import (
    DealStore,
    SubsystemCache,
    cached,
)
from proprisk_swarm.valuation import ValuationEngine

__all__ = [
    "__version__",
    "__author__",
    "PropRiskSettings",
    "get_settings",
    "AgentProtocol",
    "EventBusProtocol",
    "GraphRAGProtocol",
    "IngestionPipelineProtocol",
    "MCPServerProtocol",
    "ValuationEngineProtocol",
    "DealStore",
    "SubsystemCache",
    "cached",
    "EventBus",
    "BaseMCPServer",
    "MCPRegistry",
    "MunicipalDeedsMCP",
    "SecFilingsMCP",
    "ZoningOrdinanceMCP",
    "IngestionPipeline",
    "HybridGraphRAG",
    "ValuationEngine",
    "BaseAgent",
    "MunicipalDeedAuditorAgent",
    "SecDiligenceAnalystAgent",
    "ZoningComplianceAgent",
    "DCFValuationAgent",
    "CreditRiskUnderwriterAgent",
    "SwarmOrchestrator",
]
