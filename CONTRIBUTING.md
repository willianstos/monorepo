# Contributing

> Last Updated: 06/03/2026

This repository is a Python blueprint for a local-first AI coding assistant workspace. Most changes will touch architecture contracts, scheduler rules, provider routing, tool policy, or supporting documentation rather than a fully wired production runtime.

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install the package and development tooling with `.context/.venv/bin/python -m pip install -e .[dev]` or the equivalent active-venv `python -m pip install -e .[dev]`.
3. Keep generated notes, scaffolds, and run artefacts inside `.context/`.

## Common Commands

- `.context/.venv/bin/python -m pytest`
- `.context/.venv/bin/python -m pytest -k <pattern>`
- `.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py -q`
- `REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q`
- `.context/.venv/bin/python -m ruff check workspace projects`
- `.context/.venv/bin/python -m mypy workspace`
- `REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py snapshot`
- `REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow --reset-db --graph-id rc-local-001 --objective "RC validation" --project-name 01-monolito`
- `bash bootstrap/git-cycle.sh "06/03/2026" "nome-randomico"`

## Change Boundaries

- Edit `.agent/` when curating local skills, vendored skill catalogs, workflow notes, or agent-local memory assets. Treat `.agent/catalogs/` as vendored third-party content unless the change is intentional.
- Edit `workspace/` for Python source, contracts, and blueprint runtime behavior.
- Edit `guardrails/` and `GUARDRAILS.md` together when policy changes.
- Edit `docs/`, `README.md`, and `WORKSPACE.md` when architecture or operating rules change.
- Edit `bootstrap/` for Windows/WSL bootstrap, healthcheck, and developer environment automation.
- Edit `.context/` indexes when adding new reusable documentation or agent playbooks.
- Edit `projects/` only for target-project seeds and project-specific notes.

## Documentation Expectations

- Keep top-level docs aligned with repository structure changes.
- Keep repo-owned markdown docs on the current `Last Updated: 06/03/2026` format when they are touched.
- Do not describe the repository as "placeholders only" when the scheduler/event-bus/runtime contracts are implemented.
- Link new long-lived guidance from `.context/docs/README.md`.
- Link new reusable agent instructions from `.context/agents/README.md`.
- Include sample payloads or generated markdown when schemas or scaffolds change materially.

## Validation Expectations

- Run `python -m pytest` for any code change.
- Start Redis with `docker compose -f docker-compose.redis.yml up -d redis-integration` before running `workspace/scheduler/test_redis_integration.py`.
- If `127.0.0.1:6380` is unreliable, run `bootstrap/redis_diagnostics.py` and switch to `docker compose -f docker-compose.redis.yml up -d redis-hostnet`.
- Run `python -m ruff check workspace projects` and `python -m mypy workspace` for structural Python changes.
- If a change is documentation-only, state that validation was skipped or limited.
- Before reporting completion, run `/git dd/mm/aaaa nome-randomico` or `bash bootstrap/git-cycle.sh "dd/mm/aaaa" "nome-randomico"` from WSL.
