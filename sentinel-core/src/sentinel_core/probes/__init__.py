#!/usr/bin/env python3
"""
README
======

Filename:
    probe_files.py

Project:
    Sentinel Core v1

Purpose:
    File probe logic for Sentinel Core.

This module is responsible for:

    - probing watched file paths
    - collecting deterministic file state
    - returning explicit per-file results
    - preparing file observations for baseline and drift logic

Design notes:

    - standard library only
    - do not guess intent
    - return explicit structured data
    - missing files are valid probe results, not exceptions
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from sentinel_core.helpers.hash_utils import collect_file_state


def probe_file(path: str, must_exist: bool = True) -> Dict[str, Any]:
    """
    Probe a single file path and return deterministic state.
    """
    target = Path(path).expanduser()

    state = collect_file_state(target)
    state["object_type"] = "file"
    state["must_exist"] = bool(must_exist)

    if not state["exists"]:
        state["status"] = "missing" if must_exist else "absent_allowed"
    elif not state["is_file"]:
        state["status"] = "not_a_file"
    else:
        state["status"] = "ok"

    return state


def probe_files(file_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Probe multiple watched file entries.

    Expected entry shape:
        {
            "path": "...",
            "must_exist": true,
            "restore_allowed": false
        }
    """
    results: List[Dict[str, Any]] = []

    for entry in file_entries:
        path = str(entry["path"])
        must_exist = bool(entry.get("must_exist", True))
        restore_allowed = bool(entry.get("restore_allowed", False))

        result = probe_file(path=path, must_exist=must_exist)
        result["restore_allowed"] = restore_allowed
        results.append(result)

    return results


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/probes/probe_files.py
#
# Current role:
#   - probes watched file objects
#   - returns deterministic file state results
#
# Next required file:
#   sentinel-core/src/sentinel_core/probes/probe_directories.py
#
# Signature:
#   Sentinel Core v1
#   File probe layer
# ==========================================================
