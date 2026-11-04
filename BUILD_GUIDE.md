# Build Guide: Step-by-Step Implementation

This guide provides actionable steps for a build agent to carry out the implementation of **Agent Flight Recorder**.

---

## Phase 1: Verify the Scaffold (Ticket B00)

1. Verify environment and install requirements:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run integrity checks:
   ```bash
   python scripts/verify_manifest.py
   pytest tests/test_contracts.py
   ```
3. Ensure all contract tests pass.

---

## Phase 2: Implement Core Foundation (Tickets B01–B05)

### Ticket B02: Database Models (`src/models/foundation.py`)
- Inspect `database/migrations/001_baseline.sql`.
- Complete the SQLAlchemy declarative models for:
  - `Organization`, `User`, `Project`, `ProjectRole`, `ApiKey`
  - `Artifact`, `Upload`, `ArtifactLink`
  - `Job`, `JobAttempt`, `Idempotency`, `Outbox`
- Ensure UUID primary keys, foreign key constraints, and enum validations match the SQL schema.

### Ticket B03: Security & Authorization (`src/core/security.py`, `src/api/deps.py`)
- Implement token decoding and subject extraction in `verify_token`.
- Enforce the 5 project roles: `viewer`, `analyst`, `operator`, `maintainer`, `admin`.
- Ensure mutating requests without a valid `Idempotency-Key` header return HTTP 400.

### Ticket B04 & B05: Uploads & Jobs (`src/api/foundation.py`)
- Implement file upload handling in `foundation_create_upload`, `foundation_put_upload`, `foundation_finalize_upload`.
- Verify SHA-256 hash match on finalization.
- Implement job status queries and cancellation (`foundation_get_job`, `foundation_cancel_job`).

---

## Phase 3: Implement Domain Features (B06)

### Product Focus: Agent Flight Recorder
- Inspect `docs/01_Product_Specification.md` and `contracts/openapi.yaml`.
- Open `src/api/routes_afr.py` and `src/services/afr.py`.
- Implement the domain operations:
    - `B06`: See implementation-plan.json for specific acceptance criteria.

---

## Phase 4: Verification & Gate Signoff

1. Run full test suite:
   ```bash
   pytest -v tests/
   ```
2. Test live server:
   ```bash
   uvicorn src.main:app --reload
   python scripts/product_smoke.py
   ```
3. Check the release gate:
   ```bash
   python scripts/release_gate.py
   ```
