# Observed verification report

**Baseline:** 0.2.0 · **Date:** 2026-11-03 · **Overall production readiness: BLOCKED**

## Actually executed

| Check | Observed result | What it establishes |
|---|---|---|
| Python baseline suite | **89 passed** | Schema shape/examples and deterministic reference-algorithm checks, including known-positive/negative fixtures |
| PostgreSQL static parse | passed within test suite | SQL parses; does NOT establish database execution, permissions, RLS or concurrency correctness |
| OpenAPI reference/policy checks | passed within test suite | Referenced schemas/operation IDs/headers are internally connected; not real API conformance |
| UI contract reference checks | passed within test suite | Screen actions reference defined operations; not rendered UI or accessibility conformance |
| Separate-process contract consumer | passed; **48 domain operations consumed** | Request examples can be found/loaded without running a product; NOT an independent implementation-agent trial |
| Protected-input manifest | passed | 180 baseline input file hashes unchanged at check time; not publisher authenticity |
| Source syntax/queue dependency check | passed | Python files compile; 16-ticket dependency order has no unresolved backward reference |
| Production gate | **nonzero, as intended** | Missing production evidence is not silently accepted |
| Actual API smoke without URL | **exit2 BLOCKED** | No fake API behavior or silent test skip |
| Authenticated product journeys without API/keys | **exit2 BLOCKED** | Real integration evidence is required |

Execution used the environment/version recorded in `validation-results.json` (Python3.13). The intended application Python3.12 environment still needs verification. Raw command output and JUnit XML are alongside this report. No upstream application installer was executed. Public registry metadata was fetched for dependency/image candidate pinning; those candidates were not integration/security approved by that fetch.

## Working deterministic spikes

- Event batches: retry deduplication, contradictory duplicate rejection, rollback of a partially traversed failing batch, project scoping in the oracle.
- Recorded output matching: repeated-call ordinal selection, canonical argument matching, fail-closed missing fixture.
- Skill analysis: known +0.5 task-level effect on 12 tasks ×3 repeats ×2 arms, deterministic paired bootstrap, incomplete-pair bounds, no confidence interval for tiny samples.
- Document geometry: all four rotations, nonzero/negative crop offsets, 100-point roundtrips per rotation and out-of-crop rejection.
- Numeric/evidence: locale/negative/scale normalization, dash not zero, fabricated quote/page/hash rejection; spreadsheet formula mitigation.

These spikes validate local candidate algorithms. They do **not** substitute for upstream engine/parser integration, independent mathematical/security review, full adversarial testing or actual service behavior.

## Not executed / still release-blocking

1. Actual APIs, React UI, workers and persistence implementation.
2. PostgreSQL16 migration application, RLS/role/FK/concurrency tests.
3. OIDC browser/session/CSRF integration and full object/role authorization matrix.
4. Docling plus actual OCR/model assets, real PDF layout quality/coordinate mapping and parser containment.
5. Inspect/SkillEvaluator live integration or any paid model experiment.
6. Docker/runsc hardened host validation (Docker unavailable here); live untrusted execution remains disabled.
7. Real install/load/chaos/backup/restore/tombstone/rollback evidence.
8. Manual accessibility/usability and independently labeled document holdout.
9. Statistical and independent security reviews.
10. **Independent clean-room agent build trial**. The contract consumer was a subprocess rehearsal, not another agent implementing the system.
11. Built signed product images/transitive locks/SBOM and operator launch signoff.

The evidence ledger intentionally leaves these gates not-run/blocked. This is a substantial upgrade from prose design to executable baseline inputs, **not certification that all eight requested workstreams have been fully closed**. No deployable product is being represented as complete.
