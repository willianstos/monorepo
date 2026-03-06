# AGENTS.md

This file is the canonical Codex-facing instruction layer for `Future Agents`. Claude-specific files under `CLAUDE.md` and `.claude/` may add workflow detail, but they must stay consistent with this file.

## Repository Identity
- Local-first AI coding assistant workspace for controlled software delivery.
- Assistant-style, human-governed, and CI-authoritative. Do not turn it into an autonomous company, swarm, or alternate agent hierarchy.
- Shared runtime lives in `workspace/`, target repositories live in `projects/`, and shared skills/workflows live in `.agent/`.

## Fixed Architecture
- `planner`, `coder`, `tester`, and `reviewer` are the only primary execution agents.
- The scheduler is a separate service.
- Redis Streams is the only event and task bus.
- DAG state persists in Redis.
- Agents communicate only through events.
- CI is authoritative.
- Merge to `main` always requires human approval after CI passes.
- Local-first routing is preserved.
- Raw conversation logs must never enter durable memory.

## Agent Boundaries
- `planner`: scope work, acceptance criteria, ordering, and risk.
- `coder`: implementation code only.
- `tester`: tests, fixtures, and validation only.
- `reviewer`: quality, risk, and policy review only.
- No direct agent-to-agent calls.
- Do not collapse coder, tester, and reviewer authority into one step.

## Model Authority
- Codex is the primary coding and editing engine.
- Claude Code is the primary planning, architecture, deep debugging, and review-assistance engine.
- Ollama `qwen3.5:9b` is helper-only: cheap, bounded, low-risk, and non-authoritative.
- Gemini is legacy-only and out of scope for this repository standard.
- If a task is ambiguous, sensitive, security-affecting, architecture-affecting, or changes auth, secrets, migrations, CI, or guardrails, escalate to Codex or Claude.

## Local Helper Lane
`qwen3.5:9b` may be used for:
- `classify_request`
- `route_small_task`
- `summarize_context`
- `distill_memory`
- `normalize_json`
- `extract_structured_fields`
- `issue_triage`
- `choose_skill_category`
- `explain_policy`
- `summarize_logs`
- `file_inventory_summary`

`qwen3.5:9b` must not be used for:
- final production code for meaningful changes
- auth, authorization, or secrets logic
- database migrations
- CI configuration changes
- production guardrail design
- merge decisions or review sign-off
- security-sensitive shell decisions
- weakening tests
- scheduler state-transition authority
- final architecture decisions
- anything that bypasses planner/coder/tester/reviewer separation

Local model output is advisory until validated by Codex or Claude, the repository diff, and CI.

## Memory Rules
- Working memory is transient task state.
- Session memory is short-lived continuity.
- Durable project memory must contain distilled facts, decisions, constraints, and lessons only.
- Human and Claude durable memory lives in `.claude/memory/*.md`.
- Shared tool-agnostic notes live in `.agent/memory/`.
- Runtime memory writes must stay structured, deduplicated, tagged, and free of raw transcripts.

## Memory Tips
- Save stable decisions, architecture constraints, validated lessons, and short operator notes.
- Do not save raw chats, raw logs, prompt dumps, secrets, or duplicate summaries.
- Flush distilled memory when ending a task, switching branches, or discarding session context.
- Keep memory short enough to reuse without reopening the original session.

## Skills And Token Economy
- `AGENTS.md` is the repo-native instruction layer for Codex. Do not add a parallel Codex-only prompt system.
- Shared reusable assets live under `.agent/skills/` and `.agent/workflows/`.
- Do not bulk-load skills or entire catalogs.
- Choose a category first and load one relevant skill when possible.
- Summarize large generated context before handing it to Codex or Claude.
- When safe, use the local helper model for compression or distillation before escalating.
- Do not pass giant raw logs to stronger models unless necessary.

## Tool And Delivery Rules
- Tool use must stay repo-scoped, bounded, and auditable.
- `coder` does not edit tests or CI config.
- `tester` does not weaken tests or edit implementation files.
- `reviewer` may block progress but does not mutate code as part of review.
- No direct push to `main`.
- Required path remains `branch -> commit -> CI -> review -> human approval -> merge`.

## Validation
- Use Python 3.11 or newer.
- Install dependencies with `python -m pip install -e .[dev]`.
- Run `python -m pytest` for full validation and `python -m pytest -k <pattern>` while iterating.
- Run `python -m ruff check workspace projects` and `python -m mypy workspace` before shipping runtime, scheduler, provider, guardrail, or memory changes.
- Store generated artefacts in `.context/` so reruns stay deterministic.
