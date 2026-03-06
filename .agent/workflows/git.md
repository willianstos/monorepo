# /git
---
description: Hardened WSL-first Git workflow activated by /git for checkpoint, publish, explicit merge into main, branch rollover, dry runs, and smoke cleanup.
trigger: /git
args: "[--merge-main] {dd/mm/aaaa} {nome-randomico}"
runner: wsl
version: 3.0.0
---

> Last Updated: 06/03/2026

This workflow delegates all operational logic to `bootstrap/git-cycle.sh`.

## Run

```text
/git 06/03/2026 atlas-raven
```

Explicit merge form:

```text
/git --merge-main 06/03/2026 atlas-raven
```

Equivalent command:

```bash
bash bootstrap/git-cycle.sh "06/03/2026" "atlas-raven"
```

Default behavior:

- create a checkpoint commit only if the feature branch is dirty
- push the active feature branch to both local Gitea (`origin`) and GitHub cloud (`github`)
- record the run under `.context/runs/git/`
- do not merge into `main`

Preview only:

```bash
bash bootstrap/git-cycle.sh --dry-run "06/03/2026" "atlas-raven"
```

Explicit merge into `main` after CI, review, and human approval:

```bash
bash bootstrap/git-cycle.sh --merge-main "06/03/2026" "atlas-raven"
```

Cleanup merged smoke branches:

```bash
bash bootstrap/git-cycle.sh --cleanup-smoke
```

## Contract

- Run from WSL only.
- Treat `/git` as mandatory completion evidence for feature-branch work.
- Use `main` as the only merge target when `--merge-main` is explicitly requested.
- Keep dangerous Git operations out of the workflow.
- Persist every run under `.context/runs/git/`.
