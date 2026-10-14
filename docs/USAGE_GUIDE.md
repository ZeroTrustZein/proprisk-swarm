# PropRisk Swarm — Comprehensive Usage Guide

This guide walks through common operational workflows in **PropRisk Swarm**, from configuring a deal and orchestrating multi-agent underwriting to exporting clean, production-ready PostgreSQL SQL scripts for enterprise data warehouses.

---

## 1. Quickstart: Running a Multi-Agent Diligence Pipeline

### Programmatic Python Execution

The `SwarmOrchestrator` manages the end-to-end flow across specialized agents (`FinancialAnalyst`, `ZoningSpecialist`, `DiligenceReviewer`, `RiskOfficer`).

```python
from proprisk_swarm.agents import SwarmOrchestrator
from proprisk_swarm.types.property import PropertyDeal, PropertyType

# 1. Initialize property deal model
deal = PropertyDeal(
    id="deal-dallas-industrial-01",
    title="Dallas Logistics Center",
    address="4500 Logistics Way, Dallas, TX",
    property_type=PropertyType.INDUSTRIAL,
    target_purchase_price=28_500_000.0,
    in_place_noi=2_100_000.0,
    total_units=4,
    gross_square_feet=240_000.0,
    year_built=2021,
)

# 2. Instantiate orchestrator
orchestrator = SwarmOrchestrator()

# 3. Execute underwriting pipeline
memo = orchestrator.run_pipeline(deal)

# 4. Inspect Committee memo output
print(f"Committee Decision: {memo.recommendation.value.upper()}")
print(f"Composite Risk Score: {memo.composite_score:.2f} / 100")
print(f"Assigned Risk Rating: {memo.risk_rating.value}")
print(f"Maximum Approved LTV: {memo.approved_ltv * 100:.1f}%")

print("\nKey Risk Factors Identified:")
for factor in memo.risk_factors:
    print(f" - {factor}")
```

---

## 2. PostgreSQL Clean, Validate, and SQL Export

A primary responsibility of PropRisk Swarm is ensuring that all unstructured and raw exports from external sources are validated and sanitized before entering PostgreSQL.

### Workflow: Cleaning Raw Payload and Compiling SQL

```python
from proprisk_swarm.storage.deal_store import DealStore
from proprisk_swarm.types.property import PropertyDeal, PropertyType

store = DealStore()

# 1. Save deal to store
deal = PropertyDeal(
    id="deal-austin-retail-02",
    title="South Congress Plaza",
    address="1600 S Congress Ave, Austin, TX",
    property_type=PropertyType.RETAIL,
    target_purchase_price=16_800_000.0,
    in_place_noi=1_250_000.0,
    total_units=12,
)
store.save_deal(deal)

# 2. Export package and perform validation
pkg = store.export_deal_package("deal-austin-retail-02")
validation = store.clean_and_validate_raw_export(pkg)

if validation["is_valid"]:
    print("Schema invariants verified!")
    print(f"Sanitized Deal Title: {validation['cleaned_data']['deal']['title']}")
else:
    print("Validation failed:")
    for err in validation["errors"]:
        print(f"  [ERROR] {err}")

# 3. Compile idempotent PostgreSQL DDL and Upsert Script
sql_script = store.export_to_sql("deal-austin-retail-02", schema="cre_warehouse")

# Save script to disk for deployment via psql
with open("sync_deal.sql", "w", encoding="utf-8") as f:
    f.write(sql_script)

print("Export completed to sync_deal.sql")
```

### PostgreSQL Execution

Apply the generated SQL script directly into any PostgreSQL instance using `psql`:

```bash
psql -h localhost -U postgres -d real_estate_dw -f sync_deal.sql
```

The script is idempotent: running it repeatedly updates existing records without primary key conflicts.

---

## 3. Command Line Interface (CLI) Workflows

The `proprisk-swarm` CLI provides full operational access from your shell.

### A. System Telemetry & Configuration

Inspect active settings, ports, and model dimensions:

```bash
proprisk-swarm status
```

Output highlights:
- Project Name, Environment, Log Level
- MCP Ports: Deeds (8201), SEC (8202), Zoning (8203)
- RAG Config: Vector Dimension (1536), Hybrid Alpha (0.6)
- Swarm Concurrency limits and strict audit mode

### B. MCP Server Inspection

List all registered Model Context Protocol endpoints and their respective tool calls:

```bash
proprisk-swarm mcp-servers
```

### C. Live Deal Underwriting

Execute an autonomous multi-agent underwriting run directly from the command line:

```bash
proprisk-swarm underwrite \
  --deal-id "deal-miami-multifamily-05" \
  --title "Biscayne Bay Residences" \
  --address "1200 Biscayne Blvd, Miami, FL" \
  --price 52000000 \
  --noi 3400000 \
  --units 180 \
  --property-type multifamily \
  --format rich
```

### D. Export Deal Package to PostgreSQL SQL

Generate production PostgreSQL DDL and upsert SQL directly from CLI:

```bash
proprisk-swarm export-sql \
  --deal-id "deal-denver-office-09" \
  --title "LoDo Tech Center" \
  --address "1700 Wynkoop St, Denver, CO" \
  --price 34000000 \
  --noi 2600000 \
  --property-type office \
  --schema "cre_warehouse" \
  --output "dps_export.sql"
```

### E. Validate Raw Export JSON

Audit an existing raw export file before loading it into your database:

```bash
proprisk-swarm validate-export --input "raw_payload.json"
```

---

## 4. Multi-Year DCF Modeling & Stress Testing

Run discounted cash flow (DCF) models with debt amortization and 2D sensitivity grids:

```python
from proprisk_swarm.valuation.engine import DCFEngine

engine = DCFEngine()

# Model a 10-year holding period with 65% LTV senior debt
result = engine.calculate_dcf(
    purchase_price=50_000_000.0,
    in_place_noi=3_500_000.0,
    holding_period_years=10,
    revenue_growth_rate=0.035,
    expense_growth_rate=0.025,
    discount_rate=0.08,
    exit_cap_rate=0.065,
    ltv=0.65,
    interest_rate=0.0575,
    amortization_years=30,
)

print(f"Unlevered IRR:    {result.unlevered_irr * 100:.2f}%")
print(f"Levered IRR:      {result.levered_irr * 100:.2f}%")
print(f"Net Present Value: ${result.npv:,.2f}")
print(f"Equity Multiple:  {result.equity_multiple:.2f}x")
print(f"Minimum DSCR:     {result.min_dscr:.2f}x")

# Print 2D Sensitivity Grid (Exit Cap vs. Discount Rate)
print("\nSensitivity Matrix (Levered IRR):")
matrix = result.sensitivity_matrix
headers = [f"{cap * 100:.2f}%" for cap in matrix.exit_cap_rates]
print(f"{'Disc Rate':<12} " + " ".join([f"{h:<10}" for h in headers]))

for disc_rate, row in zip(matrix.discount_rates, matrix.matrix):
    row_str = " ".join([f"{val * 100:>9.2f}%" for val in row])
    print(f"{disc_rate * 100:.2f}%       {row_str}")
```

---

## 5. Integrating with Model Context Protocol (MCP)

PropRisk Swarm includes production MCP server tool endpoints:

```python
from proprisk_swarm.mcp import MunicipalDeedsServer, ZoningOrdinanceServer

# Query Municipal Deeds
deeds_server = MunicipalDeedsServer()
chain = deeds_server.verify_chain_of_title("APN-984-1234")
print(f"Chain Intact: {chain['is_intact']}")
print(f"Prior Transfers: {len(chain['historical_transfers'])}")

# Query Zoning Standards
zoning_server = ZoningOrdinanceServer()
compliance = zoning_server.check_permitted_uses(
    jurisdiction="City of Austin",
    zone_code="CBD",
    proposed_use="mixed_use_commercial",
)
print(f"Permitted By-Right: {compliance['permitted']}")
```
