<!-- ──────────────────────────────────────────────────────────────── -->
<!-- Future Agents 🇧🇷 — The Governed AI Engineering Workspace       -->
<!-- ──────────────────────────────────────────────────────────────── -->

<div align="center">

<br>

<img alt="Future Agents — AI Engineering Terminal" src="./docs/assets/hero-terminal.png" width="100%">

<br>

# Future Agents 🇧🇷

### The governed AI coding workspace for teams that ship real software.

<br>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Redis Streams](https://img.shields.io/badge/Bus-Redis_Streams-DC382D.svg?style=flat-square&logo=redis&logoColor=white)](./docs/architecture.md)
[![CI-Gated](https://img.shields.io/badge/CI-Authoritative-2EA44F.svg?style=flat-square)](./docs/gitea-pr-validation.md)
[![Human Approved](https://img.shields.io/badge/Merge-Human_Approved-8B5CF6.svg?style=flat-square)](./GUARDRAILS.md)
[![Gitea PR Gate](https://img.shields.io/badge/Gitea-PR_Gated-609926.svg?style=flat-square&logo=gitea&logoColor=white)](./docs/gitea-pr-validation.md)

<br>

**Codex for execution · Claude for reasoning · Qwen for cheap local helpers**

Event-driven · CI-authoritative · Human-approved · Local-first

<br>

[Why this exists](#why-this-exists) · 
[Key Features](#key-features) · 
[How it works](#how-it-works) · 
[Quick Start](#quick-start) · 
[Why not X?](#why-not-x) · 
[Model Routing](#model-routing) · 
[Docs](#documentation)

<br>

</div>

<!-- ──────────────────────────────────────────────────────────────── -->

## 💡 Why This Exists

Most AI coding setups fail in one of two ways:

> **Too weak** to be useful in real engineering workflows.
> 
> **Too autonomous** to be trustworthy in a corporate environment.

**Future Agents is the middle path.**

It is not an "AI company in a repo" toy.  
It is not a wrapper around a single LLM.  
It is a **controlled, event-driven AI engineering workspace** — purpose-built so that AI agents accelerate software delivery **without dissolving engineering discipline**.

<table>
<tr>
<td width="50%">

### ✅ What it does

- Orchestrates AI agents through a **deterministic DAG scheduler**
- Routes tasks to the right model at the right cost
- Enforces CI as the **single source of truth**
- Requires **human approval** before any merge to `main`
- Keeps memory **distilled**, never polluted with raw conversations
- Produces **structured audit trails** for every decision

</td>
<td width="50%">

### ❌ What it won't do

- Let agents loop endlessly without checkpoints
- Merge code that hasn't passed CI
- Trust a local 9B model with security-critical decisions
- Store raw chat transcripts in durable memory
- Allow direct agent-to-agent communication
- Replace engineering judgment with AI confidence

</td>
</tr>
</table>

---

## ✨ Key Features

<table>
<tr>
<td width="33%" valign="top">

### 🛡️ Governance & Safety

**Human Approval Gate**  
No merge to `main` without explicit human sign-off.

**Strict Tool Hardening**  
Policy-based rejection for dangerous operations, with audit artifacts.

**Distilled Memory Only**  
Raw conversation dumps are rejected at runtime. Only structured facts persist.

**Trusted-Source Enforcement**  
System-critical tasks (`human_approval_gate`, `merge_task`, `rerun_ci`) are source-verified.

</td>
<td width="33%" valign="top">

### 🤖 Model Orchestration

**Codex-First Execution**  
Primary engine for implementation and precise file edits.

**Claude Reasoning**  
Architecture, planning, deep debugging, and review assistance.

**Local Qwen 9B (Bounded)**  
Strictly limited to cheap, non-authoritative helper tasks. Never for auth, CI, or merge decisions.

**Cost-Aware Routing**  
Four execution lanes balance power, privacy, and token economy.

</td>
<td width="33%" valign="top">

### ⚙️ Engineering Discipline

**CI-Authoritative Fix Loops**  
Agents cannot self-report success. CI passes or work continues.

**Redis Streams Backbone**  
The exclusive orchestration bus. Auditable, persistent, and reliable.

**DAG Scheduler**  
Deterministic `Plan → Code → Test → Review → Approve → Merge` pipeline.

**Dead-Letter & Retry**  
Configurable retry limits with automatic escalation on exhaustion.

</td>
</tr>
</table>

---

## 🏗️ How It Works

### The Pipeline

Every issue flows through a fixed, auditable pipeline:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ PLANNER  │───▶│  CODER   │───▶│  TESTER  │───▶│ REVIEWER │───▶│ HUMAN OK │───▶│  MERGE   │
│          │    │          │    │          │    │          │    │          │    │          │
│ scope    │    │ impl     │    │ tests    │    │ quality  │    │ approval │    │ main ←   │
│ criteria │    │ code     │    │ fixtures │    │ risk     │    │ gate     │    │ protected│
│ ordering │    │ only     │    │ only     │    │ policy   │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │
                                     ▼ CI fails?
                              ┌──────────────┐
                              │  FIX LOOP    │
                              │ fix → rerun  │
                              │ → pass only  │
                              └──────────────┘
```

### Core Invariants

| Invariant | Enforcement |
|:---|:---|
| Scheduler is a **separate service** | `workspace/scheduler/service.py` |
| **Redis Streams** is the only bus | No Pub/Sub. Only `XADD`/`XREADGROUP`/`XACK` |
| Agents communicate **only through events** | No direct agent-to-agent calls |
| DAG state **persists in Redis** | Granular keys: `dag:*`, `task:*`, `taskstatus:*` |
| CI is **authoritative** | Agents cannot self-report success |
| Merge requires **human approval** | Metadata recorded and enforced |
| Invalid transitions are **rejected + audited** | `audit_log` events on every rejection |

### Event-Driven Architecture

```
           ┌─────────────────────────────────────────────────────┐
           │                  REDIS STREAMS                      │
           │                                                     │
           │  agent_tasks · agent_results · ci_events            │
           │  memory_events · system_events                      │
           └──────────────────────┬──────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
        ┌─────▼─────┐     ┌──────▼──────┐     ┌──────▼──────┐
        │ SCHEDULER  │     │   MEMORY    │     │  GUARDRAIL  │
        │            │     │   RUNTIME   │     │  ENFORCER   │
        │ DAG engine │     │ distilled   │     │ ownership   │
        │ dispatches │     │ writes only │     │ transitions │
        │ fix loops  │     │ rejects raw │     │ audit trail │
        └────────────┘     └─────────────┘     └─────────────┘
```

---

## 🚀 Quick Start

> **Requirements:** Python 3.12+, Docker, Redis

### 1. Clone & Setup

```bash
git clone https://github.com/willianstos/monorepo.git future-agents
cd future-agents
python3 -m venv .context/.venv
source .context/.venv/bin/activate
pip install -e .[dev]
```

### 2. Validate the Stack

```bash
# Lint + Types + Tests
ruff check workspace projects
mypy workspace
pytest workspace/scheduler/test_orchestration.py -q
```

### 3. Start Redis

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

### 4. Integration Tests

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  pytest workspace/scheduler/test_redis_integration.py -q
```

### 5. Run the Controlled Flow

```bash
REDIS_PORT=6380 REDIS_DB=15 \
  python bootstrap/local_validation.py controlled-flow \
  --reset-db \
  --graph-id rc-local-001 \
  --objective "Controlled flow validation" \
  --project-name future-agents
```

<details>
<summary><b>Expected output</b></summary>

```
✓ ruff check ..................... passed
✓ mypy .......................... passed
✓ unit tests 28/28 .............. passed
✓ redis integration ............. healthy
✓ DAG created ................... rc-local-001
✓ plan_task ..................... completed
✓ implement_task ................ completed
✓ test_task ..................... completed
✓ review_task ................... completed
⚠ merge ........................ blocked (human approval required)
```

</details>

---

## ⚖️ Why Not X?

Instead of adopting standalone agents that operate as black boxes, **Future Agents** integrates AI into a strict engineering pipeline with deterministic execution.

<table>
<tr>
<th width="25%">Compared to</th>
<th width="25%">Their approach</th>
<th width="25%">Our approach</th>
<th width="25%">Key difference</th>
</tr>
<tr>
<td><b>Claude Code / Cursor / Copilot Workspace</b></td>
<td>Powerful but opaque, closed environments</td>
<td>Open, customizable orchestration layer</td>
<td>You own the memory, the event bus, and the CI integration</td>
</tr>
<tr>
<td><b>AutoGen</b></td>
<td>Open-ended multi-agent conversations</td>
<td>Deterministic DAGs with fixed agent roles</td>
<td>No infinite loops. Agents execute nodes, they don't chat</td>
</tr>
<tr>
<td><b>CrewAI</b></td>
<td>Role-based agents with flexible execution</td>
<td>CI-authoritative pipeline with guardrail enforcement</td>
<td>CI is the source of truth, not agent self-reporting</td>
</tr>
<tr>
<td><b>LangGraph</b></td>
<td>Graph-based agent orchestration framework</td>
<td>Redis-backed DAG scheduler as a separate service</td>
<td>State persists independently. Scheduler is decoupled from agents</td>
</tr>
<tr>
<td><b>Dify</b></td>
<td>Visual workflow builder for LLM apps</td>
<td>Code-first engineering workspace with audit trails</td>
<td>Built for software delivery, not chatbot building</td>
</tr>
</table>

---

## 🚦 Model Routing

Four distinct execution lanes balance **power**, **privacy**, and **cost**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MODEL ROUTING                              │
├──────────────┬──────────────────────┬───────────────────────────────┤
│ Lane         │ Engine               │ Scope                        │
├──────────────┼──────────────────────┼───────────────────────────────┤
│ Primary      │ Codex CLI            │ Implementation & edits        │
│ Reasoning    │ Claude Code CLI      │ Architecture, planning, debug │
│ Helper       │ Ollama qwen3.5:9b    │ Cheap bounded tasks only      │
│ IDE          │ Antigravity          │ Workflow consumer, not auth   │
└──────────────┴──────────────────────┴───────────────────────────────┘
```

> [!CAUTION]
> **Local Model Policy:** The local 9B model is **never** used for production code generation, authentication logic, CI decisions, merge authority, security reviews, or scheduler state transitions. Its output is advisory until validated by CI.

See [Model Routing](./docs/model-routing.md) · [Local Model Policy](./docs/local-model-policy.md)

---

## 🛡️ Guardrails

<details>
<summary><b>Enforced in code today</b> (click to expand)</summary>

- Cross-agent coordination goes through **Redis Streams only**
- Direct agent-to-agent calls are **forbidden**
- Task ownership is enforced per agent role (`planner`, `coder`, `tester`, `reviewer`)
- Invalid status transitions are **rejected and audited**
- `coder` cannot modify tests or CI config
- `tester` can only modify tests and fixtures
- `reviewer` may block but cannot mutate code
- Merge cannot complete without **recorded human approval**
- Trusted-source checks on `human_approval_gate`, `merge_task`, `rerun_ci`
- Duplicate events are **ignored idempotently**
- Raw conversation payloads are **rejected at runtime**
- Filesystem scope and terminal allowlists with audit artifacts

</details>

### Non-Negotiable Rules

| Rule | Rationale |
|:---|:---|
| No task may bypass CI | CI is the single source of truth |
| No merge without human approval | Prevents unsupervised code shipping |
| No raw transcripts in durable memory | Keeps memory clean and reusable |
| No agent mutation outside repo scope | Prevents filesystem pollution |
| No fake success to replace CI outcomes | Agents cannot self-report passing |
| No destructive action without approval | Explicit consent for dangerous ops |

---

## 📁 Project Structure

```
future-agents/
├── .agent/                    # Shared skills, workflows, memory
│   ├── skills/                # Reusable agent skills library
│   ├── workflows/             # Workflow definitions (e.g., /git)
│   └── memory/                # Tool-agnostic durable notes
├── .claude/                   # Claude-specific rules & memory
├── .codex/                    # Codex-specific instructions
├── .context/                  # Runtime context & venv
├── .gitea/                    # Gitea CI/CD workflows
├── bootstrap/                 # Local validation & setup scripts
├── docs/                      # Architecture, routing, runbooks
├── guardrails/                # Machine-readable guardrail rules
├── projects/                  # Target repositories
└── workspace/                 # The runtime engine
    ├── agents/                # Agent implementations
    ├── config/                # Runtime configuration
    ├── event_bus/             # Redis Streams integration
    ├── gateway/               # Model gateway & routing
    ├── memory/                # Memory runtime service
    ├── providers/             # LLM provider adapters
    ├── runtime/               # Assistant runtime bootstrap
    ├── scheduler/             # DAG scheduler & guardrail enforcer
    └── tools/                 # Tool contracts & policies
```

---

## 📜 Instruction Hierarchy

Instructions are separated by audience. Each layer is consistent with the one above it:

```
AGENTS.md          ← Canonical Codex-facing contract
CLAUDE.md          ← Claude-facing reasoning layer
.claude/CLAUDE.md  ← Curated durable memory
.agent/            ← Shared skills & workflows
GUARDRAILS.md      ← Operator-facing safety model
WORKSPACE.md       ← Runtime boundaries & ownership
```

---

## 🛡️ Gitea PR Gate

All changes to `main` must pass through the full validation chain:

```
feature branch → PR → CI green → human approval → merge
```

CI checks include: `ruff` · `mypy` · `pytest` (unit) · `pytest` (Redis integration)

See [Gitea PR Validation](./docs/gitea-pr-validation.md) · [Activation Checklist](./docs/gitea-activation-checklist.md)

---

## 🎯 Current Maturity

**Release Candidate — Local Controlled Operation**

This repository is not a prototype. It enforces:

- ✅ Real runtime guardrails with code-backed rejection
- ✅ Trusted-source execution for critical system tasks
- ✅ Structured audit logging on every scheduler decision
- ✅ Local validation with deterministic replay
- ✅ Strict PR gating with human approval enforcement

It intentionally does *not* behave like a fully autonomous production platform. That is a feature.

See [Release Candidate Status](./docs/release-candidate.md)

---

## 📚 Documentation

| Document | Description |
|:---|:---|
| [Architecture](./docs/architecture.md) | Full system design, event schemas, DAG model |
| [Model Routing](./docs/model-routing.md) | Four-lane execution model |
| [Local Model Policy](./docs/local-model-policy.md) | Qwen 9B boundaries and restrictions |
| [Scheduler](./docs/scheduler.md) | DAG engine, retries, dead-letter handling |
| [Guardrails](./GUARDRAILS.md) | Safety model and enforcement details |
| [Workspace](./WORKSPACE.md) | Runtime boundaries and ownership |
| [Local Validation](./docs/local-validation.md) | Running the controlled flow locally |
| [Gitea PR Validation](./docs/gitea-pr-validation.md) | PR gate workflow and CI config |
| [CLI Auth & MCP](./docs/cli-auth-and-mcp.md) | Authentication and MCP setup |
| [Contributing](./CONTRIBUTING.md) | How to contribute to this project |

---

<div align="center">

<br>

**AI should accelerate software delivery without dissolving engineering discipline.**

*That's what Future Agents 🇧🇷 is built for.*

<br>

---

<sub>Built with discipline by engineers who believe AI is a tool, not a replacement.</sub>

</div>
