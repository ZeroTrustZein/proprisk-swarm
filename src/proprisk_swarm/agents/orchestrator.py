"""Swarm Orchestrator coordinating specialized diligence agents and warehouse synchronization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from proprisk_swarm.agents.base import BaseAgent
from proprisk_swarm.agents.specialized import (
    CreditRiskUnderwriterAgent,
    DCFValuationAgent,
    MunicipalDeedAuditorAgent,
    SecDiligenceAnalystAgent,
    ZoningComplianceAgent,
)
from proprisk_swarm.events.bus import EventBus
from proprisk_swarm.storage.deal_store import DealStore
from proprisk_swarm.types.agents import AgentRole
from proprisk_swarm.types.events import EventType


class SwarmOrchestrator(BaseAgent):
    """Central coordinator executing end-to-end multi-agent underwriting diligence."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        deal_store: Optional[DealStore] = None,
    ) -> None:
        super().__init__(
            role=AgentRole.SWARM_ORCHESTRATOR,
            supported_tasks=["underwrite", "run_diligence", "swarm_orchestration"],
        )
        self.bus = event_bus or EventBus()
        self.store = deal_store or DealStore()

        # Initialize worker agents
        self.deed_agent = MunicipalDeedAuditorAgent()
        self.sec_agent = SecDiligenceAnalystAgent()
        self.zoning_agent = ZoningComplianceAgent()
        self.valuation_agent = DCFValuationAgent()
        self.underwriter_agent = CreditRiskUnderwriterAgent()

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        deal_id = payload.get("deal_id", "DEAL-AUTO")
        return self.run_diligence_pipeline(deal_id, payload)

    def run_diligence_pipeline(self, deal_id: str, deal_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run synchronized diligence workflow across all agents and assemble warehouse export."""
        self.bus.publish(
            str(EventType.DEAL_CREATED),
            {"deal_id": deal_id, "payload": deal_payload},
        )

        # 1. Municipal Deed Audit
        deed_res = self.deed_agent.execute_task({
            "parcel_id": deal_payload.get("parcel_number", f"PARCEL-{deal_id}"),
            "county": deal_payload.get("county", "Travis"),
        })
        self.bus.publish(
            str(EventType.DEED_AUDIT_COMPLETED),
            {"deal_id": deal_id, "deeds_count": len(deed_res.get("deeds", []))},
        )

        # 2. SEC Diligence & Tenant Credit
        sec_res = self.sec_agent.execute_task({
            "cik": deal_payload.get("cik", "0001234567"),
            "tenant_name": deal_payload.get("anchor_tenant", "Primary Anchor Retail"),
        })
        self.bus.publish(
            str(EventType.SEC_FILING_INGESTED),
            {"deal_id": deal_id, "cik": sec_res.get("cik")},
        )

        # 3. Zoning & Land Use Compliance
        zoning_res = self.zoning_agent.execute_task({
            "zone_code": deal_payload.get("zone_code", "CBD"),
            "proposed_gfa": deal_payload.get("gross_leasable_area_sqft", 150000.0),
            "lot_area_sqft": deal_payload.get("lot_area_sqft", 25000.0),
        })

        # 4. DCF Valuation Modeling
        target_price = float(deal_payload.get("target_purchase_price", deal_payload.get("asking_price", 10000000.0)))
        val_res = self.valuation_agent.execute_task({
            "target_purchase_price": target_price,
            "in_place_noi": deal_payload.get("in_place_noi", target_price * 0.065),
            "discount_rate": deal_payload.get("discount_rate", 0.085),
            "terminal_cap_rate": deal_payload.get("terminal_cap_rate", 0.0575),
        })
        self.bus.publish(
            str(EventType.DCF_VALUATION_COMPLETED),
            {"deal_id": deal_id, "unlevered_irr": val_res.get("valuation", {}).get("unlevered_irr")},
        )

        # 5. IC Underwriting Memo Synthesis
        memo_res = self.underwriter_agent.execute_task({
            "deal_id": deal_id,
            "valuation": val_res.get("valuation", {}),
            "deal_title": deal_payload.get("title", f"Commercial Property: {deal_id}"),
        })
        self.bus.publish(
            str(EventType.UNDERWRITING_MEMO_GENERATED),
            {"deal_id": deal_id, "recommendation": memo_res.get("memo", {}).get("recommendation")},
        )

        # 6. Aggregate findings
        all_findings: List[Dict[str, Any]] = []
        for agent_res in [deed_res, sec_res, zoning_res, val_res]:
            all_findings.extend(agent_res.get("findings", []))

        # 7. Package raw export for warehouse clean/validate
        deal_dict = {
            "id": deal_id,
            "title": deal_payload.get("title", f"Commercial Property: {deal_id}"),
            "status": "underwriting",
            "target_purchase_price": target_price,
            "in_place_noi": deal_payload.get("in_place_noi", target_price * 0.065),
            "property_type": deal_payload.get("property_type", "multifamily"),
            "address": {
                "street_address": deal_payload.get("street_address", "100 Congress Ave"),
                "city": deal_payload.get("city", "Austin"),
                "state": deal_payload.get("state", "TX"),
                "postal_code": deal_payload.get("postal_code", "78701"),
            },
        }

        raw_export = {
            "deal_id": deal_id,
            "deal": deal_dict,
            "memo": memo_res.get("memo", {}),
            "valuation": val_res.get("valuation", {}),
            "deeds": deed_res.get("deeds", []),
            "filings": [
                {
                    "cik": sec_res.get("cik"),
                    "company_name": "Anchor REIT",
                    "filing_type": "10-K",
                    "fiscal_year": 2023,
                }
            ],
            "findings": all_findings,
            "zoning": zoning_res,
        }

        # 8. Clean and validate export payload
        validation = DealStore.clean_and_validate_raw_export(raw_export)

        return {
            "deal_id": deal_id,
            "status": "completed",
            "is_valid": validation["is_valid"],
            "validation": validation,
            "package": validation.get("cleaned_data", raw_export),
        }
