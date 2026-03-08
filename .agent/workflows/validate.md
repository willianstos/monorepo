# /validate
---
description: Run the local validation path for the repository.
trigger: /validate
args: "[--full]"
runner: cli
version: 1.0.0
---

## What it is

The shared local validation workflow. It helps reproduce the PR gate locally, but it does not replace remote CI.

## When to use

- Before running `/git`.
- After significant code changes.
- To verify a fix locally.
- See [`../../docs/local-validation.md`](../../docs/local-validation.md) and [`../../docs/workflow-validation.md`](../../docs/workflow-validation.md) for full details.

## When NOT to use

- For documentation-only changes unless targeted doc checks are needed.
- To replace the remote authoritative CI.

## Guardrails

- `/validate` is local-only and does not replace the PR human approval gate.
- `/validate` does not bypass remote CI authority.
- Must have a Python 3.11+ environment activated.
- Requires `pip install -e .[dev]`.

## Run

Fast mode:

```text
/validate
```

Full mode:

```text
/validate --full
```

## Equivalent command

Fast:

```bash
python -m ruff check workspace projects && \
python -m mypy workspace && \
python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q && \
python -m compileall bootstrap workspace
```

Full:

```bash
# Run the fast path first, then the Redis integration test.
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 python -m pytest workspace/scheduler/test_redis_integration.py -q
```

## Flow

1. **Static analysis**: run `ruff` and `mypy`.
2. **Unit tests**: run core logic tests.
3. **Compile check**: verify `bootstrap/` and `workspace/` still compile.
4. **Integration (optional)**: run the Redis Streams integration test after the fast path.

## Mental model

`/validate` is the local gate before `/git`, before the Gitea master gate, and before any best-effort GitHub mirror sync.

## Never forget

Green locally does not merge anything; it only earns the right to push.
