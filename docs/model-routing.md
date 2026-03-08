# Model Routing

Human reference guide. Canonical model authority remains in [`AGENTS.md`](../AGENTS.md).

## Runtime Authority

| Model | Role |
|-------|------|
| Codex | Primary coding and editing engine |
| Claude Code | Primary planning, architecture, deep debugging, review assistance |
| Ollama `qwen3.5:9b` | Local helper: cheap, bounded, low-risk, non-authoritative |
| Gemini | Legacy only, out of scope |

## Task Routing

| Task class | Primary | Notes |
|------------|---------|-------|
| Implementation, refactors, code edits | Codex | Primary coding lane |
| Planning, architecture, deep debugging, review analysis | Claude Code | Primary reasoning lane |
| Classification, routing, JSON normalization | `qwen3.5:9b` | Helper only |
| Context compression, memory distillation, log summarization | `qwen3.5:9b` | Advisory output only |
| Auth, secrets, migrations, CI, guardrails, scheduler authority | Codex or Claude | Never helper-only |
| Ambiguous or safety-affecting work | Codex or Claude | Escalate instead of staying local-helper-only |

## Scope Notes

- Antigravity and similar operator tools are environment surfaces, not runtime model authorities.
- Local-first is a routing preference. It is not a substitute for human approval, CI, or repository authority.

## Escalation

- Tasks that change auth, secrets, migrations, CI, or guardrails must not stay local-helper-only.
- Tasks affecting scheduler authority, merge decisions, or reviewer sign-off must not stay local-helper-only.
- When in doubt, escalate to Codex or Claude.

**Local-first does not mean local-authoritative.** Helper tasks stay local. Authoritative work routes upward. When in doubt, escalate.

See [`local-model-policy.md`](./local-model-policy.md) for the helper-model allowlist and blocklist.
