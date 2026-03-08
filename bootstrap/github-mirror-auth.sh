#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash bootstrap/github-mirror-auth.sh ensure [--quiet]
  bash bootstrap/github-mirror-auth.sh check [--quiet]
  bash bootstrap/github-mirror-auth.sh status

Commands:
  ensure   Register GitHub mirror auth once. Try GitHub CLI HTTPS first, then fall back to an SSH deploy key for the configured repo.
  check    Validate real mirror push health for the configured github remote.
  status   Print a human-readable status summary.
EOF
}

command_name="${1:-ensure}"
quiet=false

if [ "$#" -gt 0 ]; then
  shift
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --quiet)
      quiet=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

log() {
  if [ "$quiet" = false ]; then
    printf '%s\n' "$*"
  fi
}

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

read_env_value() {
  local key="$1"
  local env_file="$repo_root/env/.env"

  if [ ! -f "$env_file" ]; then
    return 1
  fi

  awk -F= -v wanted="$key" '
    $1 == wanted {
      value = substr($0, index($0, "=") + 1)
      sub(/\r$/, "", value)
      print value
      exit 0
    }
  ' "$env_file"
}

load_github_token() {
  if [ -n "${GH_TOKEN:-}" ]; then
    printf '%s' "${GH_TOKEN}"
    return 0
  fi

  if [ -n "${GITHUB_TOKEN:-}" ]; then
    printf '%s' "${GITHUB_TOKEN}"
    return 0
  fi

  if token="$(read_env_value GH_TOKEN)" && [ -n "$token" ]; then
    printf '%s' "$token"
    return 0
  fi

  if token="$(read_env_value GITHUB_TOKEN)" && [ -n "$token" ]; then
    printf '%s' "$token"
    return 0
  fi

  return 1
}

normalize_github_url() {
  local remote_url
  remote_url="$1"

  case "$remote_url" in
    https://github.com/*)
      remote_url="${remote_url#https://github.com/}"
      ;;
    git@*:*)
      remote_url="${remote_url#*:}"
      ;;
    ssh://git@*/*)
      remote_url="${remote_url#ssh://git@}"
      remote_url="${remote_url#*/}"
      ;;
    *)
      return 1
      ;;
  esac

  remote_url="${remote_url%.git}"
  if ! printf '%s' "$remote_url" | grep -Eq '^[^/]+/[^/]+$'; then
    return 1
  fi

  printf '%s' "$remote_url"
}

github_fetch_url() {
  git remote get-url github 2>/dev/null
}

github_push_url() {
  if git remote get-url --push github >/dev/null 2>&1; then
    git remote get-url --push github
  else
    github_fetch_url
  fi
}

github_explicit_pushurl() {
  git config --get remote.github.pushurl 2>/dev/null || true
}

parse_github_slug() {
  local remote_url

  if remote_url="$(github_push_url 2>/dev/null)" && [ -n "$remote_url" ]; then
    normalize_github_url "$remote_url"
    return 0
  fi

  if remote_url="$(github_fetch_url 2>/dev/null)" && [ -n "$remote_url" ]; then
    normalize_github_url "$remote_url"
    return 0
  fi

  return 1
}

slug_token() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

ssh_alias_name() {
  local slug="$1"
  printf 'github-mirror-%s' "$(slug_token "$slug")"
}

ssh_key_path() {
  local slug="$1"
  printf '%s/.ssh/id_ed25519_%s' "$HOME" "$(ssh_alias_name "$slug")"
}

ssh_config_path() {
  local slug="$1"
  printf '%s/.ssh/config.d/%s.conf' "$HOME" "$(ssh_alias_name "$slug")"
}

is_logged_in() {
  gh auth status -h github.com >/dev/null 2>&1
}

setup_git_helper() {
  gh auth setup-git --hostname github.com >/dev/null
}

login_with_token() {
  local token="$1"
  printf '%s\n' "$token" | gh auth login --hostname github.com --git-protocol https --with-token >/dev/null
}

repo_push_permission() {
  local slug="$1"
  gh api "repos/$slug" --jq '.permissions.push // false'
}

repo_admin_permission() {
  local slug="$1"
  gh api "repos/$slug" --jq '.permissions.admin // false'
}

push_probe_ref() {
  local branch_name
  branch_name="$(git branch --show-current 2>/dev/null || true)"
  if [ -z "$branch_name" ]; then
    branch_name="auth-probe-$(date +%s)"
  fi

  printf 'HEAD:refs/heads/%s' "$branch_name"
}

git_push_dry_run_ok() {
  git push --dry-run --no-verify github "$(push_probe_ref)" >/dev/null 2>&1
}

ensure_ssh_config_include() {
  mkdir -p "$HOME/.ssh/config.d"
  chmod 700 "$HOME/.ssh" "$HOME/.ssh/config.d"

  if [ ! -f "$HOME/.ssh/config" ]; then
    printf 'Include ~/.ssh/config.d/*.conf\n' >"$HOME/.ssh/config"
    chmod 600 "$HOME/.ssh/config"
    return 0
  fi

  chmod 600 "$HOME/.ssh/config"
  if ! grep -Fqx 'Include ~/.ssh/config.d/*.conf' "$HOME/.ssh/config"; then
    printf '\nInclude ~/.ssh/config.d/*.conf\n' >>"$HOME/.ssh/config"
  fi
}

ensure_ssh_keypair() {
  local slug="$1"
  local key_path comment

  key_path="$(ssh_key_path "$slug")"
  comment="github-mirror-${slug}"

  if [ ! -f "$key_path" ]; then
    ssh-keygen -t ed25519 -N '' -C "$comment" -f "$key_path" >/dev/null
  fi

  chmod 600 "$key_path"
  chmod 644 "${key_path}.pub"
}

ensure_ssh_alias() {
  local slug="$1"
  local alias_name key_path config_path

  alias_name="$(ssh_alias_name "$slug")"
  key_path="$(ssh_key_path "$slug")"
  config_path="$(ssh_config_path "$slug")"

  ensure_ssh_config_include
  cat >"$config_path" <<EOF
Host $alias_name
    HostName github.com
    User git
    IdentityFile $key_path
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
  chmod 600 "$config_path"
}

ensure_repo_deploy_key() {
  local slug="$1"
  local title pubkey existing_id existing_title existing_key existing_read_only

  title="wsl-github-mirror-$(slug_token "$slug")"
  pubkey="$(cat "$(ssh_key_path "$slug").pub")"

  while IFS=$'\t' read -r existing_id existing_title existing_key existing_read_only; do
    [ -n "$existing_id" ] || continue
    if [ "$existing_title" = "$title" ] || [ "$existing_key" = "$pubkey" ]; then
      if [ "$existing_read_only" = "false" ]; then
        return 0
      fi
      gh api "repos/$slug/keys/$existing_id" --method DELETE >/dev/null
    fi
  done < <(gh api "repos/$slug/keys" --paginate --jq '.[] | [.id, .title, .key, .read_only] | @tsv')

  gh api "repos/$slug/keys" \
    --method POST \
    -f title="$title" \
    -f key="$pubkey" \
    -F read_only=false >/dev/null
}

configure_remote_pushurl_ssh() {
  local slug="$1"
  local alias_name push_url

  alias_name="$(ssh_alias_name "$slug")"
  push_url="git@${alias_name}:${slug}.git"
  git remote set-url --push github "$push_url"
}

restore_remote_pushurl() {
  local previous_pushurl="$1"

  if [ -n "$previous_pushurl" ]; then
    git remote set-url --push github "$previous_pushurl"
    return 0
  fi

  git config --unset-all remote.github.pushurl 2>/dev/null || true
}

ensure_ssh_deploy_key_fallback() {
  local slug="$1"

  if [ "$(repo_admin_permission "$slug" 2>/dev/null || printf 'false')" != "true" ]; then
    return 1
  fi

  ensure_ssh_keypair "$slug"
  ensure_ssh_alias "$slug"
  ensure_repo_deploy_key "$slug"
  configure_remote_pushurl_ssh "$slug"
}

remote_mode() {
  local fetch_url push_url
  fetch_url="$(github_fetch_url 2>/dev/null || printf 'not-configured')"
  push_url="$(github_push_url 2>/dev/null || printf 'not-configured')"

  case "$push_url" in
    git@github-mirror-*:*)
      printf 'ssh-deploy-key'
      ;;
    https://github.com/*)
      printf 'https-helper'
      ;;
    git@*:*)
      printf 'ssh'
      ;;
    *)
      printf 'unknown'
      ;;
  esac
}

print_status() {
  local slug permission

  if is_logged_in; then
    log "GitHub CLI auth: ready"
  else
    log "GitHub CLI auth: missing"
  fi

  if slug="$(parse_github_slug)"; then
    log "GitHub mirror remote: $slug"
    log "GitHub mirror mode: $(remote_mode)"
    if is_logged_in; then
      permission="$(repo_push_permission "$slug" 2>/dev/null || printf 'unknown')"
      log "GitHub mirror push permission: $permission"
    fi
    if git_push_dry_run_ok; then
      log "GitHub mirror git push dry-run: ready"
    else
      log "GitHub mirror git push dry-run: denied"
    fi
  else
    log "GitHub mirror remote: not-configured"
  fi
}

ensure_auth() {
  local token slug permission previous_pushurl

  if git_push_dry_run_ok; then
    log "GitHub mirror already healthy."
    return 0
  fi

  if ! command -v gh >/dev/null 2>&1; then
    echo "GitHub CLI (gh) is required for bootstrap." >&2
    exit 1
  fi

  if ! is_logged_in; then
    if ! token="$(load_github_token)"; then
      echo "GitHub auth missing and no GH_TOKEN/GITHUB_TOKEN was found in env or env/.env." >&2
      exit 1
    fi

    log "Registering GitHub CLI auth from local token source."
    login_with_token "$token"
  fi

  setup_git_helper
  log "GitHub CLI auth and git credential helper are configured."

  if slug="$(parse_github_slug)"; then
    permission="$(repo_push_permission "$slug" 2>/dev/null || printf 'unknown')"
    if git_push_dry_run_ok; then
      log "GitHub mirror push permission confirmed for $slug."
      return 0
    fi

    previous_pushurl="$(github_explicit_pushurl)"
    if ensure_ssh_deploy_key_fallback "$slug" && git_push_dry_run_ok; then
      log "GitHub mirror switched to SSH deploy-key mode for $slug."
      return 0
    fi
    restore_remote_pushurl "$previous_pushurl"

    echo "GitHub auth is registered, but git push dry-run to $slug still fails (api_permissions=$permission)." >&2
    exit 2
  fi
}

check_auth() {
  local slug permission

  if git_push_dry_run_ok; then
    log "GitHub mirror auth is healthy."
    return 0
  fi

  if slug="$(parse_github_slug)"; then
    permission="$(repo_push_permission "$slug" 2>/dev/null || printf 'unknown')"
    if ! is_logged_in; then
      echo "GitHub mirror is not healthy and GitHub CLI auth is not registered." >&2
      exit 1
    fi
    if ! git_push_dry_run_ok; then
      echo "GitHub auth is present, but git push dry-run to $slug fails (api_permissions=$permission)." >&2
      exit 2
    fi
  fi

  log "GitHub mirror auth is healthy."
}

case "$command_name" in
  ensure)
    ensure_auth
    ;;
  check)
    check_auth
    ;;
  status)
    print_status
    ;;
  *)
    echo "Unknown command: $command_name" >&2
    usage >&2
    exit 1
    ;;
esac
