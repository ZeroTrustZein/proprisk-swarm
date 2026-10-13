"""Comprehensive tests for PostgreSQL Clean, Validate, and SQL Export pipeline."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from click.testing import CliRunner

from proprisk_swarm.cli import cli
from proprisk_swarm.storage.deal_store import DealStore
from proprisk_swarm.types.property import PropertyDeal, DealStatus


def test_clean_str_null_bytes_and_whitespace():
    """Verify null bytes stripped and whitespace trimmed."""
    raw = " \x00 Austin Tower \x00 "
    assert DealStore._clean_str(raw) == "Austin Tower"


def test_clean_and_validate_raw_export_success(sample_deal: PropertyDeal):
    """Verify clean_and_validate_raw_export passes on valid deal payload."""
    deal_dict = sample_deal.model_dump()
    raw = {
        "deal_id": sample_deal.id,
        "deal": deal_dict,
        "memo": {"recommendation": "approved\x00"},
        "valuation": {"unlevered_irr": 0.12},
        "deeds": [{"parcel_number": "12-345\x00"}],
        "filings": [{"cik": "0001234567 "}],
    }
    result = DealStore.clean_and_validate_raw_export(raw)
    assert result["is_valid"] is True
    assert len(result["errors"]) == 0
    cleaned = result["cleaned_data"]
    assert cleaned["deal_id"] == sample_deal.id
    assert cleaned["memo"]["recommendation"] == "approved"
    assert cleaned["deeds"][0]["parcel_number"] == "12-345"
    assert cleaned["filings"][0]["cik"] == "0001234567"


def test_clean_and_validate_raw_export_invalid():
    """Verify validation flags negative price and missing deal."""
    raw = {
        "deal_id": "",
        "deal": {
            "title": "",
            "target_purchase_price": -5000,
        },
    }
    result = DealStore.clean_and_validate_raw_export(raw)
    assert result["is_valid"] is False
    assert any("deal_id" in err for err in result["errors"])
    assert any("title" in err for err in result["errors"])
    assert any("Negative target_purchase_price" in err for err in result["errors"])


def test_export_to_sql_valid(sample_deal: PropertyDeal):
    """Verify export_to_sql produces valid PostgreSQL DDL and DML statements."""
    store = DealStore()
    store.save_deal(sample_deal)

    sql = store.export_to_sql(sample_deal.id, schema="real_estate_dw")
    assert "CREATE SCHEMA IF NOT EXISTS real_estate_dw;" in sql
    assert "CREATE TABLE IF NOT EXISTS real_estate_dw.deals" in sql
    assert f"INSERT INTO real_estate_dw.deals" in sql
    assert f"ON CONFLICT (deal_id) DO UPDATE" in sql
    assert sample_deal.id in sql


def test_export_to_sql_nonexistent_deal():
    """Verify export_to_sql raises KeyError when deal missing."""
    store = DealStore()
    with pytest.raises(KeyError):
        store.export_to_sql("nonexistent-deal-999")


def test_cli_export_sql_and_validate_export(sample_deal: PropertyDeal, tmp_path: Path):
    """Verify export-sql and validate-export CLI subcommands."""
    runner = CliRunner()

    store_file = tmp_path / "store.json"
    store = DealStore(persistence_path=store_file)
    store.save_deal(sample_deal)
    store.save_to_disk()

    sql_out = tmp_path / "out.sql"
    result = runner.invoke(
        cli,
        [
            "export-sql",
            "--deal-id",
            sample_deal.id,
            "--store-path",
            str(store_file),
            "--schema",
            "dw",
            "-o",
            str(sql_out),
        ],
    )
    assert result.exit_code == 0
    assert sql_out.exists()
    content = sql_out.read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS dw;" in content

    # Test validate-export CLI command
    export_json = tmp_path / "raw.json"
    export_json.write_text(
        json.dumps(
            {
                "deal_id": sample_deal.id,
                "deal": {
                    "title": "Clean Office \x00",
                    "target_purchase_price": 1000000,
                    "in_place_noi": 60000,
                },
            }
        ),
        encoding="utf-8",
    )
    cleaned_out = tmp_path / "cleaned.json"
    val_result = runner.invoke(
        cli,
        ["validate-export", str(export_json), "-o", str(cleaned_out)],
    )
    assert val_result.exit_code == 0
    assert "Export successfully cleaned and validated" in val_result.output
    assert cleaned_out.exists()
