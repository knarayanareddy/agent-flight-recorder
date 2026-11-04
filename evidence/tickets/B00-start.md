# Ticket B00 — Contract baseline (start record)

**Product:** afr (Agent Flight Recorder). **Branch:** `arena/33ccc0e3-agent-flight-recorder`.
**Commit:** bb0fe589238732865941c5deb52d3f6a6f501e26 (`fix: resolve app-import blocker, isolate test auth, fix EVF CSV test, and enforce fail-closed authorization`).
**Working tree:** clean at kickoff.

## Environment actually available (recorded, not claimed as target)

- Python 3.11.2 (target runtime per baseline: Python 3.12 — NOT available locally; tests below run on 3.11 and do NOT constitute 3.12 validation).
- Node 22.22.3 (target Node 24 — NOT available locally).
- pip 26.3 in isolated venv `/home/user/.venv-afr`.
- PostgreSQL 16: NOT installed (no `psql`/`pg_isready`/initdb, no `service`, no Docker). B02 real-DB migration/RLS/FK/concurrency tests cannot run yet. Requested separately below.
- OIDC issuer / IdP: none configured (production credentials must be operator-provided; local synthetic IdP only).
- Outbound network to pypi.org works; dependencies installed from requirements.txt + requirements-baseline.txt.

## Verification results (this checkout, python -m pip install -r requirements.txt -r requirements-baseline.txt first)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest -q` | 101 passed (tests/test_api.py 18, test_baseline.py 59, test_contracts.py 20, test_oracles.py 3) | 0 |
| `python scripts/verify_manifest.py` | valid=true, 299 protected files, 0 changed/missing | 0 |
| `python scripts/release_gate.py` | ready=false; 15 blocking checks (postgres_migrations, application_e2e, authorization_matrix, oidc_integration, docling_integration, executor_boundary, backup_restore, load_chaos, accessibility_manual, domain_holdout, statistical_review, independent_security_review, clean_room_agent_trial, release_images_sbom, operator_signoff) | 1 (expected pre-implementation) |

Manifest coverage note: `contracts/baseline-manifest.json` protects 299 files under reference/, contracts/, docs/, scripts/, infra/, database/, fixtures/. It does NOT cover src/, tests/, implementation/, or apps/ — a passing manifest is integrity coverage of contracts/docs only, not whole-repository certification.

## Known contradictions recorded (from kickoff authority)

1. **Scoped idempotency (to fix before project persistence):** `001_baseline.sql` `core.idempotency` uses `PRIMARY KEY(actor_id,route,key)` with nullable org/project scope; `002_roles.sql` applies project-only RLS. Approved behavior: ordinary project mutations keyed `(project_id,actor_id,route,key)` with project RLS; project creation uses a separate organization-scoped idempotency table keyed `(organization_id,actor_id,route,key)` with organization RLS. Same scoped key + same normalized request replays prior result; different request 409; 24h TTL; authenticate/authorize before replay; lock + atomic commit; no dummy projects/scope-free uniqueness/RLS bypass/weakened FKs; runtime owner privileges forbidden.
2. **Stale authority path:** `implementation/product-focus.json` `"authority": "../05_Shared_Baseline/implementation-plan.json"` points outside this checkout; must point at the local `implementation/implementation-plan.json` after reviewed diff.
3. **Repository layout mapping:** queue references `apps/api/*` and `apps/dispatcher/*` must be translated to existing paths `src/` (FastAPI backend) and `src/worker/` (Python worker); document in `docs/Repository_Map.md`. No duplicate backend created.
4. Runtime targets: Python 3.12 / Node 24 / PostgreSQL 16 — environment gaps above.

## Next slice (independent, no external service required)

1. Write this record and commit it.
2. Fix `implementation/product-focus.json` authority to local plan; add `docs/Repository_Map.md`.
3. Apply scoped-idempotency baseline revision to `database/migrations/001_baseline.sql` + `002_roles.sql`; update migration README + `docs/05_Normative_Baseline.md` cross-reference; update `contracts/baseline-manifest.json` hashes explicitly and scoped (manifest covers the migration files); add gated DB idempotency tests (skip without real Postgres).
4. Commit slice; request Python 3.12, Node 24, and PostgreSQL 16 services once.

## Status

- Machine-complete so far: baseline verification green (101 tests), manifest valid, release gate correctly blocked (exit 1).
- External-review-pending: release-gate checks, migration revision, target-runtime validation.
- `production_ready=false` remains correct; no claim of target-runtime or application correctness yet.
