#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-status}"
INTERVAL_MINUTES="${2:-5}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/autopublish-scheduler.sh status
  bash scripts/autopublish-scheduler.sh enable [interval-minutes]
  bash scripts/autopublish-scheduler.sh disable
  bash scripts/autopublish-scheduler.sh remove
  bash scripts/autopublish-scheduler.sh run-once

The scheduler is intentionally not enabled by repository setup.
EOF
}

case "${ACTION}" in
  run-once)
    exec python3 "${REPO_ROOT}/scripts/blog_release.py" run-due --ignore-switch
    ;;
  enable|disable|status|remove)
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown action: ${ACTION}" >&2
    usage >&2
    exit 2
    ;;
esac

DISTRO="${WSL_DISTRO_NAME:-}"
if [[ -z "${DISTRO}" ]]; then
  echo "WSL_DISTRO_NAME is unavailable. Run this wrapper from the target WSL distribution." >&2
  exit 1
fi

POWERSHELL="${POWERSHELL_EXE:-/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe}"
if [[ ! -x "${POWERSHELL}" ]]; then
  echo "Windows PowerShell not found: ${POWERSHELL}" >&2
  exit 1
fi

PS_SCRIPT_WIN="$(wslpath -w "${REPO_ROOT}/scripts/windows-autopublish.ps1")"

mkdir -p "${REPO_ROOT}/.bin"
FLAG="${REPO_ROOT}/.bin/autopublish.enabled"

if [[ "${ACTION}" == "disable" || "${ACTION}" == "remove" ]]; then
  rm -f "${FLAG}"
fi

"${POWERSHELL}" \
  -NoLogo \
  -NoProfile \
  -ExecutionPolicy Bypass \
  -File "${PS_SCRIPT_WIN}" \
  -Action "${ACTION}" \
  -Distro "${DISTRO}" \
  -RepoLinuxPath "${REPO_ROOT}" \
  -IntervalMinutes "${INTERVAL_MINUTES}"

if [[ "${ACTION}" == "enable" ]]; then
  printf 'enabled\n' > "${FLAG}"
  echo "repo-switch: enabled"
elif [[ "${ACTION}" == "status" ]]; then
  if [[ -f "${FLAG}" ]]; then
    echo "repo-switch: enabled"
  else
    echo "repo-switch: disabled"
  fi
fi
