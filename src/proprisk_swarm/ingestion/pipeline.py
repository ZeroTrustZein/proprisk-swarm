"""Ingestion pipeline subsystem for municipal deeds, SEC filings, and offering memorandums."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from proprisk_swarm.protocols import IngestionPipelineProtocol
from proprisk_swarm.types.ingestion import (
    DeedRecord,
    DeedType,
    IngestionJob,
    IngestionSourceType,
    IngestionStatus,
    SECFiling,
    SECFilingType,
)


class IngestionPipeline(IngestionPipelineProtocol):
    """Pipeline ingesting municipal deeds, SEC filings, and offering memorandums."""

    def __init__(self) -> None:
        self._jobs: Dict[str, IngestionJob] = {}

    def ingest_document(
        self, source_path: str, source_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Ingest raw legal or financial document and return job ID."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        meta = metadata or {}

        path = Path(source_path)
        raw_bytes = b""
        if path.exists() and path.is_file():
            raw_bytes = path.read_bytes()
        elif "content" in meta:
            content = meta["content"]
            raw_bytes = content.encode("utf-8") if isinstance(content, str) else bytes(content)

        job = IngestionJob(
            job_id=job_id,
            source_type=source_type,
            source_path=source_path,
            status=IngestionStatus.IN_PROGRESS,
            metadata=meta,
        )
        self._jobs[job_id] = job

        try:
            parsed = self.parse_payload(raw_bytes, source_type)
            job.status = IngestionStatus.COMPLETED
            job.extracted_records_count = parsed.get("record_count", 1)
        except Exception as exc:
            job.status = IngestionStatus.FAILED
            job.error_message = str(exc)

        return job_id

    def parse_payload(self, raw_data: bytes, document_type: str) -> Dict[str, Any]:
        """Parse raw bytes into structured property/deed/filing records."""
        if not raw_data:
            return {"record_count": 0, "records": []}

        text = raw_data.decode("utf-8", errors="replace").replace("\x00", "").strip()
        dtype = str(document_type).lower()

        try:
            parsed_json = json.loads(text)
            if isinstance(parsed_json, dict):
                return {"record_count": 1, "records": [parsed_json]}
            elif isinstance(parsed_json, list):
                return {"record_count": len(parsed_json), "records": parsed_json}
        except Exception:
            pass

        # Text fallback
        if "deed" in dtype:
            records = [{
                "parcel_number": "PARCEL-EXTRACTED",
                "deed_type": DeedType.SPECIAL_WARRANTY.value,
                "raw_text": text[:500],
            }]
            return {"record_count": 1, "records": records}
        elif "sec" in dtype:
            records = [{
                "cik": "0000000000",
                "filing_type": SECFilingType.FORM_10K.value,
                "raw_text": text[:500],
            }]
            return {"record_count": 1, "records": records}
        else:
            return {"record_count": 1, "records": [{"raw_text": text[:500]}]}

    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        """Retrieve ingestion job status by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[IngestionJob]:
        """List all tracked ingestion jobs."""
        return list(self._jobs.values())
