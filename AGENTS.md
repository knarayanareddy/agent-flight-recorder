# Agent Work Protocol — Agent Flight Recorder (`AFR`)

This document governs autonomous coding agents building **Agent Flight Recorder**. All instructions and constraints herein are binding.

---

## 1. Prime Directives & Stopping Rules

1. **Fail Closed:** Never make a failing gate silently pass. If a prerequisite (such as PostgreSQL or an external model) is missing, write a clear, failing check or mock fixture with documented limitations.
2. **Never Import Reference Oracles:** `reference/oracles.py` contains independent mathematical acceptance oracles for testing. Production code in `src/` must implement its own algorithms and **MUST NOT** import `reference/oracles.py`.
3. **Strict Contract Conformance:** The OpenAPI specification in `contracts/openapi.yaml` and the schemas in `contracts/schemas/` are binding contracts. You may not alter endpoint paths, parameter names, or schema fields without explicit user authorization.
4. **Idempotency & Mutating Endpoints:** Every mutating endpoint (`POST`, `PUT`, `DELETE`) must require and validate an `Idempotency-Key` header (UUIDv4) as specified in `contracts/endpoint-policy.json`.
5. **Security & Redaction:** Credential headers, query params, and sensitive metadata (`api_key`, `authorization`, `password`, `secret`, `cookie`) must be stripped before persistence using allowlist filtering.
6. **Non-Root & Security Boundaries:** All runtime configurations must assume non-root container users (`10001:10001`), read-only root filesystems, and `cap_drop: ALL`.

---

## 2. Implementation Sequence

Follow this dependency-ordered ticket queue:

| Ticket | Name | Target Paths | Verification |
| :--- | :--- | :--- | :--- |
| **B00** | Contract Baseline | `contracts/*`, `tests/*` | `python scripts/verify_manifest.py && pytest tests/test_contracts.py` |
| **B01** | Dependency & Runtime Lock | `pyproject.toml`, `requirements.txt` | Ensure clean imports and pinned versions |
| **B02** | Database & Roles | `database/migrations/*`, `src/core/database.py`, `src/models/*` | SQLAlchemy models match `001_baseline.sql` |
| **B03** | Identity & Authorization | `src/core/security.py`, `src/api/deps.py` | Role verification (`viewer`, `analyst`, `operator`, `maintainer`, `admin`) |
| **B04** | Artifact Ingestion & Deletion | `src/api/foundation.py`, `src/services/` | Chunked upload, SHA-256 verification, artifact linking |
| **B05** | Jobs & Worker Outbox | `src/models/foundation.py`, `src/services/` | Job state machine (`queued` -> `leased` -> `running` -> `succeeded`/`failed`) |
| **B06** | **Agent Flight Recorder Vertical Slice** | `src/api/routes_afr.py`, `src/services/` | Implement domain endpoints and core business logic |
| **B10** | UI & Workflow Integration | `contracts/ui-workflows.yaml` | Connect API responses to UI screen contracts |
| **B11** | Hardening & Resilience | `infra/compose.yaml`, error handlers | RFC 7807 problem details, error codes, clean shutdown |

---

## 3. Coding Conventions

- **Language:** Python >= 3.10 with full type annotations.
- **Framework:** FastAPI with async path operation handlers.
- **ORM:** SQLAlchemy 2.0 with async engine (`asyncpg`).
- **Validation:** Pydantic v2 `BaseModel` with strict typing (`pydantic.Field`).
- **Responses:** Explicit HTTP status codes (`status.HTTP_201_CREATED`, `status.HTTP_200_OK`).
- **Documentation:** Google-style docstrings on all service classes and methods.
