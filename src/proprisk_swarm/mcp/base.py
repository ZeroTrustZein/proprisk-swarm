"""Base MCP server implementation conforming to MCPServerProtocol."""

from __future__ import annotations

from typing import Any, Callable, Dict, List
from proprisk_swarm.protocols import MCPServerProtocol


class BaseMCPServer(MCPServerProtocol):
    """Abstract base class for in-memory / JSON-RPC Model Context Protocol servers."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._tools: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._tool_metadata: List[Dict[str, Any]] = []
        self._resources: List[Dict[str, Any]] = []

    @property
    def server_name(self) -> str:
        return self._name

    def register_tool(
        self, name: str, description: str, parameters: Dict[str, Any], handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Register a callable tool with its schema definition."""
        self._tools[name] = handler
        self._tool_metadata.append({
            "name": name,
            "description": description,
            "inputSchema": parameters,
        })

    def register_resource(self, uri: str, name: str, mime_type: str = "application/json") -> None:
        """Register an accessible resource endpoint."""
        self._resources.append({
            "uri": uri,
            "name": name,
            "mimeType": mime_type,
        })

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tool_metadata)

    def list_resources(self) -> List[Dict[str, Any]]:
        return list(self._resources)

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {
                "is_error": True,
                "error": f"Tool '{name}' not found on server '{self._name}'.",
                "content": [],
            }
        try:
            return self._tools[name](arguments)
        except Exception as exc:
            return {
                "is_error": True,
                "error": f"Tool execution failed: {exc}",
                "content": [],
            }
