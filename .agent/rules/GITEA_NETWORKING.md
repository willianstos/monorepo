# Gitea Networking — Invariants

Canonical reference: [`docs/gitea-pr-validation.md`](../../docs/gitea-pr-validation.md) and [`docs/gitea-activation-checklist.md`](../../docs/gitea-activation-checklist.md).

## Rule: GITEA_ROOT_URL must never be `localhost`

`GITEA_ROOT_URL` in `/home/will/projetos/gitea-wsl-ops/.env` **must always be**:

```
GITEA_ROOT_URL=http://172.17.0.1:3001/
```

**Never set it to `http://localhost:3001/`.**

### Why

`localhost` inside Docker job containers resolves to the container's own loopback (`127.0.0.1` / `::1`), not the WSL2 host. Gitea embeds `ROOT_URL` in the clone URL sent to runners. If `ROOT_URL` uses `localhost`, every `actions/checkout` step fails with a connection error.

`172.17.0.1` is the Docker bridge gateway — stable across restarts, reachable from all containers on the default bridge network.

## Rule: never use `--add-host=localhost:...` as a substitute

Adding `--add-host=localhost:172.17.0.1` to `container.options` in `config.yaml` does **not** fix the problem. The container's libc resolver returns the loopback entries from `/etc/hosts` first; the `--add-host` entry appears after them and is ignored for `localhost`.

## Rule: prefer `172.17.0.1` over LAN IP

Do not use the LAN IP (e.g., `192.168.15.83`) in `ROOT_URL` or runner registration URLs. The LAN IP can change when the network changes. `172.17.0.1` (Docker bridge gateway) is stable.

## Verification checklist

After any Gitea restart or `.env` change:

```bash
# Confirm ROOT_URL in live config
docker exec gitea grep ROOT_URL /data/gitea/conf/app.ini

# Smoke-test from a container
docker run --rm alpine sh -c "apk add -q curl && curl -sf http://172.17.0.1:3001/api/v1/version"
```

Expected output: `{"version":"1.25.4"}` (or current version).

## Stack restart procedure

```bash
cd /home/will/projetos/gitea-wsl-ops
docker compose up -d --force-recreate gitea
```

Wait ~30 s for the health check to pass before running verification.
