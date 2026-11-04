# Database Migrations Documentation & Design Patches

## Schema Structure
- `001_baseline.sql`: Normative PostgreSQL 16 migration establishing schemas:
  - `core`: Shared foundation tables (`organizations`, `users`, `memberships`, `projects`, `project_roles`, `api_keys`, `artifacts`, `uploads`, `artifact_links`, `jobs`, `job_attempts`, `idempotency`, `outbox`, `budget_reservations`, `audit_events`, `deletions`).
  - `afr`: Agent Flight Recorder domain tables (`runs`, `events`, `cases`, `replays`).
  - `skb`: SkillBench domain tables (`packages`, `package_reviews`, `suites`, `hidden_answers`, `plans`, `experiments`, `trials`, `analyses`).
  - `evf`: EvidenceForge domain tables (`documents`, `parses`, `elements`, `extractions`, `reviews`, `exports`).
- `002_roles.sql`: Least-privilege PostgreSQL database roles (`migration_owner`, `app_user`).

---

## Design Patch: Scoped Idempotency (project mutations vs. project creation)

**Approved split (replaces the nullable compromise):**

1. `core.idempotency` — ordinary project-scoped mutations only:
   ```sql
   PRIMARY KEY(project_id, actor_id, route, key)
   ```
   `project_id` is NOT NULL; every record is bound to an existing project and enforced by project RLS (`project_id = current_setting('baseline.project_id', true)`).

2. `core.project_creation_idempotency` — project creation only (organization-scoped, because no project row exists yet):
   ```sql
   PRIMARY KEY(organization_id, actor_id, route, key)
   ```
   Actor and organization derive from verified identity/membership, never an untrusted header. Enforced by organization RLS (`organization_id = current_setting('baseline.organization_id', true)`).

**Semantics (both tables):**
- Same scoped key `(scope_id, actor_id, route, key)` + same normalized request → replay the original stored response (status + body).
- Same scoped key + different normalized request → 409 conflict, no writes.
- TTL 24h via `expires_at`; expired records pruned by background lifecycle tasks.
- Mutating operations acquire an advisory lock (or insert an `in_progress` record) before execution so concurrent identical requests produce one result; rollback must not strand a fabricated success.
- Authenticate and authorize before replaying a stored response. No dummy projects, no scope-free uniqueness, no RLS bypass, no weakened FKs; runtime role is never table owner/superuser/BYPASSRLS.

**Concurrency & Locking Rules (for B02 Integration):**
- Project creation: insert into `core.project_creation_idempotency` within the same transaction that creates the project, audit row, and replay record — all-or-nothing.
- Concurrent identical requests must create exactly one project; a loser replos? no — replays the winner's stored response.
- Expired records are pruned by background lifecycle tasks based on `expires_at`.
- Pooled connection context (`set_config(... true)`) must be reset after each transaction and never persist across pool reuse.
