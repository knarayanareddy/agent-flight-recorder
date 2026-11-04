# Shared foundation — architecture and engineering contract

**Version:** 0.1 design baseline · **Date:** 2026-11-03 · **Status:** proposed, not implemented or security-certified.

Applies to Agent Flight Recorder (AFR), SkillBench (SKB), EvidenceForge (EVF). MUST means release-blocking; SHOULD requires a documented exception; MAY is optional. All performance numbers are proposed acceptance targets, not measured outcomes. The phase runbooks and backlog refine these contracts; product-specific restrictions may be stricter.

## 1. Scope and deployment promises

Three independently installable products share versioned libraries, contracts, design components, and optional deployed services. Sharing does not require installing all products. V1 supports a private, single-organization deployment with projects, roles, and authenticated collaborators. It is **not** a public untrusted multi-tenant execution service. Public demo mode only exposes synthetic fixtures and disables uploads, arbitrary code, external URLs, and paid execution.

Two modes:

- **Developer:** Docker Compose, local Postgres and artifact volume; explicit local identity bootstrap; no arbitrary untrusted execution unless a supported isolated executor is configured. Bind local services to loopback by default.
- **Private server:** TLS reverse proxy, OIDC, Postgres, S3-compatible private object storage, dedicated worker hosts, secrets service, backups, restricted ingress/egress. Container orchestration is optional, not a prerequisite for sound operations. Expose only the edge service. No default passwords or demo login.

SQLite and seamless offline synchronization are deferred. A consistent Postgres code path is preferable to three lightly tested storage backends. A product can run alone using the same deployment template with only its worker profile enabled.

## 2. Product boundaries and ownership

| Layer | Owns | Must not own |
|---|---|---|
| Identity/project module | membership, project roles, API key scope, policy checks | external IdP passwords |
| Artifact module | immutable content, digests, access authorization, retention | arbitrary active HTML execution |
| Job module | leases, retries, cancellation, limits, outbox | executing untrusted code in API process |
| Event/evaluation contracts | versioned envelopes, result definitions | application-specific grading logic |
| AFR | capture, trace completeness, replay plans, regression fixtures | general-purpose autonomous agent runtime |
| SKB | skill packages, experiment plans, comparisons, evidence | universal skill certification |
| EVF | document lineage, extraction, provenance, review, export | automatic high-stakes decisions |

One modular FastAPI application per product deployment; modules are explicit packages, not microservices by default. Optional combined deployment uses one API and module namespaces. Each product owns its tables and migrations. Access shared artifacts through a narrow library/API rather than unrestricted cross-product SQL. Schema contracts version independently from the product release.

## 3. Reference topology

```text
Browser / CLI / capture SDK
          |
    TLS edge + OIDC session
          |
React web <-> FastAPI control plane ------> Postgres
                  |                        metadata + jobs + outbox
                  +--> Artifact gateway --> private object store
                  |
          scheduler/dispatcher (trusted)
                  |
     isolated worker pool per trust class
       |              |                |
 trusted transforms  parsers       untrusted evaluation/replay
                       |                |
             no general egress     capability/model broker
                                         |
                              approved external model endpoints
```

**Critical:** the browser uses relative `/api` routes; the edge proxies backend services. Secrets never enter frontend bundles. Workers cannot connect to the control-plane database directly; a trusted dispatcher issues scoped, short-lived job capabilities. Trusted parser wrappers may use a constrained worker API; arbitrary skill/task/scorer code never receives that credential. Workers return artifacts through a per-job collector. The collector checks digest, size, media type, attempt, and project ownership.

### Stack baseline

- TypeScript strict mode, React, a pinned supported router/build stack; Tailwind or CSS tokens, accessible primitives; TanStack Query for server state. Use a reviewed PDF.js build in EVF, not a remote CDN.
- Python 3.12 baseline, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic; confirm each integration's Python support during dependency spikes. A library needing a newer Python can live in a separate pinned executor image.
- Postgres supported major pinned in deployment; connection pooling, statement timeouts, transactions, constraints, and migrations. JSONB for versioned extension payloads, not for all relational state.
- Local artifact directory with controlled gateway in developer mode; S3-compatible API in server mode. No license assumption about a particular storage implementation.
- Postgres job table and outbox initially. Introduce a queue service only after measurements show contention or scheduling limitations. Do not build both queue paths at launch.
- Pytest/Hypothesis, Vitest, Playwright, axe-core, Schemathesis or equivalent API contract tests; dependency and container scanning; deterministic fixture suite on every PR.

## 4. Common data model

Every access-controlled entity has `id`, `organization_id`, `project_id` where applicable, `created_at`, `created_by`, and a revision or immutable version. Server derives organization from authentication and verifies project membership; client-supplied organization fields are not authoritative.

Core tables: `organizations`, `users`, `memberships`, `projects`, `project_roles`, `api_keys`, `artifacts`, `artifact_links`, `jobs`, `job_attempts`, `outbox`, `audit_events`, `deletion_requests`, `provider_profiles`, `budget_reservations`.

- Use UUID identifiers; never use identifier unpredictability as authorization.
- Artifact logical ID belongs to a project; bytes are immutable. Content hash verifies integrity but does not establish authenticity or correct ownership. Never expose a cross-project deduplication oracle. Deduplicate physically only within a project in v1.
- Store observed and received timestamps separately. UTC ISO timestamps externally; monotonic durations within one process. Do not infer causal order across machines from wall time.
- Represent prices using decimal strings and explicit currency/rate-table revision. Token counts can be missing or estimated. Unknown is not zero.
- Record actor identity, action, target, decision, policy version, and request ID in audit events; exclude content and credentials. App-level append-only is not cryptographic tamper-proof storage against database administrators.
- Immutable scientific/evidence versions can coexist with deletion: mark deleted, revoke access, remove bytes and derived records, and retain only minimal non-content audit metadata according to operator policy.

### Artifact contract

`artifact_id`, `project_id`, `sha256`, `byte_size`, `media_type`, `classification`, `capture_policy_id`, `origin`, `created_at`, `expires_at`, `storage_locator` (server-only), `status` (`pending`, `ready`, `quarantined`, `deleting`, `deleted`). Creation is a two-step upload/finalize operation. Recompute digest server-side. Never allow a supplied filesystem path or object key to determine storage location. Detect orphan uploads and collect them after a bounded grace period.

## 5. API conventions

All public endpoints live under `/api/v1`; machine schemas have their own `schema_version`. Generate OpenAPI and clients; no manually divergent frontend types. Pagination uses opaque cursors and fixed maximum page size. Filters and sorting are allowlisted; query length/time are bounded.

Mutations with side effects require `Idempotency-Key`. Scope keys to actor/project/route; persist request digest and original response for 24 hours by default. Same key plus different body returns `409`. An accepted background job returns `202`, `job_id`, and status URL. A cancellation returns cancellation-requested, not falsely completed.

Errors use `application/problem+json` with stable `code`, safe `detail`, `request_id`, and field errors. Statuses: 400 malformed, 401 unauthenticated, 403 permitted disclosure of denial, 404 absent or concealed unauthorized object, 409 state/version conflict, 413 size, 415 media, 422 schema, 429 quota/rate, 503 temporary capacity. Do not leak stack traces. Optimistic concurrency uses `ETag`/`If-Match`; stale edits return 412 or a documented 409, consistently tested.

Long-running status uses SSE with authenticated same-origin sessions and monotonically increasing cursor IDs. A reconnect fetches persisted state and resumes from a cursor. SSE is not the source of truth. CLI clients can poll with exponential backoff. Log URLs and request IDs must not contain raw content.

## 6. Job state machine, durability, and cost

`queued -> leased -> running -> succeeded | failed | timed_out | cancelled`; `cancel_requested` can be entered before terminal acknowledgement. A dead worker lease is requeued only if the operation is safe to retry; otherwise terminate as `failed_unknown_effect` and require reconciliation. Preserve every attempt. Use a fencing token to reject stale attempt completion. Terminal transitions are transactionally guarded.

1. API transaction creates job and outbox entry.
2. Scheduler leases eligible work with bounded concurrency and project fairness.
3. Reserve conservative per-job cost before dispatch.
4. Executor receives only permitted inputs and capabilities.
5. Heartbeat extends lease; wall timeout still applies.
6. Collector verifies output and attempt; dispatcher finalizes atomically.
7. Outbox emits completion for indexes/UI; idempotent consumers tolerate repeats.
8. Reconciler detects orphan jobs/artifacts and unknown effects.

V1 defaults: 2 active heavy jobs/project; 4/host, adjusted by resource class; 3 infrastructure retries with jitter only for proven idempotent operations; no automatic retry of external writes. Bound output, memory, pids, CPU, file descriptors, disk, wall time, token budget, and provider concurrency. Unknown provider pricing disables strict monetary promises; enforce tokens/time/concurrency and label estimated spend. In-flight calls can exceed a monetary estimate; publish the maximum reservation/race bound and stop dispatch before a limit is reached. Cancellation cannot retract already transmitted provider data.

## 7. Security and privacy baseline

### Trust classes

A: public/synthetic metadata. B: authenticated application state. C: sensitive content and credentials. D: attacker-controlled documents, skills, logs, generated output, and plugins. D never gains B/C authority merely because a model read it.

### Threat/control/test matrix

| Threat | Required control | Required evidence |
|---|---|---|
| Object-level authorization bypass | project checks on every read/write/list/export/stream/job/artifact | role and cross-project negative tests |
| Content leaks through telemetry | metadata-only default; allowlisted fields; redact before capture/upload; separate content rights | canary-secret tests through errors, exports, logs and SDK paths |
| XSS in traces/documents | text rendering; sanitized markdown; CSP; no active uploads served same-origin | malicious payload corpus and browser tests |
| SSRF/provider URL abuse | configured endpoints only; resolve/validate all addresses; block loopback/private/link-local/metadata; redirects off or revalidated; controlled proxy | IPv4/IPv6, DNS-rebinding and redirect tests |
| Code escape | no untrusted execution in API/dispatcher; isolated executor, no host mounts/socket, restricted egress | deployment preflight, adversarial lab, unsupported-mode rejection |
| Parser compromise | no-network disposable parser worker, read-only input, quotas, patched images | malicious/truncated/oversized document tests |
| Prompt injection | separate data/instructions, no authority from content, narrow tool capabilities, independently checked outcomes | injected document/skill/trace tasks and denied-action evidence |
| Supply-chain compromise | lockfiles, image digests, SBOM, signature/provenance, dependency review, private vulnerability process | reproducible release manifest and scan dispositions |
| Stolen browser/API session | OIDC validation, short sessions, secure HttpOnly SameSite cookies, CSRF/origin checks, scoped hashed API keys, rotation | expiry/revocation/CSRF/session fixation tests |
| Archive traversal/bombs | validate normalized paths, reject symlinks/hardlinks/devices, expansion/entry limits, streaming extraction | malicious archive fixture suite |
| Export injection | safe CSV cell escaping and explicit raw export option, output encoding | spreadsheet formula fixtures |
| Budget/availability abuse | quotas, rate limits, admission control, cancellation, circuit breakers | concurrency/load/cost simulation |

Use a mature OIDC library. Validate issuer, audience, nonce, state and PKCE where relevant. No password auth system in v1. Local bootstrap is an explicit local-only mode that refuses non-loopback exposure without authentication. Proxy headers are trusted only from configured proxies; Host/Origin allowlists are deployment-configured, not `*` in production. HTTPS outside developer mode. Content rights and run rights are separate: project `viewer` sees metadata; `analyst` sees authorized content and creates drafts; `operator` runs approved workloads; `maintainer` approves packages and manages project settings; organization `admin` manages identity/retention. Admin cannot silently obtain provider secrets; secrets are write-only references.

Secrets at rest use operator-managed encryption/key services or a protected development secret file outside repository. Never put keys in a manifest, dataset, trace, environment dump, or generic object serialization. A model broker issues narrow calls using credentials outside untrusted executors. Do not allow arbitrary provider URLs or token passthrough. Data sent to external providers requires project opt-in and a visible destination notice. No hidden analytics or automatic cloud fallback.

### Untrusted execution release boundary

Developer containers alone are not a sufficient claim of hostile-code isolation. For untrusted live evaluation, require a supported hardened backend (e.g., gVisor on a dedicated host or a reviewed microVM service), isolated from API/storage networks. The actual backend is selected by an ADR and validated on supported infrastructure. Until that gate passes, v1 may release **fixture playback and trusted local authoring only**, clearly labeled; untrusted execution must remain disabled. Inspect/other frameworks can execute orchestration/scorer Python on the host: run the complete untrusted harness and plugins within the isolation boundary, not only tool subprocesses.

### Retention/deletion

Default proposal: content 30 days; operational metadata 90 days; audit metadata 180 days; operator configurable. These are product defaults, not statutory requirements. Deletion graph includes original bytes, thumbnails, extracted text, embeddings if any, traces, fixtures, derived exports and links. Legal hold is not implemented; do not promise it. Revoke online access immediately; active-store purge within 24 hours as an acceptance target; encrypted backups expire within configured 30-day maximum or an explicitly documented operator policy. Restore must reapply tombstones before serving. Explain that downloaded exports cannot be remotely revoked.

## 8. UI/UX system and accessibility

Target WCAG 2.2 AA; automated checks are necessary but do not certify conformance. Document manual keyboard, screen-reader, zoom, focus, contrast, and pointer-target review.

Global navigation: product switcher if installed; project selector; primary product sections; Jobs; Settings; Help. Shared components: page header, filterable table, status chip with icon+text, empty/error state, evidence drawer, side-by-side diff, budget preflight, confirmation dialog, keyboard shortcuts, audit detail, and notification center.

Design tokens: semantic color roles, 4/8px spacing scale, readable 14–16px base, 1.4+ line height, tabular numbers, no color-only status, reduced-motion support. Desktop workspace at 1280px is primary; at 768px collapse drawers; at 390px preserve reading/approval/download via stacked panels, not a full graph editor. Large timelines/tables require virtualized and accessible list alternatives. Live progress announces milestones, not every token. Never steal focus when events arrive.

Every screen MUST specify loading, empty, populated, partial, permission-denied, stale/conflicted, offline/reconnecting, timeout, and error states. Provide recoverable actions and a safe support request ID. Destructive actions identify project, scope, and irreversibility. Raw data visibility is explicit; redaction and missing evidence must not look like empty strings. Read-only fixture demos are unmistakable and never look like live production data.

Research gate: 5 target users per product, task-based testing; no claim that five users establish product-market fit. Acceptance: at least 4/5 complete each primary task without moderator intervention in the tested prototype, with observed issues documented and resolved or scoped. Repeat if changes alter navigation substantially.

## 9. Quality, operations, and release

Testing pyramid: unit/property tests for transforms and state machines; contract tests for schemas/adapters; DB/object integration tests with real dependencies; workflow E2E; security negative tests; chaos/fault tests; load tests; model evals separated from deterministic PR gates. Do not gate every PR on paid stochastic provider calls. Nightly or release evaluations use budget caps, pinned config and recorded provenance.

Proposed private-server acceptance load: 4 vCPU/16 GiB control-plane host plus separately measured worker hardware; 20 concurrent authenticated users; 100k AFR events in a project; 100-document EVF corpus; SKB 1k result records. API list/detail p95 <500ms, excluding artifact transfer/model work, at the specified load; error rate <1%; 95% of committed progress changes visible within 3 seconds. Measure each product's worker throughput separately. No universal OCR/model latency promise.

Operational targets: monthly control-plane availability objective 99.5% for operator-managed service, not contractual SLA; RPO <=24h and RTO <=4h for the reference private deployment, demonstrated by restore. Local development has no HA promise. Alert on failed auth spikes, job lease churn, queue age, disk pressure, error rate, cost reservation anomalies and deletion backlog. Logs contain request IDs and safe metadata only; monitor the telemetry pipeline itself for loss.

Runbooks MUST cover: install/preflight; rotate/revoke secrets; worker crash/unknown effect; provider outage/rate limit; object-store outage; DB outage; migration failure; restore and tombstone replay; sensitive-data leak; sandbox incident; quota/cost runaway; deletion failures; rollback. Incident procedure: isolate executor/revoke capabilities, stop new dispatch, preserve safe evidence, identify affected scope, notify responsible operator, remediate/rotate, restore, postmortem. Response windows are staffing decisions, not invented support guarantees.

Releases: semantic versions; signed/tagged source and image digests; SBOM and license notices; supported environment matrix; migration notes; verified quickstart; restore evidence; baseline benchmark report. Expand-contract DB changes; old readers tolerate additive fields; never rollback code into an incompatible schema. Rehearse rollback with old/new worker overlap and job draining.

## 10. Global definition of done (GDoD)

Every backlog item requires these in addition to its local acceptance:

- [ ] Requirement ID, owner, linked ADR if needed, and dependencies recorded.
- [ ] Acceptance tests implemented; negative/failure behavior tested.
- [ ] Typed contracts validated; backward compatibility assessed.
- [ ] Authorization, secrets, privacy, retention, and threat effects reviewed.
- [ ] UX states, keyboard path and error recovery reviewed when user-facing.
- [ ] Logs/metrics are useful and content-safe; limits/cancellation respected.
- [ ] Documentation/configuration/fixtures updated; dependency licenses checked.
- [ ] Reviewer other than author approves; CI passes; evidence links attached.
- [ ] No unresolved critical/high exploitable issue without explicit security-owner disposition; release-blocking ones cannot be waived for marketing deadlines.
- [ ] Rollback/cleanup path documented for persistent or operational changes.

An unchecked gate means not done. A scope reduction is an explicit decision record, not silent deletion of a failing test.

## 11. Architecture decisions and future triggers

ADR-001 modular products, shared packages, independently deployable. ADR-002 Postgres metadata/job queue initially. ADR-003 immutable private artifacts and explicit content capture. ADR-004 no untrusted code in control plane. ADR-005 OIDC and project-scoped roles. ADR-006 external model broker and data-transfer consent. ADR-007 versioned experiment/evidence schemas. ADR-008 fixture-first public demo. ADR-009 deployment-selected hardened executor. ADR-010 no universal safety/accuracy certification.

Revisit Postgres job queue when measured queue latency/lock contention threatens targets after indexing and batching. Consider columnar trace storage only when realistic workloads fail query/storage goals; preserve AFR API/contracts. Add multi-tenant SaaS only after independent isolation assessment, per-tenant encryption/key plan, abuse controls, billing reconciliation, support/on-call staffing, regional data governance, and tenant restore tests. Add enterprise SSO provisioning, fine-grained ABAC, immutable audit infrastructure and retention/legal-hold features only with real operator requirements. Re-check upstream compatibility and licenses at every minor release.


## 12. Operator privacy and governance responsibilities

Before processing personal or confidential data, the deployment owner must inventory data categories, purposes, users, external recipients, retention and deployment region; establish an appropriate legal basis and controller/processor responsibilities where applicable; and assess the need for processor agreements, international-transfer safeguards and a DPIA under the applicable law. GDPR applicability and obligations require context-specific legal review; this pack is not legal advice or a compliance certification. Do not infer a lawful basis from a checkbox acknowledging provider transfer.

Provide a privacy notice, access/export/correction/deletion request process, security incident escalation, subprocessor/provider inventory and retention schedule. Limit collection to the task; use synthetic/public authorized material during development. Subject-access exports themselves require identity/authorization checks and secure delivery. Derivative data and backups must be covered by the request/deletion procedure. Record provider training/retention terms for the selected service configuration rather than assuming all APIs have the same terms.

Development key material belongs in a permission-restricted file outside the repository; private servers use an operator-managed secret/key service with backup and rotation policy. TLS protects transport, storage encryption protects at-rest media, and scoped authorization protects content access; none substitutes for the others. Rotation tests include old-key revocation, in-flight job behavior, encrypted backups and documented recovery without putting raw keys in an evidence bundle.


---

# Implementation phase runbook

All items below are **planned and unchecked**. Each task inherits the global definition of done. Task order is conservative: the previous task and prior phase gate must pass before proceeding; explicit independent branches may be parallelized by an approved planning change. Evidence paths are proposed repository artifacts, not existing implementation evidence.


## FND-F0 — Agree scope, boundaries and evidence plan

**Accountable role:** Product + tech lead. **Entry:** Project baseline accepted; assign owner and reviewers.


### [ ] FND-F0-01 — Approve deployment contract

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Choose developer/private-server/demo modes and document disabled capabilities.
3. **Verify:** All three products have a named persona, supported mode, non-goals and no hidden public-execution promise.
4. **Review/record:** run **scope review**, attach **`scope-and-mode-ADR.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] scope review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F0-02 — Map data and trust boundaries

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Draw dataflows including workers, model calls, artifacts and human approvals.
3. **Verify:** Each boundary has actor, data classification, enforcement location and responsible reviewer.
4. **Review/record:** run **threat-model review**, attach **`dataflow-threat-model.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] threat-model review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F0-03 — Select support matrix

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Resolve runtime, OS/CPU, storage, identity and hardened-executor candidate versions.
3. **Verify:** Every required component has a pinned tested candidate and unresolved assumptions are gated.
4. **Review/record:** run **dependency preflight design**, attach **`support-matrix.yaml`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] dependency preflight design passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F0-04 — Set measurable release targets

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Freeze SLO load profile, quality targets, release blockers and benchmark ownership.
3. **Verify:** Targets have denominators, hardware, method and explicit proposed status.
4. **Review/record:** run **test-plan review**, attach **`release-targets.yaml`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] test-plan review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F0-05 — Establish delivery governance

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Assign product, frontend, backend, security, UX, QA and statistical reviewers; create ADR/risk/change templates.
3. **Verify:** Every gate has an approver; single-person teams have an explicit external review plan.
4. **Review/record:** run **responsibility review**, attach **`ownership-and-risks.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] responsibility review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### FND-F0-GATE — phase exit / definition of done

**Exit condition:** Signed baseline and risk owners; no coding before the trust/deployment boundary is agreed.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## FND-F1 — Repository, contracts and reproducible development

**Accountable role:** Platform engineer. **Entry:** FND-F0-GATE approved.


### [ ] FND-F1-01 — Scaffold independent product profiles

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Create modular apps/packages, Compose profiles, fixture data, lint/typecheck and documented commands.
3. **Verify:** Each product boots alone from clean checkout without real provider keys.
4. **Review/record:** run **clean-install smoke**, attach **`repository-layout-and-quickstart.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] clean-install smoke passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F1-02 — Implement versioned schema package

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Define event, artifact, job, error and result envelopes; generate OpenAPI/TS clients.
3. **Verify:** Positive/negative samples validate; incompatible changes fail compatibility checks.
4. **Review/record:** run **contract roundtrip**, attach **`schemas-and-client-build`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] contract roundtrip passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F1-03 — Add CI and dependency controls

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Lock dependencies/images; add tests, secret scanning, SBOM, license checks and fork-safe CI.
3. **Verify:** Untrusted fork cannot access publish/provider secrets; intentionally leaked test secret is detected.
4. **Review/record:** run **CI security fixtures**, attach **`ci-policy-and-sbom`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] CI security fixtures passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F1-04 — Build migration infrastructure

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add module-owned tables, constraints, seed/migration helpers and expand-contract policy.
3. **Verify:** Fresh DB and prior-release upgrade both pass; partial migration failure is recoverable.
4. **Review/record:** run **database upgrade tests**, attach **`migration-harness`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] database upgrade tests passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F1-05 — Implement safe error/observability base

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add problem responses, request IDs, metadata-only logs, metrics and health/readiness endpoints.
3. **Verify:** Canary content/credentials absent from logs/errors/metrics; readiness reflects required dependencies.
4. **Review/record:** run **redaction and outage tests**, attach **`observability-fixtures`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] redaction and outage tests passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### FND-F1-GATE — phase exit / definition of done

**Exit condition:** Clean checkout builds, typed contracts roundtrip, and contract CI blocks incompatible changes.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## FND-F2 — Identity, artifacts and lifecycle

**Accountable role:** Backend + security. **Entry:** FND-F1-GATE approved.


### [ ] FND-F2-01 — Implement OIDC and local bootstrap

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Validate issuer/audience/state/nonce; secure sessions; reject unsafe unauthenticated exposure.
3. **Verify:** Expiry/revocation/CSRF/host-origin tests pass; local-only mode refuses remote deployment.
4. **Review/record:** run **FND-T01**, attach **`auth-threat-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F2-02 — Enforce roles/project scope

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement central authorization and separate metadata/content/run/admin capabilities.
3. **Verify:** All resource/list/export/SSE paths deny cross-project and wrong-role access.
4. **Review/record:** run **FND-T02**, attach **`permission-matrix.csv`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F2-03 — Implement artifact upload/finalize

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Generate keys, enforce quotas, digest/media checks, authorization and bounded downloads.
3. **Verify:** Duplicate finalize is idempotent; hash mismatch/quarantined file never becomes readable.
4. **Review/record:** run **FND-T03**, attach **`artifact-contract-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F2-04 — Implement secret/provider profile handling

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Store write-only secret references, configured provider destinations and explicit transfer policy.
3. **Verify:** Secrets never returned by APIs; arbitrary endpoint/redirect/private-IP access denied.
4. **Review/record:** run **FND-T04**, attach **`provider-policy-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F2-05 — Implement lineage/retention/deletion

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Track derivatives, tombstones, revocation, purge, orphan GC and restore replay.
3. **Verify:** Delete/retry/restore exercise reaches all seeded derivatives and blocks reads immediately.
4. **Review/record:** run **FND-T05**, attach **`deletion-drill.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### FND-F2-GATE — phase exit / definition of done

**Exit condition:** No object-level bypass; artifact integrity and deletion behavior are verified.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## FND-F3 — Jobs, budgets and executor isolation

**Accountable role:** Platform + security. **Entry:** FND-F2-GATE approved.


### [ ] FND-F3-01 — Implement job/outbox leasing

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Create transactional outbox, leases, attempts, fencing and bounded idempotency.
3. **Verify:** Crash before/after commit, lost ack and stale completion cannot duplicate logical results.
4. **Review/record:** run **FND-T06**, attach **`job-state-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T06 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F3-02 — Implement limits and cancellation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Enforce fair concurrency, memory/time/output quotas, capability revocation and retry policy.
3. **Verify:** Runaway/timeout/cancel/unknown-effect states are visible and reconciled; no blind write retries.
4. **Review/record:** run **FND-T07**, attach **`limit-and-cancel-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F3-03 — Implement budget broker

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Reserve tokens/calls/estimated spend atomically; record actual/unknown cost and provider rate failures.
3. **Verify:** Concurrent jobs cannot bypass configured reservation; in-flight overshoot bound is documented.
4. **Review/record:** run **FND-T08**, attach **`budget-race-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F3-04 — Validate hardened executor

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement dedicated-host gVisor/microVM adapter, no DB/host/socket access and scoped artifact collector.
3. **Verify:** Entire untrusted harness/plugins isolated; egress/private network/host-mount probes denied.
4. **Review/record:** run **FND-T09**, attach **`executor-security-evidence.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F3-05 — Implement recovery/reconciliation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Detect orphan work/artifacts, classify retry-safe jobs, reconcile unknown effects and drain workers.
3. **Verify:** Worker death and service outage recover without lost accepted work or fabricated terminal success.
4. **Review/record:** run **FND-T10**, attach **`recovery-drill.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### FND-F3-GATE — phase exit / definition of done

**Exit condition:** Fault-tolerant scheduling and the actual hardened-executor boundary pass; unsupported live modes remain disabled.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## FND-F4 — Shared UX and verification framework

**Accountable role:** Frontend + QA. **Entry:** FND-F3-GATE approved.


### [ ] FND-F4-01 — Build design system

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement tokens, navigation, forms, tables, status/errors, safe content view and responsive layout.
3. **Verify:** All declared states have components; keyboard/contrast/focus checks pass.
4. **Review/record:** run **FND-T11**, attach **`storybook-and-accessibility-log`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T11 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F4-02 — Implement job/status UI

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add authenticated SSE reconnection, persisted status, budget preflight and cancel confirmation.
3. **Verify:** Disconnect/reconnect/expired session/stale cursor never lose authoritative job state.
4. **Review/record:** run **FND-T12**, attach **`status-flow-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T12 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F4-03 — Implement verification primitives

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Create trusted built-in verifiers, immutable result schema and evidence references.
3. **Verify:** Error/unknown/unscored differ from task failure/pass; malicious inputs cannot execute host code.
4. **Review/record:** run **FND-T13**, attach **`verifier-contract-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T13 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F4-04 — Build security/fault fixture harness

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add cross-project, XSS, archive, SSRF, injection, crash and canary-secret fixtures.
3. **Verify:** Each shared threat has an executable negative test or explicit manual deployment gate.
4. **Review/record:** run **FND-T14**, attach **`security-fixture-catalog`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T14 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F4-05 — Run shared usability/accessibility pilot

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test real primary workflows at keyboard/zoom/screen-reader plus five representative users.
3. **Verify:** Observed blockers are fixed; task completion evidence recorded; no unearned conformance claim.
4. **Review/record:** run **FND-T15**, attach **`ux-accessibility-evidence.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T15 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### FND-F4-GATE — phase exit / definition of done

**Exit condition:** Accessible primary flows and reliable test infrastructure support all products.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## FND-F5 — Deployment and release foundation

**Accountable role:** Operations + QA. **Entry:** FND-F4-GATE approved.


### [ ] FND-F5-01 — Harden deployment templates

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Configure TLS, private networks, no default credentials, resource limits and preflight checks.
3. **Verify:** Only edge port exposed; unsupported runtime and insecure config fail startup/preflight.
4. **Review/record:** run **FND-T16**, attach **`deployment-preflight-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T16 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F5-02 — Rehearse backups and recovery

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Back up DB/artifacts/secrets references; restore clean environment and apply tombstones before traffic.
3. **Verify:** Measured reference RPO/RTO meet targets; encrypted backup retention documented.
4. **Review/record:** run **FND-T17**, attach **`restore-evidence.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T17 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F5-03 — Load and chaos test foundation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Exercise declared user/event/job load and dependency outages.
3. **Verify:** Latency/error targets measured; bottlenecks and capacity envelope published.
4. **Review/record:** run **FND-T18**, attach **`load-chaos-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T18 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F5-04 — Write/rehearse incident and rollback runbooks

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Walk through leak, compromised worker, runaway cost, migration failure and old/new workers.
3. **Verify:** Named operator completes drills without undocumented permissions or unsafe data restoration.
4. **Review/record:** run **FND-T19**, attach **`operations-runbooks`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T19 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] FND-F5-05 — Approve release checklist

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Collect SBOM, licenses, signed digests, migrations, limitations and reviewer signoff.
3. **Verify:** No unresolved release blocker; every exception has owner, expiry and scope.
4. **Review/record:** run **FND-T20**, attach **`foundation-release-evidence`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] FND-T20 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### FND-F5-GATE — phase exit / definition of done

**Exit condition:** Reference install, backup/restore, rollback and incident handling are rehearsed.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.
