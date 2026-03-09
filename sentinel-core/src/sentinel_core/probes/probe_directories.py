#!/usr/bin/env python3
"""
README
======

Filename:
    probe_directories.py

Project:
    Sentinel Core v1

Purpose:
    Directory probe logic for Sentinel Core.

This module is responsible for:

    - probing watched directory paths
    - collecting deterministic directory state
    - returning explicit per-directory results
    - preparing directory observations for baseline and drift logic

Design notes:

    - standard library only
    - do not recursively hash directory trees in v1
    - missing directories are valid probe results, not exceptions
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from sentinel_core.helpers.hash_utils import collect_directory_state


def probe_directory(path: str, must_exist: bool = True) -> Dict[str, Any]:
    """
    Probe a single directory path and return deterministic state.
    """
    target = Path(path).expanduser()

    state = collect_directory_state(target)
    state["object_type"] = "directory"
    state["must_exist"] = bool(must_exist)

    if not state["exists"]:
        state["status"] = "missing" if must_exist else "absent_allowed"
    elif not state["is_dir"]:
        state["status"] = "not_a_directory"
    else:
        state["status"] = "ok"

    return state


def probe_directories(directory_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Probe multiple watched directory entries.

    Expected entry shape:
        {
            "path": "...",
            "must_exist": true
        }
    """
    results: List[Dict[str, Any]] = []

    for entry in directory_entries:
        path = str(entry["path"])
        must_exist = bool(entry.get("must_exist", True))

        result = probe_directory(path=path, must_exist=must_exist)
        results.append(result)

    return results


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/probes/probe_directories.py
#
# Current role:
#   - probes watched directory objects
#   - returns deterministic directory state results
#
# Next required file:
#   sentinel-core/src/sentinel_core/probes/probe_services.py
#
# Signature:
#   Sentinel Core v1
#   Directory probe layer
# ==========================================================
