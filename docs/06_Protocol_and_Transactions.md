# Protocol, transactions and algorithm contracts

Normative for baseline 0.2. All database operations use PostgreSQL READ COMMITTED except explicit row locking below. Every transaction derives organization/actor from verified identity, validates project membership, then executes `set_config('baseline.project_id', :project_id, true)` and organization equivalent. Never persist session settings across pooled connections. Runtime role is not owner/superuser/BYPASSRLS. Migration/lifecycle roles are not reachable from browser/executor.

## Common HTTP behavior

- JSON UTF-8; unknown request keys rejected with 422. Content-Type required for body. Request ID generated server-side and echoed. No raw content in error details/logs.
- Object IDs UUID; caller chooses neither internal object keys nor filesystem paths. IDs in paths/headers are authorization hints only.
- Every listed mutation requires UUID Idempotency-Key. Missing/invalid key=400. Transaction locks matching `(project,actor,operation,key)` via insert/unique conflict; persisted request hash + status/body. Same key/same body returns prior response; different body=409. Hash excludes cookies/CSRF and includes normalized path/body, not only payload. TTL 24h; finalize correctness also enforced by artifact state after TTL.
- All-or-nothing event batch semantics override v0.1's partial-valid-row suggestion: schema error=422 with no writes; contradictory duplicate=409 with no writes; valid new/duplicate rows=202 and receipt. SDK can split a rejected batch after explicit diagnostics, not silently discard data.
- If-Match is quoted integer revision, required on package review, plan preregister and EVF review. Missing=428 `precondition_failed`; mismatch=412. Add 428 response in OpenAPI. Body base_revision must equal If-Match, otherwise 409. Returned ETag is new quoted revision.
- Cursor order: `(created_at DESC,id DESC)` for inventories; events `(received_at ASC,id ASC)`. Cursor is HMAC-authenticated opaque JSON containing sort tuple, resource, project, filters digest and 15-minute expiry; mutation of cursor=400. No secrets/content in cursor. Reusing with another project/filter=400. Limit default50/max100.
- Upload create returns an API-relative byte PUT URL, not arbitrary external signed URL. PUT length must equal declared size; streaming server cap; SHA-256 calculated server-side. Finalize locks upload+artifact, verifies count/hash/type; mismatch=409/quarantine. Upload expires after15min; incomplete upload GC after24h. Original filename is metadata only, never storage path.
- Generic upload cap100MiB is further restricted by media and product: PDF25MiB/100pages, ZIP20MiB compressed/100MiB expanded/2000files. Request cap1MiB for event batch. Other JSON bodies2MiB; preview text2MiB. Unsupported media415; too-large413; quota429 with Retry-After for retryable capacity only.
- Only actual scheduled background work returns202. B0 fixture extraction/analysis/export may be synchronous within a 10-second request budget; otherwise implementation must introduce a versioned async API change, not silently change response shape. On capacity limitation return503. UI must not assume every create is a job.
- Not-ready result read: replay resource GET returns409 until terminal, not a fake empty success. Job GET is always available to authorized metadata readers. Product IDs for replay/parse are returned in job result_id or corresponding Parse response; do not equate job ID with replay ID.
- Download supports `Content-Disposition: attachment`, nosniff and bounded streaming. No active HTML/PDF byte serving under executable app origin; PDF UI uses authorized render/text endpoints in future adapter contract. In B0 PDF page preview can use fixture raster/SVG rendered as image; never execute embedded actions. Response cache private/no-store for sensitive content.

## Stable error mapping

| Condition | HTTP | code | Retry |
|---|---:|---|---|
| no/invalid authentication | 401 | unauthenticated | new credentials only |
| known project but wrong capability | 403 | forbidden | no |
| object absent or belongs to different project | 404 | not_found | no |
| duplicate content conflict / invalid lifecycle | 409 | conflict | correct request |
| missing If-Match | 428 | precondition_failed | fetch revision |
| stale If-Match | 412 | precondition_failed | review changes |
| malformed JSON/headers/cursor | 400 | invalid | correct request |
| invalid schema/semantic quote/field | 422 | invalid | correct request |
| disabled live/parser capability | 503 | mode_disabled | enable only after approved integration gate |
| transient storage/DB capacity outage | 503 | unavailable | bounded backoff |
| quotas/limits | 429/413 | quota/too_large | according to cause |

Do not reveal file existence, parser internals, SQL errors, OIDC token details or trace content through Problems.

## AFR transactions and replay

**Ingest:** authenticate scoped ingest key; schema + semantic validation; verify capture policy; authorize referenced artifacts in same project; begin transaction; lock/create run; compare event digest and sequence uniqueness; insert all new events; write receipt; update count/revision and materializer work outbox; commit. Identical duplicate digest acknowledges duplicate. Same ID/different content or occupied sequence/different ID rejects entire batch. Event_id uniqueness is project scoped. Late events increment run revision but never mutate existing events/cases. A run.created event may arrive after others: create recording shell; completeness tracks missing start/terminal without rewriting history.

**Case:** lock run revision; verify supplied snapshot and authorized ready artifacts; compute canonical manifest; insert immutable case; include capture limitations; checks restricted to built-in kinds and safe JSON pointer paths. Checks never deserialize Python or run arbitrary regex/scripts. JSON-pointer RFC6901 unescape `~0`,`~1`; no implicit numeric coercion. Missing pointer=check fail, invalid pointer=422 case validation.

**Replay:** validate case version/mode; create job+outbox atomically; recorded dispatcher loads frozen manifest, matches tool contract+canonical args+ordinal; returns output or error. No network/tool/model backend is linked into B0 dispatcher. Check outcomes distinguish fail/error/unscored. Visual mode does not execute checks requiring synthetic state it lacks; returns unscored with reason. Network call count0 is enforced/observed in integration tests, not trusted merely because schema says0.

**Canonicalization:** UTF-8 JSON, sorted object keys, compact separators, Unicode unchanged, arrays ordered, NaN/Infinity rejected; bool≠number in verifier, null≠missing. Digests reference this `baseline-json/1` format, not RFC8785. Float-bearing signed/digested objects should use decimal strings or integer units to avoid cross-language formatting mismatch; cross-language golden vectors required before TS hashes become authoritative. Python oracle canonicalizer is an acceptance reference, not permission to ignore JS differences.

## SKB transactions and analysis

**Inspection:** never install/run ZIP entries. Quarantined package refers to a ready same-project ZIP artifact. Inspect job enumerates safe paths/types/quotas and checks static metadata, then marks inspected or rejected. Approval requires maintainer, matching digest, current revision and inspected state; reason immutable audit. A new package is a new ID/digest.

**Suite:** freeze tasks/split/rights manifest and hash. B0 scorer IDs restricted to fixture registry compiled into trusted dispatcher. External executable scorer paths/URLs forbidden. Holdout data does not appear through suite GET; only metadata and task_count. Future candidates receive task inputs, never answer artifacts.

**Preregister:** lock plan; require draft revision; verify approved package, exact hashes and suite; freeze definition and state/hash; increment revision. Subsequent update is409. Experiment start locks plan/version and creates experiment+job+outbox in one transaction with idempotency; B0 uses preinstalled synthetic fixture trials only. Packages do not alter fixture outcomes. The report must label simulation prominently.

**Analysis:** resolve scheduled task universe from frozen plan; validate repeat/arm/outcome uniqueness; preserve attempts; trusted reconciliation picks valid authorized attempts. Missing or infra/cancelled trials=unknown, not success/zero cost. Pass=1, fail/policy_block/activation_failed=0 for declared intention-to-evaluate endpoint. Compute each arm's per-task mean across planned repeats. Complete-task delta is mean paired task difference across complete tasks; it is secondary if missingness exists. Conservative population bounds set unknown treatment success to0/baseline to1 for lower bound, reverse for upper bound, average across all planned tasks. Show complete-task N and totalN.

If fewer than10 complete distinct tasks: no CI, status insufficient; retain descriptive delta/bounds. Otherwise paired task bootstrap resamples complete task deltas with replacement, sample size=complete task count, iterations from plan100–10000, Python `random.Random(seed)` reference, 2.5/97.5 percentiles linear interpolation (type7). Cross-language equivalent must pass fixed golden vectors or use Python analysis service. Status partial if any planned task incomplete. No automatic equivalence/winner badge or p-value. Practical margin is displayed, frozen before execution. All records/hash+analysis code version stored immutably.

## EVF transactions and review

**Document:** verify ready private PDF artifact; isolated bounded file inspection before accepted. Original bytes/digest immutable. New source is new version record, never UPDATE original. Any pending deletion blocks new parse/extraction/export.

**Parse:** lock document; verify source hash and selected profile; disabled Docling integration returns503 `mode_disabled`. Fixture profile is permitted only for bundled synthetic source hashes, not arbitrary uploaded PDFs. Create Parse+job/outbox atomically. Every parse output has independent profile and source digest; incomplete pages yield partial. Parser metadata must never assert extraction accuracy.

**Geometry:** crop=(PDF x0,y0,x1,y1), PDF origin bottom-left, intrinsic rotation clockwise; normalize into displayed crop top-left. Use equations in reference oracle, transform all four bbox corners then take min/max. Reject out-of-crop/invalid geometry rather than silently clamp. Store page label separately from ordinal. Approximate fixture regions are not promoted as validated actual parser output.

**Extraction:** parse must be parsed/partial with source ownership; version is immutable eight-field baseline proposal. Deterministic extraction chooses explicit labeled line item plus period/unit evidence, not guesswork from first number. Ambiguous candidates remain missing/needs_review. Amounts use Decimal, explicit source locale and scale; ambiguous separator grouping rejected. Arithmetic crosschecks require declared complete scope; eight-field B0 does not assert full balance-sheet reconciliation.

**Review:** begin; SELECT extraction FOR UPDATE; compare If-Match/body base_revision; validate every patch against current reconstructed state; ensure key/field type and support consistency; insert review(revision+1) and increment extraction revision, but never overwrite original proposals; rerun affected validation; write audit; commit. Review content is append-only. Correcting evidence/period/unit invalidates previous acceptance for affected fields; a reject retains raw source and history.

**Export:** lock/read specific frozen revision; refuse missing revision; reconstruct from original+patches; require all eight fields have resolved review state unless allow_incomplete true. Export fixed-order fields and raw/typed/period/currency/scale/missing/support/review columns, safe CSV formula mitigation, manifest+artifact digests. CSV includes one row/field, UTF-8, RFC4180 quoting; raw export flag not in B0. Unreviewed/rejected/missing support warnings retained. Source-less claims do not become reviewed automatically.

**Delete:** authorize maintainer; transaction creates deletion marker and denies reads/new derivations immediately, cancels queued work, writes outbox; lifecycle worker walks all linked bytes/versions/export derivatives. DB rows removed in dependency order or redacted by explicit retention policy; tombstone persists outside old snapshot. Active purge target24h; backup expiry30days operator policy. Delete audit metadata contains IDs only; restored data hidden until tombstones applied.

## Database runtime tests required

Migrations are executable SQL but static parse is not a DB integration test. Required actual Postgres16 tests: apply fresh/second migration, role login separation, cross-project composite FK rejection, RLS with unset/wrong/correct project, pool context reset, append-only update denial, preregister mutation denial, concurrent review/duplicate ingestion, lease fencing, and deletion ordering. Application may not use migration owner as a shortcut. Dispatcher traverses trusted authorized project scopes, not BYPASSRLS. Missing support for any transaction is a release blocker.
