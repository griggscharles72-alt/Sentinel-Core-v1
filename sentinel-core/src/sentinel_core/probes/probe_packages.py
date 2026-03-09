Path

sentinel-core/src/sentinel_core/probes/probe_packages.py

#!/usr/bin/env python3
"""
README
======

Filename:
    probe_packages.py

Project:
    Sentinel Core v1

Purpose:
    Package probe logic for Sentinel Core.

This module is responsible for:

    - probing watched package names
    - collecting deterministic package presence state
    - returning explicit per-package results
    - preparing package observations for baseline and drift logic

Design notes:

    - standard library only
    - Debian/Ubuntu-first for v1
    - uses dpkg-query through safe subprocess helpers
    - missing packages are valid probe results, not exceptions
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sentinel_core.helpers.subprocess_safe import command_exists, run_command


def _query_dpkg_package(package_name: str) -> Dict[str, Optional[str]]:
    """
    Query a package using dpkg-query.

    Returns a small structured result with:
        - installed
        - status
        - version
    """
    result = run_command(
        ["dpkg-query", "-W", "-f=${Status}\t${Version}\n", package_name],
        timeout=10,
    )

    if not result.ok:
        return {
            "installed": False,
            "status": None,
            "version": None,
        }

    output = result.stdout.strip()
    if not output:
        return {
            "installed": False,
            "status": None,
            "version": None,
        }

    parts = output.split("\t", 1)
    status_text = parts[0].strip() if len(parts) >= 1 else ""
    version_text = parts[1].strip() if len(parts) == 2 else None

    installed = status_text == "install ok installed"

    return {
        "installed": installed,
        "status": status_text or None,
        "version": version_text or None,
    }


def probe_package(package_name: str, must_be_installed: bool = True) -> Dict[str, Any]:
    """
    Probe a single package name and return deterministic state.
    """
    state: Dict[str, Any] = {
        "object_type": "package",
        "package_name": package_name,
        "must_be_installed": bool(must_be_installed),
        "dpkg_query_available": command_exists("dpkg-query"),
        "installed": False,
        "status_text": None,
        "version": None,
        "status": None,
    }

    if not state["dpkg_query_available"]:
        state["status"] = "dpkg_query_unavailable"
        return state

    query = _query_dpkg_package(package_name)
    state["installed"] = bool(query["installed"])
    state["status_text"] = query["status"]
    state["version"] = query["version"]

    if not state["installed"]:
        state["status"] = "missing" if must_be_installed else "absent_allowed"
    else:
        state["status"] = "ok"

    return state


def probe_packages(package_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Probe multiple watched package entries.

    Expected entry shape:
        {
            "package_name": "python3",
            "must_be_installed": true
        }
    """
    results: List[Dict[str, Any]] = []

    for entry in package_entries:
        package_name = str(entry["package_name"])
        must_be_installed = bool(entry.get("must_be_installed", True))

        result = probe_package(
            package_name=package_name,
            must_be_installed=must_be_installed,
        )
        results.append(result)

    return results


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/probes/probe_packages.py
#
# Current role:
#   - probes watched package objects
#   - returns deterministic package state results
#
# Next required file:
#   sentinel-core/src/sentinel_core/baseline_build.py
#
# Signature:
#   Sentinel Core v1
#   Package probe layer
# ==========================================================
