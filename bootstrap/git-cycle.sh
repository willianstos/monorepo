#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash bootstrap/git-cycle.sh "dd/mm/aaaa" "nome-randomico"

Example:
  bash bootstrap/git-cycle.sh "06/03/2026" "atlas-raven"
EOF
}

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

random_hex() {
  od -An -N3 -tx1 /dev/urandom | tr -d ' \n'
}

require_wsl() {
  if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "This workflow must run inside WSL." >&2
    exit 1
  fi
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
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

require_wsl

git rev-parse --show-toplevel >/dev/null

current_branch="$(git branch --show-current)"
if [ -z "$current_branch" ] || [ "$current_branch" = "main" ]; then
  echo "Current branch must be a non-main feature branch." >&2
  exit 1
fi

if [ -z "$(git remote)" ] || ! git remote get-url origin >/dev/null 2>&1; then
  echo "Remote origin is required." >&2
  exit 1
fi

if git diff --name-only --diff-filter=U | grep -q .; then
  echo "Unresolved merge conflicts detected." >&2
  exit 1
fi

git fetch origin --prune
git ls-remote --exit-code --heads origin main >/dev/null

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "chore(repo): checkpoint ${checkpoint_label}"
fi

git push -u origin "$current_branch"

git switch main
git pull --ff-only origin main
git merge --no-ff "$current_branch" -m "merge(main): ${checkpoint_label}"
git push origin main

next_branch="feature/${audit_token}-$(random_hex)"
git switch -c "$next_branch"
git push -u origin "$next_branch"

printf 'next branch: %s\n' "$next_branch"
