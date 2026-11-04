# End-to-end production evidence — BLOCKED

## Status: production_ready = false; no release evidence exists

## Blocking reasons (all avenues explored)

### 1. No PostgreSQL 16 available (blocks all DB-backed e2e)

- No `psql`/`pg_ctl`/`initdb` binaries; no `/usr/lib/postgresql`; no `/usr/pgsql`
- Not root (uid 1001); `apt-get update` fails: permission denied on
  `/var/lib/apt/lists/partial`
- No Docker / docker-compose
- Outbound internet restricted to github.com, registry.npmjs.org, pypi.org,
  files.pythonhosted.org — cannot fetch PostgreSQL from apt.postgresql.org or
  enterprise mirrors
- SQLite substitution expressly prohibited ("No SQLite substitution for PostgreSQL
  guarantees; real Postgres16 tests required")

Without PostgreSQL, every DB-backed route (`/api/v1/projects`, `/api/v1/afr/*`,
uploads, artifacts, jobs) returns HTTP 503 unavailable rather than fabricating
results. End-to-end journeys cannot reach a terminal state.

### 2. No disposable API credentials (blocks product_journeys / smoke / acceptance)

- `scripts/product_smoke.py`, `product_acceptance.py`, `product_journeys.py` all
  exit 2 (BLOCKED) without a real `BASELINE_URL`/disposable API key/project and
  explicit user confirmation
- No secrets may be injected into commands, shell history, commits, chat, or evidence
- Synthetic IdP/test setup allowed without production credentials — but that only
  covers unit/auth tests, not live e2e against a real API

### 3. production_ready remains false

The release gate reports `ready=false` with exactly 15 blocking checks and null
evidence. The gate cannot pass until real implementation + integration evidence
exists. No self-certification of B00 or dependent integration guarantees.

## Avenues explored and results

| Avenue | Result |
|--------|--------|
| apt-get install postgresql-16 | Denied: not root |
| Download PG binaries from web | Outbound internet restricted (no apt.postgresql.org) |
| Docker | Not installed |
| Local e2e without PG | All DB routes return 503; cannot reach terminal state |
| product_journeys with secrets | Prohibited: no secrets in commands/history/evidence |
| SQLite substitution | Prohibited by user constraint |

## What IS verified locally

- `pytest -q`: 138 passed, 10 skipped (all skips are DB-gated; expected without PG)
- `tsc --noEmit` (frontend): clean
- `npm run build` (frontend): passes, 174 kB bundle
- Import checks: `src.main`, `src.services.afr`, `src.worker.replay_worker` all OK
- No circular imports between `src.core.security` and `src.core.oidc`

## What unblocks e2e

1. Provision PostgreSQL 16 and set `AFR_TEST_DATABASE_URL` → enables B02 DB-gated
   tests + B05 worker integration tests
2. Provide a real disposable `BASELINE_URL`/API key/project + explicit confirmation
   → enables `scripts/product_journeys.py` end-to-end evidence
3. Independent review of all evidence → release gate can be evaluated
