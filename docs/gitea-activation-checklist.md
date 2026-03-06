# Gitea Activation Checklist

> Last Updated: 2026-03-06

This is the canonical step-by-step activation guide for the `Future Agents` PR validation pipeline on the **local Gitea instance running on H1 (WSL Docker, `http://localhost:3001`)**.

It must be followed in order. Each section has explicit actions, exact commands, and explicit verification gates.

---

## Environment Reference

| Item | Value |
|------|-------|
| **Gitea HTTP (from WSL/host)** | `http://localhost:3001` |
| **Gitea HTTP (from inside containers)** | `http://192.168.15.83:3001` |
| **Gitea SSH** | `ssh://git@localhost:222/...` |
| **Gitea admin user** | `admin` |
| **Gitea image** | `gitea/gitea:1.25.4` |
| **Repository** | `admin/ai-engineering-monorepo` |
| **Compose project** | `/home/will/projetos/gitea-wsl-ops` |
| **Protected branch** | `main` |

> [!IMPORTANT]
> Containers cannot reach `localhost:3001`. When registering act_runner, always use `http://192.168.15.83:3001` so Docker job containers can reach the Gitea instance.

---

## Section A — Gitea Prerequisites

### A1. Confirm Gitea is healthy

```bash
# From WSL
curl -s http://localhost:3001/api/v1/version
# Expected: {"version":"1.25.4"}
```

If unhealthy:
```bash
cd /home/will/projetos/gitea-wsl-ops
bash scripts/gitea_wsl_healthcheck.sh
bash scripts/gitea_wsl_stabilize.sh
```

### A2. Confirm Actions are enabled in the Gitea instance

```bash
# Check via API
curl -s http://localhost:3001/api/v1/settings/api \
  -H "Authorization: token <ADMIN_TOKEN>"
```

If Actions is disabled, enable it in `app.ini`:

```ini
[actions]
ENABLED = true
```

Then restart Gitea:
```bash
cd /home/will/projetos/gitea-wsl-ops
docker compose restart gitea
```

### A3. Enable Actions per repository

In Gitea web UI (`http://localhost:3001`):
1. Open `admin/ai-engineering-monorepo`
2. Go to `Settings > Actions > General`
3. Enable Actions for the repository

### A4. Decide runner scope

For this local workspace, **repository-level** runner is the recommended scope. It limits runner access to this repo only.

| Scope | Where to obtain token |
|-------|----------------------|
| Repository-level | `Settings > Actions > Runners > Create new runner` (inside the repo) |
| Organization-level | `Organization Settings > Actions > Runners` |
| Instance-level | `Site Administration > Actions > Runners` (admin only) |

**Use repository-level scope** unless you explicitly need a shared runner across multiple repos.

### A5. Obtain the runner registration token

**Via Gitea web UI** (preferred):
1. Open `http://localhost:3001/admin/ai-engineering-monorepo/settings/actions/runners`
2. Click **Create new runner**
3. Copy the registration token

**Via API** (admin token required):
```bash
curl -s -X POST \
  "http://localhost:3001/api/v1/repos/admin/ai-engineering-monorepo/actions/runners/registration-token" \
  -H "Authorization: token <ADMIN_TOKEN>"
# Response: {"token":"<REGISTRATION_TOKEN>"}
```

---

## Section B — act_runner Activation

### B1. Install act_runner

Download from [gitea.com/gitea/act_runner/releases](https://gitea.com/gitea/act_runner/releases):

```bash
# Example for Linux x86_64 (adjust for your platform)
curl -L -o act_runner \
  https://gitea.com/gitea/act_runner/releases/download/v0.2.11/act_runner-0.2.11-linux-amd64
chmod +x act_runner
```

Or install via Docker (preferred for this environment):

```bash
docker pull gitea/act_runner:latest
```

### B2. Register the runner (Docker mode)

> [!IMPORTANT]
> Use `http://192.168.15.83:3001` — **not** `http://localhost:3001`. Inside Docker job containers, `localhost` refers to the container itself, not the host. Using the LAN IP ensures both the runner and job containers can reach Gitea.

**Binary path:**
```bash
act_runner register \
  --no-interactive \
  --instance "http://192.168.15.83:3001" \
  --token "<REGISTRATION_TOKEN>" \
  --name "future-agents-runner" \
  --labels "ubuntu-latest:docker://node:20-bookworm"
```

**Docker path (mounts docker.sock for service containers):**
```bash
mkdir -p /home/will/projetos/gitea-wsl-ops/act-runner-data

docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/will/projetos/gitea-wsl-ops/act-runner-data:/data \
  -e GITEA_INSTANCE_URL="http://192.168.15.83:3001" \
  -e GITEA_RUNNER_REGISTRATION_TOKEN="<REGISTRATION_TOKEN>" \
  -e GITEA_RUNNER_NAME="future-agents-runner" \
  -e GITEA_RUNNER_LABELS="ubuntu-latest:docker://node:20-bookworm" \
  gitea/act_runner:latest register
```

The `ubuntu-latest:docker://node:20-bookworm` label maps the `runs-on: ubuntu-latest` declared in the workflow to a Docker container image. This enables the `services:` block to function (required for the Redis integration job).

### B3. Start the runner daemon

**Binary:**
```bash
act_runner daemon
```

**Docker (persistent, recommended):**
```bash
docker run -d \
  --name act-runner \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/will/projetos/gitea-wsl-ops/act-runner-data:/data \
  gitea/act_runner:latest daemon
```

### B4. Verify runner is online

1. Open `http://localhost:3001/admin/ai-engineering-monorepo/settings/actions/runners`
2. The runner `future-agents-runner` should appear with status **idle** or **online**

Via API:
```bash
curl -s "http://localhost:3001/api/v1/repos/admin/ai-engineering-monorepo/actions/runners" \
  -H "Authorization: token <ADMIN_TOKEN>"
```

---

## Section C — First Workflow Activation

### C1. Confirm the workflow file is present

```bash
ls .gitea/workflows/
# Expected: pr-validation.yml
```

```bash
# YAML structure validation (PyYAML; on:true is normal — YAML parses "on" as boolean)
python -c "
import yaml
d = yaml.safe_load(open('.gitea/workflows/pr-validation.yml'))
print('Jobs:', list(d['jobs'].keys()))
print('Names:', [d['jobs'][j].get('name') for j in d['jobs']])
"
# Expected:
# Jobs: ['lint', 'types', 'tests-unit', 'tests-integration-redis']
# Names: ['Lint (ruff)', 'Type Check (mypy)', 'Unit Tests (pytest)', 'Integration Tests (Redis)']
```

### C2. Validate commands locally before pushing

```bash
# Full local dry run — mirrors all CI jobs
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

All must pass before proceeding. (As of 2026-03-06: ✅ confirmed locally.)

### C3. Push a feature branch and open a PR

The current branch `feature/20260306-antigravity-git-polish-4eadb2` is already pushed. Open a PR at:

```
http://localhost:3001/admin/ai-engineering-monorepo/pulls/new/feature/20260306-antigravity-git-polish-4eadb2
```

Or for any future feature branch:
```bash
# From WSL
bash bootstrap/git-cycle.sh "DD/MM/YYYY" "feature-slug"
# Then open PR in Gitea UI:
# http://localhost:3001/admin/ai-engineering-monorepo/compare/main...<branch-name>
```

### C4. Observe the workflow run

After the PR is opened:
1. Go to the PR in Gitea UI
2. Look for the **Checks** section — the workflow `PR Validation` should appear
3. Gitea will report individual job statuses using the job `name:` field

**Expected check names (copy these exactly for branch protection):**
```
Lint (ruff)
Type Check (mypy)
Unit Tests (pytest)
Integration Tests (Redis)
```

Check overall run status at:
```
http://localhost:3001/admin/ai-engineering-monorepo/actions
```

### C5. Confirm job names match exactly

The check names reported by Gitea must exactly match what you enter in branch protection. After the first run, Gitea populates a dropdown of available check names in `Settings > Branches`. Use that dropdown — do not type names manually to avoid case/spacing mismatches.

---

## Section D — Branch Protection Activation

Navigate to:
```
http://localhost:3001/admin/ai-engineering-monorepo/settings/branches
```

Click **Add protection rule** for branch pattern `main`.

### D1. Required settings

| Setting | Value | Effect |
|---------|-------|--------|
| Enable branch protection | ✅ | Activates all rules below |
| Disable push | ✅ | Blocks direct push to main |
| Enable push whitelist | ❌ (unless CI service account needed) | No exceptions by default |
| Require pull request to merge | ✅ | Forces PR-based workflow |
| Required approvals | `1` | At least one human must approve |
| Dismiss stale approvals | ✅ if available | Re-approval required after new commits |
| Block merge on rejected reviews | ✅ if available | Reviewer rejection blocks merge |
| Block merge on official review requests | ✅ if available | Pending review requests block merge |
| Require status checks to pass | ✅ | All CI jobs must be green |
| Required status check contexts | See below | Exact job names from the pipeline |
| Block merge if branch is outdated | ✅ if available | Branch must be up to date with main |

### D2. Required status check contexts (paste these in order)

```
Lint (ruff)
Type Check (mypy)
Unit Tests (pytest)
Integration Tests (Redis)
```

> [!CAUTION]
> These names must match the Gitea-reported check names exactly — case-sensitive, including parentheses and spaces. After the first pipeline run they will appear in the branch protection dropdown. Use the dropdown, not manual typing.

### D3. Save and verify

After saving branch protection:
1. Attempt a direct push to `main` from WSL → must be rejected
2. Open a PR → CI checks should appear as required
3. Before CI passes → merge button disabled
4. After CI passes, before approval → merge button disabled
5. After CI passes and 1 approval → merge button enabled

---

## Section E — Validation After Activation

Run these checks after branch protection is configured:

### E1. Merge is blocked before CI

1. Open a PR
2. Before the runner picks up jobs (or if jobs fail): confirm merge button is **disabled** or shows "required checks have not passed"

### E2. Merge is blocked before human approval

1. Let all CI jobs pass
2. Confirm merge button is still **disabled** — "required reviews have not been approved"

### E3. Merge is available only after CI + approval

1. All four jobs green
2. At least 1 approval from a reviewer
3. No pending rejection
4. Confirm merge button becomes **available**

### E4. Stale approval dismissal (if enabled)

1. Approve a PR
2. Push a new commit to the PR branch
3. Confirm the approval is dismissed and re-approval is required

---

## Section F — Practical Commands Summary

### Validate YAML locally
```bash
python -c "
import yaml, sys
d = yaml.safe_load(open('.gitea/workflows/pr-validation.yml'))
jobs = d['jobs']
print('Jobs:', list(jobs.keys()))
print('Names:', [jobs[j]['name'] for j in jobs])
print('YAML OK')
"
```

### Run full local validation
```bash
.context/.venv/bin/python -m ruff check workspace projects
.context/.venv/bin/python -m mypy workspace
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q
docker compose -f docker-compose.redis.yml up -d redis-integration
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
```

### Start Redis for local testing
```bash
# Bridge mode (preferred)
docker compose -f docker-compose.redis.yml up -d redis-integration
# Verify
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/redis_diagnostics.py
```

### Register and start the runner
```bash
# Docker-based runner registration (LAN IP, not localhost)
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/will/projetos/gitea-wsl-ops/act-runner-data:/data \
  -e GITEA_INSTANCE_URL="http://192.168.15.83:3001" \
  -e GITEA_RUNNER_REGISTRATION_TOKEN="<PASTE_TOKEN_HERE>" \
  -e GITEA_RUNNER_NAME="future-agents-runner" \
  -e GITEA_RUNNER_LABELS="ubuntu-latest:docker://node:20-bookworm" \
  gitea/act_runner:latest register

# Start daemon
docker run -d \
  --name act-runner \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/will/projetos/gitea-wsl-ops/act-runner-data:/data \
  gitea/act_runner:latest daemon
```

### Inspect workflow runs
```bash
# List recent runs via API
curl -s "http://localhost:3001/api/v1/repos/admin/ai-engineering-monorepo/actions/runs" \
  -H "Authorization: token <ADMIN_TOKEN>" | python -m json.tool | head -60
```

### Identify exact status check names for branch protection
```bash
# After at least one pipeline run, list completed checks via API
curl -s "http://localhost:3001/api/v1/repos/admin/ai-engineering-monorepo/commits/<COMMIT_SHA>/statuses" \
  -H "Authorization: token <ADMIN_TOKEN>"
```
Or simply open `Settings > Branches > Add rule > Required status checks` and use the autocomplete dropdown.

---

## Section G — First-Run Verification Checklist

After opening the first PR with a registered runner, verify each item:

| # | Check | Expected | How to verify |
|---|-------|----------|---------------|
| G1 | Workflow appears in Gitea | `PR Validation` listed in PR Checks tab | Open PR, check Checks section |
| G2 | Runner picks up jobs | Jobs transition from `waiting` to `running` | Runner logs or Gitea Actions UI |
| G3 | `Lint (ruff)` passes | ✅ Green | Gitea Actions job detail |
| G4 | `Type Check (mypy)` passes | ✅ Green | Gitea Actions job detail |
| G5 | `Unit Tests (pytest)` passes | ✅ Green | Gitea Actions job detail |
| G6 | `Integration Tests (Redis)` passes | ✅ Green | Gitea Actions job detail |
| G7 | Merge blocked before approval | Merge button disabled | PR page while checks pending |
| G8 | Merge blocked while checks red | Merge button disabled | Introduce a failing commit, confirm |
| G9 | Merge available after CI + approval | Merge button enabled | All green + 1 approval |

---

## Section H — Troubleshooting

### H1. Runner registered but idle / jobs never picked up

**Symptoms**: Runner shows as online but jobs stay in `waiting` state.

**Checks**:
- Confirm runner label `ubuntu-latest` matches `runs-on: ubuntu-latest` in the workflow.
- Confirm Docker socket is mounted: `-v /var/run/docker.sock:/var/run/docker.sock`
- Check runner logs: `docker logs act-runner --tail 50`
- Confirm runner scope matches repo (repository vs instance-level)

### H2. Jobs cannot reach Gitea (checkout fails)

**Symptoms**: `actions/checkout@v4` fails with connection refused or DNS error.

**Cause**: Runner or job containers are using `localhost:3001`, which resolves to the container itself.

**Fix**: Re-register the runner with the LAN IP:
```bash
# Use 192.168.15.83:3001, not localhost:3001
--instance "http://192.168.15.83:3001"
```

**Verify connectivity from inside Docker**:
```bash
docker run --rm curlimages/curl curl -s http://192.168.15.83:3001/api/v1/version
# Expected: {"version":"1.25.4"}
```

### H3. Status checks not visible in branch protection dropdown

**Cause**: The pipeline has not run at least once for this repository.

**Fix**:
1. Open a PR and let the pipeline run to completion (even if individual jobs fail)
2. Return to `Settings > Branches > Add rule` — the check names should now appear in the dropdown

### H4. Redis integration job fails in CI

**Symptoms**: `Integration Tests (Redis)` fails with connection error.

**Checks in this order**:
1. Confirm runner has Docker socket access (required for service containers)
2. Check that the runner label uses `docker://` prefix: `ubuntu-latest:docker://node:20-bookworm`
3. Look at job logs — the healthcheck should show Redis starting; if it times out, the service container is unhealthy
4. If service containers are unreliable: run `act_runner` with `--network host` and remove the `services:` port mapping from the workflow (fallback only)

### H5. Branch protection not blocking merge (check names mismatch)

**Symptoms**: All jobs pass but the merge button remains available without checks.

**Cause**: The strings in "Required status check contexts" do not exactly match what Gitea reports.

**Fix**:
1. Delete the existing protection rule
2. Run the pipeline once
3. Re-add the protection rule — use the **autocomplete dropdown** to select the check names, not manual text entry
4. The correct names are: `Lint (ruff)`, `Type Check (mypy)`, `Unit Tests (pytest)`, `Integration Tests (Redis)`

### H6. Docker chain corruption (DOCKER-ISOLATION-* after WSL events)

If Docker stops working inside WSL after abnormal events:
```bash
sudo systemctl restart docker
cd /home/will/projetos/gitea-wsl-ops
bash scripts/gitea_wsl_stabilize.sh
bash scripts/gitea_wsl_healthcheck.sh
```

---

## Assumptions That Require Live Gitea Execution to Confirm

The following items cannot be verified without actually running the pipeline in Gitea:

1. **Action resolution**: `actions/checkout@v4` and `actions/setup-python@v5` are resolved by act_runner from the Gitea Actions mirror or bundled actions. Their availability depends on runner version and network access (or local cache if air-gapped).

2. **Service container timing**: The Redis health check interval/timeout in the `services:` block may need tuning if the local Docker host is under load. The current values (5s interval, 3s timeout, 10 retries) match the `docker-compose.redis.yml` baseline.

3. **Status check name reporting**: Gitea may report check names differently from the `name:` field in some edge cases (e.g., when the runner name contains special characters, or when the workflow file has not been committed to the default branch). Confirmed only after first run.

4. **Branch protection dropdown availability**: The dropdown is populated after the first run against the target repository. Until then, branch protection requires manual name entry, which is error-prone.

5. **Approval dismissal behavior**: Gitea's "dismiss stale approvals" behavior may vary by version. `gitea/gitea:1.25.4` should support this — confirm in UI after the first approval + new commit sequence.
