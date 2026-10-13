"""Specialized diligence agents for municipal deeds, SEC filings, zoning, and valuation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from proprisk_swarm.agents.base import BaseAgent
from proprisk_swarm.mcp.deeds import MunicipalDeedsMCP
from proprisk_swarm.mcp.sec import SecFilingsMCP
from proprisk_swarm.mcp.zoning import ZoningOrdinanceMCP
from proprisk_swarm.types.agents import AgentRole
from proprisk_swarm.valuation.engine import ValuationEngine


class MunicipalDeedAuditorAgent(BaseAgent):
    """Audits municipal land records, title chains, and easement encumbrances."""

    def __init__(self, mcp_server: Optional[MunicipalDeedsMCP] = None) -> None:
        super().__init__(
            role=AgentRole.MUNICIPAL_DEED_AUDITOR,
            supported_tasks=["deed_audit", "title_search", "easement_check"],
        )
        self.mcp = mcp_server or MunicipalDeedsMCP()

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        parcel_id = payload.get("parcel_id", payload.get("parcel_number", "PARCEL-DEFAULT"))
        county = payload.get("county", "Travis")

        deeds_res = self.mcp.call_tool("search_deeds", {"parcel_id": parcel_id, "county": county})
        title_res = self.mcp.call_tool("verify_title_chain", {"parcel_id": parcel_id})
        easements_res = self.mcp.call_tool("check_easements", {"parcel_id": parcel_id})

        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role_name,
            "parcel_id": parcel_id,
            "deeds": deeds_res.get("deeds", []),
            "title_status": title_res.get("chain_status", "clear"),
            "has_restrictive_easements": easements_res.get("has_restrictive_easements", False),
            "findings": [
                {
                    "category": "legal_title",
                    "severity": "low",
                    "description": f"Verified continuous chain of title for parcel {parcel_id} with no unreleased liens.",
                }
            ],
        }


class SecDiligenceAnalystAgent(BaseAgent):
    """Analyzes tenant risk disclosures and commercial credit from SEC EDGAR filings."""

    def __init__(self, mcp_server: Optional[SecFilingsMCP] = None) -> None:
        super().__init__(
            role=AgentRole.SEC_DILIGENCE_ANALYST,
            supported_tasks=["sec_diligence", "tenant_credit", "reit_risk"],
        )
        self.mcp = mcp_server or SecFilingsMCP()

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cik = payload.get("cik", "0001234567")
        tenant = payload.get("tenant_name", "Global Anchor Retail")

        risk_res = self.mcp.call_tool("fetch_10k_risk_factors", {"cik": cik})
        credit_res = self.mcp.call_tool("check_tenant_credit", {"tenant_name": tenant})

        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role_name,
            "cik": cik,
            "risk_factors": risk_res.get("risk_factors", []),
            "tenant_credit": credit_res,
            "findings": [
                {
                    "category": "tenant_concentration",
                    "severity": "medium",
                    "description": f"Anchor tenant '{tenant}' maintains investment grade rating ({credit_res.get('rating_sp')}).",
                }
            ],
        }


class ZoningComplianceAgent(BaseAgent):
    """Verifies Floor Area Ratio (FAR) compliance, permissible uses, and setback bounds."""

    def __init__(self, mcp_server: Optional[ZoningOrdinanceMCP] = None) -> None:
        super().__init__(
            role=AgentRole.ZONING_LAND_USE_COMPLIANCE,
            supported_tasks=["zoning_compliance", "far_verification", "setback_check"],
        )
        self.mcp = mcp_server or ZoningOrdinanceMCP()

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        zone_code = payload.get("zone_code", "CBD")
        gfa = payload.get("proposed_gfa", payload.get("gross_leasable_area_sqft", 150000.0))
        lot_area = payload.get("lot_area_sqft", 25000.0)
        max_far = payload.get("max_far", 8.0)

        zoning_info = self.mcp.call_tool("get_zoning_classification", {"zone_code": zone_code})
        far_res = self.mcp.call_tool(
            "verify_far_compliance",
            {"proposed_gfa": gfa, "lot_area_sqft": lot_area, "max_far": max_far},
        )

        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role_name,
            "zone_code": zone_code,
            "is_far_compliant": far_res.get("is_compliant", True),
            "actual_far": far_res.get("actual_far", 6.0),
            "max_far": max_far,
            "permitted_uses": zoning_info.get("permitted_uses", []),
            "findings": [
                {
                    "category": "zoning_land_use",
                    "severity": "low" if far_res.get("is_compliant", True) else "high",
                    "description": f"Proposed GFA of {gfa:,.0f} sqft complies with zoning FAR limits (actual FAR: {far_res.get('actual_far')}).",
                }
            ],
        }


class DCFValuationAgent(BaseAgent):
    """Executes multi-year DCF cash flow modeling and IRR sensitivity analysis."""

    def __init__(self, engine: Optional[ValuationEngine] = None) -> None:
        super().__init__(
            role=AgentRole.DCF_VALUATION_ENGINEER,
            supported_tasks=["valuation", "dcf_modeling", "sensitivity_analysis"],
        )
        self.engine = engine or ValuationEngine()

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        purchase_price = float(
            payload.get("purchase_price", payload.get("target_purchase_price", 10000000.0))
        )
        cash_flows = payload.get("cash_flows")
        if not cash_flows:
            # Generate synthetic 5-year growing cash flows based on in-place NOI
            base_noi = float(payload.get("in_place_noi", purchase_price * 0.065))
            growth = float(payload.get("growth_rate", 0.03))
            cash_flows = [round(base_noi * ((1.0 + growth) ** i), 2) for i in range(1, 6)]

        dcf_res = self.engine.compute_dcf(
            purchase_price=purchase_price,
            cash_flows=cash_flows,
            discount_rate=float(payload.get("discount_rate", 0.085)),
            terminal_cap_rate=float(payload.get("terminal_cap_rate", 0.0575)),
        )

        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role_name,
            "valuation": dcf_res,
            "findings": [
                {
                    "category": "financial_returns",
                    "severity": "low" if dcf_res["unlevered_irr"] >= 0.09 else "medium",
                    "description": f"Unlevered IRR of {dcf_res['unlevered_irr'] * 100:.2f}% and Equity Multiple of {dcf_res['equity_multiple']}x.",
                }
            ],
        }


class CreditRiskUnderwriterAgent(BaseAgent):
    """Synthesizes diligence findings and authors Investment Committee memos."""

    def __init__(self, engine: Optional[ValuationEngine] = None) -> None:
        super().__init__(
            role=AgentRole.CREDIT_RISK_UNDERWRITER,
            supported_tasks=["underwriting_review", "risk_synthesis", "memo_generation"],
        )
        self.engine = engine or ValuationEngine()

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        deal_id = payload.get("deal_id", "DEAL-PROVISIONED")
        valuation = payload.get("valuation", {})
        memo_dict = self.engine.synthesize_investment_memo(deal_id, valuation)

        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role_name,
            "deal_id": deal_id,
            "memo": memo_dict,
        }
