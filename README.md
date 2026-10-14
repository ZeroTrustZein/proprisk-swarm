# PropRisk Swarm

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/ZeroTrustZein/proprisk-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/ZeroTrustZein/proprisk-swarm/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Test Coverage: 100%](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/ZeroTrustZein/proprisk-swarm)

Institutional-grade, multi-agent commercial real estate (CRE) risk assessment and underwriting diligence platform. Features automated PostgreSQL data warehouse export and validation, Model Context Protocol (MCP) servers for municipal deeds, SEC filings, and zoning codes, hybrid vector-graph RAG over offering memorandums, an audit-ready multi-year discounted cash flow (DCF) engine, and automated Investment Committee underwriting memos.

---

## Architecture Overview

```
                      ┌────────────────────────────────────────────────────────┐
                      │              External Integrations (MCP)               │
                      │  - Municipal Deeds MCP (Transfers, Deeds, Chain)       │
                      │  - SEC Filings MCP (10-K, 8-K, Sponsor Covenants)      │
                      │  - Zoning Ordinance MCP (FAR, Setbacks, Permitted Use) │
                      └───────────────────────────┬────────────────────────────┘
                                                  │
                                                  ▼
                      ┌────────────────────────────────────────────────────────┐
                      │           Decoupled Pub/Sub Event Backbone             │
                      │                  (proprisk_swarm.events)               │
                      └─────────────┬────────────────────────────┬─────────────┘
                                    │                            │
                                    ▼                            ▼
  ┌────────────────────────────────────────────────┐   ┌────────────────────────────────┐
  │         Autonomous Multi-Agent Swarm           │   │      Hybrid Vector-Graph RAG   │
  │  - Financial Analyst (NOI, Pro-Forma, Debt)    │   │  - Dense Semantic Embeddings   │
  │  - Zoning Specialist (FAR, Setbacks, By-Right) │   │  - Knowledge Graph Traversal   │
  │  - Diligence Reviewer (Tenancy, ESG, Deferred) │   │  - Hybrid Reciprocal Re-rank   │
  │  - Risk Officer (Composite Scoring, Memo)      │   └────────────────────────────────┘
  └─────────────────────────┬──────────────────────┘
                            │
                            ▼
  ┌────────────────────────────────────────────────┐   ┌────────────────────────────────┐
  │       Multi-Year DCF Valuation Engine          │   │  PostgreSQL Warehouse Sync     │
  │  - Unlevered & Levered Cash Flows              │   │  - Raw Export Sanitization     │
  │  - Exact IRR / NPV / DSCR / Equity Multiples   │   │  - Schema Invariant Validation │
  │  - 2D Exit Cap vs Discount Rate Sensitivities  │   │  - DDL & Idempotent Upsert SQL │
  └────────────────────────────────────────────────┘   └────────────────────────────────┘
```

---

## Core Features

- **Clean & Validate Raw Exports with PostgreSQL SQL Generation**:
  - Validates unstructured raw deal exports against strict schema invariants before syncing to the data warehouse.
  - Sanitizes text inputs: strips null bytes (`\x00`), removes unprintable control characters, and trims leading/trailing whitespace.
  - Coerces and validates numerical fields: bounds checking for purchase prices, net operating income (NOI), total units, and deed considerations.
  - Compiles full PostgreSQL DDL (`CREATE SCHEMA`, `CREATE TABLE IF NOT EXISTS`) and idempotent `INSERT ... ON CONFLICT (deal_id) DO UPDATE` statements with typed `JSONB` payloads.
- **Autonomous Multi-Agent Diligence Swarm**:
  - Four specialized agents (`FinancialAnalystAgent`, `ZoningSpecialistAgent`, `DiligenceReviewerAgent`, `RiskOfficerAgent`) orchestrated by `SwarmOrchestrator`.
  - Event-driven coordination via async `EventBus` with topic wildcards and structured audit logging.
- **Model Context Protocol (MCP) Services**:
  - Production MCP tool endpoints for real-time external data retrieval:
    - `MunicipalDeedsServer`: Deed chain verification, parcel lookups, assessment histories.
    - `SECFilingsServer`: Corporate sponsor 10-K risk factor extraction, debt covenants, and material 8-K events.
    - `ZoningOrdinanceServer`: Municipal zoning code compliance, maximum allowable FAR, building height caps, and parking ratios.
- **Hybrid Vector-Graph RAG Engine**:
  - Ingestion pipeline parsing offering memorandums (OMs), rent rolls, and environmental reports into chunked embeddings.
  - Dual retrieval fusing dense vector cosine similarity with directed knowledge-graph relationship traversal.
- **Multi-Year DCF Valuation & Stress Testing**:
  - Multi-period pro-forma cash flow modeling with debt amortization schedules.
  - Unlevered and levered IRR solvers, NPV calculation, equity multiples, and debt service coverage ratio (DSCR).
  - 2D sensitivity matrix generation across exit cap rates and discount rates.
- **Enterprise CLI & Rich Terminal Reporting**:
  - CLI tools built with Click and Rich for system telemetry, live diligence runs, SQL export compilation, and JSON export validation audits.

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Optional: PostgreSQL 14+ for running generated relational data warehouse scripts

### Install from Source

```bash
git clone https://github.com/ZeroTrustZein/proprisk-swarm.git
cd proprisk-swarm
pip install -e .
```

For development and test dependencies:

```bash
pip install -e ".[dev]"
```

---

## Quickstart

### 1. Python API: Multi-Agent Underwriting Workflow

```python
from proprisk_swarm.agents import SwarmOrchestrator
from proprisk_swarm.types.property import PropertyDeal, PropertyType

# Define property deal
deal = PropertyDeal(
    id="deal-austin-001",
    title="Domain Gateway Tower",
    address="2901 Capital of Texas Hwy, Austin, TX",
    property_type=PropertyType.OFFICE,
    target_purchase_price=45_000_000.0,
    in_place_noi=3_200_000.0,
    total_units=1,
    gross_square_feet=185_000.0,
)

# Run autonomous multi-agent underwriting swarm
orchestrator = SwarmOrchestrator()
memo = orchestrator.run_pipeline(deal)

print(f"Deal Recommendation: {memo.recommendation.value}")
print(f"Risk Rating:         {memo.risk_rating.value}")
print(f"Composite Score:     {memo.composite_score:.2f} / 100")
print(f"Approved Leverage:   {memo.approved_ltv * 100:.1f}% LTV")
```

---

### 2. Clean & Validate Raw Exports with PostgreSQL SQL Generation

Before syncing raw unstructured data to PostgreSQL, the storage layer sanitizes strings, checks schema invariants, and compiles production SQL DDL and upsert statements:

```python
from proprisk_swarm.storage.deal_store import DealStore

store = DealStore()
store.save_deal(deal)

# Generate complete PostgreSQL DDL and idempotent upsert statements
sql_script = store.export_to_sql(deal_id=deal.id, schema="cre_warehouse")
print(sql_script[:600])
```

#### Generated SQL Structure:
```sql
-- PostgreSQL Deal Export for: deal-austin-001
-- Schema: cre_warehouse

CREATE SCHEMA IF NOT EXISTS cre_warehouse;

CREATE TABLE IF NOT EXISTS cre_warehouse.deals (
    deal_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    property_type TEXT,
    status TEXT,
    target_purchase_price NUMERIC(18, 2),
    in_place_noi NUMERIC(18, 2),
    total_units INTEGER,
    payload JSONB,
    exported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO cre_warehouse.deals (
    deal_id, title, property_type, status,
    target_purchase_price, in_place_noi, total_units, payload
) VALUES (
    'deal-austin-001', 'Domain Gateway Tower', 'office', 'evaluating',
    45000000.00, 3200000.00, 1, '{"id": "deal-austin-001", ...}'::jsonb
)
ON CONFLICT (deal_id) DO UPDATE SET
    title = EXCLUDED.title,
    property_type = EXCLUDED.property_type,
    status = EXCLUDED.status,
    target_purchase_price = EXCLUDED.target_purchase_price,
    in_place_noi = EXCLUDED.in_place_noi,
    total_units = EXCLUDED.total_units,
    payload = EXCLUDED.payload,
    exported_at = CURRENT_TIMESTAMP;
```

---

## Command Line Interface (CLI)

The CLI executable `proprisk-swarm` provides full control over the underwriting platform:

```bash
# Check system status and configuration
proprisk-swarm status

# Inspect registered Model Context Protocol (MCP) servers
proprisk-swarm mcp-servers

# Execute full autonomous swarm diligence on a deal
proprisk-swarm underwrite --deal-id "deal-austin-001" \
  --title "Domain Gateway Tower" \
  --address "2901 Capital of Texas Hwy, Austin, TX" \
  --price 45000000 \
  --noi 3200000 \
  --property-type office \
  --format rich

# Clean, validate, and export deal package to PostgreSQL SQL
proprisk-swarm export-sql --deal-id "deal-austin-001" \
  --title "Domain Gateway Tower" \
  --address "2901 Capital of Texas Hwy, Austin, TX" \
  --price 45000000 \
  --noi 3200000 \
  --schema cre_warehouse \
  --output export.sql

# Validate an existing raw deal package JSON export
proprisk-swarm validate-export --input raw_deal.json
```

---

## Testing & Verification

Run the full pytest suite with test coverage reporting:

```bash
python -m pytest
```

Execute linting and static analysis:

```bash
python -m ruff check src tests
```

---

## Documentation Index

- [System Architecture](docs/ARCHITECTURE.md): Subsystem topology, agent communication protocols, and data warehouse synchronization pipelines.
- [API Reference](docs/API_REFERENCE.md): Class, method, and schema specifications for storage, agents, valuation, and MCP connectors.
- [Usage Guide](docs/USAGE_GUIDE.md): Detailed workflows, advanced DCF sensitivity modeling, and PostgreSQL database ingestion.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
