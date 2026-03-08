---
status: active
progress: 55
generated: 2026-03-06
agents:
  - type: "architect-specialist"
    role: "Own the architecture delta, sequencing, and invariant preservation."
  - type: "backend-specialist"
    role: "Implement scheduler, memory, MCP, A2A, and worktree services."
  - type: "frontend-specialist"
    role: "Build the DAG visualizer and approval UX."
  - type: "documentation-writer"
    role: "Keep README, architecture docs, and operator runbooks aligned."
  - type: "devops-specialist"
    role: "Extend CI, containers, and deployment support for new edge services."
  - type: "security-auditor"
    role: "Review MCP/A2A exposure, approval flow, and local-first guarantees."
  - type: "test-writer"
    role: "Add contract, integration, and regression coverage for every epic."
  - type: "performance-optimizer"
    role: "Control telemetry cardinality, SSE fan-out cost, and Redis overhead."
  - type: "code-reviewer"
    role: "Review implementation phases against quality and governance rules."
docs:
  - "project-overview.md"
  - "architecture.md"
  - "development-workflow.md"
  - "testing-strategy.md"
  - "security.md"
  - "tooling.md"
  - "data-flow.md"
phases:
  - id: "P"
    name: "Plan Baseline and ADRs"
    prevc: "P"
    agent: "architect-specialist"
  - id: "R"
    name: "Review and Contract Freeze"
    prevc: "R"
    agent: "security-auditor"
  - id: "E"
    name: "Execute by Epic"
    prevc: "E"
    agent: "backend-specialist"
  - id: "V"
    name: "Validate and Release"
    prevc: "V"
    agent: "test-writer"
  - id: "C"
    name: "Complete and Distill"
    prevc: "C"
    agent: "documentation-writer"
lastUpdated: "2026-03-06T15:35:00.000Z"
---

# Future Agents Evolution Roadmap 2026 Plan

> Historical planning snapshot. Non-authoritative.
> See [`../../AGENTS.md`](../../AGENTS.md) and [`../../docs/authority-hierarchy.md`](../../docs/authority-hierarchy.md) before treating any item here as active policy or approved scope.

> Structured execution plan for the roadmap captured on March 6, 2026. The original `plan.md` has been removed; this snapshot preserves the plan content.

## Task Snapshot

- **Primary goal:** evolve the current repository from a governed local orchestration runtime into an MCP-native, worktree-aware, observable control room while keeping Redis Streams, CI authority, human approval, and distilled memory as hard invariants.
- **Success signal:** by the end of Q3 2026, operators can create and inspect DAGs through MCP, isolate each active agent in a managed git worktree, view live DAG state in a lightweight web UI, trace scheduler activity through OpenTelemetry, and accept delegated work through A2A without creating alternate authority paths.
- **In scope:** scheduler MCP server, memory MCP server, stdio and HTTP/SSE transport support, worktree lifecycle management, OpenTelemetry tracing and metrics, skill manifest and execution model, DAG visualizer v1/v2, A2A gateway, operator and validation documentation.
- **Out of scope:** replacing Redis Streams, allowing direct agent-to-agent calls, weakening CI or human approval gates, persisting raw transcripts, turning `.agent/skills` assets into new runtime authorities, or introducing a cloud-only control plane.
- **Key references:**
  - Roadmap source: originally `plan.md` (removed; content preserved in this file)
  - [README](../../README.md)
  - [Architecture](../../docs/architecture.md)
  - [Scheduler Guide](../../docs/scheduler.md)
  - [CLI Auth And MCP](../../docs/cli-auth-and-mcp.md)
  - [Scheduler Package README](../../workspace/scheduler/README.md)
  - [Memory Package README](../../workspace/memory/README.md)

## Current Baseline

- The scheduler already exists as a separate stateless service in [workspace/scheduler/service.py](../../workspace/scheduler/service.py) and rebuilds DAG state from Redis-backed storage.
- DAG persistence, retry handling, idempotency, and operator snapshots already exist in [workspace/scheduler/dag_store.py](../../workspace/scheduler/dag_store.py) and [workspace/scheduler/service.py](../../workspace/scheduler/service.py).
- Guardrails already enforce `planner`, `coder`, `tester`, and `reviewer` boundaries plus CI-authoritative progression in [workspace/scheduler/guardrail_enforcer.py](../../workspace/scheduler/guardrail_enforcer.py).
- Distilled memory runtime writes already exist in [workspace/memory/runtime_service.py](../../workspace/memory/runtime_service.py); the gap is externalized MCP access, not the write path itself.
- The runtime already exposes an `mcp_context` bootstrap description in [workspace/runtime/runner.py](../../workspace/runtime/runner.py), but the repository does not yet expose scheduler or memory as MCP servers.
- Internal skill routing already exists in [workspace/skills_router/router.py](../../workspace/skills_router/router.py), but it is registry-based and internal only. There is no first-class `skill.json` manifest, installer flow, or scheduler-visible skill contract yet.
- There is no managed git worktree lifecycle, no OpenTelemetry exporter, no DAG visualizer UI, and no A2A edge gateway in the current codebase.

## Strategic Ordering

The roadmap should execute in dependency order, not market headline order.

| Epic | Target window | Why now | Depends on |
| --- | --- | --- | --- |
| MCP edge foundation | April 2026 | External interoperability is the largest strategic gap and reuses existing scheduler and memory boundaries. | Current scheduler and memory runtime APIs |
| Worktree lifecycle | April-May 2026 | Safe parallel execution should land before UI and external delegation increase concurrency. | Scheduler metadata extensions and guardrail review |
| OpenTelemetry basic | May 2026 | The UI and later A2A operations need standard traces and metrics instead of ad hoc logs. | Scheduler event hooks |
| Skills format v1 | May-June 2026 | Existing skill routing gives a starting point; formal manifests are needed before marketplace work. | Current skill router and `.agent/skills` inventory |
| DAG visualizer v1 | June 2026 | A live operator surface becomes useful only after MCP APIs and telemetry exist. | MCP read APIs, SSE edge, telemetry schema |
| A2A gateway | July-August 2026 | A2A should sit on top of a hardened MCP-compatible edge and never bypass review gates. | MCP contracts, security review, approval model |
| Visualizer v2 and dashboards | August-September 2026 | Deep operator UX depends on stable data contracts from earlier releases. | Telemetry, visualizer v1, gateway APIs |

## Governance Fit

The roadmap is valid only if these repository rules remain untouched throughout execution:

1. Redis Streams stays the only internal bus. UI, MCP, and A2A may expose edge adapters, but they must translate into the existing event bus rather than create side channels between agents.
2. CI remains authoritative. No MCP or A2A caller may mark a DAG successful without the same CI events already required by the scheduler.
3. Human approval remains mandatory for merge. External callers may request approval workflows but cannot grant merge rights unilaterally.
4. Distilled memory rules remain intact. OpenTelemetry spans, MCP context payloads, and A2A messages must never persist raw transcript content as durable runtime memory.
5. The scheduler stays a separate service. New edge protocols wrap the scheduler; they do not embed the scheduler into agent runtimes.
6. `.agent/skills`, Andru.ia assets, Loki Mode assets, and Antigravity assets remain advisory or operator-facing inputs. They do not create new primary runtime agent authorities beyond `planner`, `coder`, `tester`, and `reviewer`.

## Agent Lineup

| Agent | Role in this plan | Playbook | First responsibility focus |
| --- | --- | --- | --- |
| Architect Specialist | Freeze the target architecture, sequence epics, and keep invariants explicit. | [Architect Specialist](../agents/architect-specialist.md) | Define the MCP, worktree, telemetry, and A2A edge model |
| Backend Specialist | Deliver scheduler, memory, and protocol adapters. | [Backend Specialist](../agents/backend-specialist.md) | Add MCP servers, worktree manager, and A2A gateway plumbing |
| Frontend Specialist | Ship the operator surface without creating a heavyweight frontend stack. | [Frontend Specialist](../agents/frontend-specialist.md) | Build the Vite/React DAG visualizer and approval actions |
| Documentation Writer | Keep roadmap, operator docs, and onboarding consistent with implementation. | [Documentation Writer](../agents/documentation-writer.md) | Update README, architecture, and runbooks after each epic |
| Devops Specialist | Integrate new edge services with CI and optional local containers. | [Devops Specialist](../agents/devops-specialist.md) | Add validation commands, service packaging, and release wiring |
| Security Auditor | Review external protocol exposure and prevent governance regressions. | [Security Auditor](../agents/security-auditor.md) | Review MCP and A2A threat model plus approval boundary handling |
| Test Writer | Add contract and integration coverage. | [Test Writer](../agents/test-writer.md) | Extend scheduler, memory, protocol, and UI verification paths |
| Performance Optimizer | Prevent observability and UI fan-out from degrading the local-first runtime. | [Performance Optimizer](../agents/performance-optimizer.md) | Cap telemetry cardinality and Redis read amplification |
| Code Reviewer | Validate that the implementation remains coherent and non-regressive. | [Code Reviewer](../agents/code-reviewer.md) | Review each milestone before release branch or PR handoff |

## Documentation Touchpoints

| Guide | File | Why it changes |
| --- | --- | --- |
| Project positioning | [README.md](../../README.md) | Add the roadmap delta, MCP-native value proposition, and operator story once features land |
| Architecture source of truth | [docs/architecture.md](../../docs/architecture.md) | Document MCP edge, worktree manager, A2A gateway, and visualizer read path |
| Scheduler behavior | [docs/scheduler.md](../../docs/scheduler.md) | Explain worktree metadata, MCP-triggered actions, and new observability hooks |
| Scheduler package notes | [workspace/scheduler/README.md](../../workspace/scheduler/README.md) | Keep implementation-oriented details close to the package |
| Memory behavior | [workspace/memory/README.md](../../workspace/memory/README.md) | Describe memory MCP tools and context retrieval limits |
| MCP operator setup | [docs/cli-auth-and-mcp.md](../../docs/cli-auth-and-mcp.md) | Add local discovery, stdio/HTTP/SSE setup, and registry publishing notes |
| Local validation | [docs/local-validation.md](../../docs/local-validation.md) | Add validation commands for MCP, worktrees, telemetry, and UI smoke tests |
| Workflow guidance | [CONTRIBUTING.md](../../CONTRIBUTING.md) | Explain how new services and docs fit the branch -> CI -> review path |
| Model routing and guardrails | [docs/model-routing.md](../../docs/model-routing.md) and [GUARDRAILS.md](../../GUARDRAILS.md) | Clarify that new protocols do not change authority or execution lanes |

## Phase R Review Outputs

- [docs/contracts/mcp-boundary.md](../../docs/contracts/mcp-boundary.md) defines MCP as an edge adapter only and blocks any second control plane behavior.
- [docs/contracts/worktree-policy.md](../../docs/contracts/worktree-policy.md) defines minimal task isolation, naming, cleanup, and PR-flow interaction for mutable work.
- [docs/contracts/telemetry-policy.md](../../docs/contracts/telemetry-policy.md) defines required operator telemetry and forbids transcript-style or secret-bearing observability by default.
- [docs/contracts/a2a-boundary.md](../../docs/contracts/a2a-boundary.md) defers A2A behind MCP and keeps it edge-only and non-authoritative.
- [docs/contracts/phase-r-review-summary.md](../../docs/contracts/phase-r-review-summary.md) captures accepted principles, rejected patterns, unresolved questions, and Epic 1 readiness gates.

### Epic 1 Readiness Gates

Epic 1 may start only if all four Phase R contracts remain accepted, no contract conflicts with Redis Streams and scheduler authority, and no contract weakens CI authority, human approval, local-first routing, or distilled memory rules.

## Epic 1 Delivery

- `workspace/mcp/` now contains a bounded stdio MCP server plus scheduler and memory adapters.
- The scheduler adapter exposes health, graph state, task state, audit events, and a governed `issue_created` request path.
- The memory adapter exposes distilled record reads plus a governed `memory_write_requested` request path with preflight validation.
- Forbidden bypasses remain unexposed: no task mutation, no CI mutation, no merge mutation, no arbitrary event publication, no A2A.
- Operator and capability docs live in:
  - [docs/contracts/mcp-capabilities-epic1.md](../../docs/contracts/mcp-capabilities-epic1.md)
  - [docs/epics/epic-1-mcp-edge-adapters.md](../../docs/epics/epic-1-mcp-edge-adapters.md)
  - [docs/operator/mcp-local-usage.md](../../docs/operator/mcp-local-usage.md)

## Risk Assessment

### Identified Risks

| Risk | Probability | Impact | Mitigation Strategy | Owner |
| --- | --- | --- | --- | --- |
| MCP and A2A tools accidentally create a side channel around CI or human approval | Medium | High | Keep edge adapters write-only into existing scheduler events, require the same trusted completion sources, and add regression tests around `human_approval_gate` and `merge_task` | `security-auditor` |
| Worktree lifecycle leaves stale branches or corrupts local state during retries and fix loops | Medium | High | Persist worktree leases in Redis, add deterministic create/destroy hooks on terminal DAG states, and test crash recovery explicitly | `backend-specialist` |
| Telemetry attributes explode in cardinality and hurt local performance | Medium | Medium | Freeze a span and metric schema early, avoid prompt payloads, sample non-critical spans, and benchmark Redis plus exporter overhead | `performance-optimizer` |
| DAG visualizer introduces a second transport model that violates repository invariants | Low | High | Restrict the UI to read-only SSE plus explicit approval actions; agents continue using Redis Streams only | `architect-specialist` |
| First-class skills are interpreted as arbitrary plugin execution | Medium | Medium | Treat `skill.json` as manifest metadata plus policy, not unrestricted code execution; reuse the current indexed skill loading discipline | `code-reviewer` |
| A2A delegation exposes the scheduler to untrusted external callers | Medium | High | Gate delegation through explicit capability checks, namespace task creation, and keep merge and approval actions unavailable to external peers | `security-auditor` |

### Dependencies

- **Internal:** [workspace/scheduler/service.py](../../workspace/scheduler/service.py), [workspace/scheduler/dag_store.py](../../workspace/scheduler/dag_store.py), [workspace/scheduler/dispatcher.py](../../workspace/scheduler/dispatcher.py), [workspace/scheduler/guardrail_enforcer.py](../../workspace/scheduler/guardrail_enforcer.py), [workspace/memory/runtime_service.py](../../workspace/memory/runtime_service.py), [workspace/runtime/runner.py](../../workspace/runtime/runner.py), [workspace/skills_router/router.py](../../workspace/skills_router/router.py), [bootstrap/local_validation.py](../../bootstrap/local_validation.py)
- **External:** MCP SDK or protocol library, OpenTelemetry SDK and exporters, minimal React/Vite toolchain, optional Jaeger or Grafana Tempo, optional community MCP registry submission path
- **Technical:** Python 3.11 or newer, Redis integration environment, stable contract tests for stdio and HTTP/SSE, git worktree support on developer machines, Docker support for optional UI packaging

### Assumptions

- The repository keeps Python as the implementation language for scheduler, memory, and edge services during this roadmap.
- Redis Streams remains the only internal event backbone even if UI or protocol adapters expose alternate client-facing transports.
- The maintainer is willing to accept optional local dependencies for UI and observability, but the default validation path must stay local-first and deterministic.
- External registries or protocol ecosystems may evolve; the plan therefore prioritizes local correctness and adapter boundaries before community publication.

## Resource Estimation

### Time Allocation

| Phase | Estimated effort | Calendar window | Team shape |
| --- | --- | --- | --- |
| P - Plan Baseline and ADRs | 3-4 person-days | March 6-13, 2026 | Architect + docs |
| R - Review and Contract Freeze | 3-5 person-days | March 13-20, 2026 | Architect + security + reviewer |
| E - Execute by Epic | 30-40 person-days | April through August 2026 | Backend + frontend + test + devops |
| V - Validate and Release | 8-12 person-days | Per milestone and again in September 2026 | Test + security + reviewer |
| C - Complete and Distill | 2-3 person-days | End of each release wave and final September wrap-up | Docs + maintainer |
| **Total** | **46-64 person-days** | **Q2-Q3 2026** | **Cross-functional core team** |

### Required Skills

- Python service development for scheduler, edge protocols, and memory adapters
- Redis Streams and event-driven workflow design
- Git plumbing and safe worktree orchestration
- OpenTelemetry schema design and exporter wiring
- React plus Vite for a lightweight operator surface
- Security review for protocol exposure, capability checks, and approval boundaries
- Documentation and validation discipline so the roadmap stays operator-friendly

### Resource Availability

- **Available:** existing architect, backend, frontend, documentation, testing, security, and review playbooks already exist in `.context/agents/`
- **Blocked until planned:** community registry publishing, Grafana dashboards, and marketplace curation should not start before MCP contracts and skill manifests stabilize
- **Escalation path:** the repository maintainer acting as human merge approver remains the escalation point for scope cuts, release order changes, and guardrail exceptions

## Working Phases

### Phase P - Plan Baseline and ADRs

> **Primary Agent:** `architect-specialist` - [Playbook](../agents/architect-specialist.md)

**Objective:** convert the high-level market plan into repository-native contracts, phased epics, and hard guardrails.

| # | Task | Agent | Status | Deliverable |
| --- | --- | --- | --- | --- |
| P1 | Inventory the current scheduler, memory, skill router, and runtime bootstrap surfaces that can become protocol boundaries | `architect-specialist` | pending | Baseline section and interface inventory |
| P2 | Define ADRs for MCP edge adapters, worktree manager, telemetry schema, skill manifest, and A2A gateway | `architect-specialist` | pending | ADR backlog and architecture delta |
| P3 | Translate the six roadmap themes into dependency-ordered epics with concrete release windows | `documentation-writer` | pending | Sequenced roadmap table |
| P4 | Freeze non-negotiable invariants and explicitly mark what new services are edge-only adapters | `architect-specialist` | pending | Governance fit section |

**Deliverables**

- Repository-aligned roadmap plan
- ADR shortlist for every major epic
- Release sequencing and scope boundaries

**Exit criteria**

- No placeholder text remains in the plan
- Every epic is mapped to an owner, dependency set, and validation path
- Governance constraints are explicit enough to review before implementation

**Commit Checkpoint**

- `docs(plan): freeze future-agents evolution baseline`

---

### Phase R - Review and Contract Freeze

> **Primary Agent:** `security-auditor` - [Playbook](../agents/security-auditor.md)

**Objective:** review every new public surface before implementation starts.

| # | Task | Agent | Status | Deliverable |
| --- | --- | --- | --- | --- |
| R1 | Review MCP and A2A capabilities against merge approval, CI authority, and trusted-source rules | `security-auditor` | completed | `docs/contracts/mcp-boundary.md`, `docs/contracts/a2a-boundary.md` |
| R2 | Review the worktree lifecycle model against retries, fix loops, and DAG cleanup semantics | `architect-specialist` | completed | `docs/contracts/worktree-policy.md` |
| R3 | Review the telemetry schema so spans and metrics do not leak prompts or create runaway cardinality | `performance-optimizer` | completed | `docs/contracts/telemetry-policy.md` |
| R4 | Review the visualizer architecture to ensure SSE remains an operator edge, not an agent bus replacement | `code-reviewer` | completed | `docs/contracts/phase-r-review-summary.md` |
| R5 | Freeze the minimum viable contracts for Q2 implementation and defer marketplace-grade features to Q3 | `documentation-writer` | completed | `docs/contracts/phase-r-review-summary.md` |

**Deliverables**

- Threat model for MCP and A2A exposure
- Worktree and telemetry contract review notes
- Deferred scope list for marketplace and registry work
- Explicit Epic 1 readiness gates

**Exit criteria**

- Public API and event boundaries are approved for implementation
- Every blocked or deferred feature is explicitly documented
- No epic requires changing the repository's core invariants
- Phase R contract package exists under `docs/contracts/`

**Commit Checkpoint**

- `docs(plan): freeze protocol and worktree contracts`

---

### Phase E - Execute by Epic

> **Primary Agent:** `backend-specialist` - [Playbook](../agents/backend-specialist.md)

**Objective:** implement the roadmap in dependency order, one reviewable slice at a time.

#### Epic Workstreams

| Epic | Owner | Scope | Core deliverables | Evidence |
| --- | --- | --- | --- | --- |
| E1 - Scheduler MCP Server | `backend-specialist` | Expose bounded scheduler read tools plus governed request entrypoints while reusing existing scheduler logic | MCP server package, stdio adapter, bounded scheduler tool surface, contract tests | Completed in Epic 1 with unit coverage for forbidden bypasses |
| E2 - Memory MCP Server | `backend-specialist` | Expose distilled memory storage and retrieval without bypassing validation | Memory MCP tool surface, preflight validation, and event-driven submission path | Completed in Epic 1 with acceptance and rejection coverage |
| E3 - Git Worktree Manager | `backend-specialist` | Create, register, and clean per-agent worktrees with Redis metadata | Worktree service, scheduler hooks, cleanup policy, metadata keys such as `worktree:<agent>:<dag_id>` | Integration tests for create, reuse, teardown, and crash recovery |
| E4 - OpenTelemetry Basic | `performance-optimizer` | Add spans, metrics, and exporter wiring around DAG and task lifecycle | Instrumented scheduler, exporter config, baseline Grafana or Jaeger recipe | Span snapshots and performance guardrail benchmarks |
| E5 - Skills Format v1 | `backend-specialist` | Promote current skill routing into a first-class manifest-driven model | `skill.json` schema, loader updates, scheduler skill node contract, starter skills | Manifest validation tests and skill execution regression coverage |
| E6 - DAG Visualizer v1 | `frontend-specialist` | Ship a lightweight operator UI with live DAG state and approval actions | Vite/React UI, SSE-backed timeline, approval endpoint integration, optional Docker packaging | UI smoke tests and screenshot artifacts |
| E7 - A2A Gateway | `backend-specialist` | Expose agent card and delegated task submission without changing internal bus rules | `/.well-known/agent.json`, capability mapping, delegation gateway | A2A contract tests and security review sign-off |
| E8 - Visualizer v2 and Dashboards | `frontend-specialist` | Improve control-room ergonomics after the data contracts stabilize | richer DAG views, Grafana dashboard pack, alert examples | Dashboard JSON and operator walkthrough |

#### Execution Tasks

| # | Task | Agent | Status | Deliverable |
| --- | --- | --- | --- | --- |
| E1 | Build the protocol edge first: MCP scheduler and memory services with local discovery config | `backend-specialist` | completed | `workspace/mcp/`, Epic 1 docs, and MCP boundary tests |
| E2 | Add worktree orchestration and register lifecycle state in Redis before parallel agent adoption expands | `backend-specialist` | pending | Worktree manager merged |
| E3 | Instrument scheduler and memory paths with traces and metrics before building the operator UI | `performance-optimizer` | pending | Telemetry baseline merged |
| E4 | Formalize skill manifests by reusing the existing skill router discipline and allowlist model | `backend-specialist` | pending | Skills v1 merged |
| E5 | Deliver the visualizer as a thin read-oriented layer over scheduler and event data | `frontend-specialist` | pending | Visualizer v1 merged |
| E6 | Add A2A only after MCP, approvals, and observability have stable contracts | `backend-specialist` | pending | A2A gateway merged |

**Deliverables**

- MCP-native scheduler and memory edge
- Worktree isolation and Redis metadata
- Telemetry foundation and operator dashboards
- Manifest-driven skills model
- Operator visualizer and A2A gateway

**Exit criteria**

- Each epic ships with tests, docs, and rollback notes
- `python -m pytest`, `python -m ruff check workspace projects`, and `python -m mypy workspace` stay green for touched areas
- `bootstrap/local_validation.py controlled-flow` continues to block merge until human approval

**Commit Checkpoint**

- One reviewable commit series per epic, for example:
  - `feat(mcp): expose scheduler and memory as local servers`
  - `feat(worktrees): isolate agent execution per dag`
  - `feat(observability): instrument scheduler with opentelemetry`
  - `feat(skills): add manifest-driven skill contracts`
  - `feat(ui): add dag visualizer v1`
  - `feat(a2a): add delegated task gateway`

---

### Phase V - Validate and Release

> **Primary Agent:** `test-writer` - [Playbook](../agents/test-writer.md)

**Objective:** prove that the roadmap adds capability without weakening governance or local operability.

| # | Task | Agent | Status | Deliverable |
| --- | --- | --- | --- | --- |
| V1 | Add unit and integration coverage for MCP transports, worktree lifecycle, telemetry emission, and A2A delegation | `test-writer` | pending | Expanded automated test suite |
| V2 | Extend local validation commands to exercise the new edge paths and operator surface | `devops-specialist` | pending | Updated local validation runbook |
| V3 | Run security regression focused on approval gate, merge gate, and memory rejection invariants | `security-auditor` | pending | Security validation summary |
| V4 | Produce operator evidence such as screenshots, trace snapshots, and workflow examples | `documentation-writer` | pending | Release evidence bundle |

**Deliverables**

- Passing test suite and validation scripts
- Trace and metric examples
- Security and governance regression evidence
- Operator demo assets

**Exit criteria**

- All mandatory validation commands pass on the release branch
- No external protocol path bypasses CI, human approval, or memory guardrails
- Performance overhead stays acceptable for local-first operation

**Commit Checkpoint**

- `test(roadmap): validate mcp worktree telemetry and ui slices`

---

### Phase C - Complete and Distill

> **Primary Agent:** `documentation-writer` - [Playbook](../agents/documentation-writer.md)

**Objective:** finish the release wave, capture stable lessons, and prepare the next roadmap cut.

| # | Task | Agent | Status | Deliverable |
| --- | --- | --- | --- | --- |
| C1 | Distill stable decisions and lessons into durable project memory without storing raw transcripts | `documentation-writer` | pending | Distilled memory notes |
| C2 | Update README, docs, and operator narratives so the shipped platform matches reality | `documentation-writer` | pending | Final documentation sweep |
| C3 | Capture deferred backlog for registry publication, marketplace curation, and later compliance work | `architect-specialist` | pending | Follow-up backlog |
| C4 | Prepare a release summary for the human maintainer and merge approver | `code-reviewer` | pending | Handoff report |

**Deliverables**

- Finalized docs and distilled memory
- Follow-up backlog for Q4 and beyond
- Handoff package for maintainers

**Exit criteria**

- Stable architecture decisions are recorded once and deduplicated
- Documentation matches the code and operator workflow
- Remaining work is clearly separated from shipped capability

**Commit Checkpoint**

- `docs(roadmap): close future-agents evolution wave`

## Rollback Plan

### Rollback Triggers

Initiate rollback if any of the following appears during implementation or release:

- MCP or A2A exposure allows actions that should remain CI-gated or human-gated
- Worktree lifecycle causes branch corruption, stale lock buildup, or non-deterministic DAG failures
- Telemetry or UI changes noticeably degrade local execution latency or Redis load
- Skill manifests create unreviewed execution paths
- Memory services start accepting payloads that violate the distilled-memory contract

### Rollback Procedures

#### Protocol Edge Rollback

- Revert the MCP or A2A edge adapter commits only.
- Keep the scheduler, memory runtime, and Redis event model untouched.
- Remove new discovery config entries from `mcp.json` and operator docs.
- Estimated time: 1-2 hours once contracts are isolated by epic.

#### Worktree Rollback

- Disable worktree creation in scheduler config or feature flag.
- Clean Redis `worktree:*` metadata and remove any temporary worktrees created for test DAGs.
- Fall back to the current single-workspace execution model while leaving other roadmap slices intact.
- Estimated time: 2-4 hours depending on cleanup volume.

#### Observability and UI Rollback

- Turn off exporters and SSE/UI services without touching the core scheduler loop.
- Remove optional containers and local validation hooks introduced for those surfaces.
- Preserve `audit_log` as the minimum baseline while disabling OpenTelemetry and UI endpoints.
- Estimated time: 1-2 hours.

### Post-Rollback Actions

1. Record the trigger and impact in a short incident note.
2. Distill the lesson into project memory without copying raw logs.
3. Add a blocker entry to the roadmap before resuming the affected epic.
4. Re-run the controlled flow and mandatory validations to confirm the base platform is still healthy.

## Execution History

> Last updated: 2026-03-06T15:35:00.000Z | Progress: 55%
