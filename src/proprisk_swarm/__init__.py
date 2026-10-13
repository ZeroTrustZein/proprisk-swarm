"""PropRisk Swarm: Autonomous Multi-Agent Real Estate Underwriting & Risk Platform."""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Zein"

from proprisk_swarm.config import PropRiskSettings, get_settings
from proprisk_swarm.protocols import (
    AgentProtocol,
    EventBusProtocol,
    GraphRAGProtocol,
    IngestionPipelineProtocol,
    MCPServerProtocol,
    ValuationEngineProtocol,
)
from proprisk_swarm.storage import (
    DealStore,
    SubsystemCache,
    cached,
)

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
]
