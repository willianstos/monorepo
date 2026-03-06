# /git
---
description: Hardened WSL-first Git workflow activated by /git for checkpoint, publish, merge into main, branch rollover, dry runs, and smoke cleanup.
trigger: /git
args: "{dd/mm/aaaa} {nome-randomico}"
runner: wsl
version: 2.0.0
---

This workflow delegates all operational logic to `bootstrap/git-cycle.sh`.

## Run

```text
/git 06/03/2026 atlas-raven
```

Equivalent command:

```bash
bash bootstrap/git-cycle.sh "06/03/2026" "atlas-raven"
```

Preview only:

```bash
bash bootstrap/git-cycle.sh --dry-run "06/03/2026" "atlas-raven"
```

Cleanup merged smoke branches:

```bash
bash bootstrap/git-cycle.sh --cleanup-smoke
```

## Contract

- Run from WSL only.
- Use `main` as the only merge target.
- Keep dangerous Git operations out of the workflow.
- Persist every run under `.context/runs/git/`.
