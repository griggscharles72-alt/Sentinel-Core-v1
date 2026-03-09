#!/usr/bin/env python3
"""
README
======

Filename:
    drift_check.py

Project:
    Sentinel Core v1

Purpose:
    Drift detection logic for Sentinel Core.

This module is responsible for:

    - loading the active baseline
    - probing current live state
    - comparing live state to expected baseline state
    - writing drift events into SQLite
    - writing a machine-readable check snapshot
    - returning stable exit codes based on drift severity

Design notes:

    - deterministic only
    - explicit comparisons only
    - no restore actions here
    - no hidden baseline mutation
"""

from __future__ import annotations

from typing import Any, Dict, List

from sentinel_core.db_store import (
    create_check_run,
    finalize_check_run,
    get_active_baseline_run,
    get_watched_directories_for_baseline,
    get_watched_files_for_baseline,
    get_watched_packages_for_baseline,
    get_watched_services_for_baseline,
    initialize_database,
    insert_drift_event,
)
from sentinel_core.helpers.jsonio import atomic_write_json_file
from sentinel_core.helpers.paths import build_paths, ensure_runtime_directories
from sentinel_core.helpers.time_utils import utc_now_compact, utc_now_iso
from sentinel_core.probes.probe_directories import probe_directory
from sentinel_core.probes.probe_files import probe_file
from sentinel_core.probes.probe_packages import probe_package
from sentinel_core.probes.probe_services import probe_service
from sentinel_core.rules import (
    SEVERITY_HIGH,
    classify_directory_drift,
    classify_file_drift,
    classify_package_drift,
    classify_service_drift,
    count_severe_events,
)


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3
EXIT_DRIFT_DETECTED = 10
EXIT_SEVERE_DRIFT = 11
EXIT_NO_BASELINE = 12


def _check_status_from_events(events: List[Dict[str, Any]]) -> str:
    """
    Return a normalized check status string from drift events.
    """
    if not events:
        return "clean"

    severe_count = count_severe_events(events)
    if severe_count > 0:
        return "drift_severe"

    return "drift"


def _build_snapshot(
    check_run_id: int,
    baseline_run_id: int,
    started_at: str,
    finished_at: str,
    status: str,
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a machine-readable check snapshot object.
    """
    return {
        "check_run_id": check_run_id,
        "baseline_run_id": baseline_run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "drift_count": len(events),
        "severe_count": count_severe_events(events),
        "events": events,
    }


def _check_files(
    db_path,
    baseline_run_id: int,
) -> List[Dict[str, Any]]:
    """
    Check watched file baseline rows against live file state.
    """
    events: List[Dict[str, Any]] = []
    expected_rows = get_watched_files_for_baseline(db_path, baseline_run_id)

    for expected in expected_rows:
        observed = probe_file(
            path=str(expected["path"]),
            must_exist=bool(expected["must_exist"]),
        )
        observed["restore_allowed"] = bool(observed.get("restore_allowed", False))
        file_events = classify_file_drift(expected=expected, observed=observed)
        events.extend(file_events)

    return events


def _check_directories(
    db_path,
    baseline_run_id: int,
) -> List[Dict[str, Any]]:
    """
    Check watched directory baseline rows against live directory state.
    """
    events: List[Dict[str, Any]] = []
    expected_rows = get_watched_directories_for_baseline(db_path, baseline_run_id)

    for expected in expected_rows:
        observed = probe_directory(
            path=str(expected["path"]),
            must_exist=bool(expected["must_exist"]),
        )
        directory_events = classify_directory_drift(expected=expected, observed=observed)
        events.extend(directory_events)

    return events


def _check_services(
    db_path,
    baseline_run_id: int,
) -> List[Dict[str, Any]]:
    """
    Check watched service baseline rows against live service state.
    """
    events: List[Dict[str, Any]] = []
    expected_rows = get_watched_services_for_baseline(db_path, baseline_run_id)

    for expected in expected_rows:
        observed = probe_service(
            unit_name=str(expected["unit_name"]),
            must_exist=bool(expected["must_exist"]),
            expected_enabled=bool(expected["expected_enabled"]),
            expected_active=bool(expected["expected_active"]),
        )
        observed["restore_allowed"] = False
        service_events = classify_service_drift(expected=expected, observed=observed)
        events.extend(service_events)

    return events


def _check_packages(
    db_path,
    baseline_run_id: int,
) -> List[Dict[str, Any]]:
    """
    Check watched package baseline rows against live package state.
    """
    events: List[Dict[str, Any]] = []
    expected_rows = get_watched_packages_for_baseline(db_path, baseline_run_id)

    for expected in expected_rows:
        observed = probe_package(
            package_name=str(expected["package_name"]),
            must_be_installed=bool(expected["must_be_installed"]),
        )
        package_events = classify_package_drift(expected=expected, observed=observed)
        events.extend(package_events)

    return events


def run_check() -> int:
    """
    Run deterministic drift detection against the active baseline.
    """
    paths = build_paths()
    ensure_runtime_directories(paths)
    initialize_database(paths.db_path)

    baseline = get_active_baseline_run(paths.db_path)
    if not baseline:
        print("ERROR: no active baseline found.")
        return EXIT_NO_BASELINE

    baseline_run_id = int(baseline["id"])
    started_at = utc_now_iso()

    check_run_id = create_check_run(
        db_path=paths.db_path,
        started_at=started_at,
        baseline_run_id=baseline_run_id,
        status="running",
    )

    events: List[Dict[str, Any]] = []

    try:
        events.extend(_check_files(paths.db_path, baseline_run_id))
        events.extend(_check_directories(paths.db_path, baseline_run_id))
        events.extend(_check_services(paths.db_path, baseline_run_id))
        events.extend(_check_packages(paths.db_path, baseline_run_id))

        for event in events:
            insert_drift_event(
                db_path=paths.db_path,
                check_run_id=check_run_id,
                object_type=str(event["object_type"]),
                object_key=event.get("object_key"),
                path_or_name=str(event["path_or_name"]),
                drift_type=str(event["drift_type"]),
                expected_value=event.get("expected_value"),
                observed_value=event.get("observed_value"),
                severity=str(event["severity"]),
                restorable=bool(event.get("restorable", False)),
                created_at=utc_now_iso(),
            )

        finished_at = utc_now_iso()
        status = _check_status_from_events(events)
        drift_count = len(events)
        severe_count = count_severe_events(events)

        finalize_check_run(
            db_path=paths.db_path,
            check_run_id=check_run_id,
            finished_at=finished_at,
            status=status,
            drift_count=drift_count,
            severe_count=severe_count,
        )

        snapshot = _build_snapshot(
            check_run_id=check_run_id,
            baseline_run_id=baseline_run_id,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            events=events,
        )

        snapshot_name = f"check_{utc_now_compact()}.json"
        snapshot_path = paths.snapshots_dir / snapshot_name
        atomic_write_json_file(snapshot_path, snapshot)

        print(f"INFO: check completed: run_id={check_run_id}")
        print(f"INFO: drift_count={drift_count} severe_count={severe_count}")
        print(f"INFO: snapshot written: {snapshot_path}")

        if severe_count > 0:
            return EXIT_SEVERE_DRIFT

        if drift_count > 0:
            return EXIT_DRIFT_DETECTED

        return EXIT_OK

    except Exception as exc:
        finished_at = utc_now_iso()
        finalize_check_run(
            db_path=paths.db_path,
            check_run_id=check_run_id,
            finished_at=finished_at,
            status="error",
            drift_count=0,
            severe_count=0,
        )
        print(f"ERROR: drift check failed: {exc}")
        return EXIT_RUNTIME_ERROR


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/drift_check.py
#
# Current role:
#   - loads active baseline
#   - probes live state
#   - compares expected vs observed state
#   - stores drift events
#   - writes JSON check snapshots
#
# Next required file:
#   sentinel-core/src/sentinel_core/report_summary.py
#
# Signature:
#   Sentinel Core v1
#   Drift check layer
# ==========================================================
