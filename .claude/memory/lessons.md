# Lessons Memory

## Durable Lessons

- Keep instructions repo-native and auditable. Prefer `AGENTS.md`, `CLAUDE.md`, and checked-in rule files over hidden prompts.
- Distill memory before saving it. Raw transcripts and raw logs create noise and policy risk.
- Use the local helper model to compress, classify, or normalize when safe, then escalate authority to Codex or Claude.
- Load shared skills sparsely. One relevant skill is usually better than scanning an entire catalog.
- Keep coder, tester, and reviewer boundaries strict. CI and human approval remain the final gates.
