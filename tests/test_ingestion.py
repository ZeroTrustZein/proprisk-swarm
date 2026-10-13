"""Tests for Ingestion Pipeline subsystem."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from proprisk_swarm.ingestion.pipeline import IngestionPipeline
from proprisk_swarm.protocols import IngestionPipelineProtocol
from proprisk_swarm.types.ingestion import IngestionStatus


def test_ingestion_pipeline_protocol_conformance():
    """Verify IngestionPipeline satisfies IngestionPipelineProtocol."""
    pipeline = IngestionPipeline()
    assert isinstance(pipeline, IngestionPipelineProtocol)


def test_ingest_document_from_metadata(tmp_path: Path):
    """Verify document ingestion using metadata content."""
    pipeline = IngestionPipeline()
    raw_payload = json.dumps({"parcel_number": "123-45", "grantor": "Seller LP"})

    job_id = pipeline.ingest_document(
        source_path="virtual/deed.json",
        source_type="municipal_deed",
        metadata={"content": raw_payload},
    )

    assert job_id.startswith("job-")
    job = pipeline.get_job(job_id)
    assert job is not None
    assert job.status == IngestionStatus.COMPLETED
    assert job.extracted_records_count == 1
    assert len(pipeline.list_jobs()) >= 1


def test_ingest_document_from_file(tmp_path: Path):
    """Verify document ingestion from existing filesystem file."""
    doc_file = tmp_path / "filing.json"
    doc_file.write_text(json.dumps([{"cik": "0001", "item": "1A"}, {"cik": "0002"}]), encoding="utf-8")

    pipeline = IngestionPipeline()
    job_id = pipeline.ingest_document(
        source_path=str(doc_file),
        source_type="sec_10k",
    )

    job = pipeline.get_job(job_id)
    assert job is not None
    assert job.status == IngestionStatus.COMPLETED
    assert job.extracted_records_count == 2


def test_parse_payload_text_types():
    """Verify parsing non-JSON payloads into structured records."""
    pipeline = IngestionPipeline()

    # Empty payload
    empty_res = pipeline.parse_payload(b"", "deed")
    assert empty_res["record_count"] == 0

    # Deed text
    deed_res = pipeline.parse_payload(b"Warranty deed conveyed to Buyer", "deed")
    assert deed_res["record_count"] == 1
    assert deed_res["records"][0]["parcel_number"] == "PARCEL-EXTRACTED"

    # SEC text
    sec_res = pipeline.parse_payload(b"Item 1A Risk Factors: rising rates", "sec_10k")
    assert sec_res["record_count"] == 1
    assert sec_res["records"][0]["cik"] == "0000000000"

    # Generic text
    gen_res = pipeline.parse_payload(b"General underwriting guidelines", "other")
    assert gen_res["record_count"] == 1
