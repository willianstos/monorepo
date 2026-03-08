# Shared Workflows

Execution playbooks. Not the repository contract.

## Available Workflows

| Command | Purpose | File |
|---------|---------|------|
| `/git` | Checkpoint and sync the active feature branch | [`git.md`](./git.md) |
| `/pr` | Handoff into the mandatory Gitea PR gate | [`pr.md`](./pr.md) |
| `/validate` | Local validation path | [`validate.md`](./validate.md) |
| `/super-review` | Deep local pre-deploy audit for security, quality, performance, and architecture | [`super-review.md`](./super-review.md) |
| `/release-note` | Change-summary generation | [`release-note.md`](./release-note.md) |
| `/workflow-map` | Explain an existing workflow | [`workflow-map.md`](./workflow-map.md) |

## Conventions

- Keep workflows thin, explicit, and operational.
- Prefer repository scripts for executable logic.
- Do not embed repository policy in workflow files.
- Keep the workflow index synchronized with every checked-in file in this directory.
- Store workflow state and run history in `.context/workflow/` and `.context/runs/`.
