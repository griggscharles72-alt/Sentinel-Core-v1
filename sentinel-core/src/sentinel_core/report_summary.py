#!/usr/bin/env python3
"""
README
======

Filename:
    report_summary.py

Project:
    Sentinel Core v1

Purpose:
    Report generation logic for Sentinel Core.

This module is responsible for:

    - loading the latest check run
    - loading drift events for that check run
    - building a human-readable summary
    - building a machine-readable summary JSON
    - writing report artifacts to the reports directory

Design notes:

    - deterministic only
    - no restore actions here
    - summary is derived from stored DB state
    - reports should remain stable and easy to parse
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from sentinel_core.db_store import (
    get_drift_events_for_check_run,
    get_latest_check_run,
    initialize_database,
)
from sentinel_core.helpers.jsonio import atomic_write_json_file
from sentinel_core.helpers.paths import build_paths, ensure_runtime_directories
from sentinel_core.helpers.time_utils import utc_now_compact, utc_now_iso


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_NO_BASELINE = 12


def _build_summary_json(
    check_run: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a machine-readable summary object for the latest check run.
    """
    severity_counts = Counter(str(event.get("severity", "unknown")) for event in events)
    object_type_counts = Counter(str(event.get("object_type", "unknown")) for event in events)
    drift_type_counts = Counter(str(event.get("drift_type", "unknown")) for event in events)
    restorable_count = sum(1 for event in events if bool(event.get("restorable", False)))

    return {
        "generated_at": utc_now_iso(),
        "check_run": {
            "id": int(check_run["id"]),
            "started_at": check_run.get("started_at"),
            "finished_at": check_run.get("finished_at"),
            "baseline_run_id": check_run.get("baseline_run_id"),
            "status": check_run.get("status"),
            "drift_count": int(check_run.get("drift_count", 0)),
            "severe_count": int(check_run.get("severe_count", 0)),
        },
        "counts": {
            "events_total": len(events),
            "restorable_total": restorable_count,
            "severity": dict(sorted(severity_counts.items())),
            "object_type": dict(sorted(object_type_counts.items())),
            "drift_type": dict(sorted(drift_type_counts.items())),
        },
        "events": events,
    }


def _build_summary_text(
    check_run: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> str:
    """
    Build a human-readable summary text report.
    """
    severity_counts = Counter(str(event.get("severity", "unknown")) for event in events)
    object_type_counts = Counter(str(event.get("object_type", "unknown")) for event in events)
    drift_type_counts = Counter(str(event.get("drift_type", "unknown")) for event in events)
    restorable_count = sum(1 for event in events if bool(event.get("restorable", False)))

    lines: List[str] = []
    lines.append("Sentinel Core v1 — Report Summary")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Generated at: {utc_now_iso()}")
    lines.append(f"Check run id: {check_run.get('id')}")
    lines.append(f"Baseline run id: {check_run.get('baseline_run_id')}")
    lines.append(f"Started at: {check_run.get('started_at')}")
    lines.append(f"Finished at: {check_run.get('finished_at')}")
    lines.append(f"Status: {check_run.get('status')}")
    lines.append(f"Drift count: {check_run.get('drift_count', 0)}")
    lines.append(f"Severe count: {check_run.get('severe_count', 0)}")
    lines.append(f"Restorable count: {restorable_count}")
    lines.append("")

    lines.append("Severity counts:")
    if severity_counts:
        for key, value in sorted(severity_counts.items()):
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("Object type counts:")
    if object_type_counts:
        for key, value in sorted(object_type_counts.items()):
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("Drift type counts:")
    if drift_type_counts:
        for key, value in sorted(drift_type_counts.items()):
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("Event details:")
    if events:
        for index, event in enumerate(events, start=1):
            lines.append(
                f"{index}. [{event.get('severity')}] "
                f"{event.get('object_type')} "
                f"{event.get('path_or_name')} "
                f"drift={event.get('drift_type')} "
                f"expected={event.get('expected_value')} "
                f"observed={event.get('observed_value')} "
                f"restorable={event.get('restorable')}"
            )
    else:
        lines.append("No drift detected.")

    lines.append("")
    return "\n".join(lines)


def _write_text_file(path, content: str) -> None:
    """
    Write a UTF-8 text file with a trailing newline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")


def run_report() -> int:
    """
    Generate summary reports from the latest check run.
    """
    paths = build_paths()
    ensure_runtime_directories(paths)
    initialize_database(paths.db_path)

    check_run = get_latest_check_run(paths.db_path)
    if not check_run:
        print("ERROR: no check run found.")
        return EXIT_NO_BASELINE

    check_run_id = int(check_run["id"])
    events = get_drift_events_for_check_run(paths.db_path, check_run_id)

    summary_json = _build_summary_json(check_run, events)
    summary_text = _build_summary_text(check_run, events)

    stamp = utc_now_compact()
    json_path = paths.reports_dir / f"summary_{stamp}.json"
    text_path = paths.reports_dir / f"summary_{stamp}.txt"

    atomic_write_json_file(json_path, summary_json)
    _write_text_file(text_path, summary_text)

    print(f"INFO: report written: {text_path}")
    print(f"INFO: report written: {json_path}")
    return EXIT_OK


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/report_summary.py
#
# Current role:
#   - loads latest check run
#   - summarizes drift events
#   - writes text and JSON reports
#
# Next required file:
#   sentinel-core/src/sentinel_core/restore_decide.py
#
# Signature:
#   Sentinel Core v1
#   Report summary layer
# ==========================================================
