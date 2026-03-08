# Gitea PR Validation

Operator guide for the Gitea-based PR validation gate. Git and merge policy comes from [`AGENTS.md`](../AGENTS.md) and [`guide_git.md`](./guide_git.md). This document explains how Gitea Actions, `act_runner`, and branch protection enforce that policy.

Local Gitea is the master authoritative host for PR review, CI, and merge. The repository may be public-readable on the local host without changing that authority. GitHub is subordinate mirror-only. This document covers the PR gate on the authoritative host; it does not redefine the broader Git workflow.

## Gate

```
feature branch  ->  PR to main  ->  CI green  ->  human approval  ->  merge
```

No merge without both passing CI and explicit human approval.

Public visibility on local Gitea does not create a second governance path. Protected branch settings, Actions, approvals, and merge authority stay in Gitea.

## Auto-Merge Policy

Gitea branch protection applies to UI merges, API merges, and auto-merge background jobs on the authoritative host. That does not relax repository policy here.

For this repository:

- `main` still requires green CI and explicit human approval.
- `github` mirror state never authorizes a merge.
- If the host exposes auto-merge controls, do not enable blind auto-merge for `main` unless `AGENTS.md` changes through a reviewed PR first.

## 1. Enable Gitea Actions

In `app.ini`:

```ini
[actions]
ENABLED = true
```

Restart Gitea after the change, then enable Actions per-repository under `Settings > Actions > General`.

## 2. Register act_runner

### Obtain Registration Token

Via UI: `Settings > Actions > Runners > Create new runner`.

Via API:

```bash
curl -X POST "http://<GITEA_HOST>:<PORT>/api/v1/repos/<OWNER>/<REPO>/actions/runners/registration-token" \
  -H "Authorization: token <ACCESS_TOKEN>"
```

### Install and Register (Docker Mode)

```bash
act_runner register \
  --instance http://<GITEA_HOST>:<PORT> \
  --token <REGISTRATION_TOKEN> \
  --name future-agents-runner \
  --labels ubuntu-latest:docker://node:20-bookworm
```

Docker mode is required: job isolation, service containers for Redis, and reproducible images.

### Start

```bash
act_runner daemon
```

Persistent operation via Docker:

```bash
docker run -d --name act-runner --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/data:/data \
  gitea/act_runner:latest daemon
```

## 3. Networking

When `act_runner` runs in Docker mode, `localhost` inside job containers refers to the container, not the host. Register the runner with a Gitea URL reachable from inside Docker:

| Scenario | URL |
|----------|-----|
| Same host, Docker Desktop | `http://host.docker.internal:<PORT>` |
| Same host, Linux/WSL2 (Docker CE) | `http://172.17.0.1:<PORT>` (Docker bridge gateway — stable across restarts) |
| Remote host | `http://<REMOTE_IP>:<PORT>` |
| Docker Compose shared network | `http://gitea:<PORT>` |

**Important (Linux/WSL2):** Set `GITEA_ROOT_URL=http://172.17.0.1:3001/` in the Gitea stack's `.env`. This controls the clone URL embedded in workflow metadata. Using `localhost` causes checkout failures because `localhost` inside job containers resolves to the container's own loopback, not the WSL2 host.

Service containers bind ports to the job container's loopback. `ports: ["6380:6379"]` means Redis at `127.0.0.1:6380` inside the job.

Fallback: run `act_runner` with `--network host` and start Redis manually on the runner host.

## 4. Branch Protection

Configure `main` protection in `Settings > Branches`:

| Setting | Value |
|---------|-------|
| Enable branch protection | Yes |
| Disable push | Yes |
| Require pull request | Yes |
| Required approvals | 1+ |
| Dismiss stale approvals | Yes |
| Block merge on rejected reviews | Yes |
| Block merge on official review requests | Yes |
| Require status checks | Yes |
| Required checks | `Lint (ruff)`, `Type Check (mypy)`, `Unit Tests (pytest)`, `Integration Tests (Redis)` |
| Block merge on outdated branch | Recommended |

## 5. Workflow File

```
.gitea/workflows/pr-validation.yml
```

## 6. Pipeline Commands

| Job | Command |
|-----|---------|
| lint | `python -m ruff check workspace projects` |
| types | `python -m mypy workspace` |
| tests-unit | `python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q` |
| tests-integration-redis | `python -m pytest workspace/scheduler/test_redis_integration.py -q` |
| compile-check | `python -m compileall bootstrap workspace` |

All jobs use `python -m pip install -e .[dev]`.

## 7. Local Reproduction

```bash
python3 -m venv .context/.venv
.context/.venv/bin/python -m pip install -e .[dev]
.context/.venv/bin/python -m ruff check workspace projects
.context/.venv/bin/python -m mypy workspace
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q
docker compose -f docker-compose.redis.yml up -d redis-integration
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
.context/.venv/bin/python -m compileall bootstrap workspace
```

## 8. Troubleshooting

**Runner cannot clone** — The root cause is almost always `ROOT_URL` being `http://localhost:3001/`. Fix: set `GITEA_ROOT_URL=http://172.17.0.1:3001/` in `.env` and restart Gitea (`docker compose up -d --force-recreate gitea`). Verify: `docker exec gitea grep ROOT_URL /data/gitea/conf/app.ini`. Smoke-test: `docker run --rm alpine sh -c "apk add -q curl && curl -sf http://172.17.0.1:3001/api/v1/version"`. Do not use `--add-host=localhost:172.17.0.1` in runner config — it has no effect because the container's libc resolves `localhost` to its loopback before checking `/etc/hosts`.

**Redis unavailable in integration tests** — Check Docker socket access and the `docker://` runner label. Fall back to host networking if needed.

**Status checks missing in branch protection** — Run the pipeline once first, then use the autocomplete dropdown.

**Tests pass locally but fail in CI** — CI uses clean `pip install -e .[dev]`, not `.context/.venv`. Redis in CI runs at `127.0.0.1:6380` via service port mapping.
