#!/usr/bin/env bash
# =========================================================
# Sentinel Core v1
# File: scripts/verify_env.sh
# Purpose:
#   Shell-level preflight verification for Sentinel Core.
#
# This script is responsible for:
#   - checking required external tools exist
#   - checking expected repo paths exist
#   - checking required config files exist
#   - printing a simple pass/fail summary
#
# Design notes:
#   - safe, local-only, no mutation
#   - does not install anything
#   - intended as a quick operator preflight
# =========================================================

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FAIL_COUNT=0

log() {
  printf '[INFO] %s\n' "$1"
}

ok() {
  printf '[OK] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1" >&2
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    ok "command present: $name"
  else
    fail "command missing: $name"
  fi
}

check_file() {
  local path="$1"
  if [ -f "$path" ]; then
    ok "file present: $path"
  else
    fail "file missing: $path"
  fi
}

check_dir() {
  local path="$1"
  if [ -d "$path" ]; then
    ok "directory present: $path"
  else
    fail "directory missing: $path"
  fi
}

main() {
  log "Sentinel Core verify_env start"
  log "repo root: ${REPO_ROOT}"

  check_command python3
  check_command sqlite3
  check_command sha256sum

  if [ -f "${REPO_ROOT}/config/restore.json" ] && grep -q '"enabled":[[:space:]]*true' "${REPO_ROOT}/config/restore.json" 2>/dev/null; then
    check_command rsync
  else
    warn "restore not enabled in config/restore.json; rsync not required for this preflight"
  fi

  check_dir "${REPO_ROOT}/bin"
  check_dir "${REPO_ROOT}/config"
  check_dir "${REPO_ROOT}/src"
  check_dir "${REPO_ROOT}/src/sentinel_core"
  check_dir "${REPO_ROOT}/src/sentinel_core/helpers"
  check_dir "${REPO_ROOT}/src/sentinel_core/probes"

  check_file "${REPO_ROOT}/bin/sentinel-core"
  check_file "${REPO_ROOT}/config/watchlist.json"
  check_file "${REPO_ROOT}/config/restore.json"
  check_file "${REPO_ROOT}/config/thresholds.json"
  check_file "${REPO_ROOT}/src/sentinel_core/__init__.py"
  check_file "${REPO_ROOT}/src/sentinel_core/main_wrapper.py"
  check_file "${REPO_ROOT}/src/sentinel_core/doctor_env.py"
  check_file "${REPO_ROOT}/src/sentinel_core/schema.py"
  check_file "${REPO_ROOT}/src/sentinel_core/db_store.py"
  check_file "${REPO_ROOT}/src/sentinel_core/baseline_build.py"
  check_file "${REPO_ROOT}/src/sentinel_core/drift_check.py"
  check_file "${REPO_ROOT}/src/sentinel_core/report_summary.py"
  check_file "${REPO_ROOT}/src/sentinel_core/restore_decide.py"
  check_file "${REPO_ROOT}/src/sentinel_core/restore_apply.py"

  check_file "${REPO_ROOT}/src/sentinel_core/helpers/paths.py"
  check_file "${REPO_ROOT}/src/sentinel_core/helpers/jsonio.py"
  check_file "${REPO_ROOT}/src/sentinel_core/helpers/log_utils.py"
  check_file "${REPO_ROOT}/src/sentinel_core/helpers/time_utils.py"
  check_file "${REPO_ROOT}/src/sentinel_core/helpers/subprocess_safe.py"
  check_file "${REPO_ROOT}/src/sentinel_core/helpers/hash_utils.py"
  check_file "${REPO_ROOT}/src/sentinel_core/helpers/sqlite_utils.py"

  check_file "${REPO_ROOT}/src/sentinel_core/probes/probe_files.py"
  check_file "${REPO_ROOT}/src/sentinel_core/probes/probe_directories.py"
  check_file "${REPO_ROOT}/src/sentinel_core/probes/probe_services.py"
  check_file "${REPO_ROOT}/src/sentinel_core/probes/probe_packages.py"

  if [ "$FAIL_COUNT" -eq 0 ]; then
    ok "environment verification passed"
    exit 0
  fi

  fail "environment verification failed with ${FAIL_COUNT} issue(s)"
  exit 1
}

main "$@"
