# Gitea PR Validation

> Last Updated: 2026-03-06

This document is the canonical operator guide for the Gitea-based PR validation pipeline in `Future Agents`. It covers Gitea Actions enablement, act_runner registration, networking, branch protection, and the required PR gate.

## Canonical PR Gate

```text
feature branch -> PR to main -> CI checks green -> human approval -> merge
```

No merge to `main` is permitted without both passing CI and explicit human approval. This aligns with `AGENTS.md`, `GUARDRAILS.md`, and `WORKSPACE.md`.

## 1. Enabling Gitea Actions

Gitea Actions must be enabled in the Gitea instance configuration.

In `app.ini` (Gitea server config), ensure:

```ini
[actions]
ENABLED = true
```

Restart Gitea after changing `app.ini`.

Then, per repository:
1. Open `Settings > Actions > General` in the Gitea web UI.
2. Enable Actions for the repository.

## 2. Registering act_runner

### 2.1 Obtain Registration Token

Via Gitea web UI:
- Navigate to `Settings > Actions > Runners`.
- Click **Create new runner** to generate a registration token.

Via API:
```bash
curl -X POST "http://<GITEA_HOST>:<PORT>/api/v1/repos/<OWNER>/future-agents/actions/runners/registration-token" \
  -H "Authorization: token <ACCESS_TOKEN>"
```

### 2.2 Install act_runner

Download the latest `act_runner` binary from [gitea.com/gitea/act_runner/releases](https://gitea.com/gitea/act_runner/releases) for your platform.

### 2.3 Register the Runner (Docker Mode)

```bash
act_runner register \
  --instance http://<GITEA_HOST>:<PORT> \
  --token <REGISTRATION_TOKEN> \
  --name future-agents-runner \
  --labels ubuntu-latest:docker://node:20-bookworm
```

Docker mode is **required** for this pipeline because:
- Job isolation: each job runs in a fresh container, preventing state leakage.
- Service containers: the Redis integration job depends on a `redis:7.4-alpine` service container.
- Reproducibility: the same container images run locally and in CI.

### 2.4 Start the Runner

```bash
act_runner daemon
```

For persistent operation, configure as a systemd service or use Docker:

```bash
docker run -d \
  --name act-runner \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/data:/data \
  gitea/act_runner:latest daemon
```

## 3. Networking Caveats

### 3.1 Why Loopback Breaks Job Containers

When `act_runner` runs in Docker mode, each job executes inside a Docker container. Inside that container, `localhost` and `127.0.0.1` refer to the container itself, **not** the host running Gitea.

If the Gitea instance URL is configured as `http://localhost:3000` or `http://127.0.0.1:3000`, the runner containers cannot reach Gitea for checkout or artifact operations.

### 3.2 Reachable Gitea URL

The runner must be registered with a Gitea URL that is reachable from inside Docker containers.

Options (pick the one that matches your environment):

| Scenario | Gitea URL |
|----------|-----------|
| Gitea on same host, Docker Desktop | `http://host.docker.internal:<PORT>` |
| Gitea on same host, Linux | `http://<HOST_LAN_IP>:<PORT>` |
| Gitea on remote host | `http://<REMOTE_IP>:<PORT>` |
| Docker Compose with shared network | `http://gitea:<PORT>` |

**Example for this workspace** (Gitea on H1 at `192.168.15.83`):
```bash
act_runner register \
  --instance http://192.168.15.83:3000 \
  --token <TOKEN> \
  --name future-agents-runner \
  --labels ubuntu-latest:docker://node:20-bookworm
```

### 3.3 Service Container Networking

The `services:` block in workflows (used by `tests-integration-redis`) binds ports to the job container's loopback. The `ports: ["6380:6379"]` mapping means the test code inside the job container reaches Redis at `127.0.0.1:6380`.

This works because the service container and the job container share a Docker network created by `act_runner`. No host-level port binding is required.

### 3.4 Fallback: Host Networking

If Docker service containers are unreliable in your environment, you can:

1. Start Redis manually on the runner host:
   ```bash
   docker compose -f docker-compose.redis.yml up -d redis-integration
   ```
2. Run `act_runner` with `--network host` so the job container shares the host network.
3. The test code then reaches Redis at `127.0.0.1:6380` through host networking.

This is a fallback. Docker-mode service containers are the recommended path.

## 4. Required Branch Protection Settings (Gitea)

Navigate to `Settings > Branches > Branch protection for main`:

| Setting | Value |
|---------|-------|
| **Enable branch protection** | ✅ Yes |
| **Disable push** | ✅ Yes (no direct push to main) |
| **Enable push whitelist** | Only if specific service accounts need to push |
| **Require pull request to merge** | ✅ Yes |
| **Required approvals** | `1` (minimum) |
| **Dismiss stale approvals** | ✅ Yes |
| **Block merge on rejected reviews** | ✅ Yes |
| **Block merge on official review requests** | ✅ Yes |
| **Require status checks to pass** | ✅ Yes |
| **Required status check contexts** | `Lint (ruff)`, `Type Check (mypy)`, `Unit Tests (pytest)`, `Integration Tests (Redis)` |
| **Block merge on outdated branch** | ✅ Yes (recommended) |

### 4.1 Required Status Check Names

The following check names must appear in "Required status check contexts" exactly as shown (these match the `name:` field of each job in `pr-validation.yml`):

- `Lint (ruff)`
- `Type Check (mypy)`
- `Unit Tests (pytest)`
- `Integration Tests (Redis)`

After the first PR run, these names will auto-populate in the Gitea branch protection dropdown.

### 4.2 Why These Settings Matter

- **No direct push to main**: Forces all changes through the PR gate.
- **Required approvals**: Enforces human review before merge.
- **Dismiss stale approvals**: If new commits are pushed after approval, re-approval is required.
- **Block merge on rejected reviews**: A reviewer rejection prevents merge.
- **Require status checks**: All four validation jobs must pass before the merge button becomes available.

This matches the repository's governing contract:
> `branch -> commit -> CI -> review -> human approval -> merge` (AGENTS.md, line 94)

## 5. Workflow File Location

```
.gitea/workflows/pr-validation.yml
```

Gitea Actions reads workflows from `.gitea/workflows/` (not `.github/workflows/`). This is a Gitea-specific convention.

## 6. Validation Commands in the Pipeline

The PR validation workflow executes these exact commands:

| Job | Command |
|-----|---------|
| **lint** | `python -m ruff check workspace projects` |
| **types** | `python -m mypy workspace` |
| **tests-unit** | `python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q` |
| **tests-integration-redis** | `python -m pytest workspace/scheduler/test_redis_integration.py -q` |
| **compile-check** | `python -m compileall bootstrap workspace` |

All jobs use `python -m pip install -e .[dev]` for dependency installation, matching the repository's `pyproject.toml` dev dependencies (pytest, ruff, mypy).

## 7. Running the PR Validation Locally

Operators can reproduce the exact CI pipeline locally without Gitea:

```bash
# 1. Environment setup
python3 -m venv .context/.venv
.context/.venv/bin/python -m pip install -e .[dev]

# 2. Lint
.context/.venv/bin/python -m ruff check workspace projects

# 3. Type check
.context/.venv/bin/python -m mypy workspace

# 4. Unit tests
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q

# 5. Start Redis
docker compose -f docker-compose.redis.yml up -d redis-integration

# 6. Redis integration tests
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q

# 7. Compile check
.context/.venv/bin/python -m compileall bootstrap workspace
```

These are the same commands that run in CI. If all pass locally, the PR pipeline will pass.

## 8. Troubleshooting

### Runner cannot clone repository
- Verify the Gitea URL used during `act_runner register` is reachable from inside Docker containers.
- Test with `docker run --rm curlimages/curl curl -s http://<GITEA_URL>/api/v1/version`.

### Redis service not available in integration tests
- Check that `act_runner` has access to `docker.sock`.
- Verify the runner label includes `docker://` prefix for Docker-mode execution.
- Fallback: use host networking as described in section 3.4.

### Status checks not appearing in branch protection
- Run the pipeline at least once. Gitea populates the check names after the first run.
- Ensure the job `name:` fields match the strings in "Required status check contexts".

### Tests pass locally but fail in CI
- CI uses a clean `python -m pip install -e .[dev]` without pre-existing cache.
- CI does not use `.context/.venv`. It creates a fresh environment per job.
- Redis in CI runs at `127.0.0.1:6380` through Docker service port mapping, same as local.
