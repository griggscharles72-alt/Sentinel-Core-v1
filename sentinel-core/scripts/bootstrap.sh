#!/usr/bin/env bash
# =========================================================
# Sentinel Core v1
# File: scripts/bootstrap.sh
# Purpose:
#   Minimal bootstrap helper for Sentinel Core.
#
# This script is responsible for:
#   - creating expected repo runtime directories
#   - ensuring the CLI entrypoint is executable
#   - printing the next operator steps
#
# Design notes:
#   - safe, boring, local-only
#   - no package installation
#   - no hidden mutation outside repo paths
# =========================================================

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() {
  printf '[INFO] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

die() {
  printf '[ERROR] %s\n' "$1" >&2
  exit 1
}

ensure_dir() {
  local target="$1"
  mkdir -p "$target" || die "failed to create directory: $target"
  log "ensured directory: $target"
}

main() {
  log "Sentinel Core bootstrap start"
  log "repo root: ${REPO_ROOT}"

  ensure_dir "${REPO_ROOT}/bin"
  ensure_dir "${REPO_ROOT}/config"
  ensure_dir "${REPO_ROOT}/data"
  ensure_dir "${REPO_ROOT}/data/db"
  ensure_dir "${REPO_ROOT}/data/baselines"
  ensure_dir "${REPO_ROOT}/data/baselines/files"
  ensure_dir "${REPO_ROOT}/data/baselines/manifests"
  ensure_dir "${REPO_ROOT}/data/snapshots"
  ensure_dir "${REPO_ROOT}/data/reports"
  ensure_dir "${REPO_ROOT}/data/logs"
  ensure_dir "${REPO_ROOT}/docs"
  ensure_dir "${REPO_ROOT}/scripts"
  ensure_dir "${REPO_ROOT}/src"
  ensure_dir "${REPO_ROOT}/src/sentinel_core"
  ensure_dir "${REPO_ROOT}/src/sentinel_core/helpers"
  ensure_dir "${REPO_ROOT}/src/sentinel_core/probes"
  ensure_dir "${REPO_ROOT}/tests"

  if [ -f "${REPO_ROOT}/bin/sentinel-core" ]; then
    chmod +x "${REPO_ROOT}/bin/sentinel-core" || die "failed to chmod bin/sentinel-core"
    log "made executable: ${REPO_ROOT}/bin/sentinel-core"
  else
    warn "missing file: ${REPO_ROOT}/bin/sentinel-core"
  fi

  log "bootstrap complete"
  printf '\n'
  printf 'Next steps:\n'
  printf '  1. Review config/watchlist.json\n'
  printf '  2. Run: bin/sentinel-core doctor\n'
  printf '  3. Run: bin/sentinel-core baseline\n'
  printf '  4. Run: bin/sentinel-core check\n'
  printf '  5. Run: bin/sentinel-core report\n'
}

main "$@"
