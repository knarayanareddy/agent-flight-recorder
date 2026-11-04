# Verification catalog and release evidence

**Status:** test specifications only; none are represented as executed. Every automated test must link to its implementation and CI run; manual tests link to dated findings/signoff. A test ID denotes a suite, not one assertion. Shared tests are inherited by every product. Security checks are defense evidence, not a proof that every vulnerability is absent.

## 1. Shared foundation tests

| ID | Setup / stimulus | Expected outcome / evidence |
|---|---|---|
| FND-T01 Identity/session | test IdP with wrong issuer/audience, expired tokens, rotated keys; CSRF and session fixation; local bootstrap exposed remotely | All invalid cases denied; no sensitive error detail; secure session settings; exposure preflight refuses insecure mode |
| FND-T02 Authorization | two projects, all five role profiles, revoked membership, guessed IDs; read/list/write/export/job/SSE/artifact endpoints | Full endpoint×role×resource matrix denies cross-project access; revoked sessions/keys obey documented cache TTL; no list/stream side channel |
| FND-T03 Artifact integrity | duplicate finalize; corrupt bytes; wrong media; unfinished upload; interrupted download; digest collision scenario through supplied metadata | Server-computed digest authoritative; no unsafe promotion; per-project access; bounded orphan cleanup |
| FND-T04 Provider/secret boundary | canary secret in client/config/error; arbitrary provider URL, IPv6/private IP, redirects and DNS changes | No secret serialization; only configured destinations; egress proxy enforces policy at connection, not merely form validation |
| FND-T05 Deletion | source with all derivative classes; delete while processing/exporting; restore older backup | Immediate read revocation, bounded purge, tombstone replay before service; derived manifests reveal no removed content |
| FND-T06 Job durability | fail transaction, lose ack, duplicate outbox, expire lease, finish stale attempt | One logical accepted result; fencing rejects stale completion; no false exactly-once external-action claim |
| FND-T07 Limits/cancel | infinite child process, huge stdout, pid/disk/memory exhaustion, cancel during external call | Quotas enforced; cancel state honest; new capabilities revoked; in-flight external-send limitation disclosed |
| FND-T08 Budget races | simultaneous pair/job dispatch, unknown pricing, retries, grading, provider usage lag | Atomic reservation; all attempts accounted; unknowns labeled; conservative in-flight overshoot bound documented |
| FND-T09 Isolation | hostile full harness/scorer/plugin attempts host read, DB access, Docker socket, other job data and egress | Denial at actual deployment boundary; no service credentials reachable; unsupported backend refuses live mode |
| FND-T10 Recovery | terminate dispatcher/worker, unavailable DB/store/provider, stranded artifacts | Retry/reconcile safely; unknown effects require reconciliation; missing data not success |
| FND-T11 Design/accessibility | component states at keyboard, 200/400% zoom as applicable, contrast, reduced motion, assistive technology | Applicable WCAG 2.2 AA criteria reviewed; failures logged; focus/text alternatives correct; no automated-certification claim |
| FND-T12 Realtime status | SSE disconnect, old cursor, revoked session, duplicate events, browser offline | Persisted truth retrieved; auth reapplied; progress not lost or announced excessively |
| FND-T13 Verification | malformed output, verifier error, hostile custom code, self-reported pass | Typed outcomes; error/unscored not pass; built-ins safe; custom code isolated |
| FND-T14 Security regression corpus | XSS, archive traversal/bomb, SSRF, prompt injection, canary secrets and path attacks | Required boundary controls block fixture attacks; coverage and limitations recorded |
| FND-T15 UX pilot | five representative users per product on primary tasks; include keyboard/text alternative | At least four complete stated tasks unaided; observed issues reviewed; small sample not market validation |
| FND-T16 Deployment | clean host, default password, exposed data port, wrong proxy/origin, missing required executor | Secure reference install; insecure state rejected; only edge exposed; mode capabilities truthful |
| FND-T17 Backup/restore | fresh restore from reference backups and separate deletion tombstones | RPO<=24h/RTO<=4h target measured in supported profile; source/artifact references consistent |
| FND-T18 Capacity | declared 20 users and product datasets, resource instrumentation, outage/burst | API p95<500ms and error<1% excluding external work at declared profile; capacity and exceptions published |
| FND-T19 Operations | tabletop plus practical leak/worker compromise/cost/migration/rollback drill | Operator follows runbook; secrets rotated, dispatch contained, evidence preserved safely, no unsafe restore |
| FND-T20 Release integrity | install signed/pinned artifact from clean environment; check SBOM/licenses/migrations | Source/image/version provenance consistent; reproducible fixture install; release blockers absent |

## 2. Agent Flight Recorder suites

| ID | Test design | Release expectation |
|---|---|---|
| AFR-T01 Capture privacy | seed secrets in provider config, nested args, exception, object repr and exports with capture on/off | Metadata-only default; no generic object walk; all declared canaries absent from buffer/log/export; opt-in policy represented |
| AFR-T02 Ingestion | repeated batches, reorder/gaps, conflicting sequence, interleaved producers, crash/ack loss | No duplicate logical events; conflicting data rejected; per-producer gaps tracked; bounded buffer/load targets measured |
| AFR-T03 Completeness | independent oracle removes event/content/terminal span; add orphan/late events | 100% intentional loss indicators; no fake global completeness percentage; frozen case stays tied to snapshot |
| AFR-T04 Replay side effects | instrument network/filesystem sentinel; simulate repeated identical calls and unmatched args | Playback/simulation make zero live calls; exact declared matching; mismatch fails closed |
| AFR-T05 Controlled live policy | change plan after approval, attempt production tool/endpoint, expire grant, cancel | Bound approval rechecked; production writes unsupported; no live fallback; unknown effects flagged |
| AFR-T06 Trace-to-test | known defect/fix in mock state; task outcome scorer independent of agent output | Failing case fails, fixed case passes; valid JUnit/JSON; no self-reported success accepted |
| AFR-T07 Fixture portability | roundtrip clean instance, older schema, unsupported extension, corrupt/traversal bundle | Required fields preserved, unsafe/incompatible inputs rejected, provenance/omissions retained |
| AFR-T08 UX/capacity | five-user diagnosis and <=10-minute case task; 10k-event timeline; keyboard/list mode | Stated 4/5 usability goal and declared render/load target; missing evidence understood |
| AFR-T09 Evaluator boundary | malicious verifier/plugin, source hidden answers, stale job output, escaped artifact paths | Full extension isolation; hidden tests unavailable; wrong attempt rejected; unsupported mode disabled |
| AFR-T10 Lifecycle | standalone install, adapters, source/fixture deletion, backup/upgrade/rollback | Reference lifecycle evidence; independent install; inherited shared gates all pass |

## 3. SkillBench suites

| ID | Test design | Release expectation |
|---|---|---|
| SKB-T01 Intake | hostile archives, repo/protocol URLs, submodules, scripts/templates, executable preview | Inspect never executes package; source/digest/limits correct; malicious references denied |
| SKB-T02 Plan immutability | edit after preregister, repeated submit, conflicting draft, wrong source hash | New revision required; duplicate request one experiment; invalid/mismatched plans rejected |
| SKB-T03 Treatment control | paired oracle records environment/memory/cache/tasks, randomized order and activation | Only declared intervention differs; no arm contamination; actual skill load known; repeats grouped |
| SKB-T04 Runtime economics | 429/outage, retry, incomplete pair, pause/cancel, grading and unknown price | All attempts/grading charged in record; no selective rerun; truthful partial state and bound reservation |
| SKB-T05 Outcome integrity | static not-run/failed, semantic task failure, policy block, infrastructure error, malicious self-score | Distinct result categories; incomplete scan not clean; trusted validators decide outcomes |
| SKB-T06 Statistical correctness | known-effect simulations, correlated repeats, tiny/degenerate samples, missing arms, post-hoc metrics | Numerical check against independent reference; correct task clustering; no unsupported winner/equivalence claim |
| SKB-T07 Hidden-data isolation | attempt scorer/test/other-arm reads, injected judge instructions, forged result IDs | Hidden data never candidate-visible; whole untrusted harness isolated; judge has no action authority |
| SKB-T08 Interpretation/accessibility | five-user plan/result tasks, intervals as text, table drilldown and filtered results | 4/5 complete/interpret core workflow; denominators and uncertainty visible; filtered headline not silently changed |
| SKB-T09 CI reports | package/suite/plan/analysis revision drift, corrupt imports, fork PR publisher | Badge/report bound to exact evidence; stale/incomplete warning; publisher separate and minimally privileged |
| SKB-T10 Lifecycle/reproduction | keyless fixture report, pinned backend, restore/delete hidden/source artifacts | Independent installation/reproduction; nondeterminism disclosed; missing evidence prevents unearned claims |

## 4. EvidenceForge suites

| ID | Test design | Release expectation |
|---|---|---|
| EVF-T01 Hostile source | non-PDF, mismatch magic, encrypted, truncated, malformed, embedded actions/files, page/image bombs | Safe bounded reject/quarantine; no active code/network; parser failures contained |
| EVF-T02 Version lineage | identical source multiple parse versions; amended source; late completion and deletion | Original immutable; reviews not overwritten; output hashes/version relations consistent |
| EVF-T03 Geometry/citation | all rotations, nonzero crop, page labels, multi-region evidence, zoom and OCR quote | Transform error <=1 rendered pixel on synthetic oracle; valid existing refs; no fabricated locations |
| EVF-T04 Numeric/schema semantics | locales, parentheses, dash versus zero, scale/currency/period, spans/header joins | Decimal/raw/typed outputs exact on golden fixtures; unsupported ambiguity explicit |
| EVF-T05 Support versus correctness | right quote/wrong row, prior/current period, mixed scales, source contradictions, model invented quote | Validation/risk flags correct; evidence support not mislabeled factual certainty; unsupported proposals never silently verified |
| EVF-T06 Review conflicts | simultaneous edits, evidence replacement, dependent totals, stale approvals | Optimistic conflicts handled without lost updates; full immutable history; validation reruns |
| EVF-T07 Export | JSON/CSV roundtrip, formulas, missing values, incomplete review, expired source URLs | Typed state/values preserved; safe cells; artifacts referenced by stable IDs; unresolved warnings retained |
| EVF-T08 Purge/restore | delete during parse/review/export; all derivatives and cache; old backup | Reads revoked; active bytes/index/exports purged; tombstones before restored traffic |
| EVF-T09 Analyst UX | seeded wrong-row correction/export by five users, source-text keyboard/zoom path | 4/5 unaided target; source/support/confidence distinction understood; accessibility blockers fixed |
| EVF-T10 Quality/cost | 100-report issuer-family split, independently adjudicated labels, held-out classes and failures | All denominators/classes/costs published; stated in-scope targets met or supported scope honestly revised |

## 5. Test execution policy

### Every pull request

Format/lint/types, schema compatibility, deterministic unit/property tests, changed-module integration, auth/secret/XSS regression, migration smoke, build, component accessibility, smoke E2E and dependency changes. Branch protection requires independent review. Fork builds get no protected secrets and cannot publish artifacts.

### Nightly/protected branch

Full DB/object/workflow integration; provider-contract tests on capped synthetic data where configured; failure/chaos fixture matrix; adapter-version matrix; dependency/advisory review; deterministic statistical simulations. Stochastic eval jobs use protected configs, caps and explicit consent. Provider outage is infrastructure invalid, not evidence of model degradation.

### Release candidate

All requirement suites, full E2E/manual accessibility, supported-environment install, domain holdout evaluation, security deployment preflight, load/chaos report, deletion/restore drill, upgrade/rollback drill, license/SBOM verification, independent reproducibility review and product/security/statistical signoff where relevant. Artifact versions are frozen before final evaluation.

### Avoid test gaming

No editing golden expectations merely to make changed outputs pass. Any oracle/annotation/scorer change needs review, explanation and new version. Holdout exposure recorded; use fresh holdout or label post-tuning results. Document flaky tests and root cause; do not silently ignore failures. Coverage percentages supplement risk-based testing; no arbitrary coverage target substitutes for critical-path verification.

## 6. Evidence record template

```
Test ID / product requirement:
Implementation commit / image digest / schema version:
Fixture/dataset/scorer digests and rights:
Environment and hardware:
Exact command / configuration / repetitions:
Expected outcome / observed outcome:
Sample sizes, denominators, exclusions and uncertainty:
Artifact links (redacted, access-controlled):
Security/privacy scan of evidence:
Reviewer / date / pass-fail / limitations:
Remediation task and rerun if failed:
```

## 7. Release go/no-go checklist

- [ ] Every in-scope R-ID maps to implementation tasks and evidence-backed T-suites.
- [ ] No unresolved critical data integrity, isolation, authorization, credential leak or fabricated-evidence issue.
- [ ] Any high-risk issue has security-owner disposition; release-blocking issues cannot be waived to meet a launch date.
- [ ] Public demo fixtures are synthetic/authorized and cannot spend money or execute uploads.
- [ ] Benchmark scope, baselines, failed cases and uncertainty are accurately disclosed.
- [ ] All user-facing modes reflect actual executor/security capabilities.
- [ ] Privacy, deletion, backup expiry, external-provider transfer and downloaded-export limits documented.
- [ ] Source/model/data/font terms reviewed for the exact shipped versions.
- [ ] Install, migration, rollback, restore, capacity and incident drills have dated evidence.
- [ ] Post-release owner, advisory channel, maintenance policy and dependency review cadence assigned.

