# Claude Project Instructions

This file is the persistent Claude-facing instruction layer for the repository. It must remain consistent with `AGENTS.md`.

## Core Truths

- This repository is a local-first AI coding assistant workspace, not an autonomous company or swarm.
- Primary execution agents remain `planner`, `coder`, `tester`, and `reviewer`.
- The scheduler is a separate service.
- Redis Streams is the only event and task bus.
- DAG state persists in Redis.
- Agents communicate only through events.
- CI is authoritative.
- Merge to `main` requires passing CI and explicit human approval.

## Model Authority

- Codex is the main coding and editing engine.
- Claude Code is the main planning, architecture, deep debugging, and review-assistance engine.
- Ollama `qwen3.5:9b` is helper-only, low-cost, low-risk, and non-authoritative.
- Gemini is legacy-only and out of scope for this repository standard.
- If a task is ambiguous, sensitive, or architecture-affecting, do not let the local helper decide alone.

## Claude Rule Files

Use narrow rule files instead of burying policy in prompts:

- `.claude/rules/global.md`
- `.claude/rules/local-model-boundaries.md`
- `.claude/rules/ci-and-approval.md`

## Memory Behavior

- Prefer distilled durable memory over replaying old sessions.
- Never persist raw conversation, raw prompts, or raw logs into long-term memory.
- Use `.claude/memory/*.md` as curated durable project context.
- Runtime machine memory stays on the structured Redis-backed path already implemented in `workspace/memory/`.
- Distill, deduplicate, and keep entries short.

## Memory Tips

- Save stable facts, architecture decisions, durable constraints, and validated lessons.
- Do not save raw transcripts, prompt dumps, secrets, or duplicate summaries.
- Flush distilled memory when ending a task, switching branches, or intentionally discarding context.
- Keep memory short enough to read in one pass.

## Skills And Token Economy

- Shared skills and workflows live under `.agent/`.
- Prefer category selection first and load one relevant skill when possible.
- Do not bulk-load entire skill catalogs.
- Summarize large logs or context before handing them to Claude or Codex.
- When safe, let the local helper compress or normalize context before escalation.

## Operator Notes

- `/mcp` is the Claude operator path for MCP connections and authentication management.
- `/memory` is the Claude operator path for memory handling.
- Keep Claude terminal, IDE, and desktop behavior aligned with the same repo-authored instructions and memory files.
