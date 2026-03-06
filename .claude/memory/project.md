# Project Memory

## Identity

- Repository: `01-monorepo` / `01-monolito`
- Mode: local-first AI coding assistant workspace
- Maturity: release candidate for local controlled operation
- Canonical repo-wide contract: `AGENTS.md`

## Canonical References

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/CLAUDE.md`
- `docs/model-routing.md`
- `docs/local-model-policy.md`
- `GUARDRAILS.md`

## Stable Model Split

- Codex: primary implementation engine
- Claude Code: primary planning, architecture, deep debugging, and review assistance
- Ollama `qwen3.5:9b`: helper-only and non-authoritative

## Memory Tips

- Save durable facts and decisions only.
- Prefer one short distilled note over many session fragments.
