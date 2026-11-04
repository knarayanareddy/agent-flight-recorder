# Agent-executable implementation baseline — v0.2

**Agent Flight Recorder · SkillBench · EvidenceForge**

A versioned implementation contract, synthetic acceptance fixtures, independent algorithm oracles, verification tooling, deployment templates and agent work protocol. **Not three implemented products and not production-ready software.**

## What changed from the original specification pack

The original prose pack is preserved as `prior-design-pack/` in the complete download. This baseline narrows the first release so an implementing agent has fewer undefined choices. It provides:

- **48 JSON Schemas** and positive/negative structural examples.
- **48 OpenAPI operations**, endpoint permission policy and transaction/error rules.
- **Two PostgreSQL migrations**, role/RLS/immutability design and lease query examples.
- **12 UI screen/workflow contracts**, including states, fields, actions and accessibility requirements.
- **Runnable deterministic acceptance oracles/tests** for schema, deduplication, archive safety, replay matching, statistics, geometry, numeric normalization and evidence validation.
- **Actual-API smoke and authenticated journey runners** that refuse to silently pass when no implementation exists.
- **Agent operating rules, a 16-ticket build queue and fail-closed production gate**.
- Registry-resolved dependency/image candidates, exact baseline-tool versions, operator input template, deployment/restore/rollback/incident specifications and an evidence ledger.

## Quick start: verify the baseline

Run from this directory in an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-baseline.txt
python -m pytest -q
python scripts/verify_manifest.py
python scripts/consumer_trial.py
python scripts/release_gate.py
```

The last command **must exit1** while production evidence is incomplete. That is correct fail-closed behavior, not a reason to weaken the gate. Tests were executed in the authoring Python3.13 environment; Python3.12 is the application target and its CI/runtime verification remains required. No application server starts with these commands.

Available fixtures are synthetic, contain no personal data and do not need paid model APIs. The PDF/region fixture is authored metadata, not actual Docling output or a financial corpus benchmark. The SKB trial fixture is simulation, not measured skill benefit.

## Give an implementing agent these files

1. `AGENTS.md` — work protocol and stopping rules.
2. `docs/01_Normative_Baseline.md` — fixed bounded release, decisions and semantic constraints.
3. `docs/02_Protocol_and_Transactions.md` — exact behavior, concurrency, errors and algorithms.
4. `contracts/openapi.yaml`, `contracts/schemas/`, `database/migrations/`, `contracts/ui-workflows.yaml`.
5. `docs/04_Acceptance_and_Implementation_Queue.md` and `implementation-plan.json`.
6. `docs/03_Deployment_and_Operations.md`, `operator-inputs.example.yaml` and `evidence/release-status.json`.

The agent begins at the first ready implementation ticket and records evidence per slice. It must not import reference oracles into production code or replace product behavior with successful example responses. Contracts are a binding target; unresolved contradictions block a ticket and require a reviewed change, not improvisation.

## Test a real implementation later

```bash
export BASELINE_URL=https://your-private-test-host
python scripts/product_acceptance.py
# For authenticated flows, use only an explicitly disposable synthetic project:
export BASELINE_TEST_PROJECT=<project-uuid>
export BASELINE_TEST_KEY=<scoped-test-key-from-secret-store>
export BASELINE_TEST_CONFIRM=synthetic_disposable_project
python scripts/product_journeys.py
```

Do not paste real keys into source, evidence, chat, shell history or CI logs. Inject secrets through approved tooling. The scripts require an actual built product API. Their limited passing result does not replace browser, full authorization, DB, parser, OIDC, operations or independent security tests.

## Eight requested deliverables: honest status

| Deliverable | Included now | Remaining release work |
|---|---|---|
| Resolve architecture through spikes | B0 decisions fixed; exact dependency candidates; working deterministic ingestion/statistics/geometry/evidence spikes | Actual Inspect/SkillEvaluator/Docling/IdP/runsc compatibility and security validation not run |
| Freeze bounded v1 | Explicit B0 scope, disabled capabilities, future B1 gates, precedence | Product-owner approval and implementation; full original v1 remains broader |
| Formal contracts | JSON Schema/OpenAPI/SQL/UI/state/transaction/permission contracts | Real application conformance, database concurrency/RLS testing, reviewed transitive locks |
| Runnable fixtures/tests | Local baseline suite + synthetic PDF/trials + actual-API runners | Real product, browser/role matrix/hidden data/domain fixtures and adversarial integration execution |
| Production reference deployment | Digest candidates, fail-closed Compose/Caddy/policies, lifecycle runbooks | Built images, real host/IdP/parser, backup/restore/load/upgrade and isolated executor evidence |
| Agent operating contract | AGENTS.md + dependency-ordered tickets, DoD/evidence/stopping rules | Enforce in actual implementation/review workflow |
| Clean-room implementation trial | Contract-consumer subprocess rehearsal and exact separate-agent trial procedure | **Not run:** no independent agent implementation session available |
| Independent release verification | Explicit evidence checklist and nonzero fail-closed gate | **Not run:** independent security/statistical/domain/ops review and operator launch approval |

This upgrades the pack into a useful executable **baseline**, not proof that the production deliverables themselves have already been completed. `evidence/VALIDATION_REPORT.md` records only observed verification. All other gates remain accurate and visible.

## Authority and limitations

Formal artifacts reduce routine decisions; they cannot invent production credentials, legal/data rights, security risk acceptance or independent human judgment. Operator inputs are legitimate required configuration. Source-available dependency/model terms must be checked for exact shipped versions. Public fixture tests can be gamed; independent hidden acceptance cases and code review remain mandatory. A local hash manifest checks consistency, not publisher authenticity. Do not advertise safety, accuracy or conformance without corresponding measured/reviewed evidence.
