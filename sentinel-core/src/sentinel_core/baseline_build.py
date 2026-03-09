#!/usr/bin/env python3
"""
README
======

Filename:
    baseline_build.py

Project:
    Sentinel Core v1

Purpose:
    Baseline creation logic for Sentinel Core.

This module is responsible for:

    - loading and validating Sentinel configuration
    - initializing the SQLite database
    - probing watched objects
    - creating a new active baseline run
    - storing watched object expectations in SQLite
    - writing a baseline manifest JSON snapshot

Design notes:

    - baseline creation is explicit
    - v1 stores metadata first and manifest output immediately
    - baseline file-copy restore material can be added next without
      changing the baseline run contract
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from sentinel_core.db_store import (
    create_baseline_run,
    initialize_database,
    insert_watched_directory,
    insert_watched_file,
    insert_watched_package,
    insert_watched_service,
)
from sentinel_core.helpers.hash_utils import safe_sha256_file
from sentinel_core.helpers.jsonio import atomic_write_json_file, read_json_file
from sentinel_core.helpers.paths import build_paths, ensure_runtime_directories
from sentinel_core.helpers.time_utils import utc_now_compact, utc_now_iso
from sentinel_core.probes.probe_directories import probe_directories
from sentinel_core.probes.probe_files import probe_files
from sentinel_core.probes.probe_packages import probe_packages
from sentinel_core.probes.probe_services import probe_services
from sentinel_core.schema import validate_all_configs


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3


def _stable_config_hash(configs: Dict[str, Dict[str, Any]]) -> str:
    """
    Return a stable SHA-256 hash for the normalized config bundle.
    """
    payload = json.dumps(configs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_and_validate_configs(paths) -> Dict[str, Dict[str, Any]]:
    """
    Load raw config JSON and return normalized validated config objects.
    """
    watchlist_raw = read_json_file(paths.watchlist_config)
    restore_raw = read_json_file(paths.restore_config)
    thresholds_raw = read_json_file(paths.thresholds_config)

    return validate_all_configs(
        watchlist_raw=watchlist_raw,
        restore_raw=restore_raw,
        thresholds_raw=thresholds_raw,
    )


def _build_manifest(
    baseline_run_id: int,
    created_at: str,
    config_hash: str,
    file_results: List[Dict[str, Any]],
    directory_results: List[Dict[str, Any]],
    service_results: List[Dict[str, Any]],
    package_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a machine-readable baseline manifest object.
    """
    return {
        "baseline_run_id": baseline_run_id,
        "created_at": created_at,
        "config_hash": config_hash,
        "summary": {
            "file_count": len(file_results),
            "directory_count": len(directory_results),
            "service_count": len(service_results),
            "package_count": len(package_results),
        },
        "files": file_results,
        "directories": directory_results,
        "services": service_results,
        "packages": package_results,
    }


def run_baseline() -> int:
    """
    Create a new active baseline from the declared watchlist.
    """
    paths = build_paths()
    ensure_runtime_directories(paths)
    initialize_database(paths.db_path)

    configs = _load_and_validate_configs(paths)
    config_hash = _stable_config_hash(configs)
    created_at = utc_now_iso()

    watchlist = configs["watchlist"]

    file_results = probe_files(watchlist["files"])
    directory_results = probe_directories(watchlist["directories"])
    service_results = probe_services(watchlist["services"])
    package_results = probe_packages(watchlist["packages"])

    baseline_run_id = create_baseline_run(
        db_path=paths.db_path,
        created_at=created_at,
        config_hash=config_hash,
        note="baseline created",
        is_active=True,
    )

    for result in file_results:
        baseline_copy_path: str | None = None
        if result.get("exists") and result.get("is_file"):
            relative_target = Path(str(result["path"])).as_posix().lstrip("/")
            baseline_copy_path = str(paths.baseline_files_dir / relative_target)

        insert_watched_file(
            db_path=paths.db_path,
            baseline_run_id=baseline_run_id,
            path=str(result["path"]),
            must_exist=bool(result["must_exist"]),
            expected_sha256=result.get("sha256"),
            expected_mode=result.get("mode"),
            expected_uid=result.get("uid"),
            expected_gid=result.get("gid"),
            size_bytes=result.get("size_bytes"),
            mtime_epoch=result.get("mtime_epoch"),
            baseline_copy_path=baseline_copy_path,
        )

    for result in directory_results:
        insert_watched_directory(
            db_path=paths.db_path,
            baseline_run_id=baseline_run_id,
            path=str(result["path"]),
            must_exist=bool(result["must_exist"]),
            expected_mode=result.get("mode"),
            expected_uid=result.get("uid"),
            expected_gid=result.get("gid"),
        )

    for result in service_results:
        insert_watched_service(
            db_path=paths.db_path,
            baseline_run_id=baseline_run_id,
            unit_name=str(result["unit_name"]),
            must_exist=bool(result["must_exist"]),
            expected_enabled=bool(result.get("expected_enabled", True)),
            expected_active=bool(result.get("expected_active", True)),
            unit_file_path=None,
            unit_file_sha256=None,
        )

    for result in package_results:
        insert_watched_package(
            db_path=paths.db_path,
            baseline_run_id=baseline_run_id,
            package_name=str(result["package_name"]),
            must_be_installed=bool(result["must_be_installed"]),
            version_string=result.get("version"),
        )

    manifest = _build_manifest(
        baseline_run_id=baseline_run_id,
        created_at=created_at,
        config_hash=config_hash,
        file_results=file_results,
        directory_results=directory_results,
        service_results=service_results,
        package_results=package_results,
    )

    manifest_name = f"baseline_{utc_now_compact()}.json"
    manifest_path = paths.baseline_manifests_dir / manifest_name
    atomic_write_json_file(manifest_path, manifest)

    print(f"INFO: baseline created: run_id={baseline_run_id}")
    print(f"INFO: manifest written: {manifest_path}")

    return EXIT_OK


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/baseline_build.py
#
# Current role:
#   - loads and validates config
#   - initializes the DB
#   - probes watched objects
#   - creates a new active baseline run
#   - writes a baseline manifest
#
# Next required file:
#   sentinel-core/src/sentinel_core/rules.py
#
# Signature:
#   Sentinel Core v1
#   Baseline creation layer
# ==========================================================
