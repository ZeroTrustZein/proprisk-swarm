# PropRisk Swarm — System Architecture & Design Specification

## 1. System Overview

**PropRisk Swarm** is an institutional-grade, multi-agent underwriting platform engineered for commercial real estate (CRE) acquisitions, financial valuation, and regulatory due diligence. The system automates the underwriting lifecycle by coordinating autonomous specialized agents, querying external municipal and federal registers via the Model Context Protocol (MCP), constructing hybrid vector-graph representations of offering memorandums, modeling multi-year discounted cash flows (DCF), and synchronizing structured audit trails into PostgreSQL data warehouses with strict data sanitization and schema invariant verification.

### Core Architectural Principles

- **Zero-Trust Data Sanitization**: All external inputs (unstructured broker offering memorandums, municipal deed exports, SEC 10-K extracts) are treated as untrusted. Raw payloads undergo automated null-byte elimination, whitespace trimming, and schema invariant enforcement before storage or downstream computation.
- **Relational Integrity via PostgreSQL SQL Generation**: Export pipelines generate idempotent PostgreSQL DDL and `INSERT ... ON CONFLICT (id) DO UPDATE` statements with typed `JSONB` payloads, guaranteeing schema consistency across distributed warehouse nodes.
- **Decoupled Event-Driven Swarm**: Specialized agents communicate asynchronously over an in-process, topic-based publish-subscribe `EventBus`. Agents remain loosely coupled, consuming domain events and emitting verified diligence findings.
- **Protocol-First Model Context Protocol (MCP) Mesh**: Standardized MCP servers bridge proprietary and municipal data sources (deeds, SEC filings, zoning ordinances) into uniform agent tool calls.
- **Dual-Retriever Hybrid RAG**: Ingests offering memorandums into both dense vector stores (cosine similarity) and directed property knowledge graphs (entity-relationship traversal), combining results through reciprocal rank fusion.
- **Deterministic Audit-Ready DCF Engine**: Implements un-levered and levered pro-forma cash flow modeling with numeric precision, root-finding IRR solvers, dynamic debt amortization schedules, and 2D exit-cap vs. discount-rate sensitivity matrices.

---

## 2. High-Level Component Topology

```
                       ┌────────────────────────────────────────────────────────┐
                       │               External MCP Integrators                 │
                       │  - Municipal Deeds Server (Transfers, Chain of Title)  │
                       │  - SEC Filings Server (10-K, 8-K, Sponsor Covenants)   │
                       │  - Zoning Ordinance Server (FAR, Setbacks, Permitted)  │
                       └───────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
                       ┌────────────────────────────────────────────────────────┐
                       │              Decoupled Pub/Sub Event Bus               │
                       │               (proprisk_swarm.events)                  │
                       │      Topics: deal.*, diligence.*, valuation.*          │
                       └─────────────┬────────────────────────────┬─────────────┘
                                     │                            │
                                     ▼                            ▼
  ┌──────────────────────────────────────────────────┐  ┌────────────────────────────────┐
  │           Autonomous Diligence Swarm             │  │     Hybrid Vector-Graph RAG    │
  │  - SwarmOrchestrator                             │  │  - VectorStore (Cosine Sim)    │
  │  - FinancialAnalystAgent (Cash flow, NOI, Debt)  │  │  - PropertyKnowledgeGraph      │
  │  - ZoningSpecialistAgent (FAR, Height, Use)      │  │  - IngestionPipeline           │
  │  - DiligenceReviewerAgent (Tenancy, Lease, ESG)  │  │  - Hybrid Reciprocal Re-ranker │
  │  - RiskOfficerAgent (Composite Risk, Final Memo) │  └────────────────────────────────┘
  └──────────────────────────┬───────────────────────┘
                             │
                             ▼
  ┌──────────────────────────────────────────────────┐  ┌────────────────────────────────┐
  │       Multi-Year DCF Valuation Engine            │  │  PostgreSQL Warehouse Sync     │
  │  - Multi-Year Pro-Forma Cash Flows               │  │  - Raw Export Sanitizer        │
  │  - Unlevered & Levered Exact IRR Solver          │  │  - Invariant Schema Validator  │
  │  - Debt Service Amortization & DSCR Engine       │  │  - DDL & Idempotent Upsert SQL │
  │  - 2D Sensitivity Matrix Generator               │  │  - Typed JSONB Payloads        │
  └──────────────────────────────────────────────────┘  └────────────────────────────────┘
```

---

## 3. Subsystem Architecture

### 3.1 PostgreSQL Data Warehouse Export & Validation Engine (`proprisk_swarm.storage.deal_store`)

The persistence subsystem provides an audit-compliant bridge between in-memory agent models and PostgreSQL relational data warehouses.

#### Data Sanitization & Invariant Validation (`clean_and_validate_raw_export`)
Before generating SQL or persisting raw deal exports, the storage engine executes a validation pass:
1. **Control Character & Null-Byte Scrubbing**: Eliminates `\x00` null bytes and unprintable ASCII control characters that corrupt PostgreSQL text and JSONB fields.
2. **Whitespace Normalization**: Trims leading and trailing whitespace across all string fields.
3. **Numeric Coercion & Bounds Verification**:
   - `target_purchase_price`: Enforces float coercion; strictly rejects values `< 0.0`. Emits audit warnings if `purchase_price == 0.0`.
   - `in_place_noi`: Coerces numeric inputs to standard float representations.
   - `total_units`: Casts to integer, enforcing non-negative cardinality.
   - `consideration` (Deeds): Coerces transaction amounts; enforces non-negative bounds.
4. **Structural Schema Verification**: Verifies presence and structure of `deal_id`, `deal.title`, `memo`, `valuation`, `deeds`, and `filings`.

#### PostgreSQL DDL & Idempotent Upsert Generation (`export_to_sql`)
The engine generates production PostgreSQL scripts structured for idempotence:
- **Schema Provisioning**: `CREATE SCHEMA IF NOT EXISTS <schema>;`
- **Table Definitions**:
  - `deals`: Core deal attributes with relational columns and un-structured attributes in `JSONB`.
  - `underwriting_memos`: Investment committee recommendations, composite risk scores, approved LTV, and risk ratings.
  - `dcf_valuations`: Multi-year financial metrics (unlevered IRR, levered IRR, NPV, equity multiple, min DSCR, sensitivity matrix JSONB).
  - `deed_records`: Historical county records, deed types, grantors, grantees, and recording dates.
  - `sec_filings`: Corporate disclosures, CIK numbers, form types, filing dates, and material risk items.
- **Idempotent Synchronization**: Employs `INSERT INTO ... ON CONFLICT (<primary_key>) DO UPDATE SET ...` for zero-downtime ETL synchronization without duplicate primary key collisions.

---

### 3.2 Event Bus & Messaging Backbone (`proprisk_swarm.events.bus`)

The messaging layer coordinates autonomous agents without tight coupling:
- **Topic Hierarchies & Wildcards**: Hierarchical topic strings (e.g., `deal.submitted`, `diligence.zoning.completed`, `valuation.*`).
- **Synchronous & Asynchronous Handlers**: Supports standard callable callbacks and async coroutines.
- **Audit Event History**: Retains an in-memory chronological event trail with topic filtering, supporting full replay and post-mortem auditing of agent decisions.

---

### 3.3 Autonomous Multi-Agent Diligence Swarm (`proprisk_swarm.agents`)

The diligence swarm decomposes commercial underwriting into specialized functional tasks:
1. **`FinancialAnalystAgent`**: Analyzes historical and in-place net operating income (NOI), estimates capital expenditures (CapEx), verifies tenant creditworthiness, and evaluates proposed debt structures.
2. **`ZoningSpecialistAgent`**: Cross-references municipal ordinances, computes current vs. maximum allowable Floor Area Ratio (FAR), checks setback compliance, verifies permitted use classifications, and flags entitlement risks.
3. **`DiligenceReviewerAgent`**: Scans lease abstracts, tenant rollover schedules, environmental reports (Phase I/II ESA), and physical deferred maintenance items.
4. **`RiskOfficerAgent`**: Synthesizes findings across financial, zoning, and diligence dimensions; computes composite risk scores; determines approved loan-to-value (LTV) limits; and generates formal Investment Committee memos (`APPROVED`, `APPROVED_WITH_CONDITIONS`, or `REJECTED`).
5. **`SwarmOrchestrator`**: Orchestrates task distribution, tracks dependency chains, enforces audit-mode execution, and commits final underwriting memos to `DealStore`.

---

### 3.4 Model Context Protocol (MCP) Service Mesh (`proprisk_swarm.mcp`)

PropRisk Swarm implements native MCP server endpoints adhering to standard tool schemas:
- **`MunicipalDeedsServer`**:
  - `get_deed_record`: Retrieves deed by County Parcel ID (APN).
  - `search_deeds_by_address`: Finds recorded conveyances by street address.
  - `verify_chain_of_title`: Validates unbroken grantor-grantee chains and flags open liens.
- **`SECFilingsServer`**:
  - `get_company_filings`: Discovers recent 10-K, 10-Q, and 8-K filings for public sponsors or anchor tenants.
  - `extract_risk_factors`: Pulls Item 1A Risk Factors from 10-K filings.
  - `search_debt_covenants`: Analyzes credit agreement disclosures and debt covenants.
- **`ZoningOrdinanceServer`**:
  - `get_zoning_code`: Retrieves zoning classification rules (FAR, height limits, setbacks).
  - `check_permitted_uses`: Determines by-right, conditional, and prohibited uses.
  - `calculate_max_density`: Computes maximum buildable square footage and residential unit capacity.
- **`MCPRegistry`**: Central registry managing lifecycle, discovery, and dispatch for all MCP servers.

---

### 3.5 Ingestion & Hybrid RAG Engine (`proprisk_swarm.rag` & `proprisk_swarm.ingestion`)

- **Document Parser**: Ingests offering memorandums, rent rolls, appraisals, and inspection reports into normalized chunks.
- **Dense Vector Search**: Computes 1536-dimensional embeddings with cosine similarity scoring.
- **Property Knowledge Graph**: Extracts property entities (`Property`, `Tenant`, `Parcel`, `ZoningDistrict`, `Sponsor`) and relationships (`LOCATED_IN`, `LEASES_SPACE_IN`, `SUBJECT_TO_ZONING`, `OWNED_BY`).
- **Hybrid Retrieval**: Combines semantic vector similarity and graph connectivity via reciprocal rank fusion:
  $$\text{Score}(d) = \alpha \cdot \text{Sim}_{\text{vector}}(q, d) + (1 - \alpha) \cdot \text{Score}_{\text{graph}}(q, d)$$

---

### 3.6 Multi-Year DCF Valuation & Stress Testing (`proprisk_swarm.valuation.engine`)

- **Cash Flow Forecasting**: Generates multi-year pro-forma schedules projecting potential gross revenue, vacancy losses, operating expenses, and replacement reserves.
- **Debt Service Modeling**: Computes interest and principal amortization schedules, calculating annual debt service coverage ratios (DSCR).
- **Exact IRR Solver**: Utilizes bounded Brent-method numerical root-finding to solve exact un-levered and levered Internal Rate of Return (IRR) equations without approximation.
- **2D Sensitivity Matrix**: Generates two-dimensional sensitivity grids modeling the interaction between exit capitalization rates ($\pm 100$ bps) and discount rates ($\pm 150$ bps).

---

## 4. End-to-End Execution Lifecycles

### Underwriting Pipeline Sequence
```
User / CLI               SwarmOrchestrator          Specialized Agents         DealStore
    │                           │                           │                      │
    ├─── submit deal ──────────►│                           │                      │
    │                           ├─── initialize context ───►│                      │
    │                           │                           │                      │
    │                           ├─── task: financial ──────►│ (FinancialAnalyst)   │
    │                           │    returns valuation      │                      │
    │                           │                           │                      │
    │                           ├─── task: zoning ─────────►│ (ZoningSpecialist)   │
    │                           │    returns compliance     │                      │
    │                           │                           │                      │
    │                           ├─── task: diligence ──────►│ (DiligenceReviewer)  │
    │                           │    returns lease audit    │                      │
    │                           │                           │                      │
    │                           ├─── task: risk officer ───►│ (RiskOfficerAgent)   │
    │                           │    returns memo           │                      │
    │                           │                           │                      │
    │                           ├─── clean & persist ─────────────────────────────►│
    │◄── memo & audit trail ────┤                           │                      │
```

---

## 5. Security & Reliability

- **SQL Injection Prevention**: All SQL string formatting in `DealStore.sql_quote` explicitly escapes single quotes (`'` to `''`) and coerces numeric/JSON values to prevent SQL injection vulnerabilities.
- **Audit Logging**: Every agent step, tool call, and state transition emits structured events to the event bus with ISO timestamps.
- **Graceful Error Handling**: MCP servers and agent execution routines catch external timeouts, invalid payloads, and transient communication failures, returning typed error structures without aborting the swarm.
