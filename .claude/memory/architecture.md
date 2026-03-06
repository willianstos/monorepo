# Architecture Memory

## Fixed Decisions

- Scheduler is a separate service.
- Redis Streams is the only event and task bus.
- DAG state persists in Redis.
- Agents communicate only through events.
- CI is authoritative.
- Merge to `main` requires human approval after CI passes.
- Local-first routing is preserved.
- Raw conversation logs are forbidden in durable memory.

## Primary Execution Agents

- `planner`: scope, acceptance criteria, ordering, and risk
- `coder`: implementation code only
- `tester`: tests, fixtures, and validation only
- `reviewer`: review quality, risk, and guardrail compliance only

## Shared Surfaces

- `.agent/`: shared skills, workflows, and tool-agnostic notes
- `.claude/`: Claude rules and curated durable memory
- `workspace/config/`: declarative agent, routing, tool, and memory policy
