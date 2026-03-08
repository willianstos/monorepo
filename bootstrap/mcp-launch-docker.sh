#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
    printf '[ERROR] docker CLI not found in WSL PATH\n' >&2
    exit 127
fi

export DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}"

cd "${REPO_ROOT}"
exec python3 -m workspace.mcp.docker_server --transport stdio "$@"
