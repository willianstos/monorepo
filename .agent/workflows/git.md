# /git
---
description: WSL-first Git workflow for checkpointing and synchronizing feature branches.
trigger: /git
args: "[--merge-main] [--scope <paths>] [--allow-wide-merge] {dd/mm/aaaa} {branch-slug}"
runner: wsl
version: 3.1.0
---

> Last Updated: 08/03/2026

This file is the `/git` execution playbook. Repository Git policy remains in [`AGENTS.md`](../../AGENTS.md), [`docs/guide_git.md`](../../docs/guide_git.md), and [`docs/contracts/worktree-policy.md`](../../docs/contracts/worktree-policy.md). Gitea PR enforcement details live in [`docs/gitea-pr-validation.md`](../../docs/gitea-pr-validation.md).

## What it is

A WSL-first checkpoint and sync workflow for feature branches. It records branch work and publishes it to the configured remotes without replacing the protected PR gate.

`/git` assumes branch work is already happening in the correct checkout or dedicated worktree. It does not create or choose the worktree.

## When to use

- To save progress on a feature branch.
- To push changes to local Gitea (`origin`) and sync the GitHub mirror (`github`) when configured by `bootstrap/git-cycle.sh`.
- To leave completion evidence for branch work.

## When NOT to use

- For direct merges into `main` outside the documented PR process.
- To replace PR review, CI, or human approval.

## Run

```text
/git <dd/mm/aaaa> <branch-slug>
```

## Equivalent command

```bash
bash bootstrap/git-cycle.sh "<dd/mm/aaaa>" "<branch-slug>"
```

If mutable work needs isolation first:

```bash
bash bootstrap/git-worktree.sh create "<dd/mm/aaaa>" "<branch-slug>"
```

One-time GitHub mirror bootstrap for this WSL profile:

```bash
bash bootstrap/github-mirror-auth.sh ensure
```

Default behavior:

- creates a checkpoint commit only if the feature branch is dirty
- ensures GitHub CLI auth and git credential helper once when the `github` remote exists
- pushes the active feature branch to local Gitea (`origin`) and then attempts to sync the GitHub mirror (`github`)
- records the run under `.context/runs/git/`
- does not merge into `main`

Preview only:

```bash
bash bootstrap/git-cycle.sh --dry-run "<dd/mm/aaaa>" "<branch-slug>"
```

Explicit merge into `main` after CI, review, and human approval:

```bash
bash bootstrap/git-cycle.sh --merge-main --scope ".agent/workflows,.agent/rules" "<dd/mm/aaaa>" "<branch-slug>"
```

For an approved full-branch merge (rare):

```bash
bash bootstrap/git-cycle.sh --merge-main --allow-wide-merge "<dd/mm/aaaa>" "<branch-slug>"
```

Cleanup merged smoke branches:

```bash
bash bootstrap/git-cycle.sh --cleanup-smoke
```

## Flow

1. **Checkpoint**: creates a commit if the branch is dirty.
2. **Scope check**: on `--merge-main`, requires one of:
   - explicit path scope via `--scope` (recommended), or
   - `--allow-wide-merge` with explicit human approval.
3. **Sync**: pushes the active branch to Gitea and then attempts GitHub mirror sync when configured.
4. **Record**: logs execution details in `.context/runs/git/`.

## Outputs

- Active branch pushed to `origin`.
- GitHub mirror sync attempted when `github` is configured.
- Run metadata in `.context/runs/git/`.

## Guardrails

- **WSL-only**: run from WSL.
- **Worktree-first for concurrent mutable work**: if another mutable task may run in parallel, create a dedicated worktree before `/git`.
- **No default merge**: `/git` does not imply merge to `main`.
- **Gitea stays authoritative**: GitHub mirror sync is secondary and does not replace the Gitea PR, CI, or merge gate.
- **PR path remains mandatory**: use Gitea PR review plus CI and human approval before merging to `main`.
- **Merge scope guard**: `--merge-main` requires explicit scope by default (`--scope`), except `--allow-wide-merge` for approved cross-cutting changes.
- **Scope of change**: `--merge-main` now refuses to run on a dirty branch; checkpoint first with `/git` plain mode.
- **State evidence**: run history lives under `.context/runs/git/` and `.context/workflow/`.

## Contract

- Run from WSL only.
- Use `bootstrap/git-worktree.sh` for standard worktree creation when isolation is needed.
- Use `/git` as completion evidence for feature-branch work.
- Use `main` as the merge target only with `--merge-main` and the documented approval path.
- Keep dangerous Git operations out of the workflow.

## Mental model

`/git` closes branch work and syncs it; it does not replace the PR gate.
