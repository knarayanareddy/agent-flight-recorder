# Normative implementation baseline v0.2

Date: 2026-11-03. This addendum supersedes conflicting v0.1 design choices **for the bounded release below**, not the future product vision. This repository is an executable contract/oracle baseline, not three implemented applications. Read `evidence/release-status.json` before making a readiness claim.

## 1. Precedence and scope freeze

Precedence: this document and `docs/02_Protocol_and_Transactions.md` → versioned schemas/OpenAPI/SQL and explicit semantic rules → UI/workflow contracts → v0.1 specs → backlog prose. A contradiction between normative artifacts is a blocker: record it; do not choose silently. Generated files come from build scripts; update source and regenerated output together with review. Changes to expected test behavior need an independent reviewer, not the implementation agent alone.

### Bounded release 0.2

| Product | Required | Explicitly disabled/deferred |
|---|---|---|
| AFR | authenticated metadata-first ingestion; runs/events; immutable cases; visual/recorded-output replay; trusted built-in JSON/tool/state checks; private fixture results | live models, live tools, process snapshots, production writes, arbitrary plugins, OTel/provider adapters beyond captured schema |
| SKB | safe ZIP inspection; package approval; suite/plan preregistration; recorded paired-trial experiments; task-clustered descriptive analysis; reviewable fixture reports | executing submitted skill code, paid models, public submissions/leaderboard, automatic winner/safety certification; live engine/harness adapters |
| EVF | private PDF registration; fixture parse; local Docling adapter only after integration gate; eight-field typed extraction; exact source evidence; human corrections and JSON/CSV export | URLs/Office formats, cloud extraction, uncalibrated correctness probability, autonomous financial decisions, new language guarantees |

SKB fixture experiments test orchestration/analysis, **not real skill effectiveness**. AFR recorded simulation tests only captured behavior, not a new model. EVF synthetic parse fixtures are not evidence Docling works. The UI must repeat those distinctions.

Original live-agent/large-corpus requirements remain future milestones. Their v0.1 tasks are neither deleted nor completed; they are deferred behind B1 live-expansion gates. A smaller release is not a substitute for proving the original full v1 production claim. `release_gate.py` intentionally demands actual integration/product/security evidence even for private production readiness; fixture tests alone cannot authorize deployment.

## 2. Fixed technical choices

- Repository: modular monorepo; independently buildable `apps/api`, `apps/web`, `apps/dispatcher`; product modules inside API, feature-profile selected. Shared schemas generate types. No cross-product deployed-server dependency.
- Target Python 3.12, TypeScript strict, React with Vite and same-origin API proxy; Python FastAPI/Pydantic v2/SQLAlchemy/Alembic application dependencies start from exact registry-resolved candidates in `contracts/dependency-candidates.json`, then resolve and freeze full transitive locks in B01. Baseline test-tool versions already exact-pinned in `requirements-baseline.txt`. Registry candidates are not integration/security approval. Target Node24 LTS for frontend tooling; freeze exact patch in B01. No silent use of latest production dependencies; dependency-lock approval is a release blocker.
- Postgres 16; local private artifact volume (not S3) for the first reference host, behind authorized API streaming. Object-store support is deferred, eliminating a second untested storage path. Artifacts are never directly web-served. Model credentials do not exist in B0.
- Queue: Postgres leases + outbox only. No Redis/ClickHouse/Kubernetes requirement. Each job has one active fenced attempt. API, dispatcher and migration identities separate. No Docker socket is mounted in app or workers.
- Identity: external OIDC authorization-code flow + PKCE S256 with confidential backend session; no custom passwords; no public registration; organization members preprovisioned by administrator. Production issuer/client/secret/hostname are operator-provided environment inputs, never invented by an agent. Local demo uses synthetic read-only identity, loopback only, fixture resources only.
- Hosted untrusted engine: future backend fixed to dedicated Linux amd64 gVisor `runsc`, separate executor host and constrained broker. **Not installed or validated here; not enabled in B0.** No fallback to ordinary host Docker when unavailable.
- SKB B1 engine decision: choose Inspect adapter for explicit task/scorer orchestration; prefer importing/contributing static skill checks to SkillEvaluator rather than duplicating scanners. Exact research source commits are in copied upstream lock. This is a binding direction, but live compatibility still requires an executable spike; it is not falsely represented as empirically validated.
- EVF parser choice: Docling + docling-core pinned to research source commits as integration candidates; required compatible wheel/asset versions and OCR model hashes resolved by integration spike. No unreviewed runtime downloads. Fixture profile is available without installing Docling.
- Statistics: task-mean success delta, task-clustered paired bootstrap, deterministic seed and percentile rule specified in reference oracle. No efficacy/equivalence label. A statistical reviewer must approve live-result interpretation.

### Production reference topology

Single Linux amd64 4-vCPU/16-GiB control-plane host, separate parser/executor host before processing untrusted PDFs/code. TLS Caddy edge; web/API private ports; Postgres on internal network; app/dispatcher run unprivileged; original/derived bytes in artifact volume, quotas and encryption supplied by host storage. Compose is a single-host reference without HA. Its product images are deliberately `UNBUILT` until code exists. A config file is not a tested deployment.

Registry-resolved Postgres/Caddy digests are in `infra/upstream-image-lock.json`; these were resolved but not pulled/run. Runtime/container/OS patch support and image vulnerability assessment remain release evidence. The supplied CSP assumes compiled static CSS/scripts without inline script; implementation cannot relax it to `unsafe-inline` just to make a library work.

## 3. Repository target layout

```
apps/api/                 FastAPI app, modules foundation/afr/skb/evf
apps/web/                 React routes and UI state components
apps/dispatcher/          trusted lease manager and fixture jobs
packages/contracts-ts/    generated client/types from OpenAPI
packages/capture-python/  AFR metadata-only client
contracts/                normative schemas/API/examples
reference/                acceptance oracles; NOT production imports
fixtures/                 synthetic inputs and expected results
apps/*/tests/              implementation tests
acceptance/               independent black-box journey tests to implement
infra/                    fail-closed reference deployment
```

No application folders above are claimed implemented. The implementing agent creates them ticket-by-ticket. Importing `reference.oracles` into production violates separation of implementation and oracle; copy-pasting expected outputs to fake a product also fails acceptance. Golden fixtures are public development examples, not secure held-out tests.

## 4. API/data contracts

`contracts/openapi.yaml` defines 48 domain operations (browser identity/health protocol is separately fixed in `contracts/auth-flow.yaml`) and exact object types; `contracts/schemas` defines 48 standalone JSON Schemas; examples have valid/invalid structural samples. Generated TS/Python code must retain nullability and enum values, reject unknown request keys and validate responses. Semantic checks not expressible in these schemas are specified below and in transaction rules.

Examples validate shape, not cross-resource referential integrity. A missing actual project must still return not-found. No schema should cause UUID constants from examples to be seeded as production records.

### Semantic rules

- Region x0<x1 and y0<y1; page exists; source/parse/element hashes and quote must resolve. Text evidence cannot use a fabricated quote; manual-image evidence quote is empty.
- An extraction has each of the eight field keys exactly once: `entity`, `period_end`, `currency`, `scale`, `revenue_current`, `revenue_prior`, `assets_current`, `assets_prior`. Reject duplicate/missing keys. Schema `annual-report-8/1` cannot be expanded in place.
- Amount `value` is a decimal string in **base currency units**, after multiplying source value by `scale`. Preserve `raw` and source `scale`; never apply scale twice in display/export. `period_end` is ISO date; currency is uppercase ISO code. Entity is source text, no invented corporate resolution. `scale` field value is one of 1/1000/1000000; ambiguous scale blocks numeric acceptance.
- Typed absence uses null value and non-null missing reason. Present value requires null missing reason. An absent source fact can be reviewed as absence with reason; cannot become a made-up zero.
- Accepted/corrected present fields require valid support, explicit currency/scale/period for amounts, and reviewer identity. Review with unsupported evidence returns 422. Accepting an unsupported absence requires `not_present` supported by review of scope, not automated certainty.
- Preregistered plan content is immutable. Package/suite hashes must match referenced current immutable versions and package approval. B0 only accepts fixture harness/model IDs.
- Trials are unique by task×repeat×arm for final analysis input. Retry attempts are stored separately; choose the last **infrastructure-valid authorized attempt**, not the highest score. More than one valid attempt requires reviewer reconciliation; do not auto-pick. Every scheduled task/arm/repeat appears or contributes unknown bounds.
- Case creation freezes run revision and fixture artifact digests. Case replay mode must equal approved mode; mismatch is 409. Missing match is error, never network fallback.
- Metadata-only events must not contain content artifacts or free-text `reason`; allowlist scalar operational metadata. `reason` is redacted-capture only and sanitized. `capture.dropped` requires ordered sequence start/end; missing content is flagged rather than filled.

## 5. Rights and security baseline

Roles are capability sets, **not an automatic hierarchy**. Viewer=metadata inventory/status. Analyst=viewer plus authorized content and case/plan/review/export drafts. Operator=viewer plus fixture job dispatch/cancel and event ingestion, not content download. Maintainer=analyst+operator plus package approval, suite creation, preregistration and deletion. Organization admin=identity/project administration, not project content unless explicitly assigned project role. Endpoints requiring a lower role accept a role containing that capability, never string-sort role names.

API keys have explicit scope intersection with actor/project permissions. AFR ingest key may only call `afr_ingest_events`, not all operator endpoints. Project hint is path project ID or `X-Project-ID`; verify membership first, set DB context transaction-locally, then query child resources. Invalid object in authorized project is 404; cross-project child ID concealed as 404. Do not probe global resources before authorization.

Hidden test artifacts have no normal application-granted read rights. A trusted scorer collector gets only required job capabilities. In B0 there are no arbitrary candidate processes, and no claim of safe untrusted execution. Auth precedes schema/resource/mode-specific disclosures. Endpoint smoke runner checks that unauthenticated API calls receive 401.

## 6. Release boundaries

B0 developer: contracts + deterministic fixtures, no app readiness claim. B0 private product: actual APIs/UI/auth/DB/worker behavior, independent reviews and ops acceptance required. B1 live: gVisor full-harness isolation, engine/provider integration, data-transfer governance and additional threats/benchmarks; cannot be enabled by flipping one env var. Future SaaS requires tenant isolation, regional/data obligations, abuse/billing/on-call and tenant-restore review.

Every launch needs an operator-supplied domain, OIDC configuration, encrypted storage/backup destinations, named security contact and incident owner. These are legitimate deployment inputs—not decisions an agent should invent. Unknown inputs cause a blocked status.


### B0 fixture wire details

AFR metadata capture policy ID is UUIDv5(namespace=project UUID, name=`metadata_only:v1`); this deterministic ID identifies a fixed profile, not authorization. A recorded fixture artifact uses `schema_version=afr-recording/1`, `final_output` JSON object, `final_state` JSON object, and `tool_results` array of tool/contract_hash/args/ordinal/output records. Only one such recording artifact per recorded case is accepted; unrelated attached evidence is inert. `json_equals` targets final_output; `mock_state_equals` targets final_state; `forbidden_tool` compares requested tool names from tool_results, with expected equal to the forbidden name. Paths use RFC6901; forbidden_tool path must be empty. No arbitrary expression evaluation.

SKB fixture/1 executes preinstalled synthetic trial records matching the selected task IDs/repeat count; it does not derive outcomes from package instructions. User-supplied trial JSON may be stored as fixture input only in explicitly synthetic development suites and is marked imported simulation; never treat it as independently scored evidence. Rights manifest may share a synthetic artifact in development fixtures if it contains an explicit rights declaration.

EVF fixture/1 accepts only the bundled PDF SHA-256, rebases document/parse IDs to actual new records, and uses bundled synthetic text/geometry. Numeric expected revenue_current=1234000 and assets_current=5678000 EUR (source scale1000); prior amounts/date are missing unless source explicitly supplies them. Exports use `schema_version=evf-export/1`, source/extraction/review manifest and fields array with typed values/states. Fixture regions are not claimed actual renderer annotations.
