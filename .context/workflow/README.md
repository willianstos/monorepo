# Workflow State Layer

Non-authoritative. State, not policy.

Stores workflow run-state artifacts and execution history:

- `actions.jsonl` / `status.yaml` — observed workflow state transitions.
- `plans.json` / `plan-tracking/` — captured plan-state snapshots.

Policy lives in `AGENTS.md`, `.agent/rules/`, and `.agent/workflows/`.
