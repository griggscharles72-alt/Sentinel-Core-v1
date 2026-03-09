#!/usr/bin/env python3
"""
README
======

Filename:
    restore_apply.py

Project:
    Sentinel Core v1

Purpose:
    Restore application logic for Sentinel Core.

This module is responsible for:

    - locating the latest restore plan
    - applying supported restore actions
    - restoring files from baseline copies using rsync
    - correcting limited service state when allowed
    - recording restore runs and restore events
    - writing a machine-readable restore result JSON artifact

Design notes:

    - explicit apply only
    - no automatic restore during check/report flow
    - file restore is the primary v1 restore path
    - package restore is not supported in v1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from sentinel_core.db_store import (
    create_restore_run,
    finalize_restore_run,
    initialize_database,
    insert_restore_event,
)
from sentinel_core.helpers.jsonio import atomic_write_json_file, read_json_file
from sentinel_core.helpers.paths import build_paths, ensure_runtime_directories
from sentinel_core.helpers.subprocess_safe import command_exists, run_command
from sentinel_core.helpers.time_utils import utc_now_compact, utc_now_iso


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_DEPENDENCY_ERROR = 3
EXIT_RESTORE_PARTIAL = 20
EXIT_RESTORE_FAILED = 21


def _find_latest_restore_plan(reports_dir: Path) -> Optional[Path]:
    """
    Return the newest restore_plan_*.json file, if one exists.
    """
    candidates = sorted(
        reports_dir.glob("restore_plan_*.json"),
        key=lambda path: path.name,
    )
    if not candidates:
        return None
    return candidates[-1]


def _apply_file_restore(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a file restore action using rsync.
    """
    baseline_copy_path = action.get("baseline_copy_path")
    target_path = action.get("target_path")

    if not baseline_copy_path or not target_path:
        return {
            "result": "failed",
            "details": "missing baseline_copy_path or target_path",
        }

    if not command_exists("rsync"):
        return {
            "result": "failed",
            "details": "rsync not available in PATH",
        }

    source = Path(str(baseline_copy_path))
    target = Path(str(target_path))

    if not source.exists():
        return {
            "result": "failed",
            "details": f"baseline source missing: {source}",
        }

    target.parent.mkdir(parents=True, exist_ok=True)

    result = run_command(
        [
            "rsync",
            "-a",
            "--checksum",
            str(source),
            str(target),
        ],
        timeout=60,
    )

    if not result.ok:
        return {
            "result": "failed",
            "details": f"rsync failed: returncode={result.returncode} stderr={result.stderr.strip()}",
        }

    return {
        "result": "success",
        "details": f"restored file from {source} to {target}",
    }


def _apply_service_restore(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a limited service-state correction action.
    """
    unit_name = action.get("unit_name")
    expected_enabled = bool(action.get("expected_enabled", True))
    expected_active = bool(action.get("expected_active", True))

    if not unit_name:
        return {
            "result": "failed",
            "details": "missing unit_name",
        }

    if not command_exists("systemctl"):
        return {
            "result": "failed",
            "details": "systemctl not available in PATH",
        }

    steps: List[str] = []

    reload_result = run_command(["systemctl", "daemon-reload"], timeout=20)
    if reload_result.ok:
        steps.append("daemon-reload")
    else:
        steps.append(f"daemon-reload-failed({reload_result.returncode})")

    if expected_enabled:
        enable_result = run_command(["systemctl", "enable", str(unit_name)], timeout=30)
        if enable_result.ok:
            steps.append("enable")
        else:
            return {
                "result": "failed",
                "details": f"systemctl enable failed for {unit_name}: {enable_result.stderr.strip()}",
            }

    if expected_active:
        start_result = run_command(["systemctl", "start", str(unit_name)], timeout=30)
        if start_result.ok:
            steps.append("start")
        else:
            return {
                "result": "failed",
                "details": f"systemctl start failed for {unit_name}: {start_result.stderr.strip()}",
            }

    return {
        "result": "success",
        "details": f"service corrected: {unit_name}; steps={','.join(steps)}",
    }


def _apply_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a restore action by object type/action type.
    """
    object_type = str(action.get("object_type", ""))
    action_name = str(action.get("action", ""))

    if object_type == "file" and action_name == "restore_file_from_baseline":
        return _apply_file_restore(action)

    if object_type == "service" and action_name == "correct_service_state":
        return _apply_service_restore(action)

    return {
        "result": "failed",
        "details": f"unsupported restore action: object_type={object_type} action={action_name}",
    }


def _build_restore_result_json(
    restore_run_id: int,
    plan_path: Path,
    attempted_count: int,
    success_count: int,
    failed_count: int,
    action_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the machine-readable restore result object.
    """
    if attempted_count == 0:
        status = "nothing_applied"
    elif failed_count == 0:
        status = "success"
    elif success_count > 0:
        status = "partial"
    else:
        status = "failed"

    return {
        "generated_at": utc_now_iso(),
        "restore_run_id": restore_run_id,
        "source_plan_path": str(plan_path),
        "status": status,
        "summary": {
            "attempted_count": attempted_count,
            "success_count": success_count,
            "failed_count": failed_count,
        },
        "results": action_results,
    }


def run_restore_apply() -> int:
    """
    Apply the latest available restore plan.
    """
    paths = build_paths()
    ensure_runtime_directories(paths)
    initialize_database(paths.db_path)

    plan_path = _find_latest_restore_plan(paths.reports_dir)
    if not plan_path:
        print("ERROR: no restore plan found.")
        return EXIT_RUNTIME_ERROR

    plan = read_json_file(plan_path)
    planned_actions = plan.get("planned_actions", [])
    if not isinstance(planned_actions, list):
        print("ERROR: restore plan is invalid: planned_actions must be a list.")
        return EXIT_RUNTIME_ERROR

    restore_run_id = create_restore_run(
        db_path=paths.db_path,
        started_at=utc_now_iso(),
        check_run_id=plan.get("check_run_id"),
        status="running",
    )

    attempted_count = 0
    success_count = 0
    failed_count = 0
    action_results: List[Dict[str, Any]] = []

    for action in planned_actions:
        attempted_count += 1

        apply_result = _apply_action(action)
        result_status = str(apply_result.get("result", "failed"))
        result_details = str(apply_result.get("details", ""))

        if result_status == "success":
            success_count += 1
        else:
            failed_count += 1

        result_record = {
            "object_type": action.get("object_type"),
            "object_key": action.get("object_key"),
            "action": action.get("action"),
            "source_path": action.get("baseline_copy_path"),
            "target_path": action.get("target_path") or action.get("unit_name"),
            "result": result_status,
            "details": result_details,
        }
        action_results.append(result_record)

        insert_restore_event(
            db_path=paths.db_path,
            restore_run_id=restore_run_id,
            object_type=str(action.get("object_type")),
            object_key=action.get("object_key"),
            action=str(action.get("action")),
            source_path=action.get("baseline_copy_path"),
            target_path=action.get("target_path") or action.get("unit_name"),
            result=result_status,
            details=result_details,
            created_at=utc_now_iso(),
        )

    if attempted_count == 0:
        final_status = "nothing_applied"
    elif failed_count == 0:
        final_status = "success"
    elif success_count > 0:
        final_status = "partial"
    else:
        final_status = "failed"

    finalize_restore_run(
        db_path=paths.db_path,
        restore_run_id=restore_run_id,
        finished_at=utc_now_iso(),
        status=final_status,
        attempted_count=attempted_count,
        success_count=success_count,
        failed_count=failed_count,
    )

    restore_result = _build_restore_result_json(
        restore_run_id=restore_run_id,
        plan_path=plan_path,
        attempted_count=attempted_count,
        success_count=success_count,
        failed_count=failed_count,
        action_results=action_results,
    )

    result_path = paths.reports_dir / f"restore_result_{utc_now_compact()}.json"
    atomic_write_json_file(result_path, restore_result)

    print(f"INFO: restore result written: {result_path}")
    print(f"INFO: attempted={attempted_count} success={success_count} failed={failed_count}")

    if attempted_count == 0:
        return EXIT_OK
    if failed_count == 0:
        return EXIT_OK
    if success_count > 0:
        return EXIT_RESTORE_PARTIAL
    return EXIT_RESTORE_FAILED


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/restore_apply.py
#
# Current role:
#   - loads latest restore plan
#   - applies supported restore actions
#   - records restore run and restore events
#   - writes restore result JSON
#
# Next required file:
#   sentinel-core/tests/test_schema.py
#
# Signature:
#   Sentinel Core v1
#   Restore apply layer
# ==========================================================
