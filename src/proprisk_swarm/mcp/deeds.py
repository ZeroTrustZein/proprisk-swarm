"""Municipal deeds and land registry MCP server."""

from __future__ import annotations

from typing import Any, Dict
from proprisk_swarm.mcp.base import BaseMCPServer


class MunicipalDeedsMCP(BaseMCPServer):
    """MCP server providing municipal deed lookups and title encumbrance verification."""

    def __init__(self, name: str = "municipal-deeds") -> None:
        super().__init__(name=name)
        self._register_default_tools()
        self._register_default_resources()

    def _register_default_tools(self) -> None:
        self.register_tool(
            name="search_deeds",
            description="Query municipal deed transfer records by parcel ID or address.",
            parameters={
                "type": "object",
                "properties": {
                    "parcel_id": {"type": "string"},
                    "county": {"type": "string"},
                },
                "required": ["parcel_id"],
            },
            handler=self._handle_search_deeds,
        )

        self.register_tool(
            name="verify_title_chain",
            description="Verify unbroken chain of title and check for clouds on legal title.",
            parameters={
                "type": "object",
                "properties": {
                    "parcel_id": {"type": "string"},
                    "lookback_years": {"type": "integer", "default": 30},
                },
                "required": ["parcel_id"],
            },
            handler=self._handle_verify_title_chain,
        )

        self.register_tool(
            name="check_easements",
            description="Retrieve recorded utility, access, or conservation easements.",
            parameters={
                "type": "object",
                "properties": {
                    "parcel_id": {"type": "string"},
                },
                "required": ["parcel_id"],
            },
            handler=self._handle_check_easements,
        )

    def _register_default_resources(self) -> None:
        self.register_resource(
            uri="deeds://records/parcels",
            name="Municipal Land Records Registry",
        )

    def _handle_search_deeds(self, args: Dict[str, Any]) -> Dict[str, Any]:
        parcel_id = args.get("parcel_id", "")
        county = args.get("county", "Travis")
        # Deterministic deed records
        records = [
            {
                "parcel_number": parcel_id,
                "grantor": "Apex Holdings LP",
                "grantee": "Metropolitan Realty LLC",
                "deed_type": "special_warranty",
                "consideration": 45000000.0,
                "recording_date": "2021-06-15",
                "county": county,
                "book_page": "Vol 1402, Pg 88",
            },
            {
                "parcel_number": parcel_id,
                "grantor": "Heritage Ranch Partners",
                "grantee": "Apex Holdings LP",
                "deed_type": "warranty",
                "consideration": 32000000.0,
                "recording_date": "2015-11-20",
                "county": county,
                "book_page": "Vol 1105, Pg 42",
            },
        ]
        return {"parcel_id": parcel_id, "county": county, "deeds": records, "count": len(records)}

    def _handle_verify_title_chain(self, args: Dict[str, Any]) -> Dict[str, Any]:
        parcel_id = args.get("parcel_id", "")
        lookback = args.get("lookback_years", 30)
        return {
            "parcel_id": parcel_id,
            "lookback_years": lookback,
            "chain_status": "clear",
            "gaps_found": False,
            "title_clouds": [],
            "last_certified": "2024-01-10",
        }

    def _handle_check_easements(self, args: Dict[str, Any]) -> Dict[str, Any]:
        parcel_id = args.get("parcel_id", "")
        easements = [
            {"type": "utility", "grantee": "City Power & Light", "width_ft": 10.0, "impact": "low"},
            {"type": "drainage", "grantee": "Municipal Water District", "width_ft": 15.0, "impact": "low"},
        ]
        return {
            "parcel_id": parcel_id,
            "easements": easements,
            "has_restrictive_easements": False,
        }
