# Remaining Work — Agent Flight Recorder (AFR)

Tracks what is still to be done after the B01–B06 implementation landed via
PR #2 (branch `arena/33ccc0e3-agent-flight-recorder`, merged into `main`).

**Source of truth:** this file plus `implementation/implementation-plan.json`
and `implementation/backlog.csv`. Do not self-certify any ticket as complete;
each item needs independent evidence review.

## Status key
- `pending` — not started
- `written` — code/tests written, not yet validated against required infrastructure
- `blocked` — cannot proceed locally; requires external provisioning
- `review` — implementation done, awaiting independent evidence review

---

## B00 — Contract baseline
**Status:** done (committed `2ea93a4`)

Remaining: independent evidence review of the scoped idempotency fix and
repository map. No code changes needed.

---

## B01 — Dependency/runtime lock
**Status:** done (committed `79b7f95`)

Remaining: Python 3.12 / Node 24 target smoke (local env is Python 3.11.2 /
Node 22.22.3 — version drift documented, not blocking). SBOM/license review.
Independent evidence review.

---

## B02 — Database/roles
**Status:** done (committed `84176da`)

Remaining:
- Run `tests/db/test_postgres_gated.py` against real PostgreSQL 16
  (`AFR_TEST_DATABASE_URL` must be set; skipped locally — no PostgreSQL
  binaries, no Docker, not root, outbound internet restricted).
  Covers: migration apply, composite FK cross-project rejection, append-only
  triggers, RLS project scoping, pooled context reset, idempotency scoping,
  org-scoped project creation.
- Independent evidence review.

**Blockers:** real PostgreSQL 16 unavailable locally. No SQLite substitution
per constraint.

---

## B03 — Identity/authorization
**Status:** stubs done (committed `709de35`); full acceptance pending

Done:
- `src/core/oidc.py` — stdlib-only signed stub tokens, fail-closed production
  verifier, test-only injection (`configure_oidc_verifier`)
- `tests/test_oidc_stub.py` — 9 tests (issue/verify, tamper/issuer/expiry/
  malformed rejection, production fail-closed, verifier reset)
- `verify_token()` returns `None` for every token in production (no verifier
  configured)

Still to do (`pending` / `blocked`):
- Real OIDC login/logout/expiry/state/PKCE/CSRF against a live IdP
- Capability matrix + API-key scopes + 401-first endpoint smoke against real DB
- These require PostgreSQL 16 and a configured OIDC issuer; not implemented here
- Independent evidence review

**Blockers:** no PostgreSQL 16, no disposable OIDC IdP credentials.

---

## B04 — Artifacts/deletion
**Status:** foundation endpoints implemented (in `src/api/foundation.py`,
committed `2d63d52`); awaiting DB validation

Still to do:
- Stream hash/quota/finalize/idempotency tests against real DB
- No arbitrary paths; project isolation; active revoke/derived purge/restore
- Independent evidence review

**Blockers:** no PostgreSQL 16.

---

## B05 — Jobs/outbox
**Status:** worker + gated integration tests written (committed `2970f10`);
tests skipped without PostgreSQL 16

Done:
- `src/worker/replay_worker.py` — fenced lease (`SKIP LOCKED`), fence-checked
  terminal completion, stale-fence rejection, cancellation-safe
- `src/worker/main.py` — entry point (`WORKER_PROJECT_SCOPES`, SIGTERM/SIGINT)
- `tests/worker/test_replay_worker_integration.py` — 4 gated tests

Still to do:
- Run the 4 gated tests against real PostgreSQL 16 with FORCE RLS enforced
- Crash/ack/store fault tests; retry semantics
- Independent evidence review

**Blockers:** no PostgreSQL 16.

---

## B06 — AFR vertical slice
**Status:** core + frontend done (committed `2d63d52`, `4b11d59`)

Done:
- All 9 AFR routes DB-backed; idempotency-key enforced; capability checks
- `FlightRecorderService` — ingest/runs/cases/replays, fail-closed replay
- React/Vite/TS frontend: `afr_runs`, `afr_run`, `afr_case`, `afr_replay`
- `tsc --noEmit` clean; `npm run build` passes

Still to do (`blocked`):
- End-to-end producer submission → persisted run/events → inspection → frozen
  case → worker replay → terminal result in browser/API
- Requires `scripts/product_journeys.py` with real disposable API URL/key/
  project + explicit confirmation; no secrets injected
- Independent evidence review

**Blockers:** no PostgreSQL 16 (DB routes return 503), no disposable API
credentials, `production_ready=false`.

---

## B07–B15 — Deferred products / hardening / release
**Status:** planned (not started)

- B07 SKB vertical slice, B08 EVF fixture slice, B09 docling integration,
  B10 frontend qualification, B11 cross-product hardening, B12 data/statistics
  holdouts, B13 deployment/lifecycle, B14 clean-room build/review,
  B15 production release
- Per `implementation/implementation-plan.json`, these depend on B06 and are
  intentionally outside this slice.
- `production_ready=false`; release gates blocked until B06 evidence exists.

---

## Cross-cutting remaining items

| Item | Detail | Blocker |
|------|--------|---------|
| `production_ready=false` | Release gate reports ready=false with 15 blocking checks, null evidence | Requires real implementation + integration evidence |
| Evidence tickets | Complete `evidence/tickets/B03.md`…`B06.md` with review sign-offs | Independent review required |
| docs/Repository_Map.md | Keep in sync as worker/web paths evolve | Ongoing |
| Version drift | Python 3.11.2 vs target 3.12; Node 22 vs target 24 | Environment provisioning |
| No secrets | Never inject secrets into commands/history/commits/evidence | Standing constraint |

## How to unblock

1. Provision PostgreSQL 16 and set `AFR_TEST_DATABASE_URL` → enables B02 DB-gated
   tests + B05 worker integration tests
2. Provide a real disposable `BASELINE_URL`/API key/project + explicit
   confirmation → enables `scripts/product_journeys.py` end-to-end evidence
3. Configure a live OIDC IdP for B03 real-flow tests
4. Independent review of all evidence tickets → release gate can be evaluated
