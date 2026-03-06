# Local Model Boundaries

Ollama `qwen3.5:9b` is helper-only and non-authoritative.

Allowed:
- request classification
- route selection
- context summarization
- memory distillation
- JSON normalization
- structured extraction
- issue triage
- skill-category selection
- policy explanation
- log summarization
- lightweight file inventory summaries

Forbidden:
- final production code for meaningful changes
- auth, authorization, or secrets logic
- database migrations
- CI configuration changes
- production guardrail design
- merge decisions
- review sign-off
- security-sensitive shell choices
- test weakening choices
- final architecture decisions
- scheduler state-transition authority
- anything that bypasses planner, coder, tester, and reviewer separation

If the task is ambiguous, sensitive, or architecture-affecting, escalate to Codex or Claude.
