# /post-merge
---
description: Clean up local state after a PR has been merged through the Gitea master gate.
trigger: /post-merge
args: "{branch-name}"
runner: wsl
version: 1.0.0
---

## What it is

A post-merge hygiene workflow for the operator after the merge already happened in Gitea.

It refreshes the local baseline from `origin/main`, cleans the merged feature branch, and syncs the subordinate GitHub mirror from the authoritative state.

## When to use

- After the PR has been merged on Gitea.
- After a dedicated worktree branch is no longer needed.
- When the local checkout should return to a clean `main` baseline.

## When NOT to use

- Before the PR is merged on Gitea.
- To perform the merge itself.
- To force `main` into either remote before the authoritative Gitea merge exists.

## Run

```text
/post-merge <branch-name>
```

## Equivalent commands

```bash
git switch main
git pull --ff-only origin main
git push github main
git branch -d <branch-name>
git push origin --delete <branch-name>
git push github --delete <branch-name>
git worktree prune
```

## Flow

1. **Confirm merge**: verify the branch was already merged through Gitea.
2. **Refresh baseline**: switch to `main` and fast-forward from `origin/main`.
3. **Mirror authoritative state**: sync `main` to `github` only after `origin/main` is current.
4. **Delete merged branch**: remove the merged branch locally and from remotes when appropriate.
5. **Prune worktrees**: remove stale worktree metadata and any merged smoke branches if needed.

## Guardrails

- Run only from WSL.
- Never push to `origin/main` here; Gitea already authored the canonical merge.
- `git push github main` is subordinate mirror maintenance only and must happen after `origin/main` is current.
- Do not delete a branch until the authoritative merge is confirmed.
- If branch deletion fails on a mirror, keep going on the authoritative host and record the mismatch.

## Post-Merge Checklist

- [ ] PR merge is confirmed on Gitea.
- [ ] Local `main` was refreshed with `git pull --ff-only origin main`.
- [ ] GitHub mirror `main` was synced only from the refreshed local `main`.
- [ ] The merged feature branch was deleted locally.
- [ ] The merged feature branch was deleted from `origin`.
- [ ] The merged feature branch was deleted from `github` when available.
- [ ] Dedicated worktrees were pruned or removed.

## Mental model

`/post-merge` restores the operator baseline after the authoritative merge is already complete.
