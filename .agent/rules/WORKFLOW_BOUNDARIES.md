# Workflow Boundaries

The split between executable workflow guidance and state/evidence artifacts.

## `.agent/workflows/`

- Concise execution playbooks: `/git`, `/pr`, `/validate`, `/release-note`, `/workflow-map`.
- Describes how to run a workflow, expected inputs, and expected outputs.
- May point to scripts and human reference docs.

## `.agent/workflows/` Is Not

- A state store or run-history archive.
- A second repository policy layer.
- A replacement for [`AGENTS.md`](../../AGENTS.md), [`WORKSPACE.md`](../../WORKSPACE.md), [`GUARDRAILS.md`](../../GUARDRAILS.md), or `docs/`.

## State and Evidence

- `.context/runs/`: execution evidence, including `/git` artifacts.
- `.context/workflow/`: workflow-state snapshots and execution history.
