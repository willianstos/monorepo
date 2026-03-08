# /workflow-map
---
description: Generate or refresh a human-readable workflow map or mental model document.
trigger: /workflow-map
args: "{workflow-name}"
runner: any
version: 1.0.0
---

## What it is

A helper for explaining an existing workflow without changing its authority boundary.

## When to use

- When an operator needs a short mental model for an existing workflow.
- To onboard contributors into the execution-vs-state split.
- To verify that a workflow summary still matches the checked-in file.

## Run

```text
/workflow-map validate
```

## Flow

1. **Source read**: read `.agent/workflows/{name}.md`.
2. **Abstraction**: distill it into a short mental model.
3. **Verification**: check the summary against [`../../AGENTS.md`](../../AGENTS.md) and the relevant human docs.

## Outputs

- A concise workflow summary in chat or documentation.

## Guardrails

- Keep the summary short.
- If the summary contradicts the workflow file or the root authority docs, the summary loses.
