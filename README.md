<div align="center">
  
# 01-monorepo

**Local-first AI coding assistant workspace for governed software delivery.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Gitea PR Gated](https://img.shields.io/badge/Gitea-PR_Gated-609926.svg?logo=gitea&logoColor=white)](./docs/gitea-pr-validation.md)
[![Redis Backed](https://img.shields.io/badge/Event_Bus-Redis-DC382D.svg?logo=redis&logoColor=white)](./docs/architecture.md)

![Hero Image](./docs/assets/hero-terminal.png)

*Codex for execution. Claude for reasoning. Qwen for cheap local helper tasks.*  
**Event-driven. CI-authoritative. Human-approved. Built for real engineering teams.**

[Why this exists](#why-this-exists) •
[Features](#features) •
[Architecture](#architecture) •
[Quick Start](#quick-start) •
[Versus Alternatives](#why-not-x) •
[Model Routing](#model-routing) •
[Docs](#docs)

</div>

---

## 💡 Why This Exists

Most AI coding setups fail in one of two ways: they are either **too weak** to be useful in real engineering workflows, or they are **too autonomous** to be trustworthy in a corporate environment.

`01-monorepo` is built for the middle path:
- **Local-first & privacy-aware:** Sensitive code stays local where it belongs.
- **Event-driven orchestration:** Predictable, robust, and observable logic.
- **CI-governed & Human-approved:** Code doesn't merge without passing CI validation and getting human review.
- **Agent-assisted, not agent-chaos:** We want AI that accelerates software delivery, not AI that loops indefinitely and silently breaks builds.

This is not an "AI company in a repo" toy. It is a **controlled AI coding workspace**.

---

## ✨ Features

| 🛡️ Governance & Safety | 🤖 Model Orchestration | ⚙️ Engineering Discipline |
| :--- | :--- | :--- |
| **Human Approval Gate**<br>No merges to main without explicit human sign-off. | **Codex-First Execution**<br>Purpose-built for implementation and precise edits. | **CI-Authoritative Fix Loops**<br>Agents cannot bypass failing tests. |
| **Strict Tool Hardening**<br>Explicit policy rejection for dangerous operations. | **Claude Reasoning Engine**<br>For architecture, planning, and deep debugging. | **Redis Streams Backbone**<br>Reliable, auditable event-driven task bus. |
| **Distilled Memory**<br>No raw, polluted conversation dumps. Clean state only. | **Local Qwen 9B Bounded**<br>Cheap, local inference for low-risk helper tasks. | **DAG Scheduler Enforcement**<br>Predictable execution paths (Plan → Code → Test). |

---

## ⚖️ Why Not X?

Instead of adopting standalone agents that operate as black boxes, `01-monorepo` integrates AI into a strict engineering pipeline.

### vs. Claude Code & Cursor / Copilot Workspaces
Commercial tools are powerful but operate as opaque, closed environments where you have limited control over boundaries. `01-monorepo` gives you a **customizable, local-first orchestration layer** where you own the memory, the event bus (Redis), and the CI integration logic natively.

### vs. AutoGen
AutoGen excels at complex, open-ended multi-agent conversations, which is great for research but often leads to infinite loops and unpredictability in software delivery. `01-monorepo` replaces conversational chaos with **deterministic DAGs (Directed Acyclic Graphs)**. Agents execute specific nodes; they don't chat endlessly.

### vs. CrewAI
CrewAI brings structure through roles, but often lacks rigid connection to CI/CD pipelines. `01-monorepo` treats the **CI environment as authoritative**. It doesn't just write code; it orchestrates the iterative fix loop against real `pytest`, `mypy`, and `ruff` outputs, gated by local Gitea PR checks.

---

## 🏗️ Architecture

```text
issue/request
  └─> planner
        └─> coder
              └─> tester
                    └─> reviewer
                          └─> human approval
                                └─> merge
```

**CI Failure Path:**
```text
ci_failed ──> fix_task ──> rerun_ci ──> continue only after ci_passed
```

**Core invariants:**
- **Scheduler decoupling:** The scheduler is a separate runtime service.
- **Redis Streams:** The exclusive orchestration bus. State persists reliably.
- **Event-driven:** Agents communicate *only* through structured events.
- **Merge protection:** Merging to `main` ALWAYS requires manual review.

---

## 🚦 Model Routing

This workspace standardizes four distinct execution lanes to balance power, privacy, and cost:

1. **Codex CLI**: Primary implementation and localized edits.
2. **Claude Code CLI**: Planning, architectural design, deep debugging, and review support.
3. **Ollama (`qwen3.5:9b`)**: Helper-only for cheap, bounded tasks (e.g., summarizing logs).
4. **Antigravity IDE**: The visual workflow consumer and IDE, not the runtime authority.

> 🔒 **Local Model Policy:**
> The local 9B model is strictly bounded and is **never** used for production code generation, authentication logic, CI decisions, merge authority, or security reviews.

See [Model Routing](./docs/model-routing.md) and [Local Model Policy](./docs/local-model-policy.md).

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
python3 -m venv .context/.venv
source .context/.venv/bin/activate
pip install -e .[dev]
```

### 2. Fast Validation Path

```bash
pytest workspace/scheduler/test_orchestration.py -q
mypy workspace
ruff check workspace projects
```

### 3. Start Redis Infrastructure

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

### 4. Integration Validation

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  pytest workspace/scheduler/test_redis_integration.py -q
```

### 5. Run Controlled Flow

```bash
REDIS_PORT=6380 REDIS_DB=15 \
  python bootstrap/local_validation.py controlled-flow \
  --reset-db \
  --graph-id rc-local-001 \
  --objective "Controlled flow validation" \
  --project-name 01-monorepo
```

---

## 🛡️ Gitea PR Gate

All changes to `main` must pass through our structured workflow:

`feature branch` ➔ `PR` ➔ `CI green` ➔ `human approval` ➔ `merge`

Validation includes linting, static typing, unit tests, and Redis integration tests. 
See the [Gitea Activation Checklist](./docs/gitea-activation-checklist.md).

---

## 📜 Instruction Hierarchy

We separate instructions by audience and capability:

- 🏗️ [`AGENTS.md`](./AGENTS.md) — Canonical Codex-facing contract
- 🧠 [`CLAUDE.md`](./CLAUDE.md) — Canonical Claude-facing reasoning layer
- 🗃️ [`.claude/CLAUDE.md`](./.claude/CLAUDE.md) — Curated durable memory
- 🧰 [`.agent/README.md`](./.agent/README.md) — Shared skills & workflows
- 🛡️ [`GUARDRAILS.md`](./GUARDRAILS.md) — Operator-facing safety model
- 🗺️ [`WORKSPACE.md`](./WORKSPACE.md) — Runtime boundaries and ownership

---

## 🎯 Current Maturity: Local Controlled RC

**Release Candidate for Local Controlled Operation.**

This repository is not a toy. It enforces real runtime guardrails, trusted-source execution, structured audit logging, local validation, and strict PR gating. It intentionally does *not* behave like a fully autonomous (and unsafe) production platform.

See [Release Candidate Status](./docs/release-candidate.md).

<div align="center">
  <br>
  <strong>AI should accelerate software delivery without dissolving engineering discipline.</strong>
  <br><br>
</div>
