#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash bootstrap/git-cycle.sh [--dry-run] [--merge-main] "dd/mm/aaaa" "nome-randomico"
  bash bootstrap/git-cycle.sh --cleanup-smoke

Examples:
  bash bootstrap/git-cycle.sh "06/03/2026" "atlas-raven"
  bash bootstrap/git-cycle.sh --merge-main "06/03/2026" "atlas-raven"
  bash bootstrap/git-cycle.sh --dry-run "06/03/2026" "atlas-raven"
  bash bootstrap/git-cycle.sh --cleanup-smoke
EOF
}

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

random_hex() {
  openssl rand -hex 3
}

require_wsl() {
  if [ "${BOOTSTRAP_GIT_CYCLE_ALLOW_NON_WSL:-0}" = "1" ]; then
    return 0
  fi

  if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "This workflow must run inside WSL." >&2
    exit 1
  fi
}

timestamp_id() {
  date '+%Y%m%d-%H%M%S'
}

command_repr() {
  local parts=()
  local arg
  for arg in "$@"; do
    parts+=("$(printf '%q' "$arg")")
  done
  printf '%s' "${parts[*]}"
}

log_note() {
  printf '%s\n' "$*" | tee -a "$audit_log"
}

run_cmd() {
  local rendered
  rendered="$(command_repr "$@")"
  log_note "\$ $rendered"
  if [ "$dry_run" = true ]; then
    log_note "dry-run: skipped"
    return 0
  fi
  "$@" 2>&1 | tee -a "$audit_log"
}

write_summary() {
  local status_label="$1"
  {
    echo "# Git Workflow Run"
    echo
    echo "- action: $action_name"
    echo "- status: $status_label"
    echo "- repo_root: $repo_root"
    echo "- origin: $origin_url"
    echo "- github: $github_url"
    echo "- start_branch: ${start_branch:-unknown}"
    echo "- main_before: ${main_before:-unknown}"
    echo "- main_after: ${main_after:-unknown}"
    echo "- next_branch: ${next_branch:-n/a}"
    echo "- dry_run: $dry_run"
    echo "- cleanup_smoke: $cleanup_smoke"
    echo "- merge_main: $merge_main"
    if [ -n "${checkpoint_label:-}" ]; then
      echo "- label: $checkpoint_label"
    fi
    if [ -n "${checkpoint_commit:-}" ]; then
      echo "- checkpoint_commit: $checkpoint_commit"
    fi
    if [ -n "${merge_commit:-}" ]; then
      echo "- merge_commit: $merge_commit"
    fi
    if [ "${#cleaned_branches[@]}" -gt 0 ]; then
      echo "- cleaned_branches: ${cleaned_branches[*]}"
    fi
    if [ "${#skipped_branches[@]}" -gt 0 ]; then
      echo "- skipped_branches: ${skipped_branches[*]}"
    fi
    echo "- commands_log: $audit_log"
  } >"$audit_summary"
}

finish() {
  local rc="$1"
  if [ -z "${audit_summary:-}" ]; then
    return
  fi
  if [ "$rc" -eq 0 ]; then
    if [ "$dry_run" = true ]; then
      write_summary "dry-run"
    else
      write_summary "success"
    fi
  else
    write_summary "failed"
  fi
}

cleanup_smoke_branches() {
  local current_branch branch ref_for_ancestor
  local local_exists remote_exists_origin remote_exists_github

  current_branch="$(git branch --show-current || true)"
  while IFS= read -r branch; do
    [ -n "$branch" ] || continue
    if [ "$branch" = "$current_branch" ] || [ "$branch" = "main" ]; then
      skipped_branches+=("${branch}:active-or-main")
      continue
    fi

    local_exists=false
    remote_exists_origin=false
    remote_exists_github=false

    if git show-ref --verify --quiet "refs/heads/$branch"; then
      local_exists=true
      ref_for_ancestor="$branch"
    elif git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
      remote_exists_origin=true
      ref_for_ancestor="origin/$branch"
    elif git show-ref --verify --quiet "refs/remotes/github/$branch"; then
      remote_exists_github=true
      ref_for_ancestor="github/$branch"
    else
      continue
    fi

    if ! git merge-base --is-ancestor "$ref_for_ancestor" main; then
      skipped_branches+=("${branch}:not-merged-into-main")
      continue
    fi

    # Detect exact remote presence for deletion
    git show-ref --verify --quiet "refs/remotes/origin/$branch" && remote_exists_origin=true || remote_exists_origin=false
    git show-ref --verify --quiet "refs/remotes/github/$branch" && remote_exists_github=true || remote_exists_github=false

    if $remote_exists_origin; then
      run_cmd git push origin --delete "$branch"
    fi
    if $remote_exists_github && git remote get-url github >/dev/null 2>&1; then
      run_cmd git push github --delete "$branch"
    fi
    if $local_exists; then
      run_cmd git branch -d "$branch"
    fi
    cleaned_branches+=("$branch")
  done < <(
    {
      git for-each-ref --format='%(refname:short)' 'refs/heads/feature/*-git-workflow-smoke-*'
      git for-each-ref --format='%(refname:short)' 'refs/remotes/origin/feature/*-git-workflow-smoke-*' | sed 's#^origin/##'
      git for-each-ref --format='%(refname:short)' 'refs/remotes/github/feature/*-git-workflow-smoke-*' | sed 's#^github/##'
    } | sort -u
  )
}

dry_run=false
cleanup_smoke=false
merge_main=false
action_name="checkpoint"
date_label=""
name_label=""
checkpoint_label=""
checkpoint_commit=""
merge_commit=""
repo_root=""
origin_url=""
github_url=""
start_branch=""
main_before=""
main_after=""
next_branch=""
audit_log=""
audit_summary=""
audit_dir=""
cleaned_branches=()
skipped_branches=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    --merge-main)
      merge_main=true
      action_name="merge-main"
      shift
      ;;
    --cleanup-smoke)
      cleanup_smoke=true
      action_name="cleanup-smoke"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

require_wsl
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

audit_dir="$repo_root/.context/runs/git/$(timestamp_id)-${action_name}"
mkdir -p "$audit_dir"
audit_log="$audit_dir/commands.log"
audit_summary="$audit_dir/summary.md"
: >"$audit_log"
trap 'finish $?' EXIT

origin_url="$(git remote get-url origin)"
github_url="$(git remote get-url github 2>/dev/null || echo "not-configured")"
start_branch="$(git branch --show-current)"
main_before="$(git rev-parse --short main)"

if [ "$cleanup_smoke" = true ]; then
  run_cmd git fetch origin --prune
  if [ "$github_url" != "not-configured" ]; then
    run_cmd git fetch github --prune
  fi
  cleanup_smoke_branches
  main_after="$(git rev-parse --short main)"
  log_note "cleanup completed"
  exit 0
fi

if [ "$#" -lt 2 ]; then
  usage >&2
  exit 1
fi

date_label="$1"
shift
name_label="$*"

if ! printf '%s' "$date_label" | grep -Eq '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'; then
  echo "Date must use dd/mm/aaaa." >&2
  exit 1
fi

slug="$(slugify "$name_label")"
if [ -z "$slug" ]; then
  echo "Name must contain at least one alphanumeric character." >&2
  exit 1
fi

day="${date_label%%/*}"
rest="${date_label#*/}"
month="${rest%%/*}"
year="${date_label##*/}"
audit_token="${year}${month}${day}-${slug}"
checkpoint_label="${date_label} ${name_label}"

if [ -z "$start_branch" ] || [ "$start_branch" = "main" ]; then
  echo "Current branch must be a non-main feature branch." >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "Remote origin is required." >&2
  exit 1
fi

if git diff --name-only --diff-filter=U | grep -q .; then
  echo "Unresolved merge conflicts detected." >&2
  exit 1
fi

run_cmd git fetch origin --prune || log_note "Warning: failed to fetch from origin"
if [ "$github_url" != "not-configured" ]; then
  run_cmd git fetch github --prune || log_note "Warning: failed to fetch from github"
fi

if [ "$merge_main" = true ] && [ "$dry_run" = false ]; then
  git ls-remote --exit-code --heads origin main >/dev/null
elif [ "$merge_main" = true ]; then
  log_note '$ git ls-remote --exit-code --heads origin main'
  log_note 'dry-run: skipped'
fi

if [ -n "$(git status --porcelain)" ]; then
  run_cmd git add -A
  run_cmd git commit -m "chore(repo): checkpoint ${checkpoint_label}"
fi

run_cmd git push -u origin "$start_branch" || log_note "Warning: failed to push to origin"
if [ "$github_url" != "not-configured" ]; then
  run_cmd git push github "$start_branch" || log_note "Warning: failed to push to github"
fi

if [ "$dry_run" = false ]; then
  checkpoint_commit="$(git rev-parse --short HEAD)"
else
  checkpoint_commit="dry-run"
fi

if [ "$merge_main" = false ]; then
  next_branch=""
  main_after="$main_before"
  log_note "checkpoint completed on branch: $start_branch"
  printf 'checkpoint branch: %s\n' "$start_branch"
  printf 'audit dir: %s\n' "$audit_dir"
  exit 0
fi

next_branch="feature/${audit_token}-$(random_hex)"
run_cmd git switch main
run_cmd git pull --ff-only origin main
run_cmd git merge --no-ff "$start_branch" -m "merge(main): ${checkpoint_label}"
run_cmd git push origin main

if [ "$github_url" != "not-configured" ]; then
  run_cmd git push github main || log_note "Warning: failed to push main to github remote"
fi

run_cmd git switch -c "$next_branch"
run_cmd git push -u origin "$next_branch"

if [ "$github_url" != "not-configured" ]; then
  run_cmd git push github "$next_branch" || log_note "Warning: failed to push next branch to github remote"
fi

if [ "$dry_run" = false ]; then
  merge_commit="$(git rev-parse --short main)"
  main_after="$(git rev-parse --short main)"
else
  merge_commit="dry-run"
  main_after="$main_before"
fi

log_note "next branch: $next_branch"
printf 'next branch: %s\n' "$next_branch"
printf 'audit dir: %s\n' "$audit_dir"
