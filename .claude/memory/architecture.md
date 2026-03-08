# Architecture Memory

Architecture invariants and agent roles are defined in `AGENTS.md`.

## Key Surfaces

- `.agent/`: shared skills, workflows, and tool-agnostic notes
- `.claude/`: Claude rules and curated durable memory
- `.context/`: generated state, evidence, and retrieval artifacts only
- `workspace/config/`: declarative agent, routing, tool, and memory policy
