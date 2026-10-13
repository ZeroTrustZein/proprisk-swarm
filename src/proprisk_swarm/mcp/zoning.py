"""Municipal zoning codes and land development regulation MCP server."""

from __future__ import annotations

from typing import Any, Dict
from proprisk_swarm.mcp.base import BaseMCPServer


class ZoningOrdinanceMCP(BaseMCPServer):
    """MCP server for zoning classification, FAR compliance, setbacks, and parking ratios."""

    def __init__(self, name: str = "zoning-ordinances") -> None:
        super().__init__(name=name)
        self._register_default_tools()
        self._register_default_resources()

    def _register_default_tools(self) -> None:
        self.register_tool(
            name="get_zoning_classification",
            description="Retrieve zoning district classification and permissible use categories.",
            parameters={
                "type": "object",
                "properties": {
                    "jurisdiction": {"type": "string"},
                    "zone_code": {"type": "string"},
                },
                "required": ["zone_code"],
            },
            handler=self._handle_get_zoning,
        )

        self.register_tool(
            name="verify_far_compliance",
            description="Calculate Floor Area Ratio (FAR) and verify compliance against zoning limits.",
            parameters={
                "type": "object",
                "properties": {
                    "proposed_gfa": {"type": "number"},
                    "lot_area_sqft": {"type": "number"},
                    "max_far": {"type": "number"},
                },
                "required": ["proposed_gfa", "lot_area_sqft", "max_far"],
            },
            handler=self._handle_verify_far,
        )

        self.register_tool(
            name="check_setback_requirements",
            description="Lookup minimum front, side, and rear yard setbacks for zoning district.",
            parameters={
                "type": "object",
                "properties": {
                    "zone_code": {"type": "string"},
                },
                "required": ["zone_code"],
            },
            handler=self._handle_check_setbacks,
        )

    def _register_default_resources(self) -> None:
        self.register_resource(
            uri="zoning://jurisdiction/ordinance",
            name="Municipal Land Development Code",
        )

    def _handle_get_zoning(self, args: Dict[str, Any]) -> Dict[str, Any]:
        zone_code = args.get("zone_code", "CBD")
        jurisdiction = args.get("jurisdiction", "Austin")
        return {
            "zone_code": zone_code,
            "jurisdiction": jurisdiction,
            "permitted_uses": ["multifamily", "office", "retail", "hotel"],
            "conditional_uses": ["nightclub", "data_center"],
            "max_base_far": 8.0,
            "max_bonus_far": 15.0,
            "max_height_ft": 400.0,
        }

    def _handle_verify_far(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gfa = float(args.get("proposed_gfa", 0.0))
        lot_area = float(args.get("lot_area_sqft", 1.0))
        max_far = float(args.get("max_far", 8.0))

        actual_far = round(gfa / max(lot_area, 1.0), 3)
        compliant = actual_far <= max_far
        unused_gfa = max(0.0, (max_far * lot_area) - gfa) if compliant else 0.0

        return {
            "proposed_gfa": gfa,
            "lot_area_sqft": lot_area,
            "actual_far": actual_far,
            "max_far": max_far,
            "is_compliant": compliant,
            "unused_allowable_gfa": unused_gfa,
        }

    def _handle_check_setbacks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        zone_code = args.get("zone_code", "CBD")
        return {
            "zone_code": zone_code,
            "front_setback_ft": 0.0,
            "side_setback_ft": 0.0,
            "rear_setback_ft": 10.0,
            "landscape_buffer_required": False,
        }
