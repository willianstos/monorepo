# AGENTS.md

Single global repository contract for `Future Agents`. All other instruction files must stay consistent with this one.

## Authority Hierarchy

- `AGENTS.md` is the single global repository contract.
- This hierarchy is frozen. Changes require explicit human review in a PR.
- Operational rules: `.agent/rules/`
- Workflows: `.agent/workflows/`
- Skills: `.agent/skills/`
- Claude-specific extensions: `.claude/`
- `.context/` is state and evidence only. It carries no policy authority.
- Legacy and tool-specific files are compatibility pointers only.

## Repository Identity

Local-first AI coding assistant workspace for controlled software delivery. Assistant-style, human-governed, CI-authoritative. Not an autonomous company, not a swarm, not an alternate agent hierarchy.

| Directory | Role |
|-----------|------|
| `workspace/` | Shared runtime (scheduler, providers, tools, memory) |
| `projects/` | Target repositories |
| `.agent/` | Shared skills, workflows, and operator rules |

## Architecture

- Primary agents: `planner`, `coder`, `tester`, `reviewer`. No others.
- Scheduler: separate service.
- Event bus: Redis Streams only.
- DAG state: persisted in Redis.
- Agent communication: events only. No direct agent-to-agent calls.
- CI: authoritative.
- Merge to `main`: requires human approval after CI passes.
- Local-first routing: preserved.
- Raw conversation logs: never enter durable memory.

## Agent Boundaries

| Agent | Scope |
|-------|-------|
| `planner` | Scope work, acceptance criteria, ordering, risk |
| `coder` | Implementation code only |
| `tester` | Tests, fixtures, and validation only |
| `reviewer` | Quality, risk, and policy review only |

No direct agent-to-agent calls. Do not collapse coder, tester, and reviewer into one step.

## Model Authority

| Model | Role |
|-------|------|
| Codex | Primary coding and editing engine |
| Claude Code | Primary planning, architecture, deep debugging, review assistance |
| Ollama `qwen3.5:9b` | Helper only: cheap, bounded, low-risk, non-authoritative |
| Gemini | Legacy only, out of scope |

Ambiguous, sensitive, security-affecting, or architecture-affecting tasks must escalate to Codex or Claude. Local model output is advisory until validated by Codex or Claude, the repository diff, and CI.

## Local Helper Lane

`qwen3.5:9b` approved tasks: `classify_request`, `route_small_task`, `summarize_context`, `distill_memory`, `normalize_json`, `extract_structured_fields`, `issue_triage`, `choose_skill_category`, `explain_policy`, `summarize_logs`, `file_inventory_summary`.

`qwen3.5:9b` forbidden tasks: final production code, auth/authorization/secrets logic, database migrations, CI configuration, production guardrail design, merge decisions, review sign-off, security-sensitive shell decisions, test weakening, scheduler state-transition authority, final architecture decisions, anything that bypasses planner/coder/tester/reviewer separation.

## Memory Rules

- Working memory: transient task state.
- Session memory: short-lived continuity.
- Durable project memory: distilled facts, decisions, constraints, and lessons only.
- Human and Claude durable memory: `.claude/memory/*.md`
- Shared tool-agnostic notes: `.agent/memory/`
- Runtime memory writes: structured, deduplicated, tagged, free of raw transcripts.

Save stable decisions, architecture constraints, validated lessons, and short operator notes. Do not save raw chats, logs, prompt dumps, secrets, or duplicate summaries. Keep memory short enough to reuse without reopening the original session.

## Skills and Token Economy

- `AGENTS.md` is the repo-native instruction layer for Codex. No parallel Codex-only prompt system.
- Shared reusable assets: `.agent/skills/` and `.agent/workflows/`
- Choose a category first, load one relevant skill when possible.
- Summarize large generated context before handing it to Codex or Claude.
- Use the local helper for compression or distillation when safe.

## Delivery Rules

- Tool use: repository-scoped, bounded, auditable.
- `coder` does not edit tests or CI config.
- `tester` does not weaken tests or edit implementation files.
- `reviewer` may block progress but does not mutate code during review.
- No direct push to `main`.
- Required path: `branch -> commit -> CI -> review -> human approval -> merge`.
- No agent may claim success without CI evidence.

## Validation

- Python 3.11+
- Install: `python -m pip install -e .[dev]`
- Tests: `python -m pytest` (full) or `python -m pytest -k <pattern>` (iterating)
- Lint and types: `python -m ruff check workspace projects` and `python -m mypy workspace`
- Generated artifacts go in `.context/` for deterministic reruns.
