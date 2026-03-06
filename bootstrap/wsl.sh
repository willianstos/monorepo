#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REFERENCE_DATE="${REFERENCE_DATE:-2026-03-05}"
BACKUP_DIR="${REPO_ROOT}/.context/backups/${REFERENCE_DATE}/wsl-bootstrap"
EXPORT_DIR="${REPO_ROOT}/.context/exports/${REFERENCE_DATE}"
BIN_DIR="${HOME}/bin"
STATE_DIR="${HOME}/.config/dev-hybrid-wsl"
MANAGED_GITCONFIG="${STATE_DIR}/gitconfig"
MANAGED_SSH_DIR="${HOME}/.ssh/config.d"
MANAGED_SSH_CONFIG="${MANAGED_SSH_DIR}/dev-hybrid.conf"
DEV_HOME_TARGET="${DEV_HOME_TARGET:-/home/will/projetos}"
DEV_GIT_NAME="${DEV_GIT_NAME:-refrimixtecnologia-coder}"
DEV_GIT_EMAIL="${DEV_GIT_EMAIL:-refrimixtecnologia@gmail.com}"
DEV_GIT_CREDENTIAL_HELPER="${DEV_GIT_CREDENTIAL_HELPER:-cache --timeout=36000}"
MANAGE_GIT_IDENTITY="${MANAGE_GIT_IDENTITY:-auto}"
WINDOWS_SSH_IDENTITY="${WINDOWS_SSH_IDENTITY:-/mnt/c/Users/Zappro/.ssh/id_ed25519}"

log() { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
err() { printf '[ERROR] %s\n' "$*" >&2; }

backup_if_needed() {
    local src="$1"

    if [[ ! -f "${src}" ]]; then
        return 0
    fi

    mkdir -p "${BACKUP_DIR}"
    cp "${src}" "${BACKUP_DIR}/$(basename "${src}").bak"
}

write_shim() {
    local path="$1"
    local content="$2"

    mkdir -p "$(dirname "${path}")"
    if [[ -f "${path}" ]]; then
        local tmp
        tmp="$(mktemp)"
        trap 'rm -f "${tmp}"' RETURN
        printf '%s' "${content}" > "${tmp}"
        if cmp -s "${path}" "${tmp}"; then
            rm -f "${tmp}"
            trap - RETURN
            chmod 0755 "${path}"
            return 0
        fi
        backup_if_needed "${path}"
        mv "${tmp}" "${path}"
        trap - RETURN
    else
        printf '%s' "${content}" > "${path}"
    fi

    chmod 0755 "${path}"
}

write_text_file() {
    local path="$1"
    local content="$2"
    local mode="$3"

    mkdir -p "$(dirname "${path}")"
    if [[ -f "${path}" ]]; then
        local tmp
        tmp="$(mktemp)"
        trap 'rm -f "${tmp}"' RETURN
        printf '%s' "${content}" > "${tmp}"
        if cmp -s "${path}" "${tmp}"; then
            rm -f "${tmp}"
            trap - RETURN
            chmod "${mode}" "${path}"
            return 0
        fi
        backup_if_needed "${path}"
        mv "${tmp}" "${path}"
        trap - RETURN
    else
        printf '%s' "${content}" > "${path}"
    fi

    chmod "${mode}" "${path}"
}

ensure_include_line() {
    local path="$1"
    local include_line="$2"

    if [[ ! -f "${path}" ]]; then
        write_text_file "${path}" "${include_line}
" 600
        return 0
    fi

    if grep -Fxq "${include_line}" "${path}"; then
        chmod 600 "${path}"
        return 0
    fi

    backup_if_needed "${path}"
    {
        printf '%s\n\n' "${include_line}"
        cat "${path}"
    } > "${path}.tmp"
    mv "${path}.tmp" "${path}"
    chmod 600 "${path}"
}

set_managed_shell_block() {
    local path="$1"
    local block="$2"
    local start_marker="# >>> DEV_HYBRID_WSL >>>"
    local end_marker="# <<< DEV_HYBRID_WSL <<<"
    local managed="${start_marker}
${block}
${end_marker}"

    if [[ ! -f "${path}" ]]; then
        write_text_file "${path}" "${managed}
" 644
        return 0
    fi

    local current
    current="$(cat "${path}")"

    if grep -Fq "${start_marker}" "${path}"; then
        local updated
        updated="$(python3 - "${path}" "${managed}" "${start_marker}" "${end_marker}" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
managed = sys.argv[2]
start_marker = re.escape(sys.argv[3])
end_marker = re.escape(sys.argv[4])
content = path.read_text()
pattern = rf"(?s){start_marker}.*?{end_marker}"
print(re.sub(pattern, managed, content), end="")
PY
)"
        if [[ "${updated}" != "${current}" ]]; then
            backup_if_needed "${path}"
            printf '%s' "${updated}" > "${path}"
        fi
        chmod 644 "${path}"
        return 0
    fi

    backup_if_needed "${path}"
    {
        printf '%s' "${current}"
        printf '\n\n%s\n' "${managed}"
    } > "${path}.tmp"
    mv "${path}.tmp" "${path}"
    chmod 644 "${path}"
}

write_windows_shim() {
    local shim_path="$1"
    local source_path="$2"
    local content="$3"

    if [[ ! -e "${source_path}" ]]; then
        warn "Skipping shim ${shim_path}: source not found at ${source_path}"
        return 0
    fi

    write_shim "${shim_path}" "${content}"
}

export_linux_manifests() {
    mkdir -p "${EXPORT_DIR}"
    apt-mark showmanual | sort > "${EXPORT_DIR}/apt-manual.txt"
    log "Exported Linux manual package manifest."
}

configure_shell() {
    local block
    block="export DEV_HOME=\"${DEV_HOME_TARGET}\"
case \":\$PATH:\" in
    *\":\$HOME/bin:\"*) ;;
    *) export PATH=\"\$HOME/bin:\$PATH\" ;;
esac"

    set_managed_shell_block "${HOME}/.profile" "${block}"
    set_managed_shell_block "${HOME}/.bashrc" "${block}"
}

configure_git() {
    local current_name current_email manage_identity git_block legacy_direct_config legacy_direct_with_include include_only current_config
    current_name="$(git config --global --get user.name || true)"
    current_email="$(git config --global --get user.email || true)"
    manage_identity=0

    case "${MANAGE_GIT_IDENTITY}" in
        always)
            manage_identity=1
            ;;
        never)
            manage_identity=0
            ;;
        auto)
            if [[ -z "${current_name}" && -z "${current_email}" ]]; then
                manage_identity=1
            elif [[ "${current_name}" == "${DEV_GIT_NAME}" && "${current_email}" == "${DEV_GIT_EMAIL}" ]]; then
                manage_identity=1
            else
                warn "Existing WSL Git identity detected; preserving it and managing only shared defaults."
            fi
            ;;
        *)
            err "Unsupported MANAGE_GIT_IDENTITY value: ${MANAGE_GIT_IDENTITY}"
            exit 2
            ;;
    esac

    mkdir -p "${STATE_DIR}"
    git_block="[credential]
	helper = ${DEV_GIT_CREDENTIAL_HELPER}
[init]
	defaultBranch = main
[pull]
	rebase = false
"

    if [[ "${manage_identity}" -eq 1 ]]; then
        git_block="[user]
	name = ${DEV_GIT_NAME}
	email = ${DEV_GIT_EMAIL}
${git_block}"
    fi

    write_text_file "${MANAGED_GITCONFIG}" "${git_block}" 600
    include_only="[include]
	path = ${MANAGED_GITCONFIG}
"
    legacy_direct_config="[user]
	name = ${DEV_GIT_NAME}
	email = ${DEV_GIT_EMAIL}
[credential]
	helper = ${DEV_GIT_CREDENTIAL_HELPER}
[init]
	defaultBranch = main
[pull]
	rebase = false
"
    legacy_direct_with_include="${legacy_direct_config}[include]
	path = ${MANAGED_GITCONFIG}
"

    if [[ -f "${HOME}/.gitconfig" ]]; then
        current_config="$(tr -d '\r' < "${HOME}/.gitconfig")"
        if [[ "${current_config}" == "${legacy_direct_config%$'\n'}" || "${current_config}" == "${legacy_direct_with_include%$'\n'}" ]]; then
            write_text_file "${HOME}/.gitconfig" "${include_only}" 600
            log "Migrated WSL Git config to managed include file."
            return 0
        fi
    fi

    if ! git config --global --get-all include.path | grep -Fxq "${MANAGED_GITCONFIG}"; then
        backup_if_needed "${HOME}/.gitconfig"
        git config --global --add include.path "${MANAGED_GITCONFIG}"
    fi

    log "Managed WSL Git defaults through ${MANAGED_GITCONFIG}."
}

configure_ssh() {
    local managed_content include_line current
    managed_content="Host github.com
  HostName github.com
  User git
  IdentityFile ${WINDOWS_SSH_IDENTITY}
  IdentitiesOnly yes

Host gitea-local
  HostName localhost
  Port 222
  User git
  IdentityFile ${WINDOWS_SSH_IDENTITY}
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
"
    include_line="Include ~/.ssh/config.d/*.conf"

    mkdir -p "${HOME}/.ssh" "${MANAGED_SSH_DIR}"
    chmod 700 "${HOME}/.ssh" "${MANAGED_SSH_DIR}"
    write_text_file "${MANAGED_SSH_CONFIG}" "${managed_content}" 600

    if [[ -f "${HOME}/.ssh/config" ]]; then
        current="$(tr -d '\r' < "${HOME}/.ssh/config")"
        if [[ "${current}" == "${managed_content%$'\n'}" ]]; then
            write_text_file "${HOME}/.ssh/config" "${include_line}
" 600
            log "Migrated WSL SSH config to managed include file."
            return 0
        fi
    fi

    ensure_include_line "${HOME}/.ssh/config" "${include_line}"
    log "Managed WSL SSH include file is enabled."
}

main() {
    mkdir -p "${BIN_DIR}" "${EXPORT_DIR}"

    write_windows_shim "${BIN_DIR}/cmd.exe" "/mnt/c/Windows/System32/cmd.exe" '#!/usr/bin/env bash
exec /mnt/c/Windows/System32/cmd.exe "$@"
'

    write_windows_shim "${BIN_DIR}/powershell.exe" "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" '#!/usr/bin/env bash
exec /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe "$@"
'

    write_windows_shim "${BIN_DIR}/pwsh.exe" "/mnt/c/Program Files/PowerShell/7/pwsh.exe" '#!/usr/bin/env bash
exec "/mnt/c/Program Files/PowerShell/7/pwsh.exe" "$@"
'

    write_windows_shim "${BIN_DIR}/clip.exe" "/mnt/c/Windows/System32/clip.exe" '#!/usr/bin/env bash
exec /mnt/c/Windows/System32/clip.exe "$@"
'

    write_windows_shim "${BIN_DIR}/explorer.exe" "/mnt/c/Windows/explorer.exe" '#!/usr/bin/env bash
exec /mnt/c/Windows/explorer.exe "$@"
'

    write_shim "${BIN_DIR}/cmd" '#!/usr/bin/env bash
exec "$HOME/bin/cmd.exe" "$@"
'

    write_shim "${BIN_DIR}/powershell" '#!/usr/bin/env bash
exec "$HOME/bin/powershell.exe" "$@"
'

    write_shim "${BIN_DIR}/pwsh" '#!/usr/bin/env bash
exec "$HOME/bin/pwsh.exe" "$@"
'

    write_shim "${BIN_DIR}/pbcopy" '#!/usr/bin/env bash
exec "$HOME/bin/clip.exe" "$@"
'

    write_shim "${BIN_DIR}/pbpaste" '#!/usr/bin/env bash
exec "$HOME/bin/pwsh.exe" -NoProfile -Command Get-Clipboard
'

    write_shim "${BIN_DIR}/explorer" '#!/usr/bin/env bash
set -euo pipefail
target="${1:-.}"
exec /mnt/c/Windows/explorer.exe "$(wslpath -w "${target}")"
'

    write_shim "${BIN_DIR}/open" '#!/usr/bin/env bash
set -euo pipefail
target="${1:-.}"

if [[ "${target}" =~ ^[A-Za-z][A-Za-z0-9+.-]*:// ]]; then
    exec /mnt/c/Windows/System32/cmd.exe /C start "" "${target}"
fi

if [[ -e "${target}" || "${target}" == "." || "${target}" == ".." ]]; then
    exec /mnt/c/Windows/explorer.exe "$(wslpath -w "${target}")"
fi

printf "open: target not found: %s\n" "${target}" >&2
exit 1
'

    if ! command -v code >/dev/null 2>&1; then
        if [[ -x /mnt/d/VSCode/bin/code ]]; then
            write_shim "${BIN_DIR}/code" '#!/usr/bin/env bash
exec /mnt/d/VSCode/bin/code "$@"
'
        elif [[ -x "/mnt/c/Users/${USER}/AppData/Local/Programs/Microsoft VS Code/bin/code" ]]; then
            write_shim "${BIN_DIR}/code" '#!/usr/bin/env bash
exec "/mnt/c/Users/'"${USER}"'/AppData/Local/Programs/Microsoft VS Code/bin/code" "$@"
'
        else
            warn "No known code CLI found on Windows; skipping code shim."
        fi
    fi

    configure_shell
    configure_git
    configure_ssh
    export_linux_manifests

    log "Explicit Windows bridge shims are present in ${BIN_DIR}."
}

main "$@"
