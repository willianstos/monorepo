#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

exec python3 -m workspace.mcp.server --transport stdio "$@"
