# Workspace Conventions

> Last Updated: 2026-03-06

## Purpose

The monorepo separates the shared assistant runtime from target projects and operator-facing guidance:

- `workspace/`: shared runtime, scheduler integration, providers, tools, and memory adapters.
- `projects/`: target repositories the workspace may inspect and modify.
- `.agent/`: shared skills, workflows, and tool-agnostic memory notes.
- `.claude/`: Claude-specific rules and curated durable project memory.
- `docs/`: human-authored architecture, routing, policy, and operating documentation.
- `guardrails/`: machine-readable repository policy files.

## Fixed Architectural Rules

- The scheduler is a separate service.
- Redis Streams is the only event and task bus.
- DAG state persists in Redis.
- Agents communicate only through events.
- Primary execution agents remain `planner`, `coder`, `tester`, and `reviewer`.
- CI is authoritative.
- Merge to `main` requires human approval after CI passes.
- Local-first routing is preserved without giving the local helper model coding authority.

## Model And Tool Boundaries

- Codex owns primary implementation and repo edits.
- Claude owns primary planning, architecture, deep debugging, and review assistance.
- Ollama `qwen3.5:9b` is limited to bounded helper tasks such as classification, routing, summarization, extraction, and memory distillation.
- Provider choice should stay declarative through `workspace/config/`, not hardcoded through ad hoc prompts.
- Tool adapters stay isolated in `workspace/tools/`, and tool use remains repo-scoped and auditable.

## Memory Standard

- Working memory: transient task state.
- Session memory: recent continuity.
- Runtime durable memory: distilled structured records on the Redis-backed runtime path.
- Human and Claude durable memory: `.claude/memory/*.md`.
- Shared tool-agnostic notes: `.agent/memory/`.
- Raw conversations, prompt dumps, and raw logs do not belong in durable memory.

## Operating Model

- Default flow is `issue_created -> planner -> coder -> tester -> reviewer -> human approval -> merge`.
- CI failures route into scheduler-managed fix loops before review and merge can continue.
- Reviewer failures and rejected human approval block graph progression.
- Local repository wrap-up still requires a `/git` checkpoint on the active feature branch before work is reported complete.
- `/git` defaults to checkpoint-and-push on the feature branch. Merge into `main` stays explicit and gated.
- LangGraph remains descriptive here; the scheduler, event bus, and guardrails are the implemented authority.

## Editing Guide

- Edit `AGENTS.md` when Codex-facing repository rules change.
- Edit `CLAUDE.md` and `.claude/` when Claude-facing rules or durable memory structure changes.
- Edit `README.md` when the repo overview, maturity, or operator entrypoints change.
- Edit `WORKSPACE.md` when runtime ownership or orchestration boundaries change.
- Edit `GUARDRAILS.md` and `guardrails/` together when safety policy changes.
- Edit `.context/` indexes when adding new operator docs or playbooks.
