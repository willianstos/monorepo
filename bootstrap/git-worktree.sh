#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash bootstrap/git-worktree.sh create "dd/mm/aaaa" "branch-slug"
  bash bootstrap/git-worktree.sh create --base <ref> "dd/mm/aaaa" "branch-slug"
  bash bootstrap/git-worktree.sh list
  bash bootstrap/git-worktree.sh remove <path>
  bash bootstrap/git-worktree.sh prune

Creates and manages worktrees in the repository standard:
  ../.worktrees/<repo-name>/<yyyymmdd>/<branch-name>
EOF
}

require_wsl() {
  if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "This workflow must run inside WSL." >&2
    exit 1
  fi
}

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

random_hex() {
  openssl rand -hex 3
}

resolve_base_ref() {
  if [ -n "${base_ref_override:-}" ]; then
    printf '%s\n' "$base_ref_override"
    return 0
  fi
  if git show-ref --verify --quiet "refs/remotes/origin/main"; then
    printf '%s\n' "origin/main"
    return 0
  fi
  printf '%s\n' "main"
}

main() {
  require_wsl

  if [ "$#" -lt 1 ]; then
    usage >&2
    exit 1
  fi

  local cmd="$1"
  shift

  local repo_root repo_name repo_parent worktree_root
  repo_root="$(git rev-parse --show-toplevel)"
  repo_name="$(basename "$repo_root")"
  repo_parent="$(dirname "$repo_root")"
  worktree_root="${repo_parent}/.worktrees/${repo_name}"

  case "$cmd" in
    create)
      local base_ref_override=""
      if [ "${1:-}" = "--base" ]; then
        if [ "$#" -lt 3 ]; then
          usage >&2
          exit 1
        fi
        base_ref_override="$2"
        shift 2
      fi

      if [ "$#" -lt 2 ]; then
        usage >&2
        exit 1
      fi

      local date_label="$1"
      shift
      local name_label="$*"

      if ! printf '%s' "$date_label" | grep -Eq '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'; then
        echo "Date must use dd/mm/aaaa." >&2
        exit 1
      fi

      local slug
      slug="$(slugify "$name_label")"
      if [ -z "$slug" ]; then
        echo "Name must contain at least one alphanumeric character." >&2
        exit 1
      fi

      local day month year stamp branch path base_ref
      day="${date_label%%/*}"
      month="$(printf '%s' "${date_label#*/}" | cut -d/ -f1)"
      year="${date_label##*/}"
      stamp="${year}${month}${day}"
      branch="feature/${stamp}-${slug}-$(random_hex)"
      path="${worktree_root}/${stamp}/$(printf '%s' "$branch" | tr '/' '-')"
      base_ref="$(resolve_base_ref)"

      mkdir -p "$(dirname "$path")"
      git fetch origin --prune >/dev/null 2>&1 || true
      git worktree add -b "$branch" "$path" "$base_ref"
      printf 'worktree: %s\n' "$path"
      printf 'branch: %s\n' "$branch"
      printf 'base: %s\n' "$base_ref"
      ;;
    list)
      git worktree list
      ;;
    remove)
      if [ "$#" -ne 1 ]; then
        usage >&2
        exit 1
      fi
      git worktree remove "$1"
      ;;
    prune)
      git worktree prune
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
