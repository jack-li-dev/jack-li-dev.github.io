#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRITING_ROOT="/home/dev/.skills-manager/skills/my-skills/skills/write-skill/posts/jack-li-website"
HUGO_BIN="${REPO_ROOT}/.bin/hugo"

usage() {
  cat <<'EOF'
Usage:
  scripts/publish-article.sh [source-en.md] [options]

Options:
  --latest                 Use the newest *-en.md from the writing workspace.
  --date ISO8601           Override date and lastmod, e.g. 2026-05-30T12:00:00+08:00.
  --alias PATH             Add a Hugo alias, e.g. /posts/old-placeholder/.
  --replace-slug SLUG      Delete content/posts/<slug>.en.md before publishing.
  --commit                 Commit the imported article to the staging repo.
  --push-staging           Push the commit to origin/main. Implies --commit.
  --serve                  Restart local Hugo preview after build.
  -h, --help               Show this help.

Default:
  Preserves the source front matter, except for Hugo-removed keys that break builds
  such as "lang". Renders Mermaid blocks to static SVG files, runs Hugo build, and
  leaves changes uncommitted for review.
EOF
}

SOURCE_PATH=""
USE_LATEST=0
DATE_OVERRIDE=""
ALIASES=()
REPLACE_SLUG=""
DO_COMMIT=0
PUSH_STAGING=0
DO_SERVE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --latest)
      USE_LATEST=1
      shift
      ;;
    --date)
      DATE_OVERRIDE="${2:-}"
      [[ -n "${DATE_OVERRIDE}" ]] || { echo "--date requires a value" >&2; exit 2; }
      shift 2
      ;;
    --alias)
      ALIASES+=("${2:-}")
      [[ -n "${ALIASES[-1]}" ]] || { echo "--alias requires a value" >&2; exit 2; }
      shift 2
      ;;
    --replace-slug)
      REPLACE_SLUG="${2:-}"
      [[ -n "${REPLACE_SLUG}" ]] || { echo "--replace-slug requires a value" >&2; exit 2; }
      shift 2
      ;;
    --commit)
      DO_COMMIT=1
      shift
      ;;
    --push-staging)
      PUSH_STAGING=1
      DO_COMMIT=1
      shift
      ;;
    --serve)
      DO_SERVE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "${SOURCE_PATH}" ]]; then
        echo "Only one source Markdown file is allowed." >&2
        exit 2
      fi
      SOURCE_PATH="$1"
      shift
      ;;
  esac
done

cd "${REPO_ROOT}"

if [[ "${USE_LATEST}" -eq 1 ]]; then
  SOURCE_PATH="$(find "${WRITING_ROOT}" -type f -name '*-en.md' -printf '%T@ %p\n' | sort -nr | awk 'NR==1 {print $2}')"
fi

if [[ -z "${SOURCE_PATH}" ]]; then
  echo "No source file supplied. Use --latest or pass a source Markdown file." >&2
  usage >&2
  exit 2
fi

if [[ ! -f "${SOURCE_PATH}" ]]; then
  echo "Source file not found: ${SOURCE_PATH}" >&2
  exit 1
fi

if [[ ! -x "${HUGO_BIN}" ]]; then
  echo "Hugo binary not found or not executable: ${HUGO_BIN}" >&2
  exit 1
fi

git config --local user.name "Jack Li"
git config --local user.email "16163394+jack-li-dev@users.noreply.github.com"

ALIAS_ARGS=()
for alias_path in "${ALIASES[@]}"; do
  ALIAS_ARGS+=(--alias "${alias_path}")
done

PUBLISH_OUTPUT="$(
  python3 "${REPO_ROOT}/scripts/publish_article.py" \
    --source "${SOURCE_PATH}" \
    ${DATE_OVERRIDE:+--date "${DATE_OVERRIDE}"} \
    ${REPLACE_SLUG:+--replace-slug "${REPLACE_SLUG}"} \
    "${ALIAS_ARGS[@]}"
)"

echo "${PUBLISH_OUTPUT}"
TARGET_PATH="$(printf '%s\n' "${PUBLISH_OUTPUT}" | awk -F': ' '/^target: / {print $2}')"
POST_URL="$(printf '%s\n' "${PUBLISH_OUTPUT}" | awk -F': ' '/^url: / {print $2}')"

"${HUGO_BIN}" --gc --minify --baseURL http://127.0.0.1:1313/

if [[ "${DO_SERVE}" -eq 1 ]]; then
  if [[ -f /tmp/jack-li-me-hugo.pid ]] && ps -p "$(cat /tmp/jack-li-me-hugo.pid)" >/dev/null 2>&1; then
    kill "$(cat /tmp/jack-li-me-hugo.pid)"
    rm -f /tmp/jack-li-me-hugo.pid
  fi
  setsid "${HUGO_BIN}" server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender --renderToMemory > /tmp/jack-li-me-hugo.log 2>&1 < /dev/null &
  echo $! > /tmp/jack-li-me-hugo.pid
  sleep 1
  echo "preview: http://127.0.0.1:1313${POST_URL}"
fi

if [[ "${DO_COMMIT}" -eq 1 ]]; then
  git add "${TARGET_PATH}"
  git add scripts/publish_article.py scripts/publish-article.sh scripts/render-mermaid.sh
  if [[ -d scripts/mermaid ]]; then git add scripts/mermaid; fi
  if [[ -d static/mermaid ]]; then git add static/mermaid; fi

  if ! git diff --cached --quiet; then
    TITLE="$(awk -F': ' '/^title: / {print $2}' "${TARGET_PATH}" | sed 's/^"//; s/"$//')"
    git commit -m "post: publish ${TITLE:-article}"
  else
    echo "No staged changes to commit."
  fi
fi

if [[ "${PUSH_STAGING}" -eq 1 ]]; then
  git push origin HEAD:main
fi

echo "done"
