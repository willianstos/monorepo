#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="${HOME}/.codex/config.toml"
MANIFEST="${HOME}/.codex/config.governance.json"
MODE="apply"
LOCK=0
UNLOCK=0

log() { printf '[INFO] %s\n' "$*"; }
err() { printf '[ERROR] %s\n' "$*" >&2; }

usage() {
    cat <<'EOF'
Usage: bootstrap/codex-governance-wsl.sh [--apply|--check] [--lock] [--unlock] [--target PATH] [--manifest PATH]

Renders managed MCP templates from bootstrap/mcp-registry.toml and applies or checks the WSL Codex target.
EOF
}

lock_target() {
    if ! command -v chattr >/dev/null 2>&1; then
        err "chattr not available; cannot enforce immutable lock."
        exit 1
    fi
    sudo chattr +i "${TARGET}"
    log "Immutable lock applied to ${TARGET}"
}

unlock_target() {
    if ! command -v chattr >/dev/null 2>&1; then
        err "chattr not available; cannot remove immutable lock."
        exit 1
    fi
    sudo chattr -i "${TARGET}"
    log "Immutable lock removed from ${TARGET}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply)
            MODE="apply"
            ;;
        --check)
            MODE="check"
            ;;
        --target)
            TARGET="$2"
            shift
            ;;
        --manifest)
            MANIFEST="$2"
            shift
            ;;
        --lock)
            LOCK=1
            ;;
        --unlock)
            UNLOCK=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            err "Unknown argument: $1"
            usage
            exit 2
            ;;
    esac
    shift
done

cd "${REPO_ROOT}"

if [[ "${UNLOCK}" -eq 1 ]]; then
    unlock_target
fi

python3 bootstrap/render_mcp_configs.py templates >/dev/null
python3 bootstrap/render_mcp_configs.py "${MODE}" \
    --target codex_wsl \
    --output "${TARGET}" \
    --manifest "${MANIFEST}"

if [[ "${LOCK}" -eq 1 ]]; then
    lock_target
fi
