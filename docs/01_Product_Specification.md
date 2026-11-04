# Agent Flight Recorder — product and technical design

**ID:** AFR · **Version:** 0.1 proposed · **Date:** 2026-11-03. Inherits every MUST and GDoD in the shared foundation. Task-level execution plan is appended below and mirrored in the backlog.

## 1. Charter and competitive decision

**Problem:** a developer can see that an agent failed, but cannot reliably capture the relevant evidence, reproduce the controllable portion, and prevent regression after a change.

**Primary persona:** Python/TypeScript application engineer operating a tool-using agent. Secondary: maintainer reviewing a reported bug; evaluator comparing revisions. Key job: “Convert this observed failure into a reviewable test without leaking production data or accidentally repeating a real-world action.”

Phoenix already documents traces, datasets, experiments and replaying traced model calls; Langfuse provides tracing/evaluation infrastructure; AgentOps supplies instrumentation. Therefore **tracing, a timeline, and a replay button alone are not differentiation**. V1's contribution is a strict failure-to-fixture workflow, replay eligibility/completeness assessment, observable side-effect boundaries, and CI-verifiable expected outcomes. Reuse standard instrumentation/export where possible. Research details and pinned source snapshots are in the comparison document.

### Outcomes and scope

Required: typed event capture; opt-in redacted content; inspectable run timeline; import; replay eligibility; recorded-output and controlled-live modes; regression fixture authoring; deterministic local verifier runner; baseline/candidate comparison; safe export; one provider integration plus one framework integration; Python SDK, TypeScript capture client and CLI.

Not v1: universal agent debugger, OS-level record/replay, arbitrary process snapshotting, capturing hidden chain of thought, replaying production writes, full model hosting, public sharing of raw traces, or automatic root-cause certainty. Only provider-exposed outputs/metadata are captured; internal reasoning is not requested or reconstructed.

Success measures: time from known fixture failure to exported regression test <=10 minutes for 4/5 usability participants; event coverage and replay fidelity on the declared controlled suite; independently verified task outcomes; clear missing evidence. Adoption is tracked separately from engineering quality.

## 2. Requirements and traceability

| Requirement | Release test | Phase |
|---|---|---|
| AFR-R01 metadata-first capture, safe redaction | AFR-T01 canary secrets absent from all outputs | A1–A2 |
| AFR-R02 idempotent, out-of-order ingestion | AFR-T02 replay duplicate batches + reorder | A2 |
| AFR-R03 explicit completeness and causal limitations | AFR-T03 dropped/missing terminal events | A2–A3 |
| AFR-R04 no side effects in playback | AFR-T04 network/filesystem sentinel stays untouched | A4 |
| AFR-R05 live replay authorization and safe targets | AFR-T05 denied external writes and changed targets | A4 |
| AFR-R06 trace-to-test with independently validated result | AFR-T06 defect/fix known outcome | A5 |
| AFR-R07 versioned portable fixtures | AFR-T07 import/export/compatibility/tamper cases | A5 |
| AFR-R08 useful accessible timeline/diff | AFR-T08 keyboard/screen-reader + 10k-event UI | A3 |
| AFR-R09 isolated safe evaluator | AFR-T09 malicious verifier rejected/contained | A4–A6 |
| AFR-R10 deploy/restore/delete/rollback | AFR-T10 reference deployment drill | A7 |

Targets are goals before evaluation, not achieved results. Passing AFR-R09 requires the shared hardened execution gate for untrusted extensions. Trusted local verifiers must still be explicitly identified as executable code.

## 3. User journeys and UI specification

### J1 — First useful trace

1. Project owner creates project and selects capture profile: metadata only (default), allowlisted redacted content, or approved sensitive content.
2. UI generates a scoped write-only ingest key and displays it once. SDK snippets never put keys in source files.
3. Developer runs a bundled synthetic agent. A connection diagnostic checks key scope, schema and endpoint without sending a real prompt.
4. Runs list shows state, outcome, duration, event completeness, known/estimated cost, environment revision and capture profile.
5. Developer selects a failed run. Missing content is labeled “not captured,” not treated as a blank response.

Acceptance: fixture quickstart works without a model key; live example asks for explicit provider setup. Empty states contain runnable instructions and a safe fixture button.

### J2 — Investigate failure

Desktop layout:

```text
Project / Runs / run-123          FAILED · INCOMPLETE? · capture policy
[task] [code revision] [duration] [usage known/estimated] [export]
------------------------------------------------------------------
Filters/events tree  | causal timeline       | selected event drawer
agent / model / tool | errors + checkpoints  | metadata / content / IO
------------------------------------------------------------------
Outcome evidence  | warnings / missing data | create regression case
```

The timeline allows model/tool/error/approval filters, text search within authorized content only, relative time, causal links, and a list alternative. The event drawer shows source timestamp versus received timestamp, provider error code, explicit redaction, raw authorized JSON, and linked artifacts. Tool input and output are inert text. File diffs escape paths and content. Cost distinguishes provider-reported usage, estimated cost, and unknown usage.

Completeness panel identifies missing sequence ranges per producer, orphan spans, unfinished operations, redacted fields, truncated outputs, unsupported adapter fields, and model/provider version ambiguity. Do not display a fictional global completion percentage. Warnings must survive export.

### J3 — Turn failure into a regression test

Wizard: choose bounded task slice → inspect replay eligibility → choose mode → select safe fixture data → define state/output verifier → set limits → preview/redact export → save a version. Defaults: no network, no live tools, synthetic inputs, trusted built-in verifiers. Live target choice is not a preselected checkbox hidden at the end.

The preview identifies inherited missing evidence and side-effect assumptions. Tests can assert exact structured values, allowed/forbidden tool attempts, final synthetic application state, and latency/token bounds. Avoid brittle whole-transcript equality as the primary success definition.

### J4 — Compare revisions

Select fixture version, baseline and candidate run; show verified task success first, safety violations next, then cost/latency. Align by logical operation/call ordinal where known, not arbitrary event position; ambiguous alignment is flagged. Show “not comparable” when task/environment differs. A comparison is not proof of causality when model/environment revisions differ.

### UI states

Runs: loading skeleton, no runs, filter-empty, ingest lag, deleted, permission-denied. Run detail: streaming/reconnecting, incomplete, dropped-content, late event, provider failure, oversized/truncated field. Replay: ineligible, missing fixture, cost estimate unavailable, executor unavailable, awaiting approval, cancel requested, unknown external effect. Comparison: partial pair, incompatible schema, missing metric. Each state has next action, no leaked content, and a stable request ID.

Keyboard: predictable tab order; event list arrows only when focused; Enter opens detail; Escape returns focus; shortcuts opt-in and disabled during text entry. Live stream does not move selection. Responsive layout stacks drawer below timeline. Screen reader exposes chronological/causal text labels.

## 4. Architecture and event contracts

Capture SDK -> bounded in-memory buffer -> batch exporter -> authenticated ingestion -> durable Postgres event rows + artifact references -> run materializer -> query API/SSE. Replay planner reads versioned fixtures and schedules an isolated executor through the shared dispatcher. V1 does not require an upstream tracing backend; optional export interoperates with one.

### Event envelope

Required fields: `schema_version`, `event_id`, `run_id`, `producer_id`, `producer_seq`, `event_type`, `observed_at`, `received_at` (server set), `capture_policy_id`, `payload`. Optional `trace_id`, `span_id`, `parent_span_id`, `links`, `monotonic_ns`, `artifact_refs`, `adapter_version`, `source_revision`.

Types: `run.started`, `run.finished`, `agent.started`, `agent.finished`, `model.requested`, `model.responded`, `tool.requested`, `tool.responded`, `tool.failed`, `approval.decided`, `checkpoint.created`, `capture.dropped`, `artifact.linked`. Validate matching start/finish where adapter provides identifiers. Extensions are namespaced and bounded. Parentage and links express causal relationships; producer sequence is local, not a globally authoritative order.

Metadata includes requested/observed model identifier, provider, token breakdown with nullable values, tool logical name, tool contract hash, operation IDs, duration and outcome. No generic serialization of agent/client objects. Streaming token events are optional and sampled/coalesced; run summaries remain accurate about dropped detail.

### Ingestion semantics

`POST /api/v1/afr/events:batch`: <=500 events, <=1 MiB JSON excluding separately uploaded artifacts by default; project key derived server-side. Validate entire envelope and return per-event acknowledgement (`accepted`, `duplicate`, `rejected`) plus safe error code; atomically persist valid rows with a batch receipt. Retry with stable IDs. `UNIQUE(project_id,event_id)` and `(run_id,producer_id,producer_seq)` conflict policy detects differing payloads rather than silently overwriting. Return 409 for contradictory duplicate sequence data. Raw invalid content is not logged.

SDK buffers at most a configured byte count; redacts before buffering; exports asynchronously; exposes dropped count; bounded exponential backoff. Default capture does not fail the host application if telemetry is unavailable. An explicit audit-required mode can fail closed, but must be chosen and documented. Disk spool disabled by default; enabling it requires encryption/retention configuration. SDK shutdown flush has a timeout. Worker threads/async context propagation and fork behavior need tests.

### Storage

`afr_runs` (task/environment/capture state), `afr_events` (envelope + normalized searchable metadata), `afr_operations` (materialized span/operation state), `afr_checkpoints`, `afr_fixture_versions`, `afr_replay_plans`, `afr_replay_runs`, `afr_verifier_results`, `afr_comparisons`.

Indexes: project+started_at, run+producer+sequence, run+operation, project+outcome, job status. Paginate events and stream artifacts rather than returning an entire giant run. Partitioning/columnar storage is a future measured decision.

Run lifecycle: `recording -> completed | failed | abandoned`; independent completeness flags and verification result. A succeeded agent run can fail verification. Late events update a materialized revision and keep original received time; regression fixtures always freeze a snapshot. Abandoned detection uses inactivity and missing terminal marker, not an unsupported conclusion that the agent crashed.

## 5. Replay: exact guarantees and safety

| Mode | What executes | Network | Claim |
|---|---|---|---|
| Visual playback | viewer only | no tool/model calls | faithful presentation of captured data, with omissions disclosed |
| Recorded-output simulation | trusted orchestrator against recorded model/tool outputs | none by default | validates controllable orchestration/fixture matching, not fresh model behavior |
| Controlled live-model test | fresh model + synthetic tools/state | broker-approved model endpoint only | new evaluated run, not deterministic replay |
| Controlled live-tool test | approved synthetic local services | isolated allowlisted fixture network | verifies task in sandbox, never production replay |

Production write replay is not supported in v1. Generic “resume anywhere” is not supported. Checkpoints are application-defined serialized fixture state, not process memory snapshots. Never deserialize pickle or arbitrary Python objects.

Match recorded tool calls by tool contract hash, normalized schema-validated arguments and call ordinal/causal context. Repeated identical calls must not consume the wrong recorded output. Canonicalization is domain-aware; preserve order where meaningful; scrub secrets without accidentally equating distinct semantic inputs. An unmatched call fails closed with mismatch detail. No silent fallback to a live tool.

Environment manifest: OS/architecture, executor image digest, code commit, lockfile hashes, runtime, adapter versions, model IDs, provider settings, tool schemas, dataset/fixture hashes, random seeds when supported, time controls, locale, timezone, evaluator revision, capture policy and known missing content. Seeds and temperature settings do not guarantee identical hosted-model output.

Approval for controlled live activity is bound to project, fixture hash, target capability, limits, policy revision, actor, expiry and nonce. Revalidate immediately before dispatch; changed plan requires new approval. Store approval outside untrusted trace content.

## 6. Regression fixtures and CI

`afr-case/v1` bundle: manifest, redacted inputs, referenced artifacts, environment spec, expected checks, replay policy, provenance and checksums. External URLs disabled by default. Import validates archive paths, media, sizes, schema, checksums and approved image references. A checksum verifies consistency, not publisher identity. Future signed cases require a trust policy, not merely a signature field.

Built-in verifiers: JSON Schema, exact structured field, tool-attempt policy, synthetic state diff, safe regex with timeout, token/time bounds. Custom verifiers are executable extensions and require isolation. Expected hidden results never mount into the candidate workspace. Verifier errors are `invalid/error`, not agent failures or passes. Distinguish task failure, infrastructure error, policy block, cancellation, missing evidence and unscored.

CLI proposed UX: `afr capture-demo`, `afr inspect <bundle>`, `afr case validate`, `afr case run`, `afr compare`, `afr export`. Commands are design targets, not existing tools. Exit 0 all required checks pass; 1 verified regression; 2 invalid/config/infrastructure; 3 policy/permission block. Export JSON/JUnit with stable IDs and safe attachments. CI uses synthetic fixtures without secrets on fork PRs. Live-provider nightly runs require protected secrets and approved configs; never execute arbitrary fork code with credentials.

## 7. Quality/operational acceptance

Controlled suite: 50 tasks across mock refund/helpdesk, structured tool use, and file editing; at least 10 seeded failures, 10 malformed/lossy traces, and adversarial content. Freeze task/environment before evaluation. Event completeness is measured against an instrumented test oracle, not the trace itself. Goal: >=99% required expected event capture in loss-free fixture execution; 100% intentional losses/truncations signaled. No accepted critical safety test failure.

Load: reference host shared targets plus 100 events/sec sustained for 15 minutes, 5x burst for 30 seconds, 100k stored events/project, one 10k-event run. Confirm bounded SDK memory and measured p95 capture enqueue overhead <2ms without network, with environment documented. Recovery: kill ingest after commit before acknowledgement; re-send; no extra logical events. Kill replay worker; no duplicate external actions. UI renders first useful event page within 2s on declared test browser/hardware; not a claim for every client.

Operations: monitor accepted/rejected/duplicate/dropped events, ingest lag, open/abandoned runs, replay eligibility failures, verifier error rate, denied capabilities and artifact growth. Content-safe support bundle includes versions, counts and IDs, no prompts. Delete trace-derived fixtures only through declared lineage policy; user notified when deletion makes a case unusable.

## 8. Evolution and decision gates

V0.1 fixture playback/capture; V0.2 controlled regression runner; V1 private collaborative release after security/restore gates. Future: additional harness adapters, distributed causal analysis, upstream export/import, counterfactual branch exploration and team review. Only add distributed replay when external nondeterminism and artifact completeness can be modeled honestly. Public sharing requires a separate scrub/review pipeline, revocable access and leak testing. Hosted SaaS requires foundation multi-tenant gates.

**Go/no-go after discovery:** 3 of 5 interviewed target developers identify a recurring failure-to-test need that their current tooling does not solve sufficiently; otherwise reposition as a Phoenix/Langfuse integration rather than build a new observability product. This is an exploratory threshold, not validated market size.

## 9. Product release definition of done

- [ ] AFR-R01–R10 have passing evidence or explicit release scope exclusion.
- [ ] No playback path can silently call a live model/tool.
- [ ] All fixture comparisons disclose missing capture and environment differences.
- [ ] Private data is absent from default capture, logs, fixture demo and public export.
- [ ] One provider and one framework adapter pass documented compatibility tests.
- [ ] Full primary journey passes manual accessibility and task usability checks.
- [ ] Regression suite, load/fault report, deletion/restore drill and upgrade/rollback runbook published.
- [ ] Unsupported execution modes are disabled, not merely cautioned in documentation.



---

# Implementation phase runbook

All items below are **planned and unchecked**. Each task inherits the global definition of done. Task order is conservative: the previous task and prior phase gate must pass before proceeding; explicit independent branches may be parallelized by an approved planning change. Evidence paths are proposed repository artifacts, not existing implementation evidence.


## AFR-A0 — Validate differentiation and prototype failure-to-test

**Accountable role:** Product + tech lead. **Entry:** Project baseline accepted; assign owner and reviewers.

**Shared prerequisite:** FND-F0 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A0-01 — Interview target developers

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Collect five concrete failure stories and existing debugger workflows; compare Phoenix/Langfuse.
3. **Verify:** At least three interviewees identify a recurring unmet trace-to-test need or project is repositioned.
4. **Review/record:** run **AFR-R06 / interview evidence**, attach **`afr-discovery.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-R06 / interview evidence passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A0-02 — Inspect comparable workflows

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Build a minimal capture/replay/fixture comparison against pinned upstream versions.
3. **Verify:** Feature claims distinguish documented, tested and unknown; reuse boundaries recorded.
4. **Review/record:** run **comparison spike**, attach **`afr-comparison-ADR.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] comparison spike passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A0-03 — Define tasks and replay guarantees

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Select mock domain, 50-task suite plan, seeded failures and four replay mode definitions.
3. **Verify:** No production-write or deterministic-hosted-model claim remains in acceptance criteria.
4. **Review/record:** run **AFR-T04/05 design**, attach **`afr-suite-and-replay-policy`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T04/05 design passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A0-04 — Prototype primary journey

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Clickable list/timeline/eligibility/case wizard/compare flow with missing evidence states.
3. **Verify:** Five users attempt failure-to-test flow; blockers and <=10-minute target baseline recorded.
4. **Review/record:** run **AFR-T08 prototype**, attach **`afr-prototype-review`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T08 prototype passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A0-05 — Freeze requirements and threat model

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Map R01–R10, event content policy, adapter scope, state transitions and owners.
3. **Verify:** All requirements have implementation phase/test; initial source/model data rights checked.
4. **Review/record:** run **requirements review**, attach **`afr-baseline-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] requirements review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A0-GATE — phase exit / definition of done

**Exit condition:** User need and replay terminology validated; build/integrate decision signed.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A1 — Capture contracts and safe SDK skeleton

**Accountable role:** SDK engineer. **Entry:** AFR-A0-GATE approved.

**Shared prerequisite:** FND-F2 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A1-01 — Define event/run contracts

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement envelope, operation links, timestamps, completeness flags and bounded extensions.
3. **Verify:** Invalid IDs/types/sequence conflicts rejected; additive schema roundtrip succeeds.
4. **Review/record:** run **AFR-T02/03**, attach **`afr-event-contracts`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T02/03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A1-02 — Implement capture policy/redaction

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Allowlist metadata; opt-in content; recursive bounded redaction; forbid generic object serialization.
3. **Verify:** Canary credentials absent from buffer, errors, metadata, disk and export paths.
4. **Review/record:** run **AFR-T01**, attach **`afr-capture-policy-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A1-03 — Build bounded Python/TS clients

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement async batching, queue bytes limit, drop signals, context propagation and flush timeout.
3. **Verify:** Offline exporter cannot grow memory unbounded or block application indefinitely.
4. **Review/record:** run **AFR-T01/02**, attach **`afr-sdk-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01/02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A1-04 — Implement synthetic capture demo

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Provide keyless mock agent with model/tool/error/approval/checkpoint events.
3. **Verify:** Fresh user produces and inspects fixture run with no network/provider dependency.
4. **Review/record:** run **AFR-T06 smoke**, attach **`afr-demo-fixture`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T06 smoke passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A1-05 — Document adapter contract

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Specify one provider and one framework adapter including streaming/cancellation/missing fields.
3. **Verify:** Supported fields and omissions explicit; compatibility fixtures committed before integration.
4. **Review/record:** run **adapter contract review**, attach **`afr-adapter-spec`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] adapter contract review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A1-GATE — phase exit / definition of done

**Exit condition:** Metadata-only SDK and versioned fixtures work without provider credentials.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A2 — Durable ingestion and materialized runs

**Accountable role:** Backend engineer. **Entry:** AFR-A1-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A2-01 — Implement ingest authentication and receipts

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Create batch endpoint, scoped keys, size/rate limits, per-event responses and transactional persistence.
3. **Verify:** Retries preserve event IDs; unauthorized project/key cannot ingest or read content.
4. **Review/record:** run **AFR-T01/02**, attach **`afr-ingestion-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01/02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A2-02 — Implement event conflict/deduplication

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Enforce event/producer-sequence constraints and contradictory-payload handling.
3. **Verify:** Duplicate identical batches do not duplicate; changed duplicate rejected without overwrite.
4. **Review/record:** run **AFR-T02**, attach **`afr-dedup-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A2-03 — Build materializer/completeness tracking

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Derive operations/run state, sequence gaps, orphan spans and explicit truncation warnings.
3. **Verify:** Oracle-seeded omissions flagged; succeeded agent can retain failed/unknown verification.
4. **Review/record:** run **AFR-T03**, attach **`afr-completeness-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A2-04 — Add query/pagination/SSE

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement indexed lists, event pages, safe filters, content rights and reconnect cursors.
3. **Verify:** 100k-event project lists meet target; stream auth/reconnect and filter isolation pass.
4. **Review/record:** run **AFR-T08**, attach **`afr-query-load-test`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A2-05 — Integrate provider/framework adapters

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test pinned versions, stream responses, async tools, errors and optional capture.
3. **Verify:** Both adapters disclose unsupported fields and pass compatibility/canary cases.
4. **Review/record:** run **AFR-T01/02/03**, attach **`afr-integration-matrix`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01/02/03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A2-GATE — phase exit / definition of done

**Exit condition:** Duplicate/reordered events, partial capture and late arrivals are accurately represented.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A3 — Investigation UI and evidence handling

**Accountable role:** Frontend + UX. **Entry:** AFR-A2-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A3-01 — Build runs inventory

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement states, completeness, verification, cost uncertainty, filters and safe empty state.
3. **Verify:** Recording/abandoned/partial/filter-empty/deleted/denied states are distinct and tested.
4. **Review/record:** run **AFR-T08**, attach **`afr-runs-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A3-02 — Build timeline/list and event inspector

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement virtualization, causal links, drawer, artifact refs and inert raw-data views.
3. **Verify:** 10k-event run remains navigable; keyboard/list alternative and malicious text tests pass.
4. **Review/record:** run **AFR-T08/01**, attach **`afr-timeline-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T08/01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A3-03 — Implement completeness panel

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Expose gaps, redaction, missing fields, late events and adapter limitations.
3. **Verify:** No missing value appears as valid empty response or invented completion percentage.
4. **Review/record:** run **AFR-T03**, attach **`afr-completeness-ui`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A3-04 — Implement safe evidence export preview

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Show included/redacted content, artifacts, capture policy and version manifest before export.
3. **Verify:** Default public-safe fixture export excludes secrets; source permissions checked server-side.
4. **Review/record:** run **AFR-T01/07**, attach **`afr-export-preview-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A3-05 — Run investigation usability test

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Ask five developers to diagnose seeded complete and incomplete traces using keyboard/text alternatives.
3. **Verify:** Four of five identify issue and capture limits without moderator help; blockers fixed.
4. **Review/record:** run **AFR-T08**, attach **`afr-investigation-study`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A3-GATE — phase exit / definition of done

**Exit condition:** Users can find the failure and understand incomplete capture accessibly.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A4 — Replay planner and isolated execution

**Accountable role:** Runtime + security. **Entry:** AFR-A3-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A4-01 — Build replay eligibility planner

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Check required artifacts/content, environment/tool hashes, missing outputs and checkpoint support.
3. **Verify:** Every mode has explicit eligible/ineligible reason; no arbitrary process-resume promise.
4. **Review/record:** run **AFR-T03/04**, attach **`afr-replay-eligibility-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T03/04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A4-02 — Implement visual playback and output simulation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Render recorded data; match outputs by contract/arguments/ordinal/causal context.
3. **Verify:** Repeated identical calls consume correct fixture output; unmatched call fails closed.
4. **Review/record:** run **AFR-T04**, attach **`afr-playback-sentinel-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A4-03 — Implement controlled live-model runner

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Broker model only, synthetic tools, scoped inputs and frozen environment manifest.
3. **Verify:** Network/production writes denied; model revision nondeterminism shown in results.
4. **Review/record:** run **AFR-T05/09**, attach **`afr-live-model-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T05/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A4-04 — Implement controlled live-tool profile

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Use synthetic app network, approved capabilities, bounded approval and stale-plan checks.
3. **Verify:** Changed fixture/target invalidates approval; sandbox gate required; cancel revokes new calls.
4. **Review/record:** run **AFR-T05/09**, attach **`afr-live-tool-security-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T05/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A4-05 — Test replay failure recovery

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Kill executor, expire approval, remove artifact, inject output mismatch and deny provider.
3. **Verify:** Unknown effects and missing evidence never become success; no silent live fallback.
4. **Review/record:** run **AFR-T04/05/09**, attach **`afr-replay-fault-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T04/05/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A4-GATE — phase exit / definition of done

**Exit condition:** Playback has zero live side effects; controlled modes cannot silently escape fixtures.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A5 — Regression cases and comparison

**Accountable role:** Backend + frontend. **Entry:** AFR-A4-GATE approved.

**Shared prerequisite:** FND-F4 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A5-01 — Implement immutable case bundles

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Define manifest, safe archive import, checksum verification, lineage and schema migration.
3. **Verify:** Tampered/traversal/oversized/incompatible cases rejected; golden roundtrip preserved.
4. **Review/record:** run **AFR-T07**, attach **`afr-case-contract-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A5-02 — Implement case wizard and verifiers

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Select task slice, mode, evidence, trusted verifier and budget; preview before freeze.
3. **Verify:** Known defect fails and known fix passes independent outcome check; verifier errors separate.
4. **Review/record:** run **AFR-T06/09**, attach **`afr-case-wizard-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T06/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A5-03 — Implement baseline/candidate comparison

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Align logical operations, show task/safety outcomes before cost and mark incomparable runs.
3. **Verify:** Environment/task mismatch and ambiguous alignment cannot display unsupported improvement claims.
4. **Review/record:** run **AFR-T06/08**, attach **`afr-compare-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T06/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A5-04 — Implement CLI/CI export

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add validate/run/compare/report commands, JUnit/JSON outputs and documented exit codes.
3. **Verify:** No secrets on fork CI; config/error/policy/regression exits differ; fixture mode keyless.
4. **Review/record:** run **AFR-T06/07/09**, attach **`afr-ci-example`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T06/07/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A5-05 — Validate complete primary journey

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Observe five users from failed trace to exported regression; test download/import in clean deployment.
3. **Verify:** Four of five finish bounded task within ten minutes; evidence and limitations retained.
4. **Review/record:** run **AFR-T06/08**, attach **`afr-primary-journey-study`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T06/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A5-GATE — phase exit / definition of done

**Exit condition:** Failure-to-test flow yields portable, verifiable, versioned cases.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A6 — Security, fidelity and performance qualification

**Accountable role:** QA + security. **Entry:** AFR-A5-GATE approved.

**Shared prerequisite:** FND-F4 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A6-01 — Run capture completeness benchmark

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Compare captured events against independent oracle over 50 tasks and seeded omissions.
3. **Verify:** Required loss-free event coverage >=99%; 100% seeded missing/truncated cases signaled.
4. **Review/record:** run **AFR-T02/03**, attach **`afr-benchmark-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T02/03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A6-02 — Attack ingestion/viewer/bundles

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Run canary, XSS, cross-project, path/archive and malicious verifier corpus.
3. **Verify:** No accepted critical security failure; unsupported untrusted execution disabled.
4. **Review/record:** run **AFR-T01/07/09**, attach **`afr-security-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01/07/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A6-03 — Load test SDK and service

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Measure enqueue overhead, bounded buffers, sustained/burst load and large-run navigation.
3. **Verify:** Declared hardware results meet targets or supported capacity reduced and retested.
4. **Review/record:** run **AFR-T02/08**, attach **`afr-load-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T02/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A6-04 — Fault test all boundaries

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Lose acks, reorder/drop events, kill workers and disconnect DB/artifact/provider dependencies.
3. **Verify:** No duplicate logical side effects; terminal states and reconciliation remain truthful.
4. **Review/record:** run **AFR-T02/04/05**, attach **`afr-chaos-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T02/04/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A6-05 — Review compatibility/privacy/accessibility

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Verify adapter pins, content-default policy, manual assistive-tech flow and retention derivatives.
3. **Verify:** Compatibility matrix and manual review have no release blockers; privacy labels accurate.
4. **Review/record:** run **AFR-T01/08/10**, attach **`afr-qualification-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T01/08/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A6-GATE — phase exit / definition of done

**Exit condition:** Declared suite and fault matrix pass with honest capture/replay limits.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## AFR-A7 — Release, operate and evolve

**Accountable role:** Operations + maintainer. **Entry:** AFR-A6-GATE approved.

**Shared prerequisite:** FND-F5 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] AFR-A7-01 — Package independent deployment

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Build signed images/SDKs/CLI, sample env, scoped keys, preflight and read-only fixture demo.
3. **Verify:** Clean install needs no other product; insecure/demo modes cannot expose live execution.
4. **Review/record:** run **AFR-T10**, attach **`afr-release-candidate`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A7-02 — Rehearse lifecycle operations

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Upgrade prior schema, drain workers, rollback compatible release, restore and reapply deletion.
3. **Verify:** Reference RPO/RTO met; traces/fixtures deleted per lineage; no stale job result accepted.
4. **Review/record:** run **AFR-T10**, attach **`afr-ops-drill`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A7-03 — Publish docs and evaluation artifacts

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Ship quickstart, replay guarantees, API/SDK docs, benchmark data rights and negative cases.
3. **Verify:** Independent reviewer reproduces fixture benchmark without paid keys.
4. **Review/record:** run **AFR-T06/07**, attach **`afr-public-evidence-pack`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T06/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A7-04 — Run private alpha and triage

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Onboard 3–5 target developers; observe install/failure-to-test tasks; fix critical friction.
3. **Verify:** Feedback tied to issues; release blockers fixed; remaining limitations explicit.
4. **Review/record:** run **AFR-T08/10**, attach **`afr-alpha-summary`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-T08/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] AFR-A7-05 — Approve release and future triggers

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Sign R01–R10 matrix, set owners for maintenance/advisories, choose next adapter from observed demand.
3. **Verify:** Release evidence complete; roadmap separated from implemented capabilities.
4. **Review/record:** run **AFR-R01–R10**, attach **`afr-v1-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] AFR-R01–R10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### AFR-A7-GATE — phase exit / definition of done

**Exit condition:** Independent install/upgrade/restore and evidence-backed release approved.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.
