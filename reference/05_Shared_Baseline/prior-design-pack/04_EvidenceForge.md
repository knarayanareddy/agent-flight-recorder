# EvidenceForge — product and technical design

**ID:** EVF · **Version:** 0.1 proposed · **Date:** 2026-11-03. Inherits the shared foundation. Not a certified financial, legal or medical decision system.

## 1. Charter and bounded use case

**Primary user:** analyst extracting facts and comparable tables from public annual reports. Secondary: reviewer checking extracted values and developer integrating structured exports. **Job:** “Give me structured values I can inspect, correct and trace back to the exact source version.”

Initial domain: public annual reports and financial statements, **PDF only**, born-digital and scanned, English-language core benchmark with clearly labeled multilingual challenge cases. Extract a deliberately small schema: reporting entity, reporting period, statement currency, units/scale and selected statement line items with current/prior period values. Support evidence annotation and table extraction; no automated investment recommendations or write-back to accounting systems. A pilot chooses 8–12 exact fields/line-item types and documents their semantics before implementation.

Docling provides a typed document representation with hierarchy, tables, layout and provenance when available. Unstructured supplies document partitioning/ETL components; Marker provides conversion outputs with distinct code/model licensing; RAGFlow is a broader retrieval/context application. Label Studio is a complementary annotation tool. These projects do not make extraction correctness, confidence calibration, review workflow or source-version integrity automatic. **V1 differentiator:** field-to-region evidence, cautious validation, immutable extraction/review lineage and analyst correction/export—not another PDF chatbot.

Required: safe PDF ingestion; preserved original bytes; immutable document versions; parser adapters; source-coordinate normalization; field/table schema; evidence links; validation; review queue; correction with concurrency control; revision comparison; reproducible exports; deletion and restore lineage. A basic cited query interface is optional **after** extraction and review pass; no conversational UI prerequisite.

Deferred: Office files and arbitrary URLs; all languages; handwriting guarantees; automatic merging of contradictory reports; legal/financial compliance certification; accounts-payable approvals; real-time collaboration cursors; public uploads in demo; training custom OCR models; autonomous high-stakes decisions.

## 2. Requirements and traceability

| ID | Requirement | Acceptance test | Phase |
|---|---|---|---|
| EVF-R01 | safe bounded immutable upload | EVF-T01 hostile PDF/size/type corpus | E1–E2 |
| EVF-R02 | original-to-parse version lineage | EVF-T02 reparse and version/tamper test | E2–E3 |
| EVF-R03 | valid page-region evidence, never fabricated | EVF-T03 rotations/cropbox/render mappings | E3 |
| EVF-R04 | typed values with currency/units/period | EVF-T04 numeric/semantic golden set | E4 |
| EVF-R05 | source support distinct from correctness | EVF-T05 wrong-row and contradictory facts | E4/E6 |
| EVF-R06 | review/correction with history and conflicts | EVF-T06 concurrent reviewer tests | E5 |
| EVF-R07 | reliable export with evidence manifest | EVF-T07 roundtrip and formula-injection tests | E5 |
| EVF-R08 | deletion reaches derivatives | EVF-T08 lineage purge/restore drill | E7 |
| EVF-R09 | accessible evidence review | EVF-T09 keyboard/screen-reader usability | E5 |
| EVF-R10 | measured extraction quality and abstention | EVF-T10 held-out corpus report | E6 |

## 3. Domain and data contracts

### Entities

`document`: user-facing logical item; `document_version`: immutable original bytes + digest, upload origin, title, declared language, page count, scan classification and safe metadata. Multiple reports by an issuer are not automatically versions of the same report: analyst explicitly relates them. Duplicate detection is project-scoped and does not leak presence in another project.

`parse_version`: document version ID/digest, parser/renderer/image/model versions and license refs, settings, execution environment, per-page status, normalized output digest, warnings and timestamps. Reprocessing never overwrites prior parse output.

`page`: one-based ordinal, PDF page label if provided, media/crop boxes, intrinsic rotation, render dimensions/dpi, transform matrices and render artifact. A label such as “A-3” is not confused with ordinal 3.

`element`: stable within parse version only; type/text/table/image, reading-order links, hierarchy, source provenance list, parser raw reference and normalized geometry. Merged cells store row/column spans and header associations; do not flatten all table structure into markdown.

`extraction_schema_version`: field definitions, semantic labels, validation rules, unit/currency/period representation, allowed missing states and required evidence rules. `extraction_version`: exact schema+parse+extractor config/model hashes, field proposals, validation results and run trace reference.

`field_proposal`: canonical field key, raw source text, typed proposed value, period, currency, scale, source role (current/prior), evidence refs, extraction method, support status, risk factors, review state, and explicit missing reason. `table_cell_proposal`: row/column/header refs, raw text/value, merged-cell relationships and evidence. `review_revision`: immutable patches to proposals with actor/time/reason and base revision. Export freezes extraction+review revisions.

`export_manifest`: source/parse/extraction/review hashes, selected values, field states, evidence IDs, warnings, exporter version and checksums. `document_relation`: explicit prior-year/amended-report/duplicate relation, not implicit replacement.

Tables use these names prefixed `evf_`. Common artifact links connect original, rendered pages, parser output, thumbnails, extracted text, proposals and exports. Retrieval indexes are derivative artifacts. Store linkage before work runs so deletion covers intermediate outputs.

### Value semantics

Use decimal strings, never binary floating point for reported values. Preserve raw text: `(1,234)`, `1.234,50`, `—`, `0`, `N/A`, percentages and superscript notes have different meanings. Normalize with explicit locale/currency/scale rules and attach transforms. An em dash is not automatically zero. Units apply at document/table/column/cell scope with precedence rules and provenance. Distinguish accounting negative parentheses from footnote markers. Periods are typed date ranges/as-of dates with unparsed raw label retained; fiscal years need not match calendar years.

Missing-value enum: `not_present`, `unreadable`, `ambiguous`, `unsupported`, `redacted`, `not_requested`, `parse_failed`. A missing value is not an empty string or fabricated zero. Review status: `unreviewed`, `accepted`, `corrected`, `rejected`, `needs_review`. Source support: `supported_exact`, `supported_normalized`, `support_ambiguous`, `unsupported`, `source_unavailable`. Support is evidence relation, not truth of the financial statement.

## 4. End-to-end pipeline

1. **Upload preflight:** authenticated project user, declared file/size; reserve storage and job quota; accept only PDF under v1 limits. Show local/external processing destination before submit.
2. **Quarantine:** generate internal object key, stream upload, sniff magic and media, compute digest, scan if configured, inspect bounded metadata in isolated worker. Reject mismatched files, impossible size, active embeddings not supported, encryption/password-protected files and malformed documents with actionable reason. Antivirus is a layer, not proof of safety.
3. **Document registration:** finalize immutable source version; classify probable text/scanned/mixed; safe page count under quotas. No remote references or embedded attachments are followed. Do not extract embedded files.
4. **Parse dispatch:** create parse version, lease an isolated no-egress worker with approved parser image, read-only input and bounded scratch disk. Models/assets are pre-fetched and digest-pinned, not downloaded from the PDF content.
5. **Render and normalize:** preserve raw parser result; normalize hierarchy, text/tables and coordinate systems with validation. Mark failed pages and continue only under explicit partial policy. Commit per-page artifacts and terminal status without claiming whole-document success.
6. **Extraction:** deterministic rules first; optional external model only with project transfer consent. Provide relevant source elements, strict output schema and no tool authority. Candidate fields outside supplied evidence are marked unsupported. Model outputs never create arbitrary file paths, SQL or executable rules.
7. **Validation:** schema/type checks; exact/normalized evidence matching; currency/period/unit consistency; duplicate row/header checks; arithmetic where semantically applicable with declared tolerance; contradiction flags. Do not apply a balance equation without identifying component scope and units. Record each check independently.
8. **Review triage:** route unsupported, ambiguous, inconsistent or low-quality proposals to review. Default is no automatic “verified” status. Analyst can accept/correct/reject, attach new evidence and explain change.
9. **Export:** freeze the view, verify references resolve, generate typed JSON/CSV plus evidence manifest; unresolved items remain explicit. Watermark/report incomplete or unreviewed states. Safe CSV encoding by default.
10. **Version comparison:** compare extracted values and source text for explicitly related versions. Preserve old values/reviews; propose correspondence with evidence, never silently transplant reviews to changed evidence.
11. **Retention/deletion:** traverse lineage, revoke access, purge active bytes/derived indexes/exports, retain minimal tombstone, reapply on restore.

Pipeline states: `uploaded -> quarantined -> accepted -> parsing -> parsed|partial|parse_failed -> extracting -> review_ready|partial|extraction_failed -> reviewed -> exported`. Parsing, extraction, review and export are separate versioned state machines, so a new parse does not erase a reviewed earlier version. Cancellation is acknowledged only after workers stop or expire; incomplete pages remain labeled.

V1 proposed defaults: PDF <=25 MiB, <=100 pages, page render <=20 megapixels, per-job wall timeout 20 minutes, parser 2 vCPU/4 GiB with measured increase only by approved profile, expanded scratch <=2 GiB; limits may need adjustment after pilot. Excess complexity fails safely with diagnosis. Never promise all 100-page files complete within the wall limit.

## 5. Provenance and coordinate correctness

Normalized geometry uses origin **top-left**, x/y in [0,1] over the **rendered crop box after intrinsic rotation**; points ordered and schema-validated. Store original PDF coordinate bbox/polygon, source origin convention, page dimensions and explicit forward/inverse transforms. Normalized convention is a product contract, not assumed parser output. Keep original artifact digest and parse version in every region reference.

Test portrait/landscape, rotations 0/90/180/270, nonzero crop offsets, different media/crop boxes, negative PDF coordinates, unusual page labels, multiple columns, spanning table cells and multi-region evidence. Validate roundtrip point mapping within 1 rendered pixel under declared test renders. Region highlight must align across zoom and high-DPI displays. Reject invalid regions rather than clipping them into plausible false evidence; a safe corrected bbox can be a new normalization revision with warning.

Evidence reference: `document_version_id`, `source_sha256`, `parse_version_id`, `page_ordinal`, `element_id`, `region`, `text_span` (if available), `quote`, `quote_normalization`, `evidence_method`, `support_check_version`. Quotes must derive from parser/source text, not a generated paraphrase. OCR quotes are labeled OCR-transcribed; they are not “exact digital text.” Image-only evidence may be manually verified without a text quote. Highlighting a source shows where a proposal came from, not that it belongs to the correct field or row.

Citation validator verifies access and hashes, existing page/element, valid geometry, quote/span consistency where available and compatibility with the requested extraction version. Missing provenance yields source-unavailable/unsupported; never synthesize a page number. Export includes page ordinal and printed label separately. Deep links require authorization and must not disclose storage keys.

## 6. Confidence, review policy, and numeric quality

Parser-stage OCR/layout confidence, model self-confidence, rule agreement and semantic correctness are different signals. V1 displays **risk factors and validation status**, not a fabricated probability of correctness. Possible signals: OCR uncertainty, parse warnings, conflicting sources, unit ambiguity, support mismatch, arithmetic discrepancy and repeated candidates.

A later calibrated confidence model requires held-out labeled data, calibration curves, error rates by field/document class, drift checks and threshold selection against review cost and false-accept risk. If not calibrated, label “heuristic review priority” rather than “95% accurate.” No automatic approval of high-impact financial values in v1.

Corrections preserve source text and original proposal. A reviewer may correct value, unit, period, evidence link or semantic field assignment. Validation reruns on affected fields and dependent totals; accepted status is invalidated when its support changes. Concurrent corrections use revision hashes/If-Match; conflict screen shows base, mine and current. No last-writer-wins for reviewed evidence. Self-review is allowed for portfolio/private deployments but visibly recorded; optional two-person review is later policy work, not an implied assurance.

## 7. UI/UX information architecture

Navigation: Library · Processing · Review Queue · Schemas · Exports · Settings.

### Upload and library

Drag/drop and keyboard file picker; limits visible; local/external data policy explained; per-file progress; upload retries do not duplicate logical versions. Library rows show title, source version, pages, parsing status, review counts, modified date and warnings. Filters by state/schema/period and explicit issuer metadata; no hidden full-content indexing of unauthorized projects. Empty state has sample public PDF and a no-provider fixture demo.

### Review workspace

```text
Report title / source version / extraction revision   Save status
-----------------------------------------------------------------
Pages + search | original PDF + evidence overlays | fields/table grid
               | page ordinal / printed label    | value/units/period
               | zoom + rotate view controls     | source + warnings
-----------------------------------------------------------------
Selected field: raw text -> normalized value -> checks -> review log
[accept] [correct] [reject] [next needs review] [export readiness]
```

View rotation is distinct from source intrinsic rotation and does not rewrite stored geometry. Source pane loads authenticated page renders/PDF using a maintained renderer; active PDF JS/actions disabled. Provide text/element view for accessibility and for renderer failure. PDF file and parser output remain inert; user cannot navigate embedded links without explicit confirmation, preferably external browser isolation.

Selecting a field focuses relevant evidence without silently changing the value. Selecting source region lets analyst attach evidence to a field. Multi-page table views preserve repeated headers and units. Editable grid keyboard behavior follows accessible grid patterns or falls back to ordinary form rows if robust screen-reader grid support cannot be established. Review shortcuts are optional, reversible actions have undo through a new revision, destructive deletions need confirmation.

### Export readiness and version diff

Readiness displays total fields, reviewed fields, unsupported/ambiguous items, partial pages, policy restrictions and unresolved errors. Allow an explicitly incomplete export when project policy permits, but include states and warnings. “Reviewed export” requires all required fields resolved by declared policy; noncritical missing source facts may remain as typed absence, not fabricated values.

Diff screen shows old/new value, currency/units/period changes and paired evidence. No headline “value changed” until normalization accounts for scale/period. Source digest and extraction revision always visible. A new parser version causing a changed value is labeled processing change, not presumed issuer revision.

### Required states/accessibility

Uploading/retrying; quarantined; encrypted PDF; unsupported/malformed; page limit; rendering failure; partial parse; parser unavailable; extraction data-transfer consent absent; quota reached; source deleted; quote mismatch; pending review; revision conflict; export incomplete; reconnecting. Each has a safe recovery action. Progress is real stages/pages, no ungrounded accuracy meter. WCAG 2.2 AA target, source text alternative, keyboard navigation, visible focus, zoom/reflow and non-color warning icons required. On small screens switch source/form as labeled tabs while preserving selection.

## 8. APIs and integration contracts

Shared prefix `/api/v1/evf`:

- `POST /uploads`, `POST /uploads/{id}:finalize`, `GET /documents`, `GET /documents/{id}/versions`.
- `POST /document-versions/{id}/parses`, `GET /parse-versions/{id}`, `GET /parse-versions/{id}/pages` and `/elements`.
- `POST /schema-versions`, `POST /parse-versions/{id}/extractions`, `GET /extraction-versions/{id}/fields`.
- `POST /extraction-versions/{id}/review-revisions` with base revision; `GET /review-queue`.
- `POST /extraction-versions/{id}/exports`, `GET /exports/{id}/manifest`, `POST /version-comparisons`.
- `DELETE /documents/{id}` creates deletion request and returns affected derivative counts and tracking URL after authorization.

Never accept raw parser options that enable code execution, arbitrary output paths or remote model repositories. Maintain an allowlisted parser profile registry. Async jobs use shared idempotency and cancellation semantics. Export/query endpoints resolve artifact/project rights on every request. Signed object URLs, when used, expire quickly and are not embedded permanently in manifests. Persist artifact IDs, not ephemeral download URLs.

Parser adapter interface: supported profile/media; input content digest; profile/config hash; per-page output; normalized elements/tables/provenance; warnings/unsupported features; resource usage; parser and model artifacts/licenses; immutable raw output ref. Validate adapter outputs before UI or extraction consumes them. Unexpected extra fields cannot smuggle executable content/config.

## 9. Security, privacy, licensing, and operational details

No URL ingestion in v1 removes a major SSRF surface. No attachments, encrypted documents, embedded scripts or active forms are processed as code. PDFs remain hostile inputs even when virus scan is clean. Separate render/parser hosts from control plane and run per-document disposable environments with no network and no shared writable cache. Protect host renderer endpoints from path traversal and decompression/image bombs. OCR/model assets are reviewed at build time. Disable parser telemetry where supported or document it; verify actual egress in tests.

Original content is sensitive by default even if an uploader claims it is public. External extraction requires explicit authorization and provider profile; log metadata only. “Local processing” mode denies outbound model/telemetry calls by enforcement, not just a UI toggle. Exports, screenshots and review notes are derivatives subject to retention. Source redaction cannot be a visual-only overlay on downloadable original bytes; v1 does not claim secure PDF redaction. If a user needs sanitized documents, require a separately verified redaction tool and disclose limits.

Code license, model weight license, OCR datasets, sample PDFs, fonts, and commercial provider terms are separately inventoried. Do not copy a code repository license into a blanket “commercial safe” claim. Parser adapter selection includes model download and redistribution review. Benchmark documents need redistribution permission or a documented download recipe with hashes and clear rights; public availability is not automatic permission to repackage.

Metrics: upload rejection by safe reason, queue wait, per-page parse failures, time/pages/memory by profile, extraction error/missingness, support mismatch, review queue age, correction rate, export errors, deletion backlog, parser egress denials and cost. No document names/text in metric labels. Page-preview cache is project-scoped and invalidated by deletion. A support bundle contains versions/counts/status, not PDF content unless separately authorized.

## 10. Evaluation methodology and release targets

Build a 100-document corpus after rights review: 40 development, 20 validation, 40 final holdout; split by issuer/report family, not merely random pages, to reduce near-duplicate leakage. Include born-digital, scanned and mixed PDFs; diverse table layouts, rotation, units/scale, negative parentheses, footnotes and missing fields. Declare category counts and challenging unsupported cases. Ground truth labels are independently reviewed by two annotators with adjudication; measure disagreement and document ambiguous policy decisions. Sample size supports a portfolio benchmark, not broad claims across every annual report.

Metrics:

- field exact match after **declared** normalization; report denominator per field and document class;
- value+currency+scale+period joint correctness, not value alone;
- table cell/header/span structure correctness and row association;
- evidence page correctness and bbox intersection/coverage against labeled evidence; quote support validation separately;
- unsupported-citation rate, abstention/coverage and errors among accepted proposals;
- reviewer correction rate, time to reviewed export, and export roundtrip correctness;
- cost/page and wall time by hardware/profile, reporting failed jobs and retries.

Proposed release thresholds: >=95% selected numeric fields correct on the in-scope born-digital holdout; >=90% joint value/currency/scale/period correctness on that subset; >=99% existing/resolvable evidence references; **0 fabricated page/element references accepted by validator**; all unsupported proposals visibly flagged; manual review remains required. Scanned/challenge results are reported separately without folding them away. If targets fail, restrict supported fields/document classes and rerun a fresh held-out evaluation; do not tune on final holdout then reuse its score. These targets are goals and may prove infeasible without narrower scope.

Coordinate transforms must pass 100% of declared synthetic geometry tests within tolerance. All correction/export semantic golden cases pass. Review UX task target: 4/5 pilot analysts identify a seeded wrong-row value, correct it and export with provenance without moderator help. Automatic checks cannot replace this test of human trust and error detectability.

Chaos: kill parser mid-page, corrupt output, lose object store, duplicate finalize, expired lease, conflicting review edits, delete during export, restore before tombstone processing. Unknown/incomplete states cannot look reviewed. Performance: shared control-plane targets; processing throughput benchmarked on fixed 2/4-vCPU worker profiles and recorded hardware, not a universal pages/second promise.

## 11. Outlook and release checklist

V0.1 safe PDF upload + parser/evidence viewer. V0.2 typed extraction/review/export. V1 measured private release with narrow schema. Future: additional formats after separate parser threat review; multilingual quality profiles; domain schema packs; calibrated confidence; more advanced table correspondence; source-cited Q&A with abstention; optional offline model profile; human annotation export/import; enterprise retention/approval policy. Every new format/language/model requires new evaluation slices and dependency-license review.

**Release DoD**

- [ ] EVF-R01–R10 have evidence; in-scope limits are visible before upload.
- [ ] Source, parse, extraction, review and export versions are immutable and resolvable.
- [ ] Quote/geometry validator cannot mint evidence for nonexistent source content.
- [ ] Reviewer corrections preserve history and detect conflicts; new source does not inherit stale approval.
- [ ] No numerical correctness probability is displayed without calibration evidence.
- [ ] Parser is isolated/no-egress; hostile-file and geometry fixtures pass.
- [ ] Export flags unresolved data and survives roundtrip without numeric/period corruption.
- [ ] Benchmark rights, annotation guide, holdout report, limitations and failure examples are published.
- [ ] Deletion/restore/upgrade/security/accessibility runbooks pass reference-deployment drills.



---

# Implementation phase runbook

All items below are **planned and unchecked**. Each task inherits the global definition of done. Task order is conservative: the previous task and prior phase gate must pass before proceeding; explicit independent branches may be parallelized by an approved planning change. Evidence paths are proposed repository artifacts, not existing implementation evidence.


## EVF-E0 — Define domain and annotation policy

**Accountable role:** Product + domain reviewer. **Entry:** Project baseline accepted; assign owner and reviewers.

**Shared prerequisite:** FND-F0 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E0-01 — Interview target analysts

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Observe five annual-report extraction/review workflows and recurring errors.
3. **Verify:** Field choices and review priorities grounded in concrete analyst tasks.
4. **Review/record:** run **discovery review**, attach **`evf-discovery.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] discovery review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E0-02 — Freeze semantic schema

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Choose 8–12 fields with currency/scale/period/missingness and arithmetic applicability rules.
3. **Verify:** Ambiguous field policies have examples and domain reviewer signoff.
4. **Review/record:** run **EVF-T04/05**, attach **`evf-schema-guide`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T04/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E0-03 — Assemble licensed corpus/splits

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Select 100 reports with issuer-family splits, rights/download hashes and challenge categories.
3. **Verify:** 40/20/40 split frozen; redistribution rights or retrieval recipe documented.
4. **Review/record:** run **EVF-T10**, attach **`evf-corpus-manifest`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E0-04 — Compare parsers on ten documents

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test Docling and one alternate for geometry/tables/OCR/versions/compute/licenses.
3. **Verify:** Observed results, asset terms and adapter decision documented without universal accuracy claim.
4. **Review/record:** run **EVF-T02/03/10**, attach **`evf-parser-ADR`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T02/03/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E0-05 — Prototype review UX and threat model

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test upload/source/field/correction/export flow and hostile-file/data-transfer boundaries.
3. **Verify:** Users understand source support versus correctness; critical trust boundaries recorded.
4. **Review/record:** run **EVF-T01/09**, attach **`evf-prototype-study`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E0-GATE — phase exit / definition of done

**Exit condition:** Narrow schema, public corpus rights, evidence semantics and parser choice approved.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E1 — Safe source ingestion and versions

**Accountable role:** Backend + security. **Entry:** EVF-E0-GATE approved.

**Shared prerequisite:** FND-F2 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E1-01 — Implement PDF upload preflight

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Show limits/processing policy, reserve quota and accept streamed bounded upload.
3. **Verify:** Wrong type/size/quota rejected; duplicate retries do not create unintended versions.
4. **Review/record:** run **EVF-T01**, attach **`evf-upload-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E1-02 — Implement quarantine/inspection

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Sniff PDF, bounded page/encryption checks and optional scanner in isolated worker.
3. **Verify:** Malformed/encrypted/attachment/action fixtures handled safely without code/remote fetch.
4. **Review/record:** run **EVF-T01**, attach **`evf-quarantine-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E1-03 — Implement document/version lineage

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Register original digest/title/origin/pages and explicit relations between reports.
3. **Verify:** Reupload/new version never overwrites source or silently changes report relationship.
4. **Review/record:** run **EVF-T02**, attach **`evf-version-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E1-04 — Implement library/status UI

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Show source version, pages, warnings, stage/review counts and keyboard upload states.
3. **Verify:** Empty/retry/denied/partial/unsupported states recoverable without content leakage.
4. **Review/record:** run **EVF-T01/09**, attach **`evf-library-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E1-05 — Verify source access/deletion links

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Enforce project content access and connect all pending artifacts to lineage.
3. **Verify:** Unauthorized originals inaccessible; delete-before-parse revokes and cancels pending work.
4. **Review/record:** run **EVF-T01/08**, attach **`evf-source-access-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E1-GATE — phase exit / definition of done

**Exit condition:** Original PDFs immutable and hostile uploads cannot enter general application execution.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E2 — Isolated parsing and immutable outputs

**Accountable role:** Parser engineer. **Entry:** EVF-E1-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E2-01 — Build parser image/profile registry

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Pin parser/OCR/model assets and allowlist settings; no runtime content-driven downloads.
3. **Verify:** All model/code licenses inventoried; denied egress install/run test passes.
4. **Review/record:** run **EVF-T01/02**, attach **`evf-parser-image-manifest`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E2-02 — Implement per-document parser jobs

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Read-only source, disposable scratch, resource/time/page quotas and bounded outputs.
3. **Verify:** Image/complexity bombs/crash/timeouts contained; control-plane unaffected.
4. **Review/record:** run **EVF-T01**, attach **`evf-parser-security-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E2-03 — Store parse versions/raw outputs

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Record source/profile/environment hashes, page statuses and immutable raw results.
3. **Verify:** Same source can have multiple parses; previous result never overwritten.
4. **Review/record:** run **EVF-T02**, attach **`evf-parse-version-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E2-04 — Normalize text/hierarchy/tables

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Map parser items into typed elements with reading order, spans/header associations and warnings.
3. **Verify:** Golden multi-column/merged-cell fixtures retain declared structure or explicit unsupported flags.
4. **Review/record:** run **EVF-T04**, attach **`evf-normalization-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E2-05 — Implement parser recovery/progress

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Persist page-stage status, handle retries/fencing/cancel and expose partial results honestly.
3. **Verify:** Worker death/duplicate completion cannot create full-success from missing pages.
4. **Review/record:** run **EVF-T01/02**, attach **`evf-parser-fault-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E2-GATE — phase exit / definition of done

**Exit condition:** Per-page outcomes, parser assets and failed/partial states preserved.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E3 — Geometry, source viewer and evidence validation

**Accountable role:** Frontend + parser engineer. **Entry:** EVF-E2-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E3-01 — Implement canonical coordinate transforms

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Store original/normalized spaces and forward/inverse crop/rotation transforms.
3. **Verify:** 0/90/180/270 rotation, crop offsets and roundtrip fixtures within one rendered pixel.
4. **Review/record:** run **EVF-T03**, attach **`evf-geometry-oracle-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E3-02 — Implement page render/source endpoints

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Serve authorized bounded page renders/originals with active features disabled and safe caching.
3. **Verify:** No active document execution/unsafe file path; cache invalidated on deletion.
4. **Review/record:** run **EVF-T01/03/08**, attach **`evf-render-security-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/03/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E3-03 — Build PDF/text evidence viewer

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add source/page label/ordinal, zoom, highlights and accessible text alternative.
3. **Verify:** Selection highlights align on zoom/high-DPI; keyboard/text workflow usable.
4. **Review/record:** run **EVF-T03/09**, attach **`evf-viewer-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T03/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E3-04 — Implement evidence reference validator

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Check source hash, parse/page/element/geometry/quote and OCR-source labels.
3. **Verify:** Nonexistent/mismatched citations rejected; normalization never fabricates region/page.
4. **Review/record:** run **EVF-T03/05**, attach **`evf-citation-validation`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T03/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E3-05 — Review source-support edge cases

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test wrong-row, image-only/OCR quotes, multi-page evidence and deleted source.
3. **Verify:** Supported quote never implies semantic truth; missing/ambiguous support visible.
4. **Review/record:** run **EVF-T05**, attach **`evf-evidence-edge-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E3-GATE — phase exit / definition of done

**Exit condition:** Coordinates/quotes resolve to correct immutable source; missing evidence cannot look valid.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E4 — Typed extraction and validation

**Accountable role:** Extraction + domain engineer. **Entry:** EVF-E3-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E4-01 — Implement schema/value types

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Decimal strings, periods/currency/scale, raw values and missing reasons.
3. **Verify:** Locale/negative/dash/zero/percentage/footnote golden tests pass without float corruption.
4. **Review/record:** run **EVF-T04**, attach **`evf-value-semantic-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E4-02 — Implement deterministic extraction baseline

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Extract selected fields/tables using structural candidates and declared rules.
3. **Verify:** Each proposal has evidence or explicit unsupported state; baseline performance recorded.
4. **Review/record:** run **EVF-T04/05**, attach **`evf-baseline-extraction`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T04/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E4-03 — Add optional schema-constrained model extractor

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Broker approved relevant content only; no tools; validate output and consent.
3. **Verify:** No unauthorized external transfer; invented claims/citations flagged or rejected.
4. **Review/record:** run **EVF-T04/05**, attach **`evf-model-extractor-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T04/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E4-04 — Implement validators/review priority

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Check types/units/periods/arithmetic/contradictions and separate risk signals from confidence.
3. **Verify:** Wrong-row/scale/period fixtures detected; no invented probability/automatic high-stakes approval.
4. **Review/record:** run **EVF-T05**, attach **`evf-validation-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E4-05 — Implement extraction version/API

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Freeze schema/parse/extractor hashes and proposal output; idempotent jobs and queries.
3. **Verify:** Re-extract never overwrites reviewed version; errors/partial results explicit.
4. **Review/record:** run **EVF-T02/04**, attach **`evf-extraction-contract-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T02/04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E4-GATE — phase exit / definition of done

**Exit condition:** Values retain units/period/source and uncertain facts route to review.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E5 — Review, correction, version diff and export

**Accountable role:** Frontend + backend. **Entry:** EVF-E4-GATE approved.

**Shared prerequisite:** FND-F4 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E5-01 — Build review queue/workspace

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement evidence-linked field/table form, warnings, raw/normalized values and next-review action.
3. **Verify:** Keyboard/source-text alternative works; source selection never silently edits value.
4. **Review/record:** run **EVF-T05/09**, attach **`evf-review-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T05/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E5-02 — Implement revisioned corrections

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Accept/correct/reject with reason, evidence changes, dependent validation and If-Match.
3. **Verify:** Conflicting edits show base/mine/current; no lost update or stale approval.
4. **Review/record:** run **EVF-T06**, attach **`evf-review-conflict-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T06 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E5-03 — Implement explicit version comparison

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Compare related source/extraction versions accounting for scale/currency/period.
3. **Verify:** Processing-only/source changes distinct; old review not copied to new evidence automatically.
4. **Review/record:** run **EVF-T02/04/06**, attach **`evf-diff-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T02/04/06 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E5-04 — Implement export readiness/manifest

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Freeze selected revision, JSON/CSV + evidence metadata, warnings and formula-safe cells.
3. **Verify:** Roundtrip preserves typed values/state; incomplete exports labeled; no permanent signed URLs.
4. **Review/record:** run **EVF-T07**, attach **`evf-export-roundtrip`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E5-05 — Validate analyst primary journey

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Five users find seeded wrong-row value, correct evidence/value and export reviewed output.
3. **Verify:** Four of five complete without help; trust confusion and accessibility blockers fixed.
4. **Review/record:** run **EVF-T06/07/09**, attach **`evf-primary-journey-study`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T06/07/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E5-GATE — phase exit / definition of done

**Exit condition:** Analysts correct errors with history and export exact reviewed versions.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E6 — Ground truth, held-out quality and hardening

**Accountable role:** QA + domain reviewers. **Entry:** EVF-E5-GATE approved.

**Shared prerequisite:** FND-F4 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E6-01 — Annotate/adjudicate corpus

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Two annotators label fields/regions/tables; resolve disagreements and record policy changes.
3. **Verify:** Gold has source/version/label provenance; final holdout not used for tuning.
4. **Review/record:** run **EVF-T10**, attach **`evf-gold-annotation-log`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E6-02 — Run held-out extraction benchmark

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Report per-field/class joint correctness, citations, coverage/abstention and costs/failures.
3. **Verify:** Targets met on declared scope or scope narrowed and fresh holdout evaluation planned.
4. **Review/record:** run **EVF-T04/05/10**, attach **`evf-quality-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T04/05/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E6-03 — Run hostile-document/security tests

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Exercise malformed PDFs, parser egress, XSS, cross-project and external model consent.
3. **Verify:** No critical accepted boundary failure; parser cannot access application secrets/network.
4. **Review/record:** run **EVF-T01/05**, attach **`evf-security-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E6-04 — Load/fault test pipeline/review/export

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Kill parser/export worker, expire lease, lose store, conflict edits and delete during processing.
3. **Verify:** Missing pages never appear reviewed; idempotency/fencing/recovery and UI states correct.
4. **Review/record:** run **EVF-T02/06/07/08**, attach **`evf-chaos-load-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T02/06/07/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E6-05 — Audit geometry/accessibility/claims

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Independent review of transforms, provenance language, risk labels and assistive-tech flow.
3. **Verify:** All geometry tests pass; no uncalibrated probability or fabricated evidence accepted.
4. **Review/record:** run **EVF-T03/09/10**, attach **`evf-qualification-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T03/09/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E6-GATE — phase exit / definition of done

**Exit condition:** Measurements are independently labeled, honest about coverage and secure.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## EVF-E7 — Private release, lifecycle and outlook

**Accountable role:** Operations + maintainer. **Entry:** EVF-E6-GATE approved.

**Shared prerequisite:** FND-F5 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] EVF-E7-01 — Package standalone release/demo

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Ship parser models/profile manifests, safe sample PDFs, keyless fixture demo and install docs.
3. **Verify:** Runs without AFR/SKB server; public demo cannot accept uploads or paid execution.
4. **Review/record:** run **EVF-T01/10**, attach **`evf-release-candidate`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T01/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E7-02 — Rehearse deletion/restore/upgrade

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Purge source/render/text/extraction/export lineage, restore backup with tombstones and migrate versions.
3. **Verify:** No deleted derivative readable after restore; reference RPO/RTO and rollback verified.
4. **Review/record:** run **EVF-T08**, attach **`evf-lifecycle-drill`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E7-03 — Run analyst alpha

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Onboard 3–5 analysts on in-scope public documents and gather correction/export friction.
3. **Verify:** Critical usability/data-integrity issues fixed; unsupported classes prominently labeled.
4. **Review/record:** run **EVF-T09/10**, attach **`evf-alpha-summary`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T09/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E7-04 — Publish benchmark/operations docs

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Ship annotation rules, rights manifest, performance environment, failure gallery and parser/security runbooks.
3. **Verify:** Independent reviewer can reproduce accessible fixture evidence and understand limits.
4. **Review/record:** run **EVF-T10**, attach **`evf-public-evidence-pack`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] EVF-E7-05 — Approve release and expansion gates

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Sign R01–R10, maintenance owners and per-format/language calibration/re-evaluation policy.
3. **Verify:** No broadened accuracy/security claim without new evidence; roadmap not represented as delivered.
4. **Review/record:** run **EVF-R01–R10**, attach **`evf-v1-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] EVF-R01–R10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### EVF-E7-GATE — phase exit / definition of done

**Exit condition:** Standalone deployment and full derivative lifecycle validated.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.
