#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUGO_BIN="${REPO_ROOT}/.bin/hugo"
REMOTE_NAME="githubio"
REMOTE_URL="git@github.com:jack-li-dev/jack-li-dev.github.io.git"
CONFIRM=0
MESSAGE="release: publish site"

usage() {
  cat <<'EOF'
Usage:
  scripts/deploy-production.sh --confirm-production [-m "commit message"]

This script commits explicit Hugo source paths and pushes HEAD to:
  git@github.com:jack-li-dev/jack-li-dev.github.io.git main

It refuses to run without --confirm-production.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm-production)
      CONFIRM=1
      shift
      ;;
    -m|--message)
      MESSAGE="${2:-}"
      [[ -n "${MESSAGE}" ]] || { echo "--message requires a value" >&2; exit 2; }
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${CONFIRM}" -ne 1 ]]; then
  echo "Refusing production push. Re-run with --confirm-production." >&2
  exit 2
fi

cd "${REPO_ROOT}"

git config --local user.name "Jack Li"
git config --local user.email "16163394+jack-li-dev@users.noreply.github.com"

if ! git remote get-url "${REMOTE_NAME}" >/dev/null 2>&1; then
  git remote add "${REMOTE_NAME}" "${REMOTE_URL}"
fi

if [[ "$(git remote get-url "${REMOTE_NAME}")" != "${REMOTE_URL}" ]]; then
  git remote set-url "${REMOTE_NAME}" "${REMOTE_URL}"
fi

"${HUGO_BIN}" --gc --minify --baseURL https://jack-li.me/

stage_if_exists() {
  for path in "$@"; do
    if [[ -e "${path}" ]]; then
      git add "${path}"
    fi
  done
}

stage_if_exists \
  AGENTS.md \
  .github/workflows/hugo.yml \
  .gitignore \
  hugo.yaml \
  config.toml \
  hugo.toml \
  content \
  assets \
  layouts \
  static \
  scripts

if ! git diff --cached --quiet; then
  git commit -m "${MESSAGE}"
else
  echo "No source changes to commit."
fi

git log -n 3 --pretty=format:"Commit: %h | Author: %an | Email: <%ae> | Committer: %cn | CommitterEmail: <%ce> | Date: %ad%n"
git push "${REMOTE_NAME}" HEAD:main

echo "production-push: ${REMOTE_URL} main"
