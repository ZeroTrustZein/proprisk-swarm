"""SEC EDGAR filings and commercial tenant credit MCP server."""

from __future__ import annotations

from typing import Any, Dict
from proprisk_swarm.mcp.base import BaseMCPServer


class SecFilingsMCP(BaseMCPServer):
    """MCP server extracting REIT disclosures, lease exposures, and tenant risk."""

    def __init__(self, name: str = "sec-filings") -> None:
        super().__init__(name=name)
        self._register_default_tools()
        self._register_default_resources()

    def _register_default_tools(self) -> None:
        self.register_tool(
            name="fetch_10k_risk_factors",
            description="Extract Item 1A Risk Factors from commercial REIT 10-K filing.",
            parameters={
                "type": "object",
                "properties": {
                    "cik": {"type": "string"},
                    "year": {"type": "integer"},
                },
                "required": ["cik"],
            },
            handler=self._handle_fetch_10k_risk_factors,
        )

        self.register_tool(
            name="check_tenant_credit",
            description="Look up credit ratings and lease default risk for anchor tenants.",
            parameters={
                "type": "object",
                "properties": {
                    "tenant_name": {"type": "string"},
                },
                "required": ["tenant_name"],
            },
            handler=self._handle_check_tenant_credit,
        )

        self.register_tool(
            name="get_reit_covenants",
            description="Retrieve debt covenants and leverage limits for REIT borrower.",
            parameters={
                "type": "object",
                "properties": {
                    "cik": {"type": "string"},
                },
                "required": ["cik"],
            },
            handler=self._handle_get_reit_covenants,
        )

    def _register_default_resources(self) -> None:
        self.register_resource(
            uri="sec://edgar/filings",
            name="SEC EDGAR 10-K / 8-K Archive",
        )

    def _handle_fetch_10k_risk_factors(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cik = args.get("cik", "")
        year = args.get("year", 2023)
        risks = [
            {"topic": "interest_rates", "severity": "medium", "summary": "Rising benchmark rates may elevate debt financing costs and cap rates."},
            {"topic": "tenant_concentration", "severity": "high", "summary": "Top 3 anchor tenants represent 34% of aggregate portfolio base rental revenue."},
            {"topic": "environmental_climate", "severity": "low", "summary": "Physical flood and extreme weather risks mitigated by property casualty coverage."},
        ]
        return {"cik": cik, "fiscal_year": year, "risk_factors": risks}

    def _handle_check_tenant_credit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tenant = args.get("tenant_name", "")
        return {
            "tenant_name": tenant,
            "rating_sp": "BBB+",
            "rating_moodys": "Baa1",
            "investment_grade": True,
            "default_probability_5yr": 0.021,
            "credit_watch": "stable",
        }

    def _handle_get_reit_covenants(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cik = args.get("cik", "")
        return {
            "cik": cik,
            "max_debt_to_gross_assets": 0.60,
            "current_debt_to_gross_assets": 0.38,
            "min_fixed_charge_coverage": 1.50,
            "current_fixed_charge_coverage": 2.85,
            "covenant_compliant": True,
        }
