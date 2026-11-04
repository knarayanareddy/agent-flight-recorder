# Contracts Architecture & Authority

## Authority Model
- **Working Implementation Target:** The root files in `contracts/`, `src/`, `tests/`, and `database/` are the authoritative binding specifications for implementing this standalone repository.
- **Reference Canonical Baseline:** `reference/05_Shared_Baseline/` and `archive/*.zip` are preserved immutable references for auditing, cross-product schema context, and independent test oracles. Agents must not implement application code inside `reference/`.

## Manifest Coverage (`baseline-manifest.json`)
The `contracts/baseline-manifest.json` tracks cryptographic hashes of:
- All normative JSON Schemas and valid/invalid fixtures (`contracts/schemas/`, `contracts/examples/`)
- Scoped OpenAPI and endpoint policies (`contracts/openapi.yaml`, `contracts/endpoint-policy.json`)
- Database DDL migrations (`database/migrations/`)
- Reference mathematical oracles (`reference/oracles.py`)
- Synthetic test fixtures (`fixtures/`)
- Baseline verification scripts (`scripts/`)

**Deliberate Exclusions:**
The manifest intentionally does **NOT** lock `src/` (application source code) or `tests/test_api.py`. This ensures that autonomous build agents can write, refactor, and extend application code and integration tests without invalidating the contract integrity gate.

## Authorization & Roles
The authorization model enforces a clear separation:
1. **Organization Administration:** Managed in `core.memberships` (`member`, `admin`). Org admins control project creation (`foundation_create_project`).
2. **Project Privileges (Capability Sets):** Managed in `core.project_roles` (`viewer`, `analyst`, `operator`, `maintainer`). Each defines distinct operational capabilities.
