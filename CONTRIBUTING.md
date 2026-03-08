# Contributing

Setup, validation, and change boundaries for the Future Agents workspace. Most changes touch architecture contracts, scheduler rules, provider routing, tool policy, or documentation rather than a fully wired production runtime.

Last Updated: 08/03/2026

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install: `python -m pip install -e .[dev]`
3. Keep generated artifacts inside `.context/`.

## Validation Commands

```bash
# Unit tests
python -m pytest

# Specific pattern
python -m pytest -k <pattern>

# Lint
python -m ruff check workspace projects

# Type check
python -m mypy workspace

# Redis integration (start Redis first)
docker compose -f docker-compose.redis.yml up -d redis-integration
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 python -m pytest workspace/scheduler/test_redis_integration.py -q

# End-to-end controlled flow
REDIS_PORT=6380 REDIS_DB=15 python bootstrap/local_validation.py controlled-flow \
  --reset-db --graph-id rc-local-001 --objective "RC validation" --project-name 01-monolito

# Git checkpoint (from WSL)
bash bootstrap/git-cycle.sh "dd/mm/yyyy" "branch-slug"

# Standard mutable isolation (from WSL)
bash bootstrap/git-worktree.sh create "dd/mm/yyyy" "branch-slug"
```

## Change Boundaries

| Area | Where to edit |
|------|---------------|
| Skills, catalogs, agent memory | `.agent/` |
| Python source and contracts | `workspace/` |
| Safety policy | `GUARDRAILS.md` + `guardrails/` together |
| Docs, README, workspace map | `docs/`, `README.md`, `WORKSPACE.md` |
| Bootstrap and developer environment | `bootstrap/` |
| Generated state and evidence | `.context/` only |
| Target project seeds | `projects/` |

## Worktree Baseline

- Primary checkout is the stable operator baseline.
- Concurrent mutable work uses a dedicated worktree.
- Standard operator worktree root: `../.worktrees/<repo-name>/<yyyymmdd>/<branch-name>`.
- Standard helper: `bash bootstrap/git-worktree.sh create "dd/mm/aaaa" "branch-slug"`.
- Worktree policy: [`docs/contracts/worktree-policy.md`](docs/contracts/worktree-policy.md).
- End-to-end feature path for day-to-day delivery: [`docs/guide_feature_delivery.md`](docs/guide_feature_delivery.md).
- Advanced maintainer/operator path for CI/CD and merge closure: [`docs/guide_admin_cicd.md`](docs/guide_admin_cicd.md).

## CI and PR Gate

All changes to `main` pass through a Gitea pull request. The pipeline runs:

The local Gitea repository may be public-readable. That visibility is distribution-only and does not move authority. GitHub remains a mirror and does not own PR, CI, or merge decisions for this repository.

| Check | Command |
|-------|---------|
| Lint | `python -m ruff check workspace projects` |
| Type check | `python -m mypy workspace` |
| Unit tests | `python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q` |
| Integration tests | `python -m pytest workspace/scheduler/test_redis_integration.py -q` |

All four checks must pass. At least one human approval is required. No merge without CI + human approval.

See [`docs/gitea-pr-validation.md`](docs/gitea-pr-validation.md) for pipeline setup and branch protection.

## Documentation Conventions

- Keep top-level docs aligned with repository structure changes.
- Use `Last Updated: dd/mm/yyyy` format when touching dated docs.
- Put new canonical guidance in `docs/`, `README.md`, `WORKSPACE.md`, `AGENTS.md`, or `.agent/` per the frozen hierarchy.
- Treat `.context/` indexes as generated lookup aids only.

## Authority Freeze Checklist

- [ ] No new competing instruction source was created.
- [ ] Operational rules stay in `.agent/rules/`.
- [ ] Workflow logic stays in `.agent/workflows/`.
- [ ] Shared skills stay in `.agent/skills/`.
- [ ] `.context/` was not turned into policy authority.
- [ ] Any retained legacy file is explicitly non-authoritative and points to the canonical source.
- [ ] Any hierarchy change is intentional and flagged for human review in the PR.
