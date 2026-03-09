#!/usr/bin/env python3
"""
README
======

Filename:
    restore_decide.py

Project:
    Sentinel Core v1

Purpose:
    Restore planning logic for Sentinel Core.

This module is responsible for:

    - loading the latest check run
    - loading drift events for that check run
    - filtering only supported restore candidates
    - building a deterministic restore plan
    - writing a machine-readable restore plan JSON artifact

Design notes:

    - planning only
    - no restore actions here
    - only explicitly restorable drift becomes part of the plan
    - v1 supports file restore planning and limited service restore planning
"""

from __future__ import annotations

from typing import Any, Dict, List

from sentinel_core.db_store import (
    get_active_baseline_run,
    get_drift_events_for_check_run,
    get_latest_check_run,
    get_watched_files_for_baseline,
    get_watched_services_for_baseline,
    initialize_database,
)
from sentinel_core.helpers.jsonio import atomic_write_json_file
from sentinel_core.helpers.paths import build_paths, ensure_runtime_directories
from sentinel_core.helpers.time_utils import utc_now_compact, utc_now_iso


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_NO_BASELINE = 12


SUPPORTED_FILE_DRIFT_TYPES = {
    "missing",
    "hash_changed",
    "mode_changed",
}

SUPPORTED_SERVICE_DRIFT_TYPES = {
    "service_not_found",
    "service_disabled",
    "service_inactive",
}


def _index_watched_files_by_path(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Index watched file baseline rows by path.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        index[str(row["path"])] = row
    return index


def _index_watched_services_by_name(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Index watched service baseline rows by unit_name.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        index[str(row["unit_name"])] = row
    return index


def _build_file_restore_action(
    event: Dict[str, Any],
    watched_file: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a restore action record for a watched file.
    """
    return {
        "object_type": "file",
        "object_key": str(event["object_key"]),
        "path_or_name": str(event["path_or_name"]),
        "drift_type": str(event["drift_type"]),
        "action": "restore_file_from_baseline",
        "baseline_copy_path": watched_file.get("baseline_copy_path"),
        "target_path": watched_file.get("path"),
        "restorable": True,
    }


def _build_service_restore_action(
    event: Dict[str, Any],
    watched_service: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a restore action record for a watched service.
    """
    return {
        "object_type": "service",
        "object_key": str(event["object_key"]),
        "path_or_name": str(event["path_or_name"]),
        "drift_type": str(event["drift_type"]),
        "action": "correct_service_state",
        "unit_name": watched_service.get("unit_name"),
        "expected_enabled": bool(watched_service.get("expected_enabled", True)),
        "expected_active": bool(watched_service.get("expected_active", True)),
        "restorable": True,
    }


def _build_restore_plan(
    latest_check_run: Dict[str, Any],
    baseline_run: Dict[str, Any],
    actions: List[Dict[str, Any]],
    skipped_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the restore plan object.
    """
    return {
        "generated_at": utc_now_iso(),
        "check_run_id": int(latest_check_run["id"]),
        "baseline_run_id": int(baseline_run["id"]),
        "status": "plan_ready" if actions else "nothing_to_restore",
        "summary": {
            "planned_action_count": len(actions),
            "skipped_event_count": len(skipped_events),
        },
        "planned_actions": actions,
        "skipped_events": skipped_events,
    }


def run_restore_plan() -> int:
    """
    Generate a deterministic restore plan from the latest drift state.
    """
    paths = build_paths()
    ensure_runtime_directories(paths)
    initialize_database(paths.db_path)

    latest_check_run = get_latest_check_run(paths.db_path)
    if not latest_check_run:
        print("ERROR: no check run found.")
        return EXIT_NO_BASELINE

    baseline_run = get_active_baseline_run(paths.db_path)
    if not baseline_run:
        print("ERROR: no active baseline found.")
        return EXIT_NO_BASELINE

    baseline_run_id = int(baseline_run["id"])
    check_run_id = int(latest_check_run["id"])

    drift_events = get_drift_events_for_check_run(paths.db_path, check_run_id)
    watched_files = _index_watched_files_by_path(
        get_watched_files_for_baseline(paths.db_path, baseline_run_id)
    )
    watched_services = _index_watched_services_by_name(
        get_watched_services_for_baseline(paths.db_path, baseline_run_id)
    )

    planned_actions: List[Dict[str, Any]] = []
    skipped_events: List[Dict[str, Any]] = []

    for event in drift_events:
        if not bool(event.get("restorable", False)):
            skipped_events.append(
                {
                    "event_id": int(event["id"]),
                    "path_or_name": event.get("path_or_name"),
                    "drift_type": event.get("drift_type"),
                    "reason": "event_not_marked_restorable",
                }
            )
            continue

        object_type = str(event["object_type"])
        drift_type = str(event["drift_type"])
        object_key = str(event["object_key"]) if event.get("object_key") is not None else ""

        if object_type == "file":
            if drift_type not in SUPPORTED_FILE_DRIFT_TYPES:
                skipped_events.append(
                    {
                        "event_id": int(event["id"]),
                        "path_or_name": event.get("path_or_name"),
                        "drift_type": drift_type,
                        "reason": "unsupported_file_drift_type",
                    }
                )
                continue

            watched_file = watched_files.get(object_key)
            if not watched_file:
                skipped_events.append(
                    {
                        "event_id": int(event["id"]),
                        "path_or_name": event.get("path_or_name"),
                        "drift_type": drift_type,
                        "reason": "no_matching_watched_file_row",
                    }
                )
                continue

            if not watched_file.get("baseline_copy_path"):
                skipped_events.append(
                    {
                        "event_id": int(event["id"]),
                        "path_or_name": event.get("path_or_name"),
                        "drift_type": drift_type,
                        "reason": "missing_baseline_copy_path",
                    }
                )
                continue

            planned_actions.append(_build_file_restore_action(event, watched_file))
            continue

        if object_type == "service":
            if drift_type not in SUPPORTED_SERVICE_DRIFT_TYPES:
                skipped_events.append(
                    {
                        "event_id": int(event["id"]),
                        "path_or_name": event.get("path_or_name"),
                        "drift_type": drift_type,
                        "reason": "unsupported_service_drift_type",
                    }
                )
                continue

            watched_service = watched_services.get(object_key)
            if not watched_service:
                skipped_events.append(
                    {
                        "event_id": int(event["id"]),
                        "path_or_name": event.get("path_or_name"),
                        "drift_type": drift_type,
                        "reason": "no_matching_watched_service_row",
                    }
                )
                continue

            planned_actions.append(_build_service_restore_action(event, watched_service))
            continue

        skipped_events.append(
            {
                "event_id": int(event["id"]),
                "path_or_name": event.get("path_or_name"),
                "drift_type": drift_type,
                "reason": "unsupported_object_type",
            }
        )

    restore_plan = _build_restore_plan(
        latest_check_run=latest_check_run,
        baseline_run=baseline_run,
        actions=planned_actions,
        skipped_events=skipped_events,
    )

    plan_name = f"restore_plan_{utc_now_compact()}.json"
    plan_path = paths.reports_dir / plan_name
    atomic_write_json_file(plan_path, restore_plan)

    print(f"INFO: restore plan written: {plan_path}")
    print(f"INFO: planned actions: {len(planned_actions)}")
    print(f"INFO: skipped events: {len(skipped_events)}")

    return EXIT_OK


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/restore_decide.py
#
# Current role:
#   - loads latest check run
#   - filters supported restore candidates
#   - writes restore plan JSON
#
# Next required file:
#   sentinel-core/src/sentinel_core/restore_apply.py
#
# Signature:
#   Sentinel Core v1
#   Restore planning layer
# ==========================================================
