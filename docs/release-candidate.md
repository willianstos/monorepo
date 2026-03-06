# Release Candidate Status

> Last Updated: 06/03/2026

## Current Maturity Classification

`release candidate for local controlled operation`

This repository is ready for controlled local use where Redis, the scheduler, CI events, and human approval are all operated intentionally by a maintainer. It is not yet "production hardened" for broader deployment or unattended autonomy.

## What Passed In This RC Pass

- README and operator docs were rewritten to reflect actual maturity instead of aspirational production language.
- Critical orchestration/runtime paths now pass `mypy`.
- Canonical Redis compose path now lives at `docker-compose.redis.yml`.
- A host-network Redis fallback exists for environments where bridge networking is unreliable.
- Local validation tooling now includes diagnostics, DB reset, graph inspection, audit inspection, metrics snapshot, and a single-command controlled end-to-end flow.
- Tool contracts now enforce minimum filesystem scope and terminal allowlist policy, with visible audit artifacts under `.context/tool-audit/`.
- Operator-facing health snapshot now summarizes backlog, blocked tasks, merge blocks, dead letters, and CI failures.
- Gitea Actions PR validation pipeline implemented with lint, types, unit tests, and Redis integration tests. Branch protection and operator docs documented in [`docs/gitea-pr-validation.md`](./gitea-pr-validation.md).

## What Remains Open

- LangGraph nodes still contain placeholder execution behavior.
- External Gitea and Argo boundaries are still simulated in the local controlled flow.
- Git checkpoint workflow is documented and tooled, but not yet machine-attested by the scheduler.
- Tool auditing is local and file-based; it is not yet emitted end-to-end through the scheduler event model.

## Known Limitations

- This is an assistant-style system, not a fully autonomous engineer.
- The repository is designed for local-first controlled operation, not multi-tenant or internet-facing deployment.
- CI authority and human approval are enforced, but the external systems that feed those events are not yet fully integrated here.
- Operator observability is practical for local use, but not yet equivalent to a full production monitoring stack.

## Exact Validation Commands

Environment setup:

```bash
python3 -m venv .context/.venv
.context/.venv/bin/python -m pip install -e .[dev]
```

Static and unit validation:

```bash
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q
.context/.venv/bin/python -m mypy workspace
.context/.venv/bin/python -m compileall bootstrap workspace
```

Redis startup:

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/redis_diagnostics.py
```

Redis integration tests:

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
```

Controlled end-to-end local flow:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow --reset-db --graph-id rc-local-001 --objective "Release-candidate controlled flow" --project-name 01-monolito
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py audit-events --graph-id rc-local-001 --count 100
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py graph-state --graph-id rc-local-001
```

## Remaining Gap Before "Production Hardened"

- Validate the same workflow against real external CI/code-host integrations.
- Add stronger checkpoint attestation and broader end-to-end tool/action audit coverage.
- Improve operator observability beyond Redis counters, hashes, and stream inspection.
- Replace placeholder LangGraph execution behavior with real runtime work.

Until those are complete and validated, this repository should be described as RC-ready for local controlled use, not fully production-ready.
