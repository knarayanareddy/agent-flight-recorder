# SkillBench — product and technical design

**ID:** SKB · **Version:** 0.1 proposed · **Date:** 2026-11-03. Inherits the shared foundation. No evaluation or certification claims have been validated yet.

## 1. Charter, positioning, and build-versus-integrate gate

**Primary user:** skill maintainer or engineering lead deciding whether a skill improves a bounded set of agent tasks. Secondary: researcher comparing harnesses and reviewers investigating security/compatibility findings.

**Job:** “Given this exact skill version, tell me where it helps, where it harms, what it costs, and what evidence supports that conclusion.”

NVIDIA SkillEvaluator already documents static validation, overlap/deduplication, security scanning and live with/without-skill comparisons. It also describes CI integration and a sandbox-backed execution layer. A dashboard wrapping those same features is not automatically differentiated. Inspect provides composable tasks, solvers, scorers and logs; Promptfoo provides assertions, model comparisons and security testing. SkillBench must justify itself as a **controlled experiment and evidence workbench**, preferably integrating existing engines.

### Mandatory discovery spike

Run the same 10 synthetic tasks through pinned SkillEvaluator and Inspect configurations. Measure adapter work, result completeness, task control, licensing and isolation needs. Record ADR-SKB-01 selecting one primary backend; do not support two full live execution engines in v1. Default design hypothesis: use Inspect as task execution backend and import SkillEvaluator static/live reports where its versioned export contract permits; this remains a spike decision, not an assertion that a stable compatible export exists. If SkillEvaluator already satisfies 80% of the required journeys and lacks only presentation, propose contributing upstream or shipping a focused evidence/review extension. Do not maintain a second engine just to preserve the project name.

### V1 scope

Required: immutable skill intake, package/source provenance, safe validation without executing a package, static finding import, controlled experiment planning, baseline/treatment paired execution, holdout separation, budget admission, frozen result manifests, task-level comparisons, statistical uncertainty, evidence review, CI report/export, and one live harness adapter.

Deferred: public universal leaderboard, automated certification, marketplace, ranking unrelated domains with one score, multi-agent evolutionary skill search, executing arbitrary public submissions, and claims that a scan proves a package safe. Cross-harness comparison is a v1.1 expansion after the first harness is validated; schema supports it now.

## 2. Requirements and acceptance mapping

| ID | Requirement | Acceptance evidence | Phase |
|---|---|---|---|
| SKB-R01 | safe immutable skill/source intake | SKB-T01 archive/path/script/SSRF corpus | S1–S2 |
| SKB-R02 | immutable preregistered experiment | SKB-T02 hash/revision mutation checks | S3 |
| SKB-R03 | paired baseline/treatment, contamination controls | SKB-T03 execution isolation and environment equality | S4 |
| SKB-R04 | budgets, cancellation, retry accounting | SKB-T04 runaway/429/crash simulation | S4 |
| SKB-R05 | distinguish quality, security and runtime errors | SKB-T05 known synthetic cases | S2/S5 |
| SKB-R06 | defensible statistics and no false certainty | SKB-T06 simulation tests with known deltas | S5 |
| SKB-R07 | trusted scoring outside candidate reach | SKB-T07 hidden answers inaccessible | S4/S6 |
| SKB-R08 | accessible evidence-first results | SKB-T08 primary journey and keyboard tests | S3/S5 |
| SKB-R09 | versioned machine-readable CI evidence | SKB-T09 roundtrip, stale/tampered results | S6 |
| SKB-R10 | reproducible private release | SKB-T10 restore, deletion, upgrade drills | S7 |

## 3. Domain model and experimental method

### Objects

`skill_package`: immutable content digest; original repository/commit or upload; author-supplied metadata; media/entry inventory; license declaration; approval state. Separate source authenticity from integrity. A known Git commit does not establish that the author is trusted.

`task_suite_version`: tasks, fixtures, categories, inclusion criteria, license/data provenance, development/validation/holdout split IDs, scorer references and their access class. Candidate-visible prompts are separate from hidden answers/scorers. Store hidden evaluation artifacts with separate access checks and job capabilities.

`experiment_plan_version`: skill digest(s), suite digest, model/provider identity, harness/image version, tool policy, budget, repetitions, randomization method, seed where supported, primary metric, practical-effect threshold, missing-data rule and planned analysis. Drafts editable; preregistered plans immutable; changes produce a new version.

`trial_pair`: task ID × repeat × blocking factors; baseline and treatment child runs; allocation order. `trial_run`: environment, attempt history, capture refs, verified outcomes, usage, errors. `analysis_version`: input set hash, code revision, exclusions, statistical procedure and generated report. `finding`: source, severity, confidence, evidence, applicability, reviewer disposition and engine version. Static security findings remain distinct from runtime violations and task quality.

Tables: `skb_packages`, `skb_package_entries`, `skb_findings`, `skb_suite_versions`, `skb_tasks`, `skb_hidden_refs`, `skb_plan_versions`, `skb_trial_pairs`, `skb_trials`, `skb_analysis_versions`, `skb_review_decisions`, `skb_release_reports`.

### Package state machine

`received -> quarantined -> inspected -> eligible_for_review -> approved_for_selected_profile | rejected`. New package version resets approval. License unknown or scanner unavailable is visible; scanner absence cannot become a clean pass. Live execution requires a project maintainer's bounded approval and a supported hardened executor. Inspecting text never grants execution permission.

### Experiment lifecycle

`draft -> validated -> preregistered -> queued -> running -> completed | stopped | failed`; analysis has its own `pending/valid/invalid/partial` status. A completed job is not a statistically meaningful result. No mutation after preregistration; stop/restart means new plan or explicit continuation attempt with full lineage.

### Controlled comparison

1. Choose a domain before selecting favorable tasks. Freeze the suite and primary metric.
2. Define baseline precisely: same agent/harness/tool capabilities, absent the skill; do not change model settings between arms.
3. Define treatment installation and activation. Record whether the skill actually loaded; failure to load is a first-class compatibility result, not evidence it is useless when loaded.
4. Randomize baseline/treatment order within blocks to reduce provider-time and warm-cache effects. Start each arm with clean workspace/memory/cache and identical fixture state. Freeze task data; never let one arm read the other's outputs.
5. Run at least 3 repeats for exploratory work; default 5 if affordable. This is not a power calculation. Estimate required task/repetition count from pilot variance and the minimum meaningful effect before making comparative claims.
6. Validate outcome from trusted external state/tests, not from the candidate's report of success. Score collateral changes separately.
7. Record all attempts including retries. Predeclare infrastructure retry rules; semantic failure is never retried simply to improve the score. An infrastructure-retried pair is labeled.
8. Analyze at task level, accounting for repeats being correlated. Preserve paired structure and category breakdowns.
9. Freeze analysis inputs and methods. Changes to exclusions, metrics or scorers are a new analysis version with explanation.
10. Publish evidence and limitations. A domain-limited result does not imply universal skill quality.

### Statistics contract

Primary measure proposal: difference in verified task success probability between treatment and baseline, averaged by task rather than weighting tasks with more successful repeats. Also report absolute arm success rates, observed safety violations, compatibility/load failures, cost per verified success, latency and token distributions. Do not fold security and quality into a single weighted star rating.

Use task-clustered paired bootstrap intervals for quality delta when enough distinct tasks exist; test implementation against analytical/simple simulated cases. With tiny suites show descriptive results and a clear insufficient-evidence warning. For binary paired task summaries, a documented paired test may supplement estimates, but no automatic p-value winner badge. Multiplicity: predeclare one primary comparison; label other comparisons exploratory or apply a documented correction. Report effect sizes and intervals before significance language.

Default product interpretation uses a user-declared practical margin `m` (for example 0.05 absolute success probability, illustrative only): interval wholly above +m = evidence of meaningful improvement; wholly below -m = evidence of meaningful degradation; wholly within [-m,+m] = evidence consistent with practical equivalence under the chosen procedure; overlapping regions = inconclusive. Equivalence language requires a method justified for equivalence, not merely a non-significant test. Until that method is reviewed, display interval + margin without automated equivalence claims. No per-plan change of m after seeing results.

Missing data: task failures count as failures; policy blocks are separately counted and analyzed according to declared estimand; infrastructure invalids are shown with denominators, conservative bounds, and a paired-complete analysis labeled secondary if exclusions occur. Never silently drop failed baseline runs or report unknown cost as free. Stopped early for cost cannot be presented as a full planned experiment. Early efficacy stopping is out of scope in v1.

LLM judges: optional, blinded to arm/skill identity where possible, randomized answer order, rubric/version pinned, calibrated against independent human labels, prompt-injection tests, disagreements visible. Hidden deterministic tests take precedence where suitable. A judge is not an independent source merely because it is a second API call. Record judge cost separately and in total experiment cost.

## 4. UI/UX specification

Navigation: Packages · Suites · Experiments · Reviews · Reports · Settings. Default landing page shows recent experiments, incomplete prerequisites, budgets and outstanding reviews—not a leaderboard.

### Package review

Two panels: file tree and inert file viewer; findings drawer with source/severity/status; provenance/license banner. No execution of preview files, no active HTML, no automatic dependency install. Explain “no findings,” “not scanned,” and “scan failed” distinctly. Reviewer can mark finding confirmed, false positive, accepted limitation, or needs investigation, with reason. Approval is tied to package digest and execution profile.

### Experiment wizard

1. Select approved package and baseline policy.
2. Select suite version and split; never show hidden answers to execution operators by default.
3. Select supported model/harness/tool profile.
4. Choose repetitions, cost/token/time caps and maximum concurrency.
5. Select primary metric, practical margin, missing-data rules and analysis method.
6. Show estimated number of calls/jobs, provider destinations, data transfer and cost uncertainty.
7. Validate reproducibility and security readiness; fix blocking issues.
8. Preregister immutable plan and explicitly approve dispatch.

Never let “Run” silently rewrite a previous plan. Draft loss is prevented with server autosave and revision conflicts. Changing a provider endpoint or skill digest invalidates previous approval.

### Experiment monitoring

Progress is trial pairs scheduled/running/completed/invalid; no fake time remaining. Show spend reserved, observed and estimated; safe cancel action; status by failure category; provider outage banner. Interim descriptive scores are marked provisional and cannot be exported as final. Pause stops new dispatch; in-flight work may finish. Resume preserves plan and records changed availability; material environment changes require a new experiment.

### Results layout

```text
Plan v3 / skill digest / suite / model / harness / COMPLETE or PARTIAL
Primary effect: +delta [interval] · practical margin · N distinct tasks
Quality | Safety | Compatibility | Cost | Evidence | Analysis notes
-----------------------------------------------------------------
Per-task paired outcomes | repeats/variance | failures and exclusions
-----------------------------------------------------------------
Selected trial -> AFR trace evidence / verifier output / environment
```

Top-level result includes denominators, task categories, load failures, exact config hashes and analysis revision. Filters cannot silently redefine headline metrics: show “filtered view” and keep frozen report link. Drilldown reveals evidence and scorer version. Cross-experiment comparison warns on different suites/harness/models.

Accessibility: table alternative for charts; interval values readable as text; keyboard-select task and open trace; no color-only winner. At mobile width reading results and approvals works; complex plan editing can be a desktop-oriented flow with explicit limitations.

States: package quarantined, unsupported format, missing license, engine absent, scanner failed, no compatible harness, suite empty, unbalanced pairs, provider drift, budget estimate unknown, paused, cancellation pending, invalid analysis, insufficient sample, missing hidden verifier, stale report, content denied. All state changes have a defined recovery path.

## 5. Execution architecture and interfaces

Control plane schedules pairs, trusted dispatcher creates isolated arm environments, adapter invokes selected engine, collector returns outputs, trusted scorer evaluates artifacts in a **separate isolation context**, analysis service aggregates validated records. Candidate cannot access scorer process, hidden answer artifacts, control-plane identity, competing arm state or broad model credentials. Engine-generated orchestration code/plugins execute inside the untrusted boundary too.

No assumption that Docker or an engine sandbox automatically contains task-loading Python. Pinned backend deployment preflight tests actual filesystem/network permissions and fails closed. Model calls go through broker with per-trial limits; package instructions cannot change broker policy. Input fixtures mount read-only; writable workspace is disposable; scratch data erased after retention period. Never share package-managed virtual environments across arms.

APIs proposed:

- `POST /api/v1/skb/packages/uploads`, `POST /packages/{id}:finalize`, `GET /packages/{id}/entries`, `POST /packages/{id}/reviews`.
- `POST /suite-versions`, `GET /suite-versions/{id}` (role-filtered hidden refs), `POST /plan-drafts`, `POST /plan-drafts/{id}:preregister`.
- `POST /experiments` with plan hash/idempotency key; `GET /experiments/{id}`, `POST /experiments/{id}:pause|cancel`, `GET /experiments/{id}/trials`.
- `POST /experiments/{id}/analyses`, `GET /analyses/{id}`, `POST /analyses/{id}/reports`.

All paths above share `/api/v1/skb` unless written in full. A plugin adapter contract includes capabilities, input manifest, package activation evidence, result enum, trace references, usage provenance and version metadata. Importers must reject mismatched task/plan hashes and mark missing fields incomplete rather than infer them.

CLI design: `skb package inspect`, `skb plan validate`, `skb run`, `skb report`, `skb ci`. Safe inspect cannot execute skill scripts or remote templates. Config YAML uses a safe loader without object tags/custom code evaluation; executable task plugins are separately registered and isolated. CI result badge is a static report tied to exact commit/suite/engine versions, not a reusable “certified safe” seal. Stale or incomplete reports show warning. PR comment publisher has narrow permissions, runs separately from untrusted tests, and never evaluates artifacts as code.

## 6. Security-specific controls

- Archive extraction rejects traversal, absolute paths, symlinks, hardlinks, device entries, huge expansion ratios and duplicate normalized paths. V1 intake cap proposal: 20 MiB compressed, 100 MiB expanded, 2,000 files, 2 MiB per text preview; adjustable by operator, tested at boundaries.
- Repository imports restricted to approved public hosts/revisions, no arbitrary clone protocols or submodule execution; fetch by trusted service with no user credential forwarding; resolve commit before approval. Local paths are never accepted from remote callers.
- No install hooks, shell profiles, package manager postinstall, remote includes or skill scripts run during inspection.
- Scanners have their own risk/egress profile; scanner execution success is required for any “scanned” label. Scanners may miss instruction-level risks.
- Artifact text treated as untrusted when LLM judges consume it. Judges receive no action capabilities and no hidden secrets unnecessary for scoring.
- Budget and concurrency reservations are transactional across both arms. Token/call caps include grading and retries. Trial cancellation revokes broker capabilities; already completed sends cannot be undone.
- Test contamination: candidate cannot modify hidden scorer, runner image, baseline state, or final analysis input list. Verify output digest and source trial ID; no self-reported pass fields accepted.
- Public sample results use synthetic packages or author-approved material. Package licenses and suite licenses are separate rights.

## 7. Evaluation and operational acceptance

Golden suite: 40 distinct tasks in one measurable domain, with at least 5 deliberately helpful, 5 harmful/conflicting, and 5 no-op/activation-failing skill cases (categories can share tasks but identities must be declared). Development/validation/holdout split fixed before tuning. Final holdout is inaccessible to skill authors during the experiment; a downloadable OSS suite is not secret forever, so public and operator-private holdouts are explicitly distinguished.

Statistics tests use simulated zero-effect, positive/negative-effect, correlated repeats, missing arms, unequal repeats, degenerate samples, all-success/all-failure and heavy-tailed cost cases. Accept numerical tolerance against reference implementations and deterministic seeds. Any statistical interpretation rule must be reviewed by a competent statistical reviewer before automatic conclusions are enabled.

Performance targets: plan validation <2 seconds for 1k trials excluding remote checks; results page first useful render <2 seconds for 1k records on declared hardware; 20 concurrent users under shared SLO. Execution throughput depends on providers/executor and is benchmarked rather than promised. Repeated plan submission creates one logical experiment; stale completion cannot overwrite a newer terminal attempt. Cost reconciliation shows unexplained provider usage as an anomaly.

Operational signals: pair imbalance, arm load failures, infrastructure invalid rate, score/judge errors, denied egress, lease churn, plan/manifest mismatches, estimate-versus-observed cost and analysis revisions. Restore must preserve preregistration and immutable result versions. Deleting a package/source marks dependent reports unavailable or redacted as appropriate without inventing a new result.

## 8. Outlook and gates

V0.1 safe inspect/import and fixture reports; V0.2 private controlled paired experiments; V1 statistically reviewed evidence release. V1.1 a second harness, explicit instruction/activation differences and comparability studies. Later: interaction/factorial experiments for multiple skills, task-distribution drift, blinded external reviews, signed author submissions and reproducibility challenges. These require additional power/cost planning and trust policy. Public leaderboard only after gaming controls, appeals, independent reruns, disclosure rules and ongoing dataset maintenance have owners.

**Product DoD**

- [ ] Build-versus-integrate ADR includes an actual comparison spike, not marketing summaries.
- [ ] All SKB-R01–R10 acceptance evidence exists; no hidden-answer access by candidate.
- [ ] Static inspection never executes package-controlled code.
- [ ] Baseline/treatment changes limited to declared intervention; all residual differences disclosed.
- [ ] Incomplete/failed scans and experiments cannot receive clean-pass badges.
- [ ] Headline results retain denominators, exclusions, intervals, practical margin and version hashes.
- [ ] Paid/adversarial execution is disabled unless isolation, authorization, and budgets pass preflight.
- [ ] Statistical reviewer, security reviewer and product owner sign the release evidence.



---

# Implementation phase runbook

All items below are **planned and unchecked**. Each task inherits the global definition of done. Task order is conservative: the previous task and prior phase gate must pass before proceeding; explicit independent branches may be parallelized by an approved planning change. Evidence paths are proposed repository artifacts, not existing implementation evidence.


## SKB-S0 — Validate need and choose engine

**Accountable role:** Product + evaluation lead. **Entry:** Project baseline accepted; assign owner and reviewers.

**Shared prerequisite:** FND-F0 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S0-01 — Interview skill maintainers

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Collect five skill evaluation workflows and tasks they cannot assess today.
3. **Verify:** Needs distinguish evidence/experiment problems from demand for another generic leaderboard.
4. **Review/record:** run **discovery review**, attach **`skb-discovery.md`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] discovery review passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S0-02 — Run SkillEvaluator/Inspect comparison

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Execute same ten synthetic tasks in pinned backends and review licenses/trust boundaries.
3. **Verify:** Observed compatibility, outputs, setup cost and 80%-coverage integrate/upstream gate recorded.
4. **Review/record:** run **SKB-R01/03**, attach **`skb-engine-ADR`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-R01/03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S0-03 — Define domain and gold suite

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Select measurable task domain, split rules, hidden-answer ownership and helpful/harmful/no-op cases.
3. **Verify:** Suite plan has inclusion criteria and leakage controls before skill tuning.
4. **Review/record:** run **SKB-T03/07**, attach **`skb-suite-plan`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T03/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S0-04 — Prototype plan/results/review UX

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test package review, preregistration, spend preview and uncertain result interpretations.
3. **Verify:** Users understand static findings differ from task benefit and safety certification.
4. **Review/record:** run **SKB-T08**, attach **`skb-prototype-study`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S0-05 — Freeze statistical/security plan

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Approve primary metric, practical margin policy, missing-data rules, reviewers and release boundaries.
3. **Verify:** No auto statistical claims before method review; untrusted live mode gated.
4. **Review/record:** run **SKB-T06/07**, attach **`skb-analysis-threat-baseline`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T06/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S0-GATE — phase exit / definition of done

**Exit condition:** Build-versus-integrate and experiment method approved before full implementation.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S1 — Safe packages and provenance

**Accountable role:** Backend + security. **Entry:** SKB-S0-GATE approved.

**Shared prerequisite:** FND-F2 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S1-01 — Implement bounded upload intake

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Create quarantine, digest/version records and safe archive enumeration.
3. **Verify:** Traversal/symlink/device/expansion/duplicate-path/oversize cases rejected.
4. **Review/record:** run **SKB-T01**, attach **`skb-intake-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S1-02 — Implement approved repository fetch

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Fetch configured host/revision through trusted service without credentials/submodule execution.
3. **Verify:** Arbitrary protocols/SSRF/local paths blocked; resolved commit stored.
4. **Review/record:** run **SKB-T01**, attach **`skb-repo-fetch-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S1-03 — Implement package manifest and preview

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Store entries/license/source and render text inertly with size limits.
3. **Verify:** Unknown license and unsupported binary/active content are visible, never silently trusted.
4. **Review/record:** run **SKB-T01/08**, attach **`skb-package-ui-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S1-04 — Implement digest-bound approval

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Maintainer approves selected execution profile; new content/version resets review.
3. **Verify:** Changed digest/profile invalidates approval; wrong role cannot promote package.
4. **Review/record:** run **SKB-T01/07**, attach **`skb-approval-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S1-05 — Validate parser-only inspection

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Instrument network/process/file activity during inspect on hostile packages.
3. **Verify:** No install hook/script/template executes; no unauthorized egress or host write occurs.
4. **Review/record:** run **SKB-T01**, attach **`skb-static-intake-security-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S1-GATE — phase exit / definition of done

**Exit condition:** Inspection cannot execute package-controlled code; approved versions immutable.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S2 — Static checks and engine result contracts

**Accountable role:** Evaluation engineer. **Entry:** SKB-S1-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S2-01 — Implement schema/format checks

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Validate skill metadata/references and detect unsupported activation requirements.
3. **Verify:** Malformed skill returns bounded findings without executing helper code.
4. **Review/record:** run **SKB-T01/05**, attach **`skb-format-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S2-02 — Integrate selected scanner/importer

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Use pinned approved scanner or import signed-off results with source/version/schema checks.
3. **Verify:** Unavailable/failed/not-run states differ; imported result bound to exact package.
4. **Review/record:** run **SKB-T05/09**, attach **`skb-scan-adapter`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T05/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S2-03 — Build finding review model

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Record source/severity/evidence/disposition/reason and preserve original findings.
3. **Verify:** False-positive/rejected/accepted-risk decisions auditable and do not rewrite scan output.
4. **Review/record:** run **SKB-T05**, attach **`skb-finding-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S2-04 — Define execution adapter capability schema

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Map selected engine tasks, activation evidence, outcome/error enums and usage/trace metadata.
3. **Verify:** Missing engine fields marked incomplete; unsupported capability rejected before dispatch.
4. **Review/record:** run **SKB-T03/05**, attach **`skb-adapter-contract`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T03/05 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S2-05 — Build package-review UI

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Implement file tree, inert preview, finding filters and approval with known limitations.
3. **Verify:** Keyboard review works; no safety seal generated from static checks.
4. **Review/record:** run **SKB-T08**, attach **`skb-package-review-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S2-GATE — phase exit / definition of done

**Exit condition:** Findings are attributable and absent/failed scans cannot masquerade as clean.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S3 — Suites and preregistered experiment planning

**Accountable role:** Backend + frontend. **Entry:** SKB-S2-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S3-01 — Implement suite/version and hidden data

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Store task licenses/splits/fixtures; separate candidate prompts from hidden answers/scorers.
3. **Verify:** Operator/candidate cannot read hidden refs without dedicated permission; split frozen.
4. **Review/record:** run **SKB-T02/07**, attach **`skb-suite-contract-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T02/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S3-02 — Implement plan draft/version model

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Define baseline/treatment/harness/model/repeats/metric/margin/missingness configuration.
3. **Verify:** Draft edits use concurrency control; incompatible/empty plans rejected.
4. **Review/record:** run **SKB-T02**, attach **`skb-plan-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T02 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S3-03 — Implement budget/readiness preflight

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Estimate trials/calls with uncertainty and check engine/isolation/approval/provider consent.
3. **Verify:** Missing price/approval/engine produces explicit blocker or honest unknown estimate.
4. **Review/record:** run **SKB-T04**, attach **`skb-preflight-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S3-04 — Build plan wizard and preregistration

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Provide step validation, autosave, final plan/hash preview and immutable submit.
3. **Verify:** Changing package/provider/settings requires new plan/approval; repeated submit idempotent.
4. **Review/record:** run **SKB-T02/08**, attach **`skb-wizard-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T02/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S3-05 — Validate usability and leakage

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Test task planning and hidden-answer paths with pilot users and security checks.
3. **Verify:** Four of five complete valid plan unaided; hidden data absent in browser/exports/events.
4. **Review/record:** run **SKB-T07/08**, attach **`skb-plan-study`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T07/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S3-GATE — phase exit / definition of done

**Exit condition:** Validated immutable plans contain task splits, limits and analysis assumptions.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S4 — Paired execution and trusted scoring

**Accountable role:** Runtime + security. **Entry:** SKB-S3-GATE approved.

**Shared prerequisite:** FND-F3 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S4-01 — Implement paired scheduler/randomization

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Block by task/repeat, randomize arm order and create fresh identical environments.
3. **Verify:** Baseline/treatment diff limited to declared skill activation; no memory/cache crossover.
4. **Review/record:** run **SKB-T03**, attach **`skb-pair-oracle-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T03 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S4-02 — Run full harness inside executor

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Execute untrusted task/skill/plugin loading within hardened boundary and broker calls.
3. **Verify:** No control DB/host/other-arm/scorer access; activation outcome captured.
4. **Review/record:** run **SKB-T03/07**, attach **`skb-isolation-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T03/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S4-03 — Implement independent outcome collector/scorer

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Verify result digests and score in separate trusted/isolation context with hidden checks.
3. **Verify:** Candidate cannot self-report pass, edit tests or forge another trial output.
4. **Review/record:** run **SKB-T05/07**, attach **`skb-scorer-security-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T05/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S4-04 — Enforce retries/limits/cancellation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Reserve pair/grading budgets, retry only infrastructure-safe work and record all attempts.
3. **Verify:** Runaway/429/crash/cancel cannot hide cost or turn semantic failure into selective rerun.
4. **Review/record:** run **SKB-T04**, attach **`skb-runtime-fault-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T04 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S4-05 — Build experiment monitor

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Show pair completion/imbalance, provisional state, observed/reserved spend and pause/cancel.
3. **Verify:** Partial/stopped/provider-drift runs cannot appear final; cancel pending honest.
4. **Review/record:** run **SKB-T04/08**, attach **`skb-monitor-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T04/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S4-GATE — phase exit / definition of done

**Exit condition:** Both arms isolated, intervention controlled, hidden scorer protected and spend bounded.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S5 — Statistical analysis and inspectable results

**Accountable role:** Evaluation + statistical reviewer. **Entry:** SKB-S4-GATE approved.

**Shared prerequisite:** FND-F4 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S5-01 — Implement outcome taxonomy/analysis inputs

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Freeze input result set, exclusions and primary denominator; keep quality/safety/error separate.
3. **Verify:** Missing arms/scans/usage remain visible and cannot be silently excluded.
4. **Review/record:** run **SKB-T05/06**, attach **`skb-analysis-input-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T05/06 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S5-02 — Implement paired task-level estimates

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Add cluster-aware intervals, practical margin display, per-category breakdown and cost/success.
3. **Verify:** Zero/positive/negative/correlated/degenerate simulation cases match reference within tolerance.
4. **Review/record:** run **SKB-T06**, attach **`skb-statistical-validation`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T06 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S5-03 — Validate optional judge pipeline

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Blind arm identity, pin rubric/model, calibrate with human labels and sandbox untrusted text.
3. **Verify:** Disagreements/order effects/injection failures documented; no unreviewed auto conclusions.
4. **Review/record:** run **SKB-T06/07**, attach **`skb-judge-calibration`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T06/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S5-04 — Build results/evidence UI

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Show effect/interval/N, compatibility, safety, exclusions, cost and per-trial trace links.
3. **Verify:** Filters do not redefine frozen headline silently; mismatched experiments marked noncomparable.
4. **Review/record:** run **SKB-T08**, attach **`skb-results-e2e`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S5-05 — Conduct method and UX review

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Statistical reviewer approves estimands/intervals; pilot users interpret helpful/harmful/inconclusive examples.
3. **Verify:** No equivalence/winner claim unsupported by reviewed method; four of five interpret core result.
4. **Review/record:** run **SKB-T06/08**, attach **`skb-method-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T06/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S5-GATE — phase exit / definition of done

**Exit condition:** Known-effect simulations pass and results disclose uncertainty/missingness.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S6 — CI evidence and qualification

**Accountable role:** QA + security. **Entry:** SKB-S5-GATE approved.

**Shared prerequisite:** FND-F4 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S6-01 — Implement versioned report/CI exporter

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Bind report to package/plan/suite/engine/analysis hashes; add narrow CI publisher.
3. **Verify:** Tampered/stale/missing evidence cannot receive clean badge; fork secrets remain protected.
4. **Review/record:** run **SKB-T09**, attach **`skb-report-ci-tests`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S6-02 — Run 40-task held-out evaluation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Use preregistered repetitions/splits with declared helpful/harmful/no-op cases and full denominators.
3. **Verify:** Holdout not tuned; quality/safety/activation/cost and invalids all published.
4. **Review/record:** run **SKB-T03/05/06**, attach **`skb-heldout-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T03/05/06 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S6-03 — Attack trust and contamination boundaries

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Attempt answer leakage, scorer tampering, package injection, exfiltration and forged results.
3. **Verify:** No critical boundary failure accepted; live feature disabled if isolation gate fails.
4. **Review/record:** run **SKB-T01/07**, attach **`skb-security-qualification`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T01/07 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S6-04 — Load/fault test plans and results

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Exercise 1k trials/records, concurrent submit/cancel, stale attempts and provider outages.
3. **Verify:** Declared UI/validation targets met; no duplicate experiment or lost budget accounting.
4. **Review/record:** run **SKB-T02/04/08**, attach **`skb-load-chaos-report`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T02/04/08 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S6-05 — Audit reproduction and documentation

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Independent reviewer rebuilds fixture report and checks statistics/config/license lineage.
3. **Verify:** Fixture report reproducible keylessly; live nondeterminism and costs disclosed.
4. **Review/record:** run **SKB-T09/10**, attach **`skb-reproduction-review`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T09/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S6-GATE — phase exit / definition of done

**Exit condition:** Immutable reports survive roundtrip and benchmark/security limitations are explicit.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.


## SKB-S7 — Private release and maintenance

**Accountable role:** Operations + maintainer. **Entry:** SKB-S6-GATE approved.

**Shared prerequisite:** FND-F5 gate, plus any earlier foundation gate required by the task (especially artifact/auth and hardened execution before real data/live work).


### [ ] SKB-S7-01 — Package standalone install

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Build pinned engine/executor profiles, offline sample reports and safe provider setup.
3. **Verify:** SkillBench installs without AFR server; optional AFR trace links degrade gracefully.
4. **Review/record:** run **SKB-T10**, attach **`skb-release-candidate`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S7-02 — Rehearse lifecycle/deletion

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Upgrade/restore plans/results/hidden artifacts, delete source derivatives and drain workers.
3. **Verify:** Immutability retained; tombstones applied; reports marked unavailable when evidence deleted.
4. **Review/record:** run **SKB-T10**, attach **`skb-operations-drill`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S7-03 — Run maintainer alpha

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Onboard 3–5 skill maintainers to inspect/plan/run/read a bounded experiment.
3. **Verify:** Observed friction fixed; results not marketed as universal certification.
4. **Review/record:** run **SKB-T08/10**, attach **`skb-alpha-summary`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T08/10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S7-04 — Publish method and integration docs

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Document backend decision, controlled comparison, missingness, limitations and benchmark rights.
3. **Verify:** External reviewer can identify exact conditions behind any report.
4. **Review/record:** run **SKB-T06/09**, attach **`skb-docs-and-method`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-T06/09 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### [ ] SKB-S7-05 — Sign release and future gates

1. **Prepare:** verify dependencies and establish the test fixture/negative case for this task.
2. **Implement:** Approve R01–R10, dependency maintenance and second-harness criteria.
3. **Verify:** No public arbitrary submissions/leaderboard until separate abuse/gaming/isolation gates pass.
4. **Review/record:** run **SKB-R01–R10**, attach **`skb-v1-signoff`**, update contracts/docs and satisfy GDoD.

**Local DoD:**
- [ ] Acceptance above demonstrated with evidence, including failure behavior.
- [ ] SKB-R01–R10 passes or required manual review signed.
- [ ] Evidence artifact linked in task tracker; no secrets or unsupported claims.
- [ ] Independent reviewer accepts; GDoD complete.


### SKB-S7-GATE — phase exit / definition of done

**Exit condition:** Install/restore/alpha/signoff completed without overstating evaluation authority.

- [ ] All five task-local checklists and GDoD complete.
- [ ] Required requirement/test mappings have passing evidence; negative and recovery cases reviewed.
- [ ] Security/privacy/UX/data-integrity implications accepted by named reviewers.
- [ ] Outstanding risks have owner, severity, mitigation and next review date; blockers not deferred silently.
- [ ] Next phase entry approved; any scope/architecture change captured in an ADR.
