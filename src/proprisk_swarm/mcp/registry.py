"""MCP Server Registry for aggregating and routing tool invocations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from proprisk_swarm.protocols import MCPServerProtocol
from proprisk_swarm.mcp.deeds import MunicipalDeedsMCP
from proprisk_swarm.mcp.sec import SecFilingsMCP
from proprisk_swarm.mcp.zoning import ZoningOrdinanceMCP


class MCPRegistry:
    """Central registry managing connected MCP servers."""

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerProtocol] = {}

    def register_server(self, server: MCPServerProtocol) -> None:
        """Register an MCP server instance."""
        self._servers[server.server_name] = server

    def get_server(self, name: str) -> Optional[MCPServerProtocol]:
        """Retrieve server by registered name."""
        return self._servers.get(name)

    def list_servers(self) -> List[str]:
        """List registered server names."""
        return list(self._servers.keys())

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool invocation to specified server."""
        server = self.get_server(server_name)
        if not server:
            return {
                "is_error": True,
                "error": f"Server '{server_name}' not found in registry.",
                "content": [],
            }
        return server.call_tool(tool_name, arguments)

    @classmethod
    def create_default(cls) -> MCPRegistry:
        """Factory initializing default municipal deeds, SEC, and zoning servers."""
        reg = cls()
        reg.register_server(MunicipalDeedsMCP())
        reg.register_server(SecFilingsMCP())
        reg.register_server(ZoningOrdinanceMCP())
        return reg
