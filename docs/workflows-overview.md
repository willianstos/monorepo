# Workflow and State Overview

How the execution layer and state layer are separated. Does not replace root authority files.

## Two Layers

1. **Execution**: [`.agent/workflows/*.md`](../.agent/workflows/README.md) — how to run workflows.
2. **State and evidence**: [`.context/workflow/`](../.context/workflow/README.md) and `.context/runs/` — what happened.

## Where Things Live

| What | Where |
|------|-------|
| Repository contract | [`AGENTS.md`](../AGENTS.md) |
| Repository layout | [`WORKSPACE.md`](../WORKSPACE.md) |
| Safety model | [`GUARDRAILS.md`](../GUARDRAILS.md) |
| Shared operator rules | [`.agent/rules/`](../.agent/rules/README.md) |
| Workflow playbooks | [`.agent/workflows/`](../.agent/workflows/README.md) |
| Workflow state | `.context/workflow/` |
| Run evidence | `.context/runs/` |
| Capability assets | [`.agent/skills/`](../.agent/skills/README.md) |

## Lookup Order

1. [`AGENTS.md`](../AGENTS.md) for the contract.
2. `.agent/rules/*` for the relevant operator rule.
3. `.agent/workflows/*` for execution steps.
4. `.context/workflow/` or `.context/runs/` for current state or evidence.

## Workflow Summary

| Command | Purpose |
|---------|---------|
| `/git` | Close branch work, leave evidence |
| `/pr` | Hand branch into the Gitea PR gate |
| `/validate` | Local validation before the remote gate |
| `/super-review` | Run the deepest local audit before deploy or a high-risk PR |
| `/release-note` | Generate a reviewer-facing or operator-facing change summary |
| `/workflow-map` | Explain an existing workflow without changing authority |

None of these replace CI, review, or human approval.
