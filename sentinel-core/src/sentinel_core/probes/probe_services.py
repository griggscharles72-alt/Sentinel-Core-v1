#!/usr/bin/env python3
"""
README
======

Filename:
    probe_services.py

Project:
    Sentinel Core v1

Purpose:
    Systemd service probe logic for Sentinel Core.

This module is responsible for:

    - probing watched systemd unit names
    - collecting deterministic service state
    - returning explicit per-service results
    - preparing service observations for baseline and drift logic

Design notes:

    - standard library only
    - uses systemctl through safe subprocess helpers
    - missing units are valid probe results, not exceptions
    - v1 focuses on exists/enabled/active state
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sentinel_core.helpers.subprocess_safe import command_exists, run_command


def _systemctl_show_value(unit_name: str, field: str) -> Optional[str]:
    """
    Read a single property from systemctl show.

    Returns:
        property value string, or None if unavailable
    """
    result = run_command(
        ["systemctl", "show", unit_name, "--property", field, "--value"],
        timeout=10,
    )

    if not result.ok:
        return None

    return result.stdout.strip()


def probe_service(
    unit_name: str,
    must_exist: bool = True,
    expected_enabled: bool = True,
    expected_active: bool = True,
) -> Dict[str, Any]:
    """
    Probe a single systemd service unit and return deterministic state.
    """
    state: Dict[str, Any] = {
        "object_type": "service",
        "unit_name": unit_name,
        "must_exist": bool(must_exist),
        "expected_enabled": bool(expected_enabled),
        "expected_active": bool(expected_active),
        "systemctl_available": command_exists("systemctl"),
        "exists": False,
        "load_state": None,
        "unit_file_state": None,
        "active_state": None,
        "sub_state": None,
        "status": None,
    }

    if not state["systemctl_available"]:
        state["status"] = "systemctl_unavailable"
        return state

    load_state = _systemctl_show_value(unit_name, "LoadState")
    unit_file_state = _systemctl_show_value(unit_name, "UnitFileState")
    active_state = _systemctl_show_value(unit_name, "ActiveState")
    sub_state = _systemctl_show_value(unit_name, "SubState")

    state["load_state"] = load_state
    state["unit_file_state"] = unit_file_state
    state["active_state"] = active_state
    state["sub_state"] = sub_state

    exists = load_state not in (None, "", "not-found")
    state["exists"] = exists

    if not exists:
        state["status"] = "missing" if must_exist else "absent_allowed"
        return state

    enabled_states = {"enabled", "static", "alias", "linked", "generated", "indirect"}
    state["enabled"] = unit_file_state in enabled_states
    state["active"] = active_state == "active"

    if expected_enabled and not state["enabled"]:
        state["status"] = "disabled"
    elif expected_active and not state["active"]:
        state["status"] = "inactive"
    else:
        state["status"] = "ok"

    return state


def probe_services(service_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Probe multiple watched service entries.

    Expected entry shape:
        {
            "unit_name": "example.service",
            "must_exist": true,
            "expected_enabled": true,
            "expected_active": true,
            "restore_allowed": false
        }
    """
    results: List[Dict[str, Any]] = []

    for entry in service_entries:
        unit_name = str(entry["unit_name"])
        must_exist = bool(entry.get("must_exist", True))
        expected_enabled = bool(entry.get("expected_enabled", True))
        expected_active = bool(entry.get("expected_active", True))
        restore_allowed = bool(entry.get("restore_allowed", False))

        result = probe_service(
            unit_name=unit_name,
            must_exist=must_exist,
            expected_enabled=expected_enabled,
            expected_active=expected_active,
        )
        result["restore_allowed"] = restore_allowed
        results.append(result)

    return results


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/probes/probe_services.py
#
# Current role:
#   - probes watched service objects
#   - returns deterministic service state results
#
# Next required file:
#   sentinel-core/src/sentinel_core/probes/probe_packages.py
#
# Signature:
#   Sentinel Core v1
#   Service probe layer
# ==========================================================
