# Gitea Activation Checklist

Host-specific activation checklist for the local Gitea PR validation pipeline. Subordinate runbook only.

Policy comes from [`AGENTS.md`](../AGENTS.md), [`guide_git.md`](./guide_git.md), and [`gitea-pr-validation.md`](./gitea-pr-validation.md).

---

## Environment

| Item | Value |
|------|-------|
| Gitea HTTP (WSL/host) | `http://localhost:3001` |
| Gitea HTTP (from containers) | `http://192.168.15.83:3001` |
| Gitea SSH | `ssh://git@localhost:222/...` |
| Admin user | `admin` |
| Gitea image | `gitea/gitea:1.25.4` |
| Repository | `admin/ai-engineering-monorepo` |
| Compose project | `/home/will/projetos/gitea-wsl-ops` |
| Protected branch | `main` |

> Containers cannot reach `localhost:3001`. Register `act_runner` with `http://192.168.15.83:3001`.

---

## A. Gitea Prerequisites

**A1. Health check:**

```bash
curl -s http://localhost:3001/api/v1/version
```

If unhealthy: `bash scripts/gitea_wsl_healthcheck.sh` then `bash scripts/gitea_wsl_stabilize.sh` from the Gitea ops directory.

**A2. Enable Actions** in `app.ini` (`[actions] ENABLED = true`), restart Gitea.

**A3. Enable Actions per-repository** in `Settings > Actions > General`.

**A4. Runner scope:** repository-level recommended. Obtain token from `Settings > Actions > Runners > Create new runner`.

---

## B. act_runner Activation

**B1. Install:**

```bash
curl -L -o act_runner \
  https://gitea.com/gitea/act_runner/releases/download/v0.2.11/act_runner-0.2.11-linux-amd64
chmod +x act_runner
```

**B2. Register (Docker mode):**

```bash
act_runner register --no-interactive \
  --instance "http://192.168.15.83:3001" \
  --token "<REGISTRATION_TOKEN>" \
  --name "future-agents-runner" \
  --labels "ubuntu-latest:docker://node:20-bookworm"
```

**B3. Start daemon:**

```bash
act_runner daemon
```

Persistent Docker path:

```bash
docker run -d --name act-runner --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/will/projetos/gitea-wsl-ops/act-runner-data:/data \
  gitea/act_runner:latest daemon
```

**B4. Verify** the runner appears online at `Settings > Actions > Runners`.

---

## C. First Workflow Run

1. Confirm `.gitea/workflows/pr-validation.yml` exists.
2. Run validation commands locally (see [`gitea-pr-validation.md`](./gitea-pr-validation.md) section 7).
3. Push a feature branch: `bash bootstrap/git-cycle.sh "DD/MM/YYYY" "feature-slug"`
4. Open a PR in Gitea and confirm the four checks appear: `Lint (ruff)`, `Type Check (mypy)`, `Unit Tests (pytest)`, `Integration Tests (Redis)`.

---

## D. Branch Protection

Configure `main` protection: PR-based merge, at least one approval, the four required status checks, stale-approval dismissal. Use the autocomplete dropdown after the first pipeline run.

---

## E. Post-Activation Validation

1. Merge blocked before CI passes.
2. Merge blocked before human approval.
3. Merge available only after CI + approval.
4. Stale approvals dismissed after new commits (if enabled).

---

## F. Troubleshooting

**Runner idle** — Confirm labels match `runs-on`, Docker socket is mounted.

**Jobs cannot reach Gitea** — Re-register with `http://192.168.15.83:3001`. Test: `docker run --rm curlimages/curl curl -s http://192.168.15.83:3001/api/v1/version`.

**Status checks missing** — Run the pipeline at least once, then use the branch-protection dropdown.

**Redis integration fails in CI** — Verify Docker socket access and the `docker://` label. Fall back to host networking if needed.
