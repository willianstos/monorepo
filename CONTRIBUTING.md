# Contributing

This repository is a Python blueprint for a local-first AI engineering workspace. Most changes will touch architecture contracts, scheduler rules, provider routing, or supporting documentation rather than a fully wired production runtime.

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install the package and development tooling with `python -m pip install -e .[dev]`.
3. Keep generated notes, scaffolds, and run artefacts inside `.context/`.

## Common Commands

- `python -m pytest`
- `python -m pytest -k <pattern>`
- `REDIS_INTEGRATION_PORT=6380 python -m pytest workspace/scheduler/test_redis_integration.py -q`
- `python -m ruff check workspace projects`
- `python -m mypy workspace`
- `REDIS_PORT=6380 python bootstrap/local_validation.py snapshot`

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
- Do not describe the repository as "placeholders only" when the scheduler/event-bus/runtime contracts are implemented.
- Link new long-lived guidance from `.context/docs/README.md`.
- Link new reusable agent instructions from `.context/agents/README.md`.
- Include sample payloads or generated markdown when schemas or scaffolds change materially.

## Validation Expectations

- Run `python -m pytest` for any code change.
- Start Redis with `docker compose -f env/docker-compose.redis.yml up -d redis-integration` before running `workspace/scheduler/test_redis_integration.py`.
- Run `python -m ruff check workspace projects` and `python -m mypy workspace` for structural Python changes.
- If a change is documentation-only, state that validation was skipped or limited.
