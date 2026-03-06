#!/usr/bin/env bash
set -euo pipefail

ALLOW_OPEN=0
if [[ "${1:-}" == "--allow-open" ]]; then
    ALLOW_OPEN=1
fi

GITEA_OPS_DIR="${GITEA_OPS_DIR:-${HOME}/projetos/gitea-wsl-ops}"

log() { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
err() { printf '[ERROR] %s\n' "$*" >&2; }

failures=0
warnings=0

check_cmd() {
    local name="$1"
    if command -v "${name}" >/dev/null 2>&1; then
        log "${name}: $(command -v "${name}")"
    else
        err "${name} not found"
        failures=$((failures + 1))
    fi
}

check_windows_invocation() {
    local cmd_version=""
    local powershell_version=""
    local pwsh_version=""

    cmd_version="$(cmd.exe /c echo CMD-OK 2>/dev/null | tr -d '\r' | head -n 1 || true)"
    powershell_version="$(powershell.exe -NoProfile -Command '$PSVersionTable.PSVersion.ToString()' 2>/dev/null | tr -d '\r' | head -n 1 || true)"
    pwsh_version="$(pwsh.exe -NoProfile -Command '$PSVersionTable.PSVersion.ToString()' 2>/dev/null | tr -d '\r' | head -n 1 || true)"

    [[ -n "${cmd_version}" ]] && log "cmd.exe OK: ${cmd_version}" || { err "cmd.exe invocation failed"; failures=$((failures + 1)); }
    [[ -n "${powershell_version}" ]] && log "powershell.exe OK: ${powershell_version}" || { err "powershell.exe invocation failed"; failures=$((failures + 1)); }
    [[ -n "${pwsh_version}" ]] && log "pwsh.exe OK: ${pwsh_version}" || { err "pwsh.exe invocation failed"; failures=$((failures + 1)); }
}

check_wsl_policy() {
    if grep -Eq '^\s*systemd\s*=\s*true\s*$' /etc/wsl.conf 2>/dev/null; then
        log "WSL systemd enabled"
    else
        err "WSL systemd is not enabled in /etc/wsl.conf"
        failures=$((failures + 1))
    fi

    if grep -Eq '^\s*appendWindowsPath\s*=\s*false\s*$' /etc/wsl.conf 2>/dev/null; then
        log "WSL appendWindowsPath disabled"
    else
        warn "WSL appendWindowsPath is not explicitly disabled"
        warnings=$((warnings + 1))
    fi
}

check_clipboard() {
    local token expected actual
    token="hybrid-wsl-check-$(date +%s)"
    expected="${token}"
    printf '%s' "${expected}" | pbcopy
    actual="$(pbpaste | tr -d '\r')"

    if [[ "${actual}" == "${expected}" ]]; then
        log "Clipboard bridge OK"
    else
        err "Clipboard bridge mismatch"
        failures=$((failures + 1))
    fi
}

check_openers() {
    if [[ "${ALLOW_OPEN}" -eq 1 ]]; then
        explorer . >/dev/null 2>&1 || { err "explorer smoke check failed"; failures=$((failures + 1)); }
        open "http://localhost:3001" >/dev/null 2>&1 || { err "open smoke check failed"; failures=$((failures + 1)); }
        log "Interactive opener smoke checks executed"
        return 0
    fi

    if command -v open >/dev/null 2>&1 && command -v explorer >/dev/null 2>&1; then
        log "open/explorer commands are available"
    else
        err "open/explorer commands are missing"
        failures=$((failures + 1))
    fi
}

check_docker() {
    if systemctl is-active --quiet docker; then
        log "Docker service active in WSL"
    else
        err "Docker service is not active in WSL"
        failures=$((failures + 1))
    fi
}

check_gitea() {
    if [[ -f "${GITEA_OPS_DIR}/scripts/gitea_wsl_healthcheck.sh" ]]; then
        if (cd "${GITEA_OPS_DIR}" && bash scripts/gitea_wsl_healthcheck.sh); then
            log "Gitea ops healthcheck passed"
            return 0
        fi

        err "Gitea ops healthcheck failed"
        failures=$((failures + 1))
        return 0
    fi

    local version
    version="$(curl -fsS http://localhost:3001/api/v1/version 2>/dev/null || true)"
    if [[ -n "${version}" ]]; then
        log "Gitea HTTP OK: ${version}"
    else
        err "Gitea HTTP endpoint is unavailable on localhost:3001"
        failures=$((failures + 1))
    fi

    local ssh_output
    ssh_output="$(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes -T git@localhost -p 222 2>&1 || true)"
    if [[ "${ssh_output}" == *"Permission denied"* || "${ssh_output}" == *"successfully authenticated"* || "${ssh_output}" == *"Shell access is disabled"* ]]; then
        log "Gitea SSH listener reachable on localhost:222"
    else
        err "Gitea SSH listener is not reachable on localhost:222"
        failures=$((failures + 1))
    fi
}

check_git_context() {
    local name email helper branch rebase
    name="$(git config --get user.name || true)"
    email="$(git config --get user.email || true)"
    helper="$(git config --get credential.helper || true)"
    branch="$(git config --get init.defaultBranch || true)"
    rebase="$(git config --get pull.rebase || true)"

    if [[ -z "${name}" || -z "${email}" ]]; then
        warn "WSL global Git identity is not configured"
        warnings=$((warnings + 1))
    else
        log "WSL global Git identity present: ${name} <${email}>"
    fi

    if [[ -z "${helper}" ]]; then
        warn "WSL credential.helper is not configured"
        warnings=$((warnings + 1))
    else
        log "WSL credential.helper=${helper}"
    fi

    if [[ -n "${branch}" ]]; then
        log "WSL init.defaultBranch=${branch}"
    fi

    if [[ -n "${rebase}" ]]; then
        log "WSL pull.rebase=${rebase}"
    fi
}

main() {
    check_cmd cmd.exe
    check_cmd powershell.exe
    check_cmd pwsh.exe
    check_cmd pbcopy
    check_cmd pbpaste
    check_cmd open
    check_cmd explorer
    check_cmd curl
    check_cmd git
    if command -v code >/dev/null 2>&1; then
        log "code: $(command -v code)"
    else
        warn "code command not found in WSL PATH"
        warnings=$((warnings + 1))
    fi
    check_wsl_policy
    check_windows_invocation
    check_clipboard
    check_openers
    check_docker
    check_gitea
    check_git_context

    if [[ "${warnings}" -gt 0 ]]; then
        warn "Healthcheck completed with ${warnings} warning(s)."
    fi

    if [[ "${failures}" -gt 0 ]]; then
        err "Healthcheck failed with ${failures} critical issue(s)."
        exit 1
    fi

    log "WSL hybrid healthcheck passed."
}

main "$@"
