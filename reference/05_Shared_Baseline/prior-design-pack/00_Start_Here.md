# Engineering design pack
## Agent Flight Recorder · SkillBench · EvidenceForge

**Prepared:** 3 November 2026 · **Baseline:** v0.1 proposed specifications · **Deployment:** independently usable, self-hostable private products with shared foundations · **Stack:** TypeScript/React, Python/FastAPI, Postgres and private artifact storage.

> This is an implementation design and verification plan, not implemented software. All task checkboxes are intentionally unchecked. Performance/quality/security objectives are proposed acceptance gates; no tests, interviews, dependency spikes or audits are represented as already completed.

## What is included

1. **Shared foundation:** architecture, boundaries, identity/roles, storage, jobs, budgets, secrets, privacy, design system, testing, deployment and operations.
2. **Agent Flight Recorder:** safe capture, run inspection, explicit replay modes, trace-to-regression cases, independent verification and CI.
3. **SkillBench:** package intake, preregistered controlled experiments, isolated paired runs, statistical analysis, evidence review and CI reports.
4. **EvidenceForge:** PDF ingestion, typed extraction, page-region provenance, analyst review, correction/versioning and export.
5. **Comparative research:** fifteen primary repository snapshots plus official standards/documentation; reuse/compete/integrate decisions and mandatory validation spikes.
6. **Verification catalog:** 50 named test suites and a release evidence template.
7. **Implementation backlog:** 150 implementation tasks and 30 phase gates, with sequence/dependencies, roles, implementation actions, acceptance criteria, DoD and evidence requirements. Available as CSV, JSON and a formatted Excel tracker.

Each product has **eight phases**, from discovery through release/maintenance; the shared foundation has **six phases**. Every implementation task has a prepare → implement → verify → review sequence and a local DoD checklist. Every phase has an exit gate. The accompanying spreadsheet is the practical execution tracker.

## Recommended reading order

Read this overview, then **Comparative Research**, then the **Shared Foundation**, then your chosen product spec. Use the **Verification Catalog** while implementing tasks. Product specs inherit shared requirements even where not repeated. The consolidated document orders foundation first for reference. Linked filenames in the modular pack are portable; use the combined document if your viewer does not resolve sibling links.

| Document | Purpose |
|---|---|
| `01_Shared_Foundation.md` | cross-product technical/security/operational contract + six-phase runbook |
| `02_Agent_Flight_Recorder.md` | AFR requirements/design/UI/contracts + eight-phase runbook |
| `03_SkillBench.md` | SKB requirements/method/UI/contracts + eight-phase runbook |
| `04_EvidenceForge.md` | EVF requirements/evidence/UI/contracts + eight-phase runbook |
| `05_Comparative_Research_and_Decisions.md` | source-grounded overlaps, dependency decisions and pinned source appendix |
| `06_Verification_and_Release_Catalog.md` | shared/product test specifications and release gates |
| `Implementation_Tracker.xlsx` | editable planning/execution workbook; no task marked completed |
| `Implementation_Backlog.csv` | importable backlog; map fields to your issue tracker |
| `research/source-manifest.json` | exact repository commits/acquisition times and license-detection metadata |

## Three consequential design decisions

### 1. Do not rebuild generic tracing

Phoenix and Langfuse are substantial comparables. AFR must prove value in **failure-to-test conversion, honest replay guarantees and side-effect controls**. Discovery can change its form into an integration if that is the better engineering outcome.

### 2. Skill evaluation already has direct competition

NVIDIA SkillEvaluator already validates skills and compares live runs with/without skills. SKB must evaluate reuse/upstream contribution before committing to a separate engine. Its proposed emphasis is controlled experiment design, preregistration, uncertainty and reviewable evidence; cross-harness support comes after one engine/harness works correctly.

### 3. Source evidence is not correctness

Docling and other parsers supply useful building blocks, but a correct source quote can still belong to the wrong row, period or unit. EVF therefore separates **source support**, **typed semantic validation**, **human review** and any future calibrated confidence. It never invents page references or presents uncalibrated probabilities as accuracy.

## Execution and dependency map

```text
Shared F0 -> F1 -> F2 -> F3 -> F4 -> F5
     |          |      |             |
Product phase 0 |      |             |
          phase 1      |             |
                 phases 2–4         |
                       phases 5–6   |
                             phase 7

AFR: A0 -> A1 -> A2 -> A3 -> A4 -> A5 -> A6 -> A7
SKB: S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7
EVF: E0 -> E1 -> E2 -> E3 -> E4 -> E5 -> E6 -> E7
```

The actual backlog conservatively requires FND-F2 before product phase 1, FND-F3 before phases 2–4, FND-F4 before phases 5–6, FND-F5 before phase 7. Earlier dependency gates are inherited transitively. This intentionally prevents real data/live execution before identity/artifact/isolation support exists. Prototypes and synthetic design spikes can run earlier under phase 0. Shared F4 usability is tested on component/prototype workflows and rechecked on complete product flows; it is not a circular dependency on finished releases.

Products share packages but **do not require each other's deployed server**. SKB can emit its own trace artifacts and optionally link/import AFR; EVF can emit capture data without requiring an AFR installation. Coupled release trains are avoided through schema compatibility and separate module ownership.

### Delivery envelope, not an artificial deadline

Suggested core staffing: one technical lead/backend engineer, one frontend/product engineer, one runtime/evaluation/document engineer, plus part-time UX/QA/security and statistical/domain review. These are roles, not a claim that one individual can provide independent review of their own work. A two-person team should obtain outside security/statistics/domain review and expect a longer schedule.

Illustrative sequencing for a focused 3-engineer team:

| Workstream | Planning allowance | Dependencies / caveat |
|---|---|---|
| Shared discovery/contracts/prototype | 1–2 weeks | decisions before implementation |
| Shared auth/artifacts/jobs/isolation minimum | 3–5 weeks | uncertainty concentrated in executor/identity integration |
| AFR focused private v1, including qualification | 8–12 weeks of product work | can overlap shared foundation; hardening cannot be assumed free |
| SKB focused v1 after backend decision | 8–12 weeks of product work | statistics/hidden-data isolation adds review time |
| EVF narrow-domain v1 | 10–14 weeks of product work | annotation rights and parser quality are critical path |
| Integrated portfolio hardening/buffer | 3–5 weeks across programme | independent review, upgrades, reproducibility and alpha |

Do not simply add or overlap these numbers without capacity planning. For one team building mostly sequentially, **roughly 8–12 calendar months** is a reasonable initial planning envelope, not a commitment. Earlier “1–3 months per project” targets describe focused MVPs with limited scope and reusable foundations. The rigorous v1 gates here can exceed that, especially for hardened code execution or a difficult document corpus. Reestimate after discovery and each spike, record P50/P90 estimates, and reserve at least 20–30% capacity for uncertainty. No assumption that all three production-minded products finish in one quarter.

### Cost planning

Set explicit project and programme monthly budgets before provider experiments. Initial planning allowances (excluding salaries, reviewer fees and existing hardware): control plane/storage/backups €100–400/month at low private usage; separate executor/parser infrastructure €100–500/month; capped provider/evaluation experiments €200–1,000/month across active workstreams. These are rough budget envelopes, not researched vendor quotes or guaranteed bills. Concurrency, OCR models, GPU use and repetition counts can materially increase them. Fixture demos remain keyless and cheap. Provider consumption, annotation effort and external reviews require separate estimates in phase 0.

## Decision register: resolve before relevant implementation

| Decision | Owner role | Latest gate | Required evidence |
|---|---|---|---|
| D01 Supported local/server hardware and runtime versions | tech lead | FND-F0 | tested support matrix |
| D02 Hardened executor backend/topology | security + platform | FND-F3 | actual deployment probes; no host/DB/network escape |
| D03 OIDC provider/session integration | backend + security | FND-F2 | IdP compatibility and abuse tests |
| D04 Source/model/provider data-transfer policy | product + privacy | FND-F2 | destination notice, enforceable consent, retention |
| D05 AFR initial provider/framework adapter versions | SDK lead | AFR-A1 | compatibility spike and omission list |
| D06 AFR difference from existing user tools | product | AFR-A0 | interviews/comparison; integrate/pivot option |
| D07 SKB engine versus upstream contribution | evaluation lead | SKB-S0 | 10-task engine comparison and license review |
| D08 SKB statistical estimand/power/interval procedure | statistical reviewer | SKB-S0/S5 | preregistered protocol and simulation review |
| D09 EVF exact fields/semantic normalization | domain reviewer | EVF-E0 | annotation guide and examples |
| D10 EVF parser/assets and alternate baseline | document engineer | EVF-E0/E2 | ten-document spike; model/code terms |
| D11 Corpus redistribution and holdout access | domain/data owner | EVF-E0 | rights manifest and split hashes |
| D12 Retention/backup expiry/operator jurisdiction | deployment owner | FND-F2/F5 | documented policy and deletion/restore tests |
| D13 Release licensing and trademark availability | maintainer | before public release | exact dependencies/assets/product name review |

ADR entries in the foundation are **proposed design decisions**, not approvals already obtained. Approving or changing them requires a named reviewer and evidence. Product names are working names; no trademark or domain clearance has been performed.

## Initial risk register

| ID | Risk | Impact | Mitigation / decision trigger | Owner |
|---|---|---|---|---|
| RK01 | hostile task/skill code reaches host | critical | hardened full-harness isolation; disable live mode if unavailable | security/platform |
| RK02 | sensitive content enters telemetry/export | critical | metadata defaults, pre-buffer redaction, content rights, canary fixtures | SDK/security |
| RK03 | misleading replay claim causes production side effect | critical | explicit replay modes; no production write replay; no fallback | AFR runtime |
| RK04 | skill result confounded or overstated | high | paired protocol, hidden tests, preregistration, statistical review | evaluation/statistics |
| RK05 | SkillBench duplicates existing tool | high | direct comparison; contribute/integrate/pivot gate | product |
| RK06 | fabricated or misassigned document evidence | high | geometry/quote validator plus semantic tests and review | EVF/domain |
| RK07 | parser compromise/resource exhaustion | critical | disposable no-egress parser, quotas, patched pinned assets | document/security |
| RK08 | model/API/suite/license change breaks assumptions | high | pins, compatibility tests, periodic license review | maintainers |
| RK09 | holdout leakage and benchmark gaming | high | issuer/task split, access separation, fresh holdout on exposure | data/evaluation |
| RK10 | provider cost runaway | high | reservations, broker, caps, cancellation, honest unknown spend | platform |
| RK11 | architecture exceeds small-team capacity | high | narrow v1, shared packages, no premature microservices/queues | tech lead |
| RK12 | backups resurrect deleted content | high | tombstones outside old snapshot; apply before restored traffic | operations |
| RK13 | false confidence in accessibility/security | high | manual testing and actual environment evidence; no certification claim | QA/security |
| RK14 | annotation quality/rights delay EVF | high | rights/label pilot at E0; adjudicate and budget human effort | domain/data |
| RK15 | exported data escapes retention controls | high | explicit warning, minimized exports, no remote-revocation promise | product/privacy |

Review likelihood/severity with real deployment context in F0; impacts above are initial triage. Add likelihood, residual risk, expiry and evidence link in the tracker before execution. Treat new formats, public uploads, new tools/providers and multi-tenant hosting as security-relevant changes.

## Change management and future outlook

- Freeze a baseline revision after phase 0. New requirement: identify user need, affected contracts/threats/data, workload, tests, cost and migration before acceptance.
- Maintain schema migrations and old/new compatibility tests; no cross-product breaking release by surprise.
- Review upstream dependency/security/licensing changes monthly and on advisory notice; prioritize supported version updates.
- Review actual usage and failure rates after alpha, 30 days and 90 days. Choose next capability from evidence, not another trending list.
- Future public SaaS, third-party submissions, public sharing, more formats/languages and automated conclusions each have explicit gates in product/foundation docs. Do not quietly enable them through configuration.

## First actions

1. Assign owners and approve FND-F0 scope/trust map.
2. Run the three product discovery/comparison spikes using synthetic or licensed public material.
3. Resolve executor, engine, parser and corpus decisions before building broad UI.
4. Select **AFR as the first implementation flagship** unless discovery invalidates its differentiation.
5. Import the backlog, assign people/estimates/evidence URLs, and keep all gates unchecked until demonstrated.

