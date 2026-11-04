# Agent operating contract — binding implementation instructions

## Mission

Implement the bounded v0.2 product release against the supplied contracts. Do not claim the original full v1 feature scope or production readiness merely because fixture tests pass. `docs/01_Normative_Baseline.md` fixes scope; prior pack is reference context. Follow `implementation-plan.json` in dependency order. Operator inputs are in `operator-inputs.example.yaml`; missing required production values block deployment.

## Start each session

1. Read README, this file, normative baseline, protocol/transactions, release-status, then the selected ticket and its linked v0.1 tasks.
2. Run `python -m pytest -q`; preserve current result and repository diff. If tooling cannot install or tests fail, diagnose before changing behavior.
3. Select the first ready ticket whose dependencies are complete and reviewed. Do not parallelize database/security/schema work without an explicit branch/merge plan.
4. Read relevant schemas, examples, transaction rules, UI states and security fixtures. List exact files to change and acceptance commands before coding.

## Implement one vertical slice

- Use `apps/api`, `apps/web`, `apps/dispatcher` boundaries and generated clients. Avoid placeholder endpoints returning successful example data.
- Begin with negative/acceptance cases and real persistence transaction design. Complete handler/service/repository/UI paths for the ticket, including failure states.
- No production import from `reference/` and no hardcoded fixture task success. Acceptance oracles must remain independent; public fixture data may be loaded only in explicitly labeled fixture mode.
- Enforce auth before object/schema/disabled-mode detail; intersect actor/project/API scope; set project DB context locally; never connect runtime as migration owner.
- No hidden external calls, paid APIs, new provider keys, arbitrary URL ingestion, untrusted plugin execution, remote install scripts or “temporary” auth bypass.
- Secrets remain outside source/fixtures/evidence. Don't print environments, tokens, OIDC responses or personal documents. Use synthetic/public-authorized data only.
- Preserve immutable source/event/plan/review evidence; no weakening constraints or skipping tests to make green.
- If a required behavior is ambiguous or contracts conflict, STOP that ticket, create a decision request with failing example and options, mark blocked. Do not silently improvise a security/statistics/domain assumption.

## Verification per ticket

1. Run formatter/type checker/module unit/property tests; API schema/semantic tests; real DB integration for persistent changes; UI component/keyboard tests for user-facing changes.
2. Run `python -m pytest -q` for baseline contract/oracles and `python scripts/verify_manifest.py` for fixture/contract integrity.
3. When real API exists, run `python scripts/product_acceptance.py` and `python scripts/product_journeys.py` against a disposable synthetic project. Missing environment is BLOCKED, not a pass or silent skip.
4. Run cross-project/role negative tests, logs-canary checks and failure/cancellation tests relevant to the ticket. Golden public examples are not a substitute for additional independent holdout tests.
5. Record command, exit code, runtime versions, commit/digests, fixture IDs, expected/observed results and limitations in a ticket evidence file. Never append a fabricated execution record.
6. Obtain reviewer approval before marking ticket done. A building agent cannot mark its own independent security/statistical/domain/clean-room reviews passed.

## Scope changes and dependencies

New dependency: justify need, check code/model/data licenses separately, inspect install/network behavior, pin exact version and transitive lock, run compatibility spike, update SBOM. No production lockfile with open ranges. Changing normative schema/test/SQL expectations requires reviewed ADR and regenerated artifacts. Run old/new compatibility and migration tests. Do not change held-out expectations after observing failure without versioning and review.

## Evidence and status policy

Allowed states: planned, ready, in_progress, blocked, in_review, done. Done requires actual evidence+independent review. Release statuses: not_run, failed, blocked, passed; never “passed because not applicable” without explicit release-scope approval. The release gate exits nonzero while any required item lacks passing evidence. It is a reporting guard, not proof a human approval is authentic.

At end of session output: completed ticket IDs, changed files, actual verification commands/results, remaining blockers, next ready ticket and any operator inputs needed. Preserve a small `SESSION_HANDOFF.md` with those facts. No vague “production ready” language. If the application is not implemented, say so.

## Escalation / prohibited authority

Humans must approve: public internet exposure; production credentials/OIDC/hostname; external data transfer; scope widening to live models/code; security risk acceptance; statistical interpretation; document gold-label policy; legal/data rights; incident disclosure; production launch. An agent may draft/propose these, never invent signoff.

No changing `evidence/release-status.json` for independent gates without linked reviewer evidence. Automated contract test status may be updated by CI with exact logs; other gates need the responsible owner. Manifest updates are reviewed changes, not a command to erase evidence of tampering.

## Definition of done

- [ ] All ticket-local acceptance cases, failure states and linked shared/product requirements implemented.
- [ ] Real integration evidence for persistent/network behavior; no oracle-only substitution.
- [ ] Type/contract/unit/integration/UI/security tests pass within declared scope.
- [ ] Auth, quotas, cancellation, immutable evidence, privacy and safe errors reviewed.
- [ ] Docs/locks/migrations/rollback/monitoring updated.
- [ ] No unreviewed baseline/fixture changes; independent reviewer approval linked.
- [ ] Release blockers remain accurately recorded; next-session handoff complete.
