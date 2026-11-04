# Reference deployment and operational acceptance

## Capability statement

This repository supplies infrastructure **templates and tests**, not built product images or a tested production deployment. `infra/compose.yaml` references `baseline-api:UNBUILT` and `baseline-web:UNBUILT` until application tickets produce signed, digest-pinned images. PostgreSQL/Caddy digest locks were resolved from the public registry, not run here. No Docker binary was available during authoring. SQL syntax parsing is not migration execution.

## Operator inputs and prerequisites

Complete `operator-inputs.example.yaml` outside source with private hostname, OIDC issuer/client/secret references, approved project/organization memberships, TLS/DNS, encrypted storage, backup destination/key references, security contact, alert destinations and capacity. Do not commit completed credentials. Exact image digest, SBOM, application lockfiles and release commit must correspond.

Reference host: supported patched Linux amd64, 4vCPU/16GiB control plane, Docker Engine+Compose reviewed/pinned by operator, encrypted volumes, firewall only80/443 inbound, restricted administrative access. Separate no-egress parser host required before untrusted PDF processing. Future untrusted code requires separate runsc host with verified boundary. No executor access to control-plane network, DB credentials or host sockets.

## Install sequence

1. Verify release source/signatures/digests and SBOM/license/advisory dispositions; run baseline tests on Python3.12. Production images must not include test or oracle packages unnecessarily.
2. Provision encrypted volumes and external backup/key service. Create secrets directory0700 and secret files0600. Generate high-entropy DB owner credentials using operator-approved secrets tooling; no example password.
3. Configure `infra/secrets/db_owner_password`; start only DB profile with `docker compose -f infra/compose.yaml up -d db`. Confirm health and internal-only DB port. Do not expose5432 for convenience.
4. Apply migration001 then002 as migration owner using protected psql connection. Maintain a migration ledger with version/digest/applied_at; applying a changed already-applied migration must fail. Add Alembic wrapper during implementation rather than using `IF NOT EXISTS` to hide drift.
5. Provision login roles that inherit `baseline_app` and `baseline_dispatcher` with separate strong credentials; no owner privileges. Secret DSNs in `app_db_dsn`/`dispatcher_db_dsn`. Test RLS and unset/wrong context before first application data.
6. Bootstrap authorized organization/users from verified OIDC subjects through a migration/admin tool, not an unauthenticated web endpoint. Register exact callback URL and PKCE policy; set session/CSRF secrets with rotation plan.
7. Set API_IMAGE/WEB_IMAGE to approved `repository@sha256:...`; supply PUBLIC_HOST and OIDC settings. Reject UNBUILT/UNCONFIGURED, mutable tags and BASELINE_LIVE_ENABLED=true.
8. Start product profile; verify `/health/live` and `/health/ready` (implementation infrastructure endpoints, not domain OpenAPI operations) and TLS/cookie/CSP settings. No default shared credentials. Readiness is503 until DB migrations/identity/storage are usable.
9. Create disposable project and scoped test credentials; run API smoke/journey suites and complete role matrix/UI/OIDC/manual reviews. No real confidential document before parser/data-policy gates.
10. Backup/restore/load/failure/release checks below; operator launch signoff only after release gate and evidence review.

## Health, monitoring and alerts to implement

- `/health/live`:200 if process/event loop responsive; no dependency details publicly.
- `/health/ready`:200 only if required migration version matches, DB read/write probe and artifact volume check succeed, identity configuration valid; otherwise503 with safe request ID. No external model check in B0.
- Structured logs: timestamp, request ID, operation ID, project opaque ID, actor opaque ID, safe status/error, duration. No raw prompt/file content/tokens/cookies/query secrets. Cardinality-bounded metrics only.
- Metrics: request count/error/latency histograms; ingest accepted/duplicate/rejected/dropped; queue age; lease expiry/fencing rejection; artifacts bytes/purge backlog; experiment invalid/missing pairs; parser errors; review conflicts; auth denials; worker memory/disk.
- Alerts: error ratio>1% for10min at meaningful traffic; queue oldest>5min; no dispatcher heartbeat>60s; disk>80% warning/>90% critical; deletion overdue24h; repeated auth denials; backup missing>24h; unapproved egress attempt; unexplained budget usage. Thresholds calibrated against actual workload before production.

## Backup/restore implementation contract

Daily encrypted Postgres logical backup plus consistent artifact snapshot and manifest; target RPO24h/RTO4h on the reference dataset. Maintain deletion/tombstone journal independently of the old backup so restores cannot resurrect revoked data. Protect secrets and backup keys separately; test recovery with authorized key access. Retention maximum30days unless operator records stricter/different policy and updates notices.

Restore drill: isolate destination/no traffic; restore database/bytes; restore secret references (not obsolete raw credentials); replay all tombstones newer than backup; verify source/artifact digests and DB references; deny all deleted resources; run migrations/contract/journey checks; reconcile queued/leased jobs as failed/retry-safe, never automatically replay external writes; record measured recovery time/data loss; operator approves traffic. A successful pg_restore alone is not passing restoration.

## Upgrade and rollback

Freeze candidate commit/image/dependency/DB digests. Snapshot and verify restore first. Stop new dispatch, drain or expire workers, apply additive migration as owner, deploy compatible API/worker versions, run smoke and schema compatibility, resume dispatch. If failure: stop dispatch, return to compatible images only; never run old code against an incompatible changed schema. Destructive migration needs explicit later release and restore-based rollback procedure. Do not edit applied migrations in place. All live writes remain out of B0.

## Incident/cost/compromise runbooks

Sensitive leak: stop capture/export paths, revoke compromised credentials/capabilities, restrict affected artifacts, preserve safe IDs/digests not raw copies in tickets, identify recipients and scope, notify responsible operator/privacy/security authority according to applicable policy, remediate/rotate, validate deletion and publish a postmortem with reviewer approval. Do not assume downloaded exports can be revoked.

Compromised worker: stop new dispatch, isolate host, revoke collector/broker tokens, preserve safe evidence, rotate impacted secrets, rebuild from approved image and investigate access scope before replay. Parser crash alone does not justify broad host privileges. Future model cost runaway: revoke broker capabilities, stop queue admission, account in-flight calls and reconcile usage; don't pretend cancelled calls were not billed.

## What must remain blocked

- Product image/startup/install claims until application exists and is exercised.
- Migration/RLS/transaction claims until actual PostgreSQL16 tests.
- OIDC/auth/cookie/CSRF claims until real IdP/browser review.
- Parser containment/quality until actual pinned Docling/assets + dedicated host tests.
- Live task/skill execution until full harness/scorer isolation independently verified.
- Public SaaS until separate tenant, abuse, billing, data-governance and support gates.

Infrastructure as code must be expanded/reviewed for the selected hosting provider before cloud production; inventing Terraform account IDs/roles or disabling network controls is prohibited.
