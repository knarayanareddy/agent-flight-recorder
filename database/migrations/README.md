# Database Migrations Documentation & Design Patches

## Schema Structure
- `001_baseline.sql`: Normative PostgreSQL 16 migration establishing schemas:
  - `core`: Shared foundation tables (`organizations`, `users`, `memberships`, `projects`, `project_roles`, `api_keys`, `artifacts`, `uploads`, `artifact_links`, `jobs`, `job_attempts`, `idempotency`, `outbox`, `budget_reservations`, `audit_events`, `deletions`).
  - `afr`: Agent Flight Recorder domain tables (`runs`, `events`, `cases`, `replays`).
  - `skb`: SkillBench domain tables (`packages`, `package_reviews`, `suites`, `hidden_answers`, `plans`, `experiments`, `trials`, `analyses`).
  - `evf`: EvidenceForge domain tables (`documents`, `parses`, `elements`, `extractions`, `reviews`, `exports`).
- `002_roles.sql`: Least-privilege PostgreSQL database roles (`migration_owner`, `app_user`).

---

## Design Patch: Organization-Scoped Project Creation Idempotency
- **Table**: `core.idempotency`
- **Original Schema Constraint**:
  In early scaffold definitions, `core.idempotency` declared `project_id uuid NOT NULL REFERENCES core.projects`.
- **Architectural Gap**:
  Project creation (`POST /api/v1/projects`) is an organization-level operation executed by Organization Admins *before* any project workspace exists. A foreign key constraint requiring a non-null `project_id` on all idempotency records prevented registering or enforcing idempotency locks during project creation requests.
- **Reviewed Design Correction**:
  ```sql
  CREATE TABLE core.idempotency(
      organization_id uuid REFERENCES core.organizations,
      project_id uuid REFERENCES core.projects,
      actor_id uuid NOT NULL,
      route text NOT NULL,
      key uuid NOT NULL,
      request_sha256 text NOT NULL,
      response_status integer NOT NULL,
      response_body jsonb NOT NULL,
      expires_at timestamptz NOT NULL,
      PRIMARY KEY(actor_id, route, key),
      CHECK(project_id IS NOT NULL OR organization_id IS NOT NULL)
  );
  ```
- **Concurrency & Locking Rules (for B02 Integration)**:
  - Idempotency records for project creation are keyed by `(actor_id, route, key)` scoped to `organization_id`.
  - Mutating operations must acquire an advisory lock or insert in `in_progress` state prior to execution to prevent duplicate concurrent project fabrication.
  - Expired records are pruned by background lifecycle tasks based on `expires_at`.
