# Shared Workflows

Execution playbooks. Not the repository contract.

## Available Workflows

| Command | Purpose | File |
|---------|---------|------|
| `/git` | Checkpoint and sync the active feature branch to `origin` first, then the `github` mirror | [`git.md`](./git.md) |
| `/pr` | Handoff into the mandatory Gitea master PR gate | [`pr.md`](./pr.md) |
| `/admin-cicd` | Advanced operator handoff into Gitea CI/CD without bypassing the human merge gate | [`admin-cicd.md`](./admin-cicd.md) |
| `/merge-ready` | Final pre-merge checklist for the Gitea master gate | [`merge-ready.md`](./merge-ready.md) |
| `/post-merge` | Restore local baseline after a merge already happened on Gitea | [`post-merge.md`](./post-merge.md) |
| `/validate` | Local validation path | [`validate.md`](./validate.md) |
| `/mcp-fleet` | Converge MCP server config (11 servers, pinned versions) across Claude Code CLI, Codex WSL, Codex Windows, and Claude Desktop | [`mcp-fleet.md`](./mcp-fleet.md) |
| `/super-review` | Deep local pre-deploy audit for security, quality, performance, and architecture | [`super-review.md`](./super-review.md) |
| `/release-note` | Change-summary generation | [`release-note.md`](./release-note.md) |
| `/workflow-map` | Explain an existing workflow | [`workflow-map.md`](./workflow-map.md) |
| `/tutor` | Activate the Antigravity Tutor Persona | [`tutor.md`](./tutor.md) |
| `/compact` | Summarize and persist session state for memory saving | [`compact.md`](./compact.md) |

## Conventions

- Keep workflows thin, explicit, and operational.
- Prefer repository scripts for executable logic.
- Do not embed repository policy in workflow files.
- In Git-host terms, treat `origin`/Gitea as the master authoritative remote and `github` as subordinate mirror-only.
- Keep the workflow index synchronized with every checked-in file in this directory.
- Store workflow state and run history in `.context/workflow/` and `.context/runs/`.
