#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_OUT_DIR="${REPO_ROOT}/static/mermaid"
MMD_SOURCE="/home/dev/.skills-manager/skills/my-skills/skills/write-skill/.tools/mermaid-cli/node_modules/.bin/mmdc"
CHROME_BIN="/usr/bin/chromium-browser"
MERMAID_CFG="${REPO_ROOT}/static/mermaid/mermaid-dark-config.json"

usage() {
  cat <<'EOF'
Usage:
  scripts/render-mermaid.sh <source.md|source.mmd> [output.svg]

Rules:
  - If source is Markdown, the script extracts the first Mermaid code block.
  - If output is omitted, the script writes to static/mermaid/<source>.svg.
  - If output does not contain "/", it is treated as a filename under static/mermaid/.
EOF
}

if [[ "${1:-}" == "" ]] || [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SOURCE_PATH="$1"
if [[ ! -f "${SOURCE_PATH}" ]]; then
  echo "Source file not found: ${SOURCE_PATH}" >&2
  exit 1
fi

if [[ ! -x "${MMD_SOURCE}" ]]; then
  echo "Mermaid CLI not found: ${MMD_SOURCE}" >&2
  echo "Install it first in the writing workspace." >&2
  exit 1
fi

if [[ ! -x "${CHROME_BIN}" ]]; then
  echo "Chromium not found: ${CHROME_BIN}" >&2
  exit 1
fi

mkdir -p "${DEFAULT_OUT_DIR}"

if [[ "${SOURCE_PATH}" == *.md ]]; then
  TMP_MMD="$(mktemp /tmp/mermaid-from-md.XXXXXX.mmd)"
  if ! sed -n '/^```mermaid$/,/^```$/p' "${SOURCE_PATH}" | sed '1d;$d' > "${TMP_MMD}"; then
    echo "Failed to extract Mermaid block from: ${SOURCE_PATH}" >&2
    rm -f "${TMP_MMD}"
    exit 1
  fi
  if [[ ! -s "${TMP_MMD}" ]]; then
    echo "No Mermaid block found in: ${SOURCE_PATH}" >&2
    rm -f "${TMP_MMD}"
    exit 1
  fi
  INPUT_MMD="${TMP_MMD}"
else
  INPUT_MMD="${SOURCE_PATH}"
  TMP_MMD=""
fi

if [[ "${2:-}" == "" ]]; then
  BASENAME="$(basename "${SOURCE_PATH}")"
  OUTPUT_PATH="${DEFAULT_OUT_DIR}/${BASENAME%.*}.svg"
elif [[ "$2" == */* ]]; then
  OUTPUT_PATH="$2"
else
  OUTPUT_PATH="${DEFAULT_OUT_DIR}/$2"
fi

mkdir -p "$(dirname "${OUTPUT_PATH}")"

PUPPETEER_CFG="$(mktemp /tmp/puppeteer-mermaid.XXXXXX.json)"
trap 'rm -f "${TMP_MMD:-}" "${PUPPETEER_CFG}"' EXIT

cat > "${PUPPETEER_CFG}" <<EOF
{
  "executablePath": "${CHROME_BIN}",
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
}
EOF

"${MMD_SOURCE}" \
  -p "${PUPPETEER_CFG}" \
  -c "${MERMAID_CFG}" \
  -b transparent \
  -i "${INPUT_MMD}" \
  -o "${OUTPUT_PATH}"

echo "Rendered Mermaid: ${OUTPUT_PATH}"
