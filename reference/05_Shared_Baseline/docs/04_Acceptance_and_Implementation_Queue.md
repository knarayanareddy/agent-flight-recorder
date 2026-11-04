# Agent implementation queue and acceptance map

The original 150-task/30-gate backlog remains in the prior pack. The B0 queue below fixes a smaller executable slice and its ordering. Do not mark original live-engine or production qualification tasks complete when only B0 fixtures pass.

## Ready sequence

| Ticket | Depends | Required implementation files | Acceptance / DoD |
|---|---|---|---|
| B00 Contract baseline | none | contracts/*, tests/*, docs/* | Local baseline suite and manifest pass; review limitations; source controls frozen |
| B01 Runtime/dependency lock | B00 | apps/api/pyproject.toml + transitive lock, apps/web/package.json + lock, images/Dockerfiles | Use exact registry candidates as starting versions; resolve compatibility; run Python3.12/Node24 smoke; pin all runtime/transitive versions and images; SBOM/license review |
| B02 Database/roles | B01 | apps/api/db/*, Alembic wrapper, tests/db/* | Apply both SQL migrations on real Postgres16; role/RLS/FK/immutability/concurrency/pool-reset tests; never runtime owner |
| B03 Identity/authorization | B02 | apps/api/auth/*, permission service, web session routes | Real OIDC login/logout/expiry/state/PKCE/CSRF, capability matrix, API-key scopes, 401-first endpoint smoke |
| B04 Artifacts/deletion | B03 | apps/api/foundation/uploads.py, artifacts.py, lifecycle.py | Stream hash/quota/finalize/idempotency; no arbitrary paths; project isolation; active revoke/derived purge/restore tests |
| B05 Jobs/outbox | B04 | apps/dispatcher/*, job repository, broker-disabled policy | Transactional enqueue/leases/fencing/cancel/retry; crash/ack/store fault tests; fixture dispatcher no external network |
| B06 AFR vertical slice | B05 | apps/api/afr/*, capture client, apps/web/afr/* | Actual ingest/dedupe/case/replay APIs+DB+UI; authenticated AFR journey positive+negative control; no oracle production import |
| B07 SKB vertical slice | B05 | apps/api/skb/*, analysis service, apps/web/skb/* | Safe ZIP inspect, approval, immutable plans, fixture pairs, descriptive analysis; actual SKB journey; explicitly simulation |
| B08 EVF fixture slice | B05 | apps/api/evf/*, review/export service, apps/web/evf/* | Actual fixture source/parse/extract/review/conflict/export/delete journey; eight semantic fields; all source links resolve |
| B09 Docling integration | B08 | isolated parser adapter/images/assets.lock, tests/parser/* | Real parser on synthetic and licensed ten-document pilot; actual coordinate transforms/model/code terms/resource/no-egress tests; not fixture-only substitution |
| B10 Frontend qualification | B06,B07,B08 | component tests, browser journeys, accessibility evidence | All12 screen/state contracts; real OIDC session; keyboard/text alternatives; manual assistive-tech review and five-user tasks |
| B11 Cross-product hardening | B06,B07,B08,B09 | acceptance/security/*, chaos/load/* | Full endpoint role/object matrix, secret canaries, duplicate/concurrent/failure tests and capacity report; fixture API smoke alone insufficient |
| B12 Data/statistics holdouts | B07,B09 | rights manifest, hidden gold, evaluation reports | Independent domain/statistical review; no tuning final holdout; intervals/missingness/correctness/coverage results published |
| B13 Deployment/lifecycle | B10,B11,B12 | built signed images, SBOM, ops evidence | Install actual product on reference host; encrypted backup/restore/tombstone/upgrade/rollback/load drills |
| B14 Clean-room build/review | B13 | separate session log, resulting commit, question ledger | A separate agent/person implements/reproduces selected slices from frozen baseline without undocumented help; review assumption gaps; not the authoring subprocess |
| B15 Production release | B14 | evidence/release-status.json, signed release review | All required gate evidence reviewed; actual operator signoff; no unresolved critical auth/isolation/data-integrity issue |

Each ticket uses global GDoD from prior pack plus AGENTS.md. Completion evidence: exact commands/exits, source/image/config hashes, environment/hardware, fixtures/data rights, expected/observed results, failures/exclusions, independent reviewer and limitations. Assign people/effort before implementation; roles are not substitute for named owners.

## Exact available commands

```
python -m pip install -r requirements-baseline.txt
python -m pytest -q
python scripts/verify_manifest.py
python scripts/consumer_trial.py
python scripts/release_gate.py           # EXPECTED FAIL until production evidence exists
python scripts/product_acceptance.py     # BLOCKED/exit2 without actual API URL
python scripts/product_journeys.py        # BLOCKED/exit2 without actual API+test credentials
```

Fresh fixture regeneration is `python scripts/build_contracts.py && python scripts/build_fixtures.py`; contract changes are reviewed. Manifest verification must fail after an unreviewed contract/fixture modification; an implementation agent must not regenerate the manifest to conceal changes.

## Black-box versus oracle tests

`tests/test_baseline.py` validates contracts and independent deterministic algorithms, not product handlers. `product_acceptance.py` exercises every domain operation unauthenticated, ensuring auth precedes object/schema/mode disclosures. `product_journeys.py` exercises actual positive/negative AFR cases, SKB fixture experiment and EVF review/export/conflict/delete against an implemented disposable API. It never calls the Python oracle. Neither black-box script proves complete security, frontend correctness, a real IdP, Docling, transaction durability or operational readiness.

For full role coverage, implementation adds generated cases from endpoint policy × roles × object ownership, including revoked memberships and API scope intersection. Test each GET/list/mutation/download, including repeated requests and stale revisions. Use two authorized projects in distinct organizations and users with each capability. Do not simply assert every forbidden response is403: concealed cross-project object is404 after project authorization, unauthenticated401, known project wrong capability403.

## Required browser journeys

1. AFR: fixture capture → failed/incomplete run inspection → case freeze → recorded pass/fail → clear omissions. Keyboard flow and10k-event list target.
2. SKB: inspect ZIP without execution → reviewer digest approval → plan freeze → fixture monitor → result with taskN/interval/bounds and simulation label. Invalid scan state never clean.
3. EVF: upload → source/evidence → wrong-row/period detection → correction conflict → explicitly incomplete or reviewed export → deletion read denial. Screen-reader source-text alternative.

Every journey runs loading/empty/denied/offline/error/partial/conflict variants as applicable. Network retries cannot duplicate mutations. Comparison, charts, advanced reporting, adapters and public sharing from prior full-v1 pack are not silently claimed in B0.

## Live expansion B1 gates

Full untrusted harness loading/scorer process isolated on verified dedicated runsc host; Inspect live engine spike; SkillEvaluator static/report integration spike; model broker and consent/secret/cost enforcement; actual paired outcomes and reviewed analysis; AFR provider/framework capture/replay safety; EVF corpus/format/language validation. Add schemas/API/profile versions instead of widening B0 enums in place. Public tenant/marketplace/SaaS support requires additional threat/abuse/legal/on-call review.

## Clean-room trial procedure

Freeze the baseline manifest+commit. Give a separate implementation agent only README/AGENTS/operator non-secret inputs. Assign B02+B06 or another nontrivial slice. Record every clarification, assumption, failed contract and dependency issue in a question ledger. Do not answer with undocumented architecture; amend baseline with reviewed decisions then restart/retest affected work. Validate resulting implementation with independent tests/hidden fixtures, not only that agent's own suite. Measure clarification count, unexplained deviations and failing acceptance cases. Zero questions is not a success if the agent guessed wrong. This trial remains NOT RUN until such an independent session exists.
