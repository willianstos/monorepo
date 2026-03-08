#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash bootstrap/github-mirror-auth.sh ensure [--quiet]
  bash bootstrap/github-mirror-auth.sh check [--quiet]
  bash bootstrap/github-mirror-auth.sh status

Commands:
  ensure   Register GitHub CLI auth once from env/.env or process env, then configure git credential helper.
  check    Validate GitHub CLI auth and mirror push permission for the configured github remote.
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

parse_github_slug() {
  local remote_url

  if ! remote_url="$(git remote get-url github 2>/dev/null)"; then
    return 1
  fi

  case "$remote_url" in
    https://github.com/*)
      remote_url="${remote_url#https://github.com/}"
      ;;
    git@github.com:*)
      remote_url="${remote_url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      remote_url="${remote_url#ssh://git@github.com/}"
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

print_status() {
  local slug permission

  if is_logged_in; then
    log "GitHub CLI auth: ready"
  else
    log "GitHub CLI auth: missing"
  fi

  if slug="$(parse_github_slug)"; then
    log "GitHub mirror remote: $slug"
    if is_logged_in; then
      permission="$(repo_push_permission "$slug" 2>/dev/null || printf 'unknown')"
      log "GitHub mirror push permission: $permission"
      if git_push_dry_run_ok; then
        log "GitHub mirror git push dry-run: ready"
      else
        log "GitHub mirror git push dry-run: denied"
      fi
    fi
  else
    log "GitHub mirror remote: not-configured"
  fi
}

ensure_auth() {
  local token slug permission

  if ! command -v gh >/dev/null 2>&1; then
    echo "GitHub CLI (gh) is required." >&2
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
    if [ "$permission" = "true" ] && git_push_dry_run_ok; then
      log "GitHub mirror push permission confirmed for $slug."
    else
      echo "GitHub auth is registered, but git push dry-run to $slug still fails (api_permissions=$permission)." >&2
      exit 2
    fi
  fi
}

check_auth() {
  local slug permission

  if ! is_logged_in; then
    echo "GitHub CLI auth is not registered." >&2
    exit 1
  fi

  if slug="$(parse_github_slug)"; then
    permission="$(repo_push_permission "$slug" 2>/dev/null || printf 'unknown')"
    if [ "$permission" != "true" ] || ! git_push_dry_run_ok; then
      echo "GitHub auth is present, but git push dry-run to $slug fails (api_permissions=$permission)." >&2
      exit 2
    fi
  fi

  log "GitHub CLI auth is healthy."
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
