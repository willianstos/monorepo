# Local Model Policy

Human reference guide for the local helper lane. Authoritative task classes remain in [`AGENTS.md`](../AGENTS.md).

## Helper Model

Ollama `qwen3.5:9b` — cheap, bounded, low-risk, non-authoritative. Output is advisory until validated by Codex or Claude, the repository diff, and CI.

## Approved Tasks

`route_small_task`, `classify_request`, `summarize_context`, `distill_memory`, `normalize_json`, `extract_structured_fields`, `issue_triage`, `choose_skill_category`, `explain_policy`, `summarize_logs`, `file_inventory_summary`

## Forbidden Tasks

Final production code, auth/authorization/secrets logic, database migrations, CI configuration, production guardrail design, merge decisions, review sign-off, security-sensitive shell choices, test weakening, final architecture decisions, scheduler state-transition authority, anything that bypasses planner/coder/tester/reviewer separation.

## Rule of Thumb

Use the local helper to compress, classify, normalize, or summarize. Escalate the moment the task becomes ambiguous, sensitive, or authoritative.
