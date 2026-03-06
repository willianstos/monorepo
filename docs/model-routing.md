# Model Routing

> Last Updated: 2026-03-06

This document is the canonical model-routing policy for the repository.

## Authority Split

- Active authoritative CLI lanes: Codex CLI and Claude Code CLI.
- Codex: primary code generation, repository edits, and implementation work.
- Claude Code: primary planning, architecture, deep debugging, and review assistance.
- Ollama `qwen3.5:9b`: local helper only for cheap, bounded, low-risk tasks.
- Antigravity: IDE environment and shared skill consumer, not headless runtime authority.
- Gemini: legacy-only and out of scope for this repository standard.

## Local-First Meaning

Local-first does not mean local-authoritative. It means safe helper tasks may stay local first, while ambiguous, sensitive, or authoritative work routes upward to Codex or Claude.

## Routing Table

| Task class | Primary model/tool | Notes |
| --- | --- | --- |
| Implementation, refactors, code edits, test code changes | Codex | Main coding engine |
| Planning, architecture, deep debugging, review analysis | Claude Code | Main reasoning engine |
| Request classification, route selection, JSON normalization | Ollama `qwen3.5:9b` | Helper-only |
| Context compression, memory distillation, log summarization | Ollama `qwen3.5:9b` | Advisory output only |
| Ambiguous, sensitive, auth, secrets, migrations, CI, guardrails | Claude Code or Codex | Never local-helper-only |

## Escalation Rules

- If the task changes auth, authorization, secrets, migrations, CI, or production guardrails, do not keep it local.
- If the task affects scheduler authority, merge decisions, or reviewer sign-off, do not keep it local.
- If the task is unclear, route to Claude for reasoning or Codex for implementation, not to the helper model alone.
