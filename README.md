# PropRisk Swarm

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/ZeroTrustZein/proprisk-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/ZeroTrustZein/proprisk-swarm/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Test Coverage: 100%](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/ZeroTrustZein/proprisk-swarm)

Institutional-grade, multi-agent commercial real estate (CRE) risk assessment and underwriting diligence platform. Features automated PostgreSQL data warehouse export and validation, Model Context Protocol (MCP) servers for municipal deeds, SEC filings, and zoning codes, hybrid vector-graph RAG over offering memorandums, an audit-ready multi-year discounted cash flow (DCF) engine, and automated Investment Committee underwriting memos.

---

## Core Features

- **Clean & Validate Raw Exports with PostgreSQL SQL Generation**: Validates raw unstructured exports, sanitizes text attributes (null bytes, whitespace trimming), enforces schema invariants, and compiles complete PostgreSQL relational DDL and idempotent `INSERT ... ON CONFLICT DO UPDATE` warehouse sync scripts.
- **Autonomous Multi-Agent Diligence Swarm**: Coordinated swarm consisting of Financial Analyst, Zoning Specialist, Diligence Reviewer, and Risk Officer agents communicating via an asynchronous, decoupled event bus.
- **Model Context Protocol (MCP) Services**: Production-ready MCP service registry bridging municipal deed registries, SEC EDGAR 10-K/8-K filings, and municipal zoning ordinances.
- **Multi-Year DCF Valuation & Stress Testing**: Unlevered and levered IRR solvers, NPV calculation, equity multiple, debt service coverage ratio (DSCR), and dynamic 2D sensitivity matrices.
- **Enterprise CLI & Rich Terminal Reporting**: Interactive CLI tools built with Click and Rich for system telemetry, diligence execution, SQL export, and validation audits.
