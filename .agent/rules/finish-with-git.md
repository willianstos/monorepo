# Finish With /git

> Last Updated: 06/03/2026

Every completed task must end with a Git checkpoint before the assistant reports completion.

## Rule

- Run `/git {dd/mm/aaaa} {nome-randomico}` from WSL before declaring work complete.
- The default `/git` flow is checkpoint-only: it commits pending work if needed and pushes the active feature branch.
- Merge into `main` is never implied by task completion.
- Merge into `main` requires explicit `--merge-main`, passing CI, review, and human approval.
- Persist every `/git` run under `.context/runs/git/`.

## Equivalent Command

```bash
bash bootstrap/git-cycle.sh "06/03/2026" "atlas-raven"
```

Explicit merge path:

```bash
bash bootstrap/git-cycle.sh --merge-main "06/03/2026" "atlas-raven"
```

## Completion Evidence

- A task is not complete until the active branch has a recorded `/git` run.
- If the runner cannot invoke `/git`, use the script directly and keep the generated audit trail.
