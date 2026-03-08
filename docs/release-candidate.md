# Release Candidate Status

**Release candidate for local controlled operation.**

Ready for controlled local use where Redis, the scheduler, CI events, and human approval are operated intentionally by a maintainer. Not yet production-hardened for broader deployment or unattended autonomy.

## What Passed

- Operator docs rewritten to reflect actual maturity.
- Critical orchestration/runtime paths pass `mypy`.
- Canonical Redis compose path at `docker-compose.redis.yml` with host-network fallback.
- Local validation tooling: diagnostics, DB reset, graph inspection, audit inspection, metrics snapshot, and single-command end-to-end flow.
- Tool contracts enforce bounded filesystem scope and terminal allowlist, with audit artifacts under `.context/tool-audit/`.
- Operator health snapshot summarizes backlog, blocked tasks, merge blocks, dead letters, and CI failures.
- Gitea Actions PR pipeline: lint, types, unit tests, Redis integration. Branch protection documented in [`gitea-pr-validation.md`](./gitea-pr-validation.md).

## What Remains Open

- LangGraph nodes contain placeholder execution behavior.
- External Gitea and Argo boundaries are simulated locally.
- Git checkpoint workflow is documented but not yet machine-attested by the scheduler.
- Tool auditing is local and file-based, not yet end-to-end through the scheduler event model.

## Known Limitations

- Assistant-style system, not a fully autonomous engineer.
- Designed for local-first controlled operation, not multi-tenant or internet-facing deployment.
- CI authority and human approval enforced, but external feed systems not yet fully integrated.
- Operator observability is practical for local use, not equivalent to a full monitoring stack.

## Validation Commands

```bash
# Setup
python3 -m venv .context/.venv
.context/.venv/bin/python -m pip install -e .[dev]

# Static and unit validation
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q
.context/.venv/bin/python -m mypy workspace
.context/.venv/bin/python -m compileall bootstrap workspace

# Redis
docker compose -f docker-compose.redis.yml up -d redis-integration
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/redis_diagnostics.py

# Integration tests
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q

# End-to-end
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow \
  --reset-db --graph-id rc-local-001 \
  --objective "Release-candidate controlled flow" --project-name 01-monolito
```

## Remaining Gaps

| Gap | What it means |
|-----|---------------|
| Real CI/code-host integrations | Gitea and Argo boundaries are scaffolded, not exercised end-to-end |
| Checkpoint attestation | Git workflow evidence is file-based, not yet machine-attested by the scheduler |
| Audit completeness | Strong for scheduler/memory, not yet covering every prompt and artifact boundary |
| LangGraph execution | Nodes contain placeholder behavior, not real agent work |

Until these are resolved, the repository is RC-ready for local controlled use, not production-ready.
