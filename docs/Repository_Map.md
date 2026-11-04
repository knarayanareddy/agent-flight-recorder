# Repository map — Agent Flight Recorder (AFR) checkout

**Purpose:** translate inherited queue/path references into the actual layout of this
checkout. This file is working authority for path mapping only; it does not authorize
API changes or wider product scope.

## Product scope

Only **AFR** is implemented here. Shared foundation tables/migrations exist for all
three products, but SKB/EVF application code is intentionally absent (deferred to their
own products/sessions).

## Actual layout vs. inherited queue names

| Inherited reference (B queue / docs) | Actual path in this checkout | Notes |
|---|---|---|
| `apps/api/*` | `src/` | FastAPI backend: `src/main.py`, `src/core/`, `src/models/`, `src/schemas/`, `src/api/`, `src/services/`. Route prefix `/api/v1`. |
| `apps/api/pyproject.toml + transitive lock` | `pyproject.toml`, `requirements.txt`, `requirements-baseline.txt` | Root packaging; no separate `apps/api` package. |
| `apps/api/db/*, Alembic wrapper` | `src/core/database.py` (engine/session), Alembic env wrapper under `src/`, SQL in `database/migrations/` | Migrations are SQL files applied to PostgreSQL 16 outside the app process. |
| `apps/api/auth/*` | `src/core/security.py`, `src/api/deps.py` | Token verification, fail-closed auth deps, capability checks. |
| `apps/api/foundation/uploads.py, artifacts.py, lifecycle.py` | `src/api/foundation.py` | Upload/finalize/job routes (501 stubs until B02/B04 persistence connects). |
| `apps/dispatcher/*` | `src/worker/` | Python worker: `replay_worker.py` (fenced lease/fence execution via `SKIP LOCKED`), `main.py` entry point. Claims `afr.replay` jobs and publishes terminal results fail-closed (zero network calls). |
| `apps/web/*` | `apps/web/` | React/Vite strict-TypeScript frontend; four AFR UI routes: `afr_runs` (`/afr/runs`), `afr_run` (`/afr/runs/:run_id`), `afr_case` (`/afr/cases/new`), `afr_replay` (`/afr/replays/:id`). Proxies `/api/v1` to the FastAPI backend. |
| `acceptance/` | `evidence/` + `scripts/product_*.py` | Black-box journey/smoke acceptance tooling runs against a real disposable API. |
| `reference/05_Shared_Baseline/` | `reference/05_Shared_Baseline/` | Provenance/reference material only; never copied into working source, never edited to make root verification pass. |
| `implementation/*` | `implementation/product-focus.json`, `implementation-plan.json`, `backlog.csv` | `product-focus.json` authority now points at the local `implementation-plan.json`. |

## Directories that exist but hold no application code

- `src/worker/` — implemented: fenced replay worker + entry point (B06).
- `apps/web/` — implemented: React/Vite strict-TypeScript frontend (B06).
- `apps/api/` — does NOT exist; do not create. Backend lives at `src/`.

## Conventions

- All public API routes are mounted under `/api/v1` in `src/main.py`.
- Migrations: `database/migrations/001_baseline.sql` (schema, RLS, immutability triggers) and `002_roles.sql` (roles, grants, policies), applied once as migration owner on PostgreSQL 16.
- Runtime app role must never be table owner/superuser/BYPASSRLS.
