# Comparative research and dependency decisions

**Research date:** 2026-11-03. Primary documentation and README snapshots informed these designs. This is a documentation/architecture comparison, not a hands-on benchmark, security audit or proof of missing competitor features. Development spikes in the backlog must validate integration claims before dependencies are adopted.

## 1. Research findings that materially change the build

### Agent Flight Recorder

**Phoenix** documents OpenTelemetry-based tracing, evaluation, versioned datasets, experiments, prompt management and replaying traced model calls. **Langfuse** offers an established self-hostable observability/evaluation platform. **AgentOps** provides instrumentation/monitoring integrations. Therefore “a trace viewer with replay” is not a sufficient differentiation claim. AFR narrows to trace completeness, explicit side-effect/replay semantics, safe fixture authoring and test export. If discovery finds these needs already satisfied by a user's current platform, build an integration rather than a replacement.

Primary sources: [Phoenix README](https://github.com/arize-ai/phoenix), [Langfuse self-hosting](https://langfuse.com/self-hosting), [AgentOps](https://github.com/AgentOps-AI/agentops). The directly fetched Langfuse self-host page identified itself as v4; old v3 comparison articles were not treated as the current version authority. Its architecture description includes application web/worker components, Postgres, Redis/Valkey, ClickHouse and blob storage. AFR deliberately starts with a smaller stack for its bounded workload, not because that larger architecture is wrong.

### SkillBench

**NVIDIA SkillEvaluator is a direct comparable, not merely a complementary library.** Its captured README explicitly describes quality/security checking, deduplication and live comparisons with and without a skill; CI onboarding and use of Harbor for sandboxed agent execution are also documented. It labels support experimental/best effort. This removes the novelty claim that with/without-skill testing is unserved. SKB's candidate contribution is experiment design, preregistration, held-out task separation, statistical interpretation, reviewable evidence, and later cross-harness analysis. These may overlap other tools too; the discovery gate is mandatory.

**Inspect** composes datasets, solvers and scorers, with execution limits and sandbox interfaces. Its documentation explicitly warns that provisioning a sandbox does not automatically move tool/agent/scorer Python into it: only work requested through the sandbox interface executes there. Its security policy treats untrusted task/config/solver/scorer loading as running untrusted code and describes Docker's limited isolation. That is why the entire untrusted harness/plugin must be isolated in this design.

**Promptfoo** documents deterministic, model-graded and custom assertions, evaluation configuration and security testing. Reuse result imports or selected checks where licensing and API stability allow; do not claim scans prove safety. **Anthropic skills** supplies real skill-format examples; licenses and terms may vary by content and require specific inspection.

Primary sources: [SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator), [Inspect sandboxing](https://inspect.aisi.org.uk/sandboxing.html), [Inspect security policy](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md), [Inspect tasks](https://inspect.aisi.org.uk/tasks.html), [Promptfoo assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/), [Anthropic skills](https://github.com/anthropics/skills).

### EvidenceForge

**Docling** documents a typed `DoclingDocument` with texts, tables, pictures, hierarchy, reading order, layout when available and provenance. It does not make field semantics or extraction correctness automatic. **Unstructured** is a partitioning/ETL comparison baseline. **Marker** provides conversion outputs and has a separate weight-license concern: repository license detection alone is insufficient. **RAGFlow** is a broader application/context ecosystem, not a required dependency. **Label Studio** is a potential annotation workflow partner; adopting it only makes sense if its annotation schema, access model and export preserve EVF's versioned provenance.

**Ragas** is relevant to optional retrieval/Q&A evaluation, but source-grounded field extraction must first use exact/structural domain checks. An LLM judged “faithful” answer does not prove the right table row, reporting period or units were selected.

Primary sources: [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/), [Docling core](https://github.com/docling-project/docling-core), [Unstructured](https://github.com/Unstructured-IO/unstructured), [Marker](https://github.com/VikParuchuri/marker), [RAGFlow](https://github.com/infiniflow/ragflow), [Label Studio](https://github.com/HumanSignal/label-studio), [Ragas](https://github.com/explodinggradients/ragas).

## 2. Comparison matrix: reuse, integrate, or avoid duplicating

| Project/standard | Relevant capability described in primary source | Proposed relationship | Spike/decision required |
|---|---|---|---|
| Phoenix | traces, datasets, experiments, model-call replay | optional AFR import/export, UX benchmark | versioned data mapping; license/feature review |
| Langfuse | self-hostable observability/evals; separate data services | optional adapter, not mandatory platform | supported OTLP/API contract; deployment burden |
| AgentOps | agent instrumentation and monitoring integrations | capture adapter inspiration/optional integration | compatibility, capture defaults, SDK overhead |
| OpenTelemetry GenAI | model/tool/agent telemetry conventions | AFR compatibility mapping; own stable envelope | pin convention revision and migration strategy |
| SkillEvaluator | skill validation, overlap and live impact | direct competitor; preferred import/upstream candidate | 10-task comparison; build-versus-contribute decision |
| Inspect | task/solver/scorer composition and sandbox API | primary SKB backend hypothesis | full harness isolation, limits, result schema |
| Promptfoo | assertions and security evaluation | optional report import/check integration | safe plugin execution and versioned formats |
| Anthropic skills | skill examples/formats | compatibility fixtures | exact skill/license/activation behavior |
| Docling + core | typed parse, layout/provenance | primary EVF parser hypothesis | geometry, table semantics, assets and quality |
| Unstructured | partitioning/ETL | EVF alternate baseline, not all formats v1 | preserved provenance, table outputs, compute |
| Marker | PDF conversion outputs | EVF alternate candidate | code AND model terms; coordinate metadata |
| Label Studio | annotation workflows | gold-data labeling/export candidate | annotation-to-EVF mapping, license/role model |
| RAGFlow | retrieval/context application | competitive reference; no required install | compare review/provenance workflows if user demand |
| Ragas | evaluation tooling | optional later Q&A metrics | exact metric applicability and judge calibration |

“Optional” is not a promise of implemented integration. Dependency choice is gated by the corresponding spike and approved ADR.

## 3. Standards and security evidence

### OpenTelemetry

The old OpenTelemetry GenAI spans URL now redirects conceptually to a dedicated GenAI semantic-conventions repository. The design does not bake in a stale convention URL or assume all attributes are stable. The captured/current primary source describes sensitive message content and external content storage patterns. AFR defaults to metadata, explicit opt-in content and allowlisted serialization; semantic-convention updates are isolated in mapping adapters.

Sources: [moved documentation notice](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/), [GenAI conventions repository](https://github.com/open-telemetry/semantic-conventions-genai), [client spans definition](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md).

### Agent threats and authorization

OWASP's official Agentic Applications 2026 resource supplies a threat-review starting point, not certification. The shared threat matrix is implementation-specific and must also address conventional web/file-processing vulnerabilities. MCP's security guidance discusses confused-deputy risk and per-client consent. If an MCP integration is added, it must have a separate authorization review; protocol support does not confer safe token handling.

Sources: [OWASP official resource](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), [MCP security guidance](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices). The latter redirected during research to dated 2026-07-28 documentation; implementation must pin its actual protocol/SDK version.

### Accessibility

WCAG 2.2 is the normative target for applicable AA criteria. Automated scans cannot establish complete conformance; manual keyboard, zoom, focus, assistive-technology and task testing are explicit release gates.

Source: [WCAG 2.2 W3C Recommendation](https://www.w3.org/TR/WCAG22/).

## 4. Dependency due-diligence checklist

Before adopting any dependency:

- [ ] Pin actual release/commit and transitive dependency lockfile; record maintainer/source.
- [ ] Review code, model, data, font, example and commercial API terms separately.
- [ ] Verify needed features through a minimal executable spike on supported hardware.
- [ ] Identify what runs in the host process and what crosses network/filesystem boundaries.
- [ ] Exercise malformed input, missing dependency, denied egress, cancellation and upgrade cases.
- [ ] Measure resource use and SDK overhead on representative fixtures.
- [ ] Record output-format stability and backward-compatibility plan.
- [ ] Verify telemetry/default cloud behavior and disable or document it.
- [ ] Record advisory exposure, release provenance and vulnerability-report process.
- [ ] Specify fallback/deprecation path without violating user data policy.

## 5. Evidence quality and limitations

Fifteen repositories were queried directly for metadata and default-branch commit hashes, with README snapshots stored when available. Exact hashes and acquisition times are in `research/source-manifest.json`. A generated source appendix follows. Web documentation is time-sensitive and was inspected, but not all rendered website content is archived. No upstream installers were executed, no integrations were benchmarked and no claim of absence of a competitor feature is proven. Product decisions and targets in this pack are proposed engineering choices. Dependency spikes, user research and security/statistical reviews remain implementation work, not work already completed by this document.



## Pinned primary repository snapshot appendix

These hashes identify research snapshots, not the versions automatically approved for implementation. Review and pin actual release dependencies during spikes. `NOASSERTION` or missing API license detection is unresolved, not a permissive license grant.

| Repository | Research commit | API license detection |
|---|---|---|
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | [db598ac1277c](https://github.com/langfuse/langfuse/tree/db598ac1277ca2e70d8911b47169e9040dabdcf2) | NOASSERTION |
| [arize-ai/phoenix](https://github.com/arize-ai/phoenix) | [5835389ca5a2](https://github.com/arize-ai/phoenix/tree/5835389ca5a29a8505cb827a6e59796d3f8f0138) | NOASSERTION |
| [AgentOps-AI/agentops](https://github.com/AgentOps-AI/agentops) | [f8e907b92dab](https://github.com/AgentOps-AI/agentops/tree/f8e907b92dabe47232978023fdcb01e2a7d4b752) | MIT |
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | [882a5db3af19](https://github.com/UKGovernmentBEIS/inspect_ai/tree/882a5db3af19eb9b311e24d2395d8443df45179f) | MIT |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | [f2b012e3c9f9](https://github.com/promptfoo/promptfoo/tree/f2b012e3c9f9ffb7b23edf4cf88ea63febf72f5a) | MIT |
| [NVIDIA/SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) | [8532d57b7067](https://github.com/NVIDIA/SkillEvaluator/tree/8532d57b7067700a16272bf0a0e46a9d4dba302d) | Apache-2.0 |
| [anthropics/skills](https://github.com/anthropics/skills) | [ca45fc496a34](https://github.com/anthropics/skills/tree/ca45fc496a3436251f191354091d557da31c15b5) | UNDETECTED |
| [docling-project/docling](https://github.com/docling-project/docling) | [0634e2f74561](https://github.com/docling-project/docling/tree/0634e2f74561e5950d69b2cace67ef95400506ad) | MIT |
| [docling-project/docling-core](https://github.com/docling-project/docling-core) | [1517ab727571](https://github.com/docling-project/docling-core/tree/1517ab72757163d751750b42c87c4049290bd166) | MIT |
| [Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) | [d505b6010964](https://github.com/Unstructured-IO/unstructured/tree/d505b6010964de066a33fcce716a644e5887e7d3) | Apache-2.0 |
| [VikParuchuri/marker](https://github.com/VikParuchuri/marker) | [71dd5fd7e51a](https://github.com/VikParuchuri/marker/tree/71dd5fd7e51ab24f8624b6ba2fcb6014b4e40ed4) | Apache-2.0 |
| [HumanSignal/label-studio](https://github.com/HumanSignal/label-studio) | [a5b3125889f8](https://github.com/HumanSignal/label-studio/tree/a5b3125889f89929892b02e52c6988affb3e7e2f) | Apache-2.0 |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | [2c4bbbc720fe](https://github.com/infiniflow/ragflow/tree/2c4bbbc720fe24bd7ac509ab989325d4c1e8e532) | Apache-2.0 |
| [explodinggradients/ragas](https://github.com/explodinggradients/ragas) | [298b68274234](https://github.com/explodinggradients/ragas/tree/298b68274234c060deacab3cf5fb52aa3a20e885) | Apache-2.0 |
| [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) | [95aff9cdf605](https://github.com/open-telemetry/semantic-conventions-genai/tree/95aff9cdf605bbc7d7e8f7c4745a693bd0c4eea8) | Apache-2.0 |
