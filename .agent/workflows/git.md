# GIT WORKFLOW
---
description: Hardened WSL-first Git workflow activated by /git for checkpoint, publish, merge into main, and branch rollover.
trigger: /git
args: "{dd/mm/aaaa} {nome-randomico}"
runner: wsl
version: 1.0.0
---

Use this workflow when the current feature branch is ready to be checkpointed, merged into `main`, and rolled over into the next feature branch.

## Invocation

```text
/git 06/03/2026 atlas-raven
```

## Behavior

1. Validate that the command is running inside a Git repository from WSL.
2. Validate that the current branch is not `main`.
3. Validate that `origin` exists and `origin/main` is reachable.
4. Validate that there are no unresolved merge conflicts.
5. If the working tree is dirty, stage and create:
   - `chore(repo): checkpoint 06/03/2026 atlas-raven`
6. Push the current feature branch to `origin`.
7. Switch to `main`.
8. Sync `main` with:
   - `git pull --ff-only origin main`
9. Merge the previous feature branch with:
   - `git merge --no-ff <feature-branch> -m "merge(main): 06/03/2026 atlas-raven"`
10. Push `main` to `origin`.
11. Create the next branch from updated `main`:
   - `feature/20260306-atlas-raven-<hex>`
12. Push the new branch with upstream tracking and leave it checked out.

## Execution

Run:

```bash
bash bootstrap/git-cycle.sh "06/03/2026" "atlas-raven"
```

## Safety Contract

- Run only from WSL.
- Never run from `main`.
- Never use `git reset`, `git clean`, `git rebase`, or force-push.
- Stop on any fetch, pull, merge, or push failure.
- Use `main` as the only merge target.

## Expected Output

- Current feature branch checkpointed and pushed.
- `main` updated and pushed with a merge commit.
- New feature branch created, pushed, and active.
- Final line prints the next branch name.
