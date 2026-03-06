# CLAUDE.md

This file is the root Claude-facing entrypoint for the repository. Persistent Claude instructions live in `.claude/CLAUDE.md`; narrow constraints live in `.claude/rules/*.md`; curated durable memory lives in `.claude/memory/*.md`. `AGENTS.md` remains the repo-wide canonical contract for architecture and execution boundaries.

## Core Contract
- Keep the assistant-style, local-first, CI-authoritative, human-governed architecture.
- Primary execution agents remain `planner`, `coder`, `tester`, and `reviewer`.
- The scheduler stays separate, Redis Streams stays the only bus, DAG state stays in Redis, and agents communicate only through events.
- CI is authoritative. Merge to `main` requires CI plus explicit human approval.
- Never persist raw conversation or raw transcript content into durable memory.

## Model Split
- Codex: primary code and edit engine.
- Claude Code: primary planning, architecture, deep debugging, and review-assistance engine.
- Ollama `qwen3.5:9b`: helper-only, bounded, and non-authoritative.
- Gemini is legacy-only and out of scope.

## Claude Operating Notes
- Use `.claude/rules/*.md` for narrow, auditable constraints instead of burying extra policy in prompts.
- Use `.claude/memory/*.md` as curated durable context. Distill before saving.
- Prefer one relevant `.agent` skill at a time. Summarize logs and context before escalating.
- If a task touches auth, secrets, migrations, CI, scheduler authority, or final architecture, do not let the local helper decide alone.
