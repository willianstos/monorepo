# Worktree Standard

Baseline adopted on 08/03/2026.

Canonical chain:

1. [`AGENTS.md`](../../AGENTS.md)
2. [`docs/guide_git.md`](../../docs/guide_git.md)
3. [`docs/contracts/worktree-policy.md`](../../docs/contracts/worktree-policy.md)
4. [`bootstrap/git-worktree.sh`](../../bootstrap/git-worktree.sh)
5. [`.agent/workflows/git.md`](../workflows/git.md)

## Rule

- Mutable work that may run concurrently must use a dedicated `git worktree`.
- Read-only work may stay in the primary checkout.
- The primary checkout remains the operator baseline and must not carry multiple independent mutable tasks at once.
- The standard operator worktree root is a sibling path outside the repo:
  - `../.worktrees/<repo-name>/<yyyymmdd>/<branch-name>`
- The standard branch shape for worktree-created feature work is:
  - `feature/<yyyymmdd>-<slug>-<random>`
- Worktrees do not change Git authority. They are local isolation only.
- No worktree may push directly to `main`.
- Cleanup is mandatory after merge or explicit abandonment.

## Commands

Create:

```bash
bash bootstrap/git-worktree.sh create "08/03/2026" "agent-workflows-main"
```

List:

```bash
bash bootstrap/git-worktree.sh list
```

Remove:

```bash
bash bootstrap/git-worktree.sh remove ../.worktrees/01-monorepo/20260308/feature-20260308-agent-workflows-main-79b7ee
```
