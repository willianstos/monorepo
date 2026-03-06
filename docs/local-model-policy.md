# Local Model Policy

> Last Updated: 2026-03-06

This repository treats Ollama `qwen3.5:9b` as a helper model only.

## Low-Risk Helper Principle

`qwen3.5:9b` is:

- cheap
- bounded
- low-risk
- non-authoritative

Its output is advisory until validated by Codex or Claude, the repository diff, and CI.

## Approved Task Classes

- `route_small_task`
- `classify_request`
- `summarize_context`
- `distill_memory`
- `normalize_json`
- `extract_structured_fields`
- `issue_triage`
- `choose_skill_category`
- `explain_policy`
- `summarize_logs`
- `file_inventory_summary`

## Forbidden Task Classes

- final production code for meaningful changes
- auth, authorization, or secrets logic
- database migrations
- CI configuration changes
- production guardrail design
- merge decisions
- review sign-off
- security-sensitive shell choices
- test weakening decisions
- final architecture decisions
- scheduler state-transition authority
- anything that bypasses planner, coder, tester, and reviewer separation

## Allowed And Disallowed Examples

- Allowed: classify an issue as bug or feature, summarize a failing CI log, normalize JSON, compress a long context bundle, extract changed file categories.
- Disallowed: write the final patch for a feature, decide whether to merge, change auth middleware, edit GitHub or Argo CI config, decide that a weakened test is acceptable.

## Token Economy

- Use the local helper to compress or distill when the task is safe and bounded.
- Do not pass giant raw logs to Claude or Codex if a short trusted summary is enough.
- Use category selection before opening skills.
- Load one relevant skill when possible.
- Escalate early when the task becomes ambiguous or sensitive.
