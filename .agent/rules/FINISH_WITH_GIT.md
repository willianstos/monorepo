# Finish With `/git`

Every completed task must end with a `/git` checkpoint before reporting completion.

## Rule

- Run `/git {dd/mm/aaaa} {branch-slug}` from WSL before declaring work complete.
- Persist every `/git` run under `.context/runs/git/`.
- `/git` is a branch checkpoint and sync step. It does not replace the PR path or the merge gate.

## Equivalent Command

```bash
bash bootstrap/git-cycle.sh "{dd/mm/aaaa}" "{branch-slug}"
```

## Git Chain

[`AGENTS.md`](../../AGENTS.md) > [`docs/guide_git.md`](../../docs/guide_git.md) > [`workflows/git.md`](../workflows/git.md) > [`docs/gitea-pr-validation.md`](../../docs/gitea-pr-validation.md)
