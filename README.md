# Agent Flight Recorder (`AFR`)

> **Mission:** Deterministic black-box recording, run inspection, side-effect sandboxing, and trace-to-regression test generator for autonomous AI agents.

---

## 🎯 Repository Status & Purpose

This repository is an **independent, self-contained, build-agent-ready project** for **Agent Flight Recorder**.
It contains:
1. **Binding API & Schema Contracts:** Scoped OpenAPI specification, JSON Schemas (Draft 2020-12) with positive and negative test fixtures, endpoint security & permission policies, and UI workflows.
2. **Database Migrations:** PostgreSQL 16 DDL with strict schemas (`core` + `afr`), Row Level Security (RLS), and append-only immutability.
3. **Reference Oracles:** Independent deterministic mathematical algorithms for deduplication, validation, security, and statistics in `reference/oracles.py` (for verification; never imported into application code).
4. **Application Skeleton:** Async FastAPI application in `src/` with structured configuration, async SQLAlchemy engine, auth/role dependencies, foundation routes, and `afr` domain routes.
5. **Contract Test Suite:** Runnable tests in `tests/` verifying schema validity, OpenAPI path/role consistency, and reference oracles.
6. **Agent Execution Protocol:** Complete instructions in `AGENTS.md` and `BUILD_GUIDE.md` for an autonomous build agent.

---

## 🏗️ Directory Layout

```
.
├── AGENTS.md                  # Strict instructions & stopping rules for the build agent
├── BUILD_GUIDE.md             # Ticket queue & step-by-step implementation guide
├── Makefile                   # setup, dev, test, verify, gate commands
├── pyproject.toml             # Python packaging configuration
├── requirements.txt           # Production and dev dependencies
├── README.md                  # This file
│
├── docs/                      # Complete specifications & architectural context
│   ├── 01_Product_Specification.md
│   ├── 02_Shared_Foundation.md
│   ├── 03_Comparative_Analysis.md
│   ├── 04_Verification_Catalog.md
│   ├── 05_Normative_Baseline.md
│   └── 06_Protocol_and_Transactions.md
│
├── contracts/                 # Machine-verifiable interface contracts
│   ├── openapi.yaml           # Scoped OpenAPI 3.1 specification
│   ├── endpoint-policy.json   # Role requirements & idempotency policy
│   ├── ui-workflows.yaml      # Screen states & user journey actions
│   ├── auth-flow.yaml         # OIDC & token lifecycle routes
│   ├── baseline-manifest.json # SHA-256 integrity manifest
│   ├── schemas/               # Scoped JSON Schemas
│   └── examples/              # Positive (.valid.json) & negative (.invalid.json) fixtures
│
├── database/                  # Storage definitions
│   ├── migrations/
│   │   ├── 001_baseline.sql   # Tables, schemas, RLS, immutability
│   │   └── 002_roles.sql      # Database roles, grants, barrier isolation
│   └── lease_queries.sql      # Worker lease SQL queries
│
├── infra/                     # Hardened deployment infrastructure
│   ├── compose.yaml           # Rootless, read-only FS, PostgreSQL 16
│   ├── Caddyfile              # TLS & reverse proxy configuration
│   └── runtime-policy.yaml    # Container security policies
│
├── fixtures/                  # Product-specific test fixtures
│
├── reference/                 # Independent mathematical oracles (VERIFICATION ONLY)
│   └── oracles.py             # DO NOT IMPORT IN SRC
│
├── implementation/            # Ticket queue & backlog
│   ├── implementation-plan.json
│   ├── backlog.csv
│   └── product-focus.json
│
├── src/                       # Application Source Code
│   ├── main.py                # FastAPI app entrypoint
│   ├── core/                  # Config, database engine, security
│   ├── models/                # SQLAlchemy models (core + afr)
│   ├── schemas/               # Pydantic schemas (core + afr)
│   ├── api/                   # API route handlers (foundation + afr)
│   └── services/              # Domain business logic
│
├── tests/                     # Test Suite
│   ├── conftest.py
│   ├── test_contracts.py      # Validates schemas & OpenAPI against fixtures
│   ├── test_oracles.py        # Validates mathematical oracles
│   └── test_api.py            # API route integration tests
│
└── scripts/                   # Verification tooling
    ├── verify_manifest.py     # Hash integrity checker
    └── release_gate.py        # Fail-closed production release gate
```

---

## ⚡ Quickstart

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify Baseline & Contracts
```bash
make verify   # Check contract hash manifest
make test     # Run pytest suite
```

### 3. Run Development Server
```bash
make dev      # Starts FastAPI at http://localhost:8000
```
- Open Swagger Docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/healthz`

---

## 🤖 Instructions for the Build Agent

If you are an autonomous coding agent (Claude Code, Antigravity, Codex, etc.) tasked with building this repository:

1. **Read `AGENTS.md` first:** Familiarize yourself with the non-negotiable architectural boundaries and stopping rules.
2. **Consult `BUILD_GUIDE.md`:** Work sequentially through tickets `B00` through `B06` (or product tickets).
3. **Do not hallucinate passing tests:** Never import `reference/oracles.py` into application code in `src/`.
4. **Preserve Contracts:** All request/response types must strictly conform to `contracts/openapi.yaml` and `contracts/schemas/`.
5. **Run tests frequently:** Execute `pytest tests/` after each slice to verify regressions.
