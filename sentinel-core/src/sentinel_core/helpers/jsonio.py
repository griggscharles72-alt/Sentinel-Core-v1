#!/usr/bin/env python3
"""
README
======

Filename:
    jsonio.py

Project:
    Sentinel Core v1

Purpose:
    Safe JSON read/write helpers for Sentinel Core.

This module is responsible for:

    - Reading JSON objects from disk
    - Writing JSON objects to disk
    - Using deterministic formatting
    - Supporting atomic-style writes where practical
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def read_json_file(path: Path) -> Dict[str, Any]:
    """
    Read a JSON object from disk.
    """
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")

    return data


def write_json_file(path: Path, data: Dict[str, Any]) -> None:
    """
    Write a JSON object to disk with stable formatting.
    """
    if not isinstance(data, dict):
        raise ValueError("write_json_file expects a dict")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def atomic_write_json_file(path: Path, data: Dict[str, Any]) -> None:
    """
    Write a JSON object using a temporary sibling file and replace.
    """
    if not isinstance(data, dict):
        raise ValueError("atomic_write_json_file expects a dict")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")

    temp_path.replace(path)


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/jsonio.py
#
# Current role:
#   - reads and writes JSON config/report files
#   - provides stable formatting and atomic-style writes
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/log_utils.py
#
# Signature:
#   Sentinel Core v1
#   JSON I/O layer
# ==========================================================
