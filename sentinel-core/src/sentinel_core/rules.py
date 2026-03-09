#!/usr/bin/env python3
"""
README
======

Filename:
    rules.py

Project:
    Sentinel Core v1

Purpose:
    Deterministic drift classification and severity rules for Sentinel Core.

This module is responsible for:

    - classifying file drift
    - classifying directory drift
    - classifying service drift
    - classifying package drift
    - assigning deterministic severity values
    - deciding baseline comparison outcomes in a narrow v1-safe way

Design notes:

    - explicit rules only
    - no fuzzy scoring
    - no AI logic
    - one object comparison in, structured drift result out
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"


def _stringify(value: Any) -> Optional[str]:
    """
    Convert a value to a stable string form, preserving None.
    """
    if value is None:
        return None
    return str(value)


def _event(
    object_type: str,
    object_key: str,
    path_or_name: str,
    drift_type: str,
    expected_value: Any,
    observed_value: Any,
    severity: str,
    restorable: bool = False,
) -> Dict[str, Any]:
    """
    Build a normalized drift event object.
    """
    return {
        "object_type": object_type,
        "object_key": object_key,
        "path_or_name": path_or_name,
        "drift_type": drift_type,
        "expected_value": _stringify(expected_value),
        "observed_value": _stringify(observed_value),
        "severity": severity,
        "restorable": bool(restorable),
    }


def classify_file_drift(
    expected: Dict[str, Any],
    observed: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compare expected file state to observed file state and return drift events.
    """
    events: List[Dict[str, Any]] = []

    path = str(expected["path"])
    must_exist = bool(expected.get("must_exist", True))
    restore_allowed = bool(observed.get("restore_allowed", False))
    object_key = path

    if must_exist and not observed.get("exists", False):
        events.append(
            _event(
                object_type="file",
                object_key=object_key,
                path_or_name=path,
                drift_type="missing",
                expected_value=True,
                observed_value=False,
                severity=SEVERITY_HIGH,
                restorable=restore_allowed,
            )
        )
        return events

    if observed.get("exists", False) and not observed.get("is_file", False):
        events.append(
            _event(
                object_type="file",
                object_key=object_key,
                path_or_name=path,
                drift_type="not_a_file",
                expected_value="regular_file",
                observed_value="other_path_type",
                severity=SEVERITY_HIGH,
                restorable=False,
            )
        )
        return events

    if not observed.get("exists", False):
        return events

    expected_sha256 = expected.get("expected_sha256")
    observed_sha256 = observed.get("sha256")
    if expected_sha256 != observed_sha256:
        events.append(
            _event(
                object_type="file",
                object_key=object_key,
                path_or_name=path,
                drift_type="hash_changed",
                expected_value=expected_sha256,
                observed_value=observed_sha256,
                severity=SEVERITY_HIGH,
                restorable=restore_allowed,
            )
        )

    expected_mode = expected.get("expected_mode")
    observed_mode = observed.get("mode")
    if expected_mode != observed_mode:
        events.append(
            _event(
                object_type="file",
                object_key=object_key,
                path_or_name=path,
                drift_type="mode_changed",
                expected_value=expected_mode,
                observed_value=observed_mode,
                severity=SEVERITY_MEDIUM,
                restorable=restore_allowed,
            )
        )

    expected_uid = expected.get("expected_uid")
    observed_uid = observed.get("uid")
    if expected_uid != observed_uid:
        events.append(
            _event(
                object_type="file",
                object_key=object_key,
                path_or_name=path,
                drift_type="owner_uid_changed",
                expected_value=expected_uid,
                observed_value=observed_uid,
                severity=SEVERITY_MEDIUM,
                restorable=False,
            )
        )

    expected_gid = expected.get("expected_gid")
    observed_gid = observed.get("gid")
    if expected_gid != observed_gid:
        events.append(
            _event(
                object_type="file",
                object_key=object_key,
                path_or_name=path,
                drift_type="owner_gid_changed",
                expected_value=expected_gid,
                observed_value=observed_gid,
                severity=SEVERITY_MEDIUM,
                restorable=False,
            )
        )

    return events


def classify_directory_drift(
    expected: Dict[str, Any],
    observed: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compare expected directory state to observed directory state and return drift events.
    """
    events: List[Dict[str, Any]] = []

    path = str(expected["path"])
    must_exist = bool(expected.get("must_exist", True))
    object_key = path

    if must_exist and not observed.get("exists", False):
        events.append(
            _event(
                object_type="directory",
                object_key=object_key,
                path_or_name=path,
                drift_type="directory_missing",
                expected_value=True,
                observed_value=False,
                severity=SEVERITY_HIGH,
                restorable=False,
            )
        )
        return events

    if observed.get("exists", False) and not observed.get("is_dir", False):
        events.append(
            _event(
                object_type="directory",
                object_key=object_key,
                path_or_name=path,
                drift_type="not_a_directory",
                expected_value="directory",
                observed_value="other_path_type",
                severity=SEVERITY_HIGH,
                restorable=False,
            )
        )
        return events

    if not observed.get("exists", False):
        return events

    expected_mode = expected.get("expected_mode")
    observed_mode = observed.get("mode")
    if expected_mode != observed_mode:
        events.append(
            _event(
                object_type="directory",
                object_key=object_key,
                path_or_name=path,
                drift_type="mode_changed",
                expected_value=expected_mode,
                observed_value=observed_mode,
                severity=SEVERITY_MEDIUM,
                restorable=False,
            )
        )

    expected_uid = expected.get("expected_uid")
    observed_uid = observed.get("uid")
    if expected_uid != observed_uid:
        events.append(
            _event(
                object_type="directory",
                object_key=object_key,
                path_or_name=path,
                drift_type="owner_uid_changed",
                expected_value=expected_uid,
                observed_value=observed_uid,
                severity=SEVERITY_MEDIUM,
                restorable=False,
            )
        )

    expected_gid = expected.get("expected_gid")
    observed_gid = observed.get("gid")
    if expected_gid != observed_gid:
        events.append(
            _event(
                object_type="directory",
                object_key=object_key,
                path_or_name=path,
                drift_type="owner_gid_changed",
                expected_value=expected_gid,
                observed_value=observed_gid,
                severity=SEVERITY_MEDIUM,
                restorable=False,
            )
        )

    return events


def classify_service_drift(
    expected: Dict[str, Any],
    observed: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compare expected service state to observed service state and return drift events.
    """
    events: List[Dict[str, Any]] = []

    unit_name = str(expected["unit_name"])
    must_exist = bool(expected.get("must_exist", True))
    expected_enabled = bool(expected.get("expected_enabled", True))
    expected_active = bool(expected.get("expected_active", True))
    restore_allowed = bool(observed.get("restore_allowed", False))
    object_key = unit_name

    if observed.get("status") == "systemctl_unavailable":
        events.append(
            _event(
                object_type="service",
                object_key=object_key,
                path_or_name=unit_name,
                drift_type="systemctl_unavailable",
                expected_value="systemctl_available",
                observed_value="systemctl_unavailable",
                severity=SEVERITY_HIGH,
                restorable=False,
            )
        )
        return events

    if must_exist and not observed.get("exists", False):
        events.append(
            _event(
                object_type="service",
                object_key=object_key,
                path_or_name=unit_name,
                drift_type="service_not_found",
                expected_value=True,
                observed_value=False,
                severity=SEVERITY_HIGH,
                restorable=restore_allowed,
            )
        )
        return events

    if not observed.get("exists", False):
        return events

    if expected_enabled and not observed.get("enabled", False):
        events.append(
            _event(
                object_type="service",
                object_key=object_key,
                path_or_name=unit_name,
                drift_type="service_disabled",
                expected_value=True,
                observed_value=False,
                severity=SEVERITY_HIGH,
                restorable=restore_allowed,
            )
        )

    if expected_active and not observed.get("active", False):
        events.append(
            _event(
                object_type="service",
                object_key=object_key,
                path_or_name=unit_name,
                drift_type="service_inactive",
                expected_value=True,
                observed_value=False,
                severity=SEVERITY_HIGH,
                restorable=restore_allowed,
            )
        )

    return events


def classify_package_drift(
    expected: Dict[str, Any],
    observed: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compare expected package state to observed package state and return drift events.
    """
    events: List[Dict[str, Any]] = []

    package_name = str(expected["package_name"])
    must_be_installed = bool(expected.get("must_be_installed", True))
    object_key = package_name

    if observed.get("status") == "dpkg_query_unavailable":
        events.append(
            _event(
                object_type="package",
                object_key=object_key,
                path_or_name=package_name,
                drift_type="dpkg_query_unavailable",
                expected_value="dpkg-query_available",
                observed_value="dpkg_query_unavailable",
                severity=SEVERITY_HIGH,
                restorable=False,
            )
        )
        return events

    if must_be_installed and not observed.get("installed", False):
        events.append(
            _event(
                object_type="package",
                object_key=object_key,
                path_or_name=package_name,
                drift_type="package_missing",
                expected_value=True,
                observed_value=False,
                severity=SEVERITY_HIGH,
                restorable=False,
            )
        )

    return events


def count_severe_events(events: List[Dict[str, Any]]) -> int:
    """
    Count high-severity events.
    """
    return sum(1 for event in events if event.get("severity") == SEVERITY_HIGH)


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/rules.py
#
# Current role:
#   - classifies drift for files, directories, services, and packages
#   - assigns deterministic severity values
#
# Next required file:
#   sentinel-core/src/sentinel_core/drift_check.py
#
# Signature:
#   Sentinel Core v1
#   Drift rules layer
# ==========================================================
