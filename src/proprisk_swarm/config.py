"""Configuration and environment settings for PropRisk Swarm."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for custom MCP servers."""

    deeds_host: str = Field(default="127.0.0.1", description="Municipal deeds MCP server host")
    deeds_port: int = Field(default=8201, description="Municipal deeds MCP server port")
    sec_host: str = Field(default="127.0.0.1", description="SEC/REIT filing MCP server host")
    sec_port: int = Field(default=8202, description="SEC/REIT filing MCP server port")
    zoning_host: str = Field(default="127.0.0.1", description="Zoning code MCP server host")
    zoning_port: int = Field(default=8203, description="Zoning code MCP server port")
    request_timeout_seconds: float = Field(
        default=30.0, description="MCP request timeout in seconds"
    )


class RAGConfig(BaseModel):
    """Configuration for Hybrid Graph-RAG pipeline."""

    vector_dimension: int = Field(default=1536, description="Embedding vector dimensionality")
    embedding_model: str = Field(
        default="text-embedding-3-small", description="Model name for embeddings"
    )
    chunk_size: int = Field(default=512, description="Target chunk token length")
    chunk_overlap: int = Field(default=64, description="Chunk token overlap")
    hybrid_alpha: float = Field(
        default=0.6, description="Weight between vector search (alpha) and sparse BM25 (1-alpha)"
    )
    graph_enabled: bool = Field(
        default=True, description="Enable knowledge graph relation traversal"
    )


class SwarmConfig(BaseModel):
    """Configuration for autonomous agent swarm execution."""

    max_concurrent_agents: int = Field(default=6, description="Maximum parallel agent workers")
    task_timeout_seconds: int = Field(
        default=120, description="Max execution time per agent subtask"
    )
    max_reflection_loops: int = Field(default=3, description="Maximum self-correction cycles")
    strict_audit_mode: bool = Field(
        default=True, description="Enforce strict citation grounding on all findings"
    )


class ValuationConfig(BaseModel):
    """Default underwriting parameters for DCF valuation engine."""

    default_holding_period_years: int = Field(
        default=5, description="Standard projection period in years"
    )
    default_discount_rate: float = Field(
        default=0.085, description="Discount rate for net present value"
    )
    default_exit_cap_rate: float = Field(
        default=0.0575, description="Terminal exit capitalization rate"
    )
    default_rent_growth_rate: float = Field(
        default=0.03, description="Annual pro forma rent escalation"
    )
    default_opex_growth_rate: float = Field(
        default=0.025, description="Annual operating expense inflation"
    )
    default_general_vacancy_rate: float = Field(
        default=0.05, description="Standard physical vacancy assumption"
    )


class PropRiskSettings(BaseModel):
    """Global configuration settings for PropRisk Swarm."""

    project_name: str = Field(default="proprisk-swarm", description="Application identifier")
    version: str = Field(default="0.1.0", description="Application release version")
    data_dir: Path = Field(default=Path("./data"), description="Root storage directory")
    log_level: str = Field(default="INFO", description="Logging verbosity")
    mcp: MCPServerConfig = Field(default_factory=MCPServerConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    swarm: SwarmConfig = Field(default_factory=SwarmConfig)
    valuation: ValuationConfig = Field(default_factory=ValuationConfig)

    @classmethod
    def from_env(cls) -> PropRiskSettings:
        """Construct settings instance populated from environment overrides."""
        log_level = os.getenv("PROPRISK_LOG_LEVEL", "INFO")
        data_dir = Path(os.getenv("PROPRISK_DATA_DIR", "./data"))

        mcp_cfg = MCPServerConfig(
            deeds_host=os.getenv("PROPRISK_MCP_DEEDS_HOST", "127.0.0.1"),
            deeds_port=int(os.getenv("PROPRISK_MCP_DEEDS_PORT", "8201")),
            sec_host=os.getenv("PROPRISK_MCP_SEC_HOST", "127.0.0.1"),
            sec_port=int(os.getenv("PROPRISK_MCP_SEC_PORT", "8202")),
            zoning_host=os.getenv("PROPRISK_MCP_ZONING_HOST", "127.0.0.1"),
            zoning_port=int(os.getenv("PROPRISK_MCP_ZONING_PORT", "8203")),
        )

        rag_cfg = RAGConfig(
            vector_dimension=int(os.getenv("PROPRISK_VECTOR_DIMENSION", "1536")),
            embedding_model=os.getenv("PROPRISK_EMBEDDING_MODEL", "text-embedding-3-small"),
        )

        swarm_cfg = SwarmConfig(
            max_concurrent_agents=int(os.getenv("PROPRISK_MAX_CONCURRENT_AGENTS", "6")),
            task_timeout_seconds=int(os.getenv("PROPRISK_TASK_TIMEOUT_SECONDS", "120")),
        )

        return cls(
            log_level=log_level,
            data_dir=data_dir,
            mcp=mcp_cfg,
            rag=rag_cfg,
            swarm=swarm_cfg,
        )


@lru_cache(maxsize=1)
def get_settings() -> PropRiskSettings:
    """Retrieve singleton global settings."""
    return PropRiskSettings.from_env()
