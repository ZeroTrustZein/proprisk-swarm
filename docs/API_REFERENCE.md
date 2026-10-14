# PropRisk Swarm — API Reference

This document provides a comprehensive technical reference for the public modules, classes, methods, and data structures in the `proprisk_swarm` package.

---

## 1. Storage & Relational SQL Synchronization

### `proprisk_swarm.storage.deal_store.DealStore`

The repository managing persistence of real estate deals, valuation outputs, and diligence memos, including sanitization and PostgreSQL SQL generation.

```python
from proprisk_swarm.storage.deal_store import DealStore
```

#### Methods

##### `clean_and_validate_raw_export(raw_export: Dict[str, Any]) -> Dict[str, Any]` *(classmethod)*
Validates and sanitizes a raw export dictionary before database synchronization.
- **Parameters**:
  - `raw_export`: Raw dictionary containing deal metadata, memos, valuations, deeds, and SEC filings.
- **Returns**:
  - `Dict[str, Any]` with keys:
    - `is_valid` (`bool`): `True` if no schema violations occurred.
    - `cleaned_data` (`Dict[str, Any]`): Sanitized data with null bytes stripped, whitespace trimmed, and numbers coerced.
    - `errors` (`List[str]`): List of validation error descriptions.
    - `warnings` (`List[str]`): List of non-fatal warnings (e.g. zero purchase price).

##### `export_to_sql(deal_id: str, schema: str = "public") -> str`
Generates PostgreSQL DDL (`CREATE SCHEMA`, `CREATE TABLE IF NOT EXISTS`) and idempotent `INSERT ... ON CONFLICT DO UPDATE` statements for a complete deal package.
- **Parameters**:
  - `deal_id` (`str`): Target deal identifier.
  - `schema` (`str`): Destination PostgreSQL schema (default: `"public"`).
- **Returns**:
  - `str`: Formatted, syntax-validated PostgreSQL script.
- **Raises**:
  - `KeyError`: If `deal_id` is not found in the store.
  - `ValueError`: If the deal package fails schema validation.

##### `sql_quote(val: Any) -> str` *(staticmethod)*
Escapes arbitrary Python values for safe insertion into PostgreSQL SQL literals.
- **Parameters**:
  - `val` (`Any`): Value to escape (handles `None`, numeric types, strings, dictionaries, lists, booleans).
- **Returns**:
  - `str`: PostgreSQL-escaped literal string (e.g. `NULL`, `123`, `'Austin''s Tower'`, `'{"key": "val"}'::jsonb`).

##### `save_deal(deal: PropertyDeal) -> None`
Upserts a property deal record in memory and to disk if configured.

##### `get_deal(deal_id: str) -> Optional[PropertyDeal]`
Retrieves a property deal by its unique identifier.

##### `list_deals(status: Optional[DealStatus] = None, property_type: Optional[PropertyType] = None) -> List[PropertyDeal]`
Filters stored deals by status or property classification.

##### `delete_deal(deal_id: str) -> bool`
Deletes a deal record and its associated artifacts. Returns `True` if deleted, `False` if not found.

##### `save_memo(memo: UnderwritingMemo) -> None`
Persists an Investment Committee underwriting memorandum.

##### `get_memo(deal_id: str) -> Optional[UnderwritingMemo]`
Retrieves the underwriting memo for a specific deal.

##### `save_valuation(deal_id: str, valuation: DCFValuationResult) -> None`
Stores the multi-year DCF valuation output for a deal.

##### `get_valuation(deal_id: str) -> Optional[DCFValuationResult]`
Retrieves the DCF valuation result for a deal.

##### `export_deal_package(deal_id: str) -> Optional[Dict[str, Any]]`
Compiles all data artifacts (deal, memo, valuation, deeds, filings) into a consolidated dictionary package.

##### `import_deal_package(package: Dict[str, Any]) -> None`
Deserializes and stores a complete deal package from a dictionary.

---

## 2. Autonomous Multi-Agent Swarm

### `proprisk_swarm.agents.orchestrator.SwarmOrchestrator`

Coordinates multi-agent workflows across specialized diligence agents.

```python
from proprisk_swarm.agents import SwarmOrchestrator
```

#### Methods

##### `__init__(event_bus: Optional[EventBus] = None, deal_store: Optional[DealStore] = None, auto_register: bool = True)`
Initializes the orchestrator, event bus, deal store, and registers default specialized agents.

##### `run_pipeline(deal: PropertyDeal) -> UnderwritingMemo`
Executes an end-to-end multi-agent underwriting diligence run on a property deal.
- **Parameters**:
  - `deal` (`PropertyDeal`): Target property deal object.
- **Returns**:
  - `UnderwritingMemo`: Comprehensive investment committee underwriting memo.

##### `dispatch_task(task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]`
Dispatches a discrete task to the appropriate registered specialized agent.

##### `audit_log() -> List[Dict[str, Any]]`
Returns the chronological execution history of all agent tasks and transitions.

---

### Specialized Agents (`proprisk_swarm.agents.specialized`)

- **`FinancialAnalystAgent`**: Computes net operating income (NOI), analyzes debt terms, and runs multi-year DCF models.
- **`ZoningSpecialistAgent`**: Verifies municipal zoning ordinances, FAR limits, setback boundaries, and permitted uses.
- **`DiligenceReviewerAgent`**: Evaluates rent rolls, lease commitments, deferred maintenance, and environmental reports.
- **`RiskOfficerAgent`**: Synthesizes cross-discipline findings into composite risk ratings, approved LTVs, and formal committee recommendations.

---

## 3. Event Bus Subsystem

### `proprisk_swarm.events.bus.EventBus`

Asynchronous, decoupled publish-subscribe messaging bus supporting hierarchical topic matching.

```python
from proprisk_swarm.events import EventBus
```

#### Methods

##### `subscribe(topic_pattern: str, handler: Callable[[Any], None]) -> None`
Subscribes a callback handler to a topic pattern (supports `*` wildcards, e.g. `deal.*`).

##### `unsubscribe(topic_pattern: str, handler: Callable[[Any], None]) -> bool`
Removes an active subscription handler.

##### `publish(topic: str, payload: Any) -> None`
Publishes a payload to matching subscribers and logs the event to audit history.

##### `publish_event(event: Event) -> None`
Publishes a strongly-typed `Event` object.

##### `get_history(topic_prefix: Optional[str] = None) -> List[Event]`
Returns chronological event history, optionally filtered by topic prefix.

---

## 4. Model Context Protocol (MCP) Services

### `proprisk_swarm.mcp`

Bridge connecting external registries to agent tool calls.

#### Classes

- **`MunicipalDeedsServer`**:
  - `get_deed_record(parcel_id: str)`: Fetches county deed record by parcel identifier.
  - `search_deeds_by_address(address: str)`: Searches historical transfers by street address.
  - `verify_chain_of_title(parcel_id: str)`: Evaluates grantor-grantee continuity.
- **`SECFilingsServer`**:
  - `get_company_filings(cik: str, form_type: str)`: Retrieves SEC EDGAR filings.
  - `extract_risk_factors(cik: str)`: Extracts Item 1A Risk Factors from 10-K filings.
  - `search_debt_covenants(cik: str)`: Extracts debt restrictions and covenant terms.
- **`ZoningOrdinanceServer`**:
  - `get_zoning_code(jurisdiction: str, zone_code: str)`: Retrieves dimensional standards.
  - `check_permitted_uses(jurisdiction: str, zone_code: str, proposed_use: str)`: Checks by-right use compliance.
  - `calculate_max_density(lot_size_sqft: float, far: float)`: Computes maximum allowable gross square footage.
- **`MCPRegistry`**: Central registry for discovering, registering, and routing tool calls across MCP servers.

---

## 5. Multi-Year DCF Valuation Engine

### `proprisk_swarm.valuation.engine.DCFEngine`

Institutional-grade discounted cash flow modeling and IRR solver.

```python
from proprisk_swarm.valuation import DCFEngine
```

#### Methods

##### `calculate_dcf(...) -> DCFValuationResult`
Generates multi-year pro-forma projections, debt schedules, returns, and sensitivity matrices.
- **Parameters**:
  - `purchase_price` (`float`): Acquisition purchase price.
  - `in_place_noi` (`float`): Year 1 Net Operating Income.
  - `holding_period_years` (`int`): Holding period in years (default: `5`).
  - `revenue_growth_rate` (`float`): Annual revenue growth rate (default: `0.03`).
  - `expense_growth_rate` (`float`): Annual operating expense inflation (default: `0.025`).
  - `discount_rate` (`float`): Target discount rate for NPV (default: `0.08`).
  - `exit_cap_rate` (`float`): Exit capitalization rate for reversion (default: `0.065`).
  - `ltv` (`float`): Loan-to-value percentage (default: `0.65`).
  - `interest_rate` (`float`): Annual mortgage interest rate (default: `0.055`).
  - `amortization_years` (`int`): Amortization term in years (default: `30`).
- **Returns**:
  - `DCFValuationResult`: Multi-period cash flows, unlevered IRR, levered IRR, NPV, equity multiple, min DSCR, and sensitivity grid.

##### `calculate_irr(cash_flows: List[float]) -> float`
Calculates exact internal rate of return using numerical root-finding.

##### `calculate_npv(rate: float, cash_flows: List[float]) -> float`
Calculates Net Present Value for a series of cash flows given a discount rate.

##### `generate_sensitivity_matrix(...) -> SensitivityMatrix`
Computes 2D return matrix varying exit cap rates and discount rates.

---

## 6. Hybrid Vector-Graph RAG & Ingestion

### `proprisk_swarm.rag.hybrid_rag.HybridRAG`

Combines dense vector cosine similarity with knowledge graph traversal.

#### Methods

##### `index_document(document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None`
Extracts entities, updates the knowledge graph, and indexes chunk embeddings in the vector store.

##### `query(query_text: str, top_k: int = 5, alpha: float = 0.6) -> List[Dict[str, Any]]`
Executes hybrid retrieval scoring results using weighted reciprocal rank fusion.

---

## 7. Command Line Interface Reference

### `proprisk_swarm.cli`

- `proprisk-swarm status`: Displays package metadata, environment flags, and active settings.
- `proprisk-swarm mcp-servers`: Inspects status and registered tools across MCP servers.
- `proprisk-swarm underwrite`: Executes the autonomous multi-agent underwriting pipeline for a deal.
- `proprisk-swarm export-sql`: Validates a deal package and exports production PostgreSQL DDL and upsert SQL.
- `proprisk-swarm validate-export`: Inspects and validates a raw deal package JSON export.
