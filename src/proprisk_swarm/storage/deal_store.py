"""Persistence and repository store for property deals, valuation outputs, and diligence memos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from proprisk_swarm.types.financial import DCFValuationResult
from proprisk_swarm.types.ingestion import DeedRecord, OfferingMemorandum, SECFiling
from proprisk_swarm.types.property import DealStatus, PropertyDeal, PropertyType
from proprisk_swarm.types.risk import UnderwritingMemo


class DealStore:
    """Repository managing lifecycle persistence of real estate deals and underwriting artifacts."""

    def __init__(self, persistence_path: Optional[Path | str] = None) -> None:
        self._persistence_path = Path(persistence_path) if persistence_path else None
        self._deals: Dict[str, PropertyDeal] = {}
        self._memos: Dict[str, UnderwritingMemo] = {}
        self._valuations: Dict[str, DCFValuationResult] = {}
        self._deeds: Dict[str, List[DeedRecord]] = {}
        self._filings: Dict[str, List[SECFiling]] = {}
        self._oms: Dict[str, OfferingMemorandum] = {}

    # -------------------------------------------------------------------------
    # Property Deals
    # -------------------------------------------------------------------------

    def save_deal(self, deal: PropertyDeal) -> None:
        """Upsert a property deal record."""
        self._deals[deal.id] = deal

    def get_deal(self, deal_id: str) -> Optional[PropertyDeal]:
        """Retrieve deal by ID."""
        return self._deals.get(deal_id)

    def list_deals(
        self,
        status: Optional[DealStatus] = None,
        property_type: Optional[PropertyType] = None,
    ) -> List[PropertyDeal]:
        """List deals matching optional status or type criteria."""
        results = list(self._deals.values())
        if status is not None:
            results = [d for d in results if d.status == status]
        if property_type is not None:
            results = [d for d in results if d.property_type == property_type]
        return results

    def delete_deal(self, deal_id: str) -> bool:
        """Remove deal and related stored artifacts."""
        existed = deal_id in self._deals
        self._deals.pop(deal_id, None)
        self._memos.pop(deal_id, None)
        self._valuations.pop(deal_id, None)
        self._deeds.pop(deal_id, None)
        self._oms.pop(deal_id, None)
        return existed

    # -------------------------------------------------------------------------
    # Underwriting Memos & Valuations
    # -------------------------------------------------------------------------

    def save_memo(self, memo: UnderwritingMemo) -> None:
        """Store synthesized investment memo."""
        self._memos[memo.deal_id] = memo

    def get_memo(self, deal_id: str) -> Optional[UnderwritingMemo]:
        """Retrieve latest investment memo for a deal."""
        return self._memos.get(deal_id)

    def list_memos(self) -> List[UnderwritingMemo]:
        """Retrieve all stored investment memos."""
        return list(self._memos.values())

    def save_valuation(self, deal_id: str, valuation: DCFValuationResult) -> None:
        """Store DCF modeling output."""
        self._valuations[deal_id] = valuation

    def get_valuation(self, deal_id: str) -> Optional[DCFValuationResult]:
        """Retrieve DCF valuation output for a deal."""
        return self._valuations.get(deal_id)

    # -------------------------------------------------------------------------
    # Ingestion Artifacts
    # -------------------------------------------------------------------------

    def add_deed(self, deal_id: str, deed: DeedRecord) -> None:
        """Associate deed record with deal."""
        self._deeds.setdefault(deal_id, []).append(deed)

    def get_deeds(self, deal_id: str) -> List[DeedRecord]:
        """Retrieve recorded deeds for a deal."""
        return self._deeds.get(deal_id, [])

    def add_filing(self, deal_id: str, filing: SECFiling) -> None:
        """Associate SEC filing record with deal."""
        self._filings.setdefault(deal_id, []).append(filing)

    def get_filings(self, deal_id: str) -> List[SECFiling]:
        """Retrieve recorded SEC filings for a deal."""
        return self._filings.get(deal_id, [])

    def save_om(self, om: OfferingMemorandum) -> None:
        """Store offering memorandum."""
        self._oms[om.deal_id] = om

    def get_om(self, deal_id: str) -> Optional[OfferingMemorandum]:
        """Retrieve offering memorandum for a deal."""
        return self._oms.get(deal_id)

    # -------------------------------------------------------------------------
    # Aggregate Deal Audit Package
    # -------------------------------------------------------------------------

    def export_deal_package(self, deal_id: str) -> Optional[Dict[str, Any]]:
        """Assemble all diligence and financial underwriting outputs into a complete audit package."""
        deal = self._deals.get(deal_id)
        if not deal:
            return None

        memo = self._memos.get(deal_id)
        val = self._valuations.get(deal_id)
        deeds = self._deeds.get(deal_id, [])
        filings = self._filings.get(deal_id, [])
        om = self._oms.get(deal_id)

        return {
            "deal_id": deal_id,
            "title": deal.title,
            "deal": deal.model_dump(mode="json"),
            "memo": memo.model_dump(mode="json") if memo else None,
            "valuation": val.model_dump(mode="json") if val else None,
            "deeds": [d.model_dump(mode="json") for d in deeds],
            "filings": [f.model_dump(mode="json") for f in filings],
            "offering_memorandum": om.model_dump(mode="json") if om else None,
        }

    def import_deal_package(self, package: Dict[str, Any]) -> None:
        """Import a cleaned and validated raw export package into DealStore."""
        deal_id = package.get("deal_id")
        if not deal_id:
            return

        deal_data = package.get("deal")
        if deal_data and isinstance(deal_data, dict):
            try:
                deal = PropertyDeal.model_validate(deal_data)
                self.save_deal(deal)
            except Exception:
                pass

        memo_data = package.get("memo")
        if memo_data and isinstance(memo_data, dict):
            try:
                memo = UnderwritingMemo.model_validate(memo_data)
                self.save_memo(memo)
            except Exception:
                pass

        val_data = package.get("valuation")
        if val_data and isinstance(val_data, dict):
            try:
                val = DCFValuationResult.model_validate(val_data)
                self.save_valuation(deal_id, val)
            except Exception:
                pass

        deeds = package.get("deeds", [])
        if isinstance(deeds, list):
            for d in deeds:
                try:
                    deed = DeedRecord.model_validate(d)
                    self.add_deed(deal_id, deed)
                except Exception:
                    pass

        filings = package.get("filings", [])
        if isinstance(filings, list):
            for f in filings:
                try:
                    filing = SECFiling.model_validate(f)
                    self.add_filing(deal_id, filing)
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Clean, Validate & SQL Warehouse Export (PostgreSQL)
    # -------------------------------------------------------------------------

    @staticmethod
    def _clean_str(val: str) -> str:
        return val.replace("\x00", "").strip()

    @classmethod
    def _clean_dict(cls, data: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return None
        return {k: (cls._clean_str(v) if isinstance(v, str) else v) for k, v in data.items()}

    @classmethod
    def _clean_record_list(cls, records: Any) -> List[Dict[str, Any]]:
        if not isinstance(records, list):
            return []
        return [
            {k: (cls._clean_str(v) if isinstance(v, str) else v) for k, v in d.items()}
            for d in records
            if isinstance(d, dict)
        ]

    @staticmethod
    def _coerce_float(
        val: Any,
        name: str,
        errors: List[str],
        warnings: Optional[List[str]] = None,
        check_negative: bool = False,
        check_zero: bool = False,
        default: float = 0.0,
    ) -> float:
        try:
            num = float(val) if val is not None else default
            if check_negative and num < 0:
                errors.append(f"Negative {name}: {num}")
            elif check_zero and num == 0.0 and warnings is not None:
                warnings.append(f"Zero {name} recorded.")
            return num
        except (ValueError, TypeError):
            errors.append(f"Invalid non-numeric {name}: {val}")
            return default

    @staticmethod
    def sql_quote(val: Any) -> str:
        """Escape and quote Python values for PostgreSQL SQL expressions."""
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, (dict, list)):
            escaped = json.dumps(val, default=str).replace("'", "''")
            return f"'{escaped}'::jsonb"
        escaped = str(val).replace("'", "''")
        return f"'{escaped}'"

    @classmethod
    def clean_and_validate_raw_export(cls, raw_export: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate raw deal export dictionary for storage or SQL export.

        Performs:
        - Strips whitespace, null bytes, and control characters from text fields
        - Coerces and validates numerical fields (purchase_price, in_place_noi, total_units, consideration)
        - Enforces schema invariants (presence of deal_id, deal.title, non-negative purchase price)
        - Normalizes nested dictionary and list structures
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(raw_export, dict):
            return {
                "is_valid": False,
                "cleaned_data": {},
                "errors": ["Raw export payload must be a dictionary."],
                "warnings": [],
            }

        cleaned: Dict[str, Any] = {}

        # 1. Validate deal_id
        deal_id = raw_export.get("deal_id")
        if not deal_id or not isinstance(deal_id, str) or not deal_id.strip():
            errors.append("Missing or invalid 'deal_id' in export payload.")
            clean_deal_id = ""
        else:
            clean_deal_id = cls._clean_str(deal_id)
        cleaned["deal_id"] = clean_deal_id

        # 2. Clean & validate deal
        deal_data = raw_export.get("deal")
        clean_deal = cls._clean_dict(deal_data)
        if clean_deal is None:
            errors.append("Missing or invalid 'deal' dictionary in export payload.")
            cleaned["deal"] = {}
        else:
            title = clean_deal.get("title")
            if not title or not isinstance(title, str) or not title.strip():
                errors.append("Deal missing required non-empty 'title'.")

            clean_deal["target_purchase_price"] = cls._coerce_float(
                clean_deal.get("target_purchase_price"),
                name="target_purchase_price",
                errors=errors,
                warnings=warnings,
                check_negative=True,
                check_zero=True,
            )

            clean_deal["in_place_noi"] = cls._coerce_float(
                clean_deal.get("in_place_noi"),
                name="in_place_noi",
                errors=errors,
            )

            cleaned["deal"] = clean_deal
            cleaned["title"] = clean_deal.get("title", raw_export.get("title", ""))

        # 3. Clean memo, valuation, offering memorandum
        cleaned["memo"] = cls._clean_dict(raw_export.get("memo"))
        cleaned["valuation"] = cls._clean_dict(raw_export.get("valuation"))
        cleaned["offering_memorandum"] = cls._clean_dict(raw_export.get("offering_memorandum"))

        # 4. Clean deeds & filings
        cleaned["deeds"] = cls._clean_record_list(raw_export.get("deeds"))
        cleaned["filings"] = cls._clean_record_list(raw_export.get("filings"))

        return {
            "is_valid": len(errors) == 0,
            "cleaned_data": cleaned,
            "errors": errors,
            "warnings": warnings,
        }

    def export_to_sql(self, deal_id: str, schema: str = "public") -> str:
        """Generate PostgreSQL DDL and INSERT / ON CONFLICT SQL statements for the deal package.

        Validates the raw export, sanitizes attributes, and produces PostgreSQL-compatible
        SQL scripts for relational warehouse synchronization.
        """
        pkg = self.export_deal_package(deal_id)
        if not pkg:
            raise KeyError(f"Deal '{deal_id}' not found in DealStore.")

        validation = self.clean_and_validate_raw_export(pkg)
        if not validation["is_valid"]:
            raise ValueError(f"Cannot export invalid deal package: {validation['errors']}")

        cleaned = validation["cleaned_data"]
        deal = cleaned["deal"]
        memo = cleaned["memo"]
        val = cleaned["valuation"]
        deeds = cleaned["deeds"]
        filings = cleaned["filings"]
        sql_quote = self.sql_quote

        lines: List[str] = [
            f"-- PostgreSQL Deal Export for: {deal_id}",
            f"-- Schema: {schema}",
            "",
            f"CREATE SCHEMA IF NOT EXISTS {schema};",
            "",
            f"CREATE TABLE IF NOT EXISTS {schema}.deals (",
            "    deal_id TEXT PRIMARY KEY,",
            "    title TEXT NOT NULL,",
            "    property_type TEXT,",
            "    status TEXT,",
            "    target_purchase_price NUMERIC(18, 2),",
            "    in_place_noi NUMERIC(18, 2),",
            "    total_units INTEGER,",
            "    payload JSONB,",
            "    exported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            ");",
            "",
            f"CREATE TABLE IF NOT EXISTS {schema}.underwriting_memos (",
            f"    deal_id TEXT PRIMARY KEY REFERENCES {schema}.deals(deal_id) ON DELETE CASCADE,",
            "    recommendation TEXT,",
            "    risk_findings_count INTEGER,",
            "    payload JSONB,",
            "    exported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            ");",
            "",
            f"CREATE TABLE IF NOT EXISTS {schema}.valuations (",
            f"    deal_id TEXT PRIMARY KEY REFERENCES {schema}.deals(deal_id) ON DELETE CASCADE,",
            "    net_present_value NUMERIC(18, 2),",
            "    unlevered_irr NUMERIC(8, 4),",
            "    levered_irr NUMERIC(8, 4),",
            "    equity_multiple NUMERIC(8, 4),",
            "    payload JSONB,",
            "    exported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            ");",
            "",
            f"CREATE TABLE IF NOT EXISTS {schema}.deeds (",
            "    deed_id TEXT PRIMARY KEY,",
            f"    deal_id TEXT REFERENCES {schema}.deals(deal_id) ON DELETE CASCADE,",
            "    parcel_number TEXT,",
            "    grantor TEXT,",
            "    grantee TEXT,",
            "    consideration_amount NUMERIC(18, 2),",
            "    payload JSONB,",
            "    exported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            ");",
            "",
            f"CREATE TABLE IF NOT EXISTS {schema}.sec_filings (",
            "    filing_id TEXT PRIMARY KEY,",
            f"    deal_id TEXT REFERENCES {schema}.deals(deal_id) ON DELETE CASCADE,",
            "    cik TEXT,",
            "    company_name TEXT,",
            "    form_type TEXT,",
            "    payload JSONB,",
            "    exported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            ");",
            "",
            "-- Upsert Deal",
            f"INSERT INTO {schema}.deals (deal_id, title, property_type, status, target_purchase_price, in_place_noi, total_units, payload)",
            f"VALUES ({sql_quote(deal_id)}, {sql_quote(deal.get('title'))}, {sql_quote(deal.get('property_type'))}, {sql_quote(deal.get('status'))}, {sql_quote(deal.get('target_purchase_price'))}, {sql_quote(deal.get('in_place_noi'))}, {sql_quote(deal.get('unit_mix', {}).get('total_units') if isinstance(deal.get('unit_mix'), dict) else None)}, {sql_quote(deal)})",
            "ON CONFLICT (deal_id) DO UPDATE SET",
            "    title = EXCLUDED.title,",
            "    property_type = EXCLUDED.property_type,",
            "    status = EXCLUDED.status,",
            "    target_purchase_price = EXCLUDED.target_purchase_price,",
            "    in_place_noi = EXCLUDED.in_place_noi,",
            "    total_units = EXCLUDED.total_units,",
            "    payload = EXCLUDED.payload,",
            "    exported_at = CURRENT_TIMESTAMP;",
        ]

        if memo:
            recommendation = memo.get("recommendation")
            findings_count = (
                len(memo.get("risk_findings", []))
                if isinstance(memo.get("risk_findings"), list)
                else 0
            )
            lines.extend(
                [
                    "",
                    "-- Upsert Underwriting Memo",
                    f"INSERT INTO {schema}.underwriting_memos (deal_id, recommendation, risk_findings_count, payload)",
                    f"VALUES ({sql_quote(deal_id)}, {sql_quote(recommendation)}, {sql_quote(findings_count)}, {sql_quote(memo)})",
                    "ON CONFLICT (deal_id) DO UPDATE SET",
                    "    recommendation = EXCLUDED.recommendation,",
                    "    risk_findings_count = EXCLUDED.risk_findings_count,",
                    "    payload = EXCLUDED.payload,",
                    "    exported_at = CURRENT_TIMESTAMP;",
                ]
            )

        if val:
            metrics = val.get("metrics", {}) if isinstance(val.get("metrics"), dict) else {}
            npv = val.get("net_present_value")
            unlev = metrics.get("unlevered_irr")
            lev = metrics.get("levered_irr")
            em = metrics.get("equity_multiple")
            lines.extend(
                [
                    "",
                    "-- Upsert Valuation",
                    f"INSERT INTO {schema}.valuations (deal_id, net_present_value, unlevered_irr, levered_irr, equity_multiple, payload)",
                    f"VALUES ({sql_quote(deal_id)}, {sql_quote(npv)}, {sql_quote(unlev)}, {sql_quote(lev)}, {sql_quote(em)}, {sql_quote(val)})",
                    "ON CONFLICT (deal_id) DO UPDATE SET",
                    "    net_present_value = EXCLUDED.net_present_value,",
                    "    unlevered_irr = EXCLUDED.unlevered_irr,",
                    "    levered_irr = EXCLUDED.levered_irr,",
                    "    equity_multiple = EXCLUDED.equity_multiple,",
                    "    payload = EXCLUDED.payload,",
                    "    exported_at = CURRENT_TIMESTAMP;",
                ]
            )

        for idx, deed in enumerate(deeds):
            deed_id = deed.get("id") or f"{deal_id}-deed-{idx}"
            lines.extend(
                [
                    "",
                    f"-- Upsert Deed {deed_id}",
                    f"INSERT INTO {schema}.deeds (deed_id, deal_id, parcel_number, grantor, grantee, consideration_amount, payload)",
                    f"VALUES ({sql_quote(deed_id)}, {sql_quote(deal_id)}, {sql_quote(deed.get('parcel_number'))}, {sql_quote(deed.get('grantor'))}, {sql_quote(deed.get('grantee'))}, {sql_quote(deed.get('consideration_amount'))}, {sql_quote(deed)})",
                    "ON CONFLICT (deed_id) DO UPDATE SET",
                    "    parcel_number = EXCLUDED.parcel_number,",
                    "    grantor = EXCLUDED.grantor,",
                    "    grantee = EXCLUDED.grantee,",
                    "    consideration_amount = EXCLUDED.consideration_amount,",
                    "    payload = EXCLUDED.payload,",
                    "    exported_at = CURRENT_TIMESTAMP;",
                ]
            )

        for idx, filing in enumerate(filings):
            filing_id = filing.get("id") or f"{deal_id}-filing-{idx}"
            lines.extend(
                [
                    "",
                    f"-- Upsert SEC Filing {filing_id}",
                    f"INSERT INTO {schema}.sec_filings (filing_id, deal_id, cik, company_name, form_type, payload)",
                    f"VALUES ({sql_quote(filing_id)}, {sql_quote(deal_id)}, {sql_quote(filing.get('cik'))}, {sql_quote(filing.get('company_name'))}, {sql_quote(filing.get('form_type'))}, {sql_quote(filing)})",
                    "ON CONFLICT (filing_id) DO UPDATE SET",
                    "    cik = EXCLUDED.cik,",
                    "    company_name = EXCLUDED.company_name,",
                    "    form_type = EXCLUDED.form_type,",
                    "    payload = EXCLUDED.payload,",
                    "    exported_at = CURRENT_TIMESTAMP;",
                ]
            )

        return "\n".join(lines) + "\n"

    # -------------------------------------------------------------------------
    # Disk Persistence
    # -------------------------------------------------------------------------

    def save_to_disk(self, destination: Optional[Path | str] = None) -> Path:
        """Serialize repository state to disk as JSON."""
        target_path = Path(destination) if destination else self._persistence_path
        if not target_path:
            raise ValueError("No destination path specified for DealStore persistence.")

        if target_path.is_dir() or (not target_path.suffix and target_path.exists()):
            target_path = target_path / "deal_store.json"
        elif not target_path.suffix:
            target_path = target_path / "deal_store.json"

        target_path.parent.mkdir(parents=True, exist_ok=True)
        dump_data = {
            "deals": {k: v.model_dump(mode="json") for k, v in self._deals.items()},
            "memos": {k: v.model_dump(mode="json") for k, v in self._memos.items()},
            "valuations": {k: v.model_dump(mode="json") for k, v in self._valuations.items()},
            "deeds": {k: [d.model_dump(mode="json") for d in v] for k, v in self._deeds.items()},
            "filings": {
                k: [f.model_dump(mode="json") for f in v] for k, v in self._filings.items()
            },
            "oms": {k: v.model_dump(mode="json") for k, v in self._oms.items()},
        }
        target_path.write_text(json.dumps(dump_data, indent=2), encoding="utf-8")
        return target_path

    def load_from_disk(self, source: Optional[Path | str] = None) -> int:
        """Hydrate repository state from JSON disk export."""
        target_path = Path(source) if source else self._persistence_path
        if not target_path:
            return 0

        if target_path.is_dir():
            target_path = target_path / "deal_store.json"
        elif not target_path.suffix and not target_path.exists():
            target_path = target_path / "deal_store.json"

        if not target_path.exists():
            return 0

        raw_text = target_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        loaded_count = 0
        for deal_id, d_data in data.get("deals", {}).items():
            self._deals[deal_id] = PropertyDeal.model_validate(d_data)
            loaded_count += 1

        for deal_id, m_data in data.get("memos", {}).items():
            self._memos[deal_id] = UnderwritingMemo.model_validate(m_data)

        for deal_id, v_data in data.get("valuations", {}).items():
            self._valuations[deal_id] = DCFValuationResult.model_validate(v_data)

        for deal_id, d_list in data.get("deeds", {}).items():
            self._deeds[deal_id] = [DeedRecord.model_validate(item) for item in d_list]

        for deal_id, f_list in data.get("filings", {}).items():
            self._filings[deal_id] = [SECFiling.model_validate(item) for item in f_list]

        for deal_id, om_data in data.get("oms", {}).items():
            self._oms[deal_id] = OfferingMemorandum.model_validate(om_data)

        return loaded_count

    def clear(self) -> None:
        """Clear all stored state."""
        self._deals.clear()
        self._memos.clear()
        self._valuations.clear()
        self._deeds.clear()
        self._filings.clear()
        self._oms.clear()

