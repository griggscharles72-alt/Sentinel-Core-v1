#!/usr/bin/env python3
"""
README
======

Filename:
    hash_utils.py

Project:
    Sentinel Core v1

Purpose:
    File hashing and file-state helpers for Sentinel Core.

This module is responsible for:

    - computing SHA-256 hashes for files
    - collecting deterministic file metadata
    - checking file existence and type
    - preparing file state data for probe and baseline logic

Design notes:

    - standard library only
    - read files in chunks
    - do not hash directories
    - keep returned structures explicit
"""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from typing import Any, Dict, Optional


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA-256 for a file and return the hex digest.
    """
    if not path.exists():
        raise FileNotFoundError(f"file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"path is not a regular file: {path}")

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def file_mode_octal(path: Path) -> str:
    """
    Return the file mode as a zero-padded octal permission string.

    Example:
        0644
        0755
    """
    mode = path.stat().st_mode
    perms = stat.S_IMODE(mode)
    return f"{perms:04o}"


def collect_file_state(path: Path) -> Dict[str, Any]:
    """
    Collect deterministic file state for a regular file.

    Returned keys:
        - path
        - exists
        - is_file
        - sha256
        - mode
        - size_bytes
        - mtime_epoch
        - uid
        - gid
    """
    result: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": False,
        "sha256": None,
        "mode": None,
        "size_bytes": None,
        "mtime_epoch": None,
        "uid": None,
        "gid": None,
    }

    if not path.exists():
        return result

    if not path.is_file():
        return result

    info = path.stat()

    result["is_file"] = True
    result["sha256"] = sha256_file(path)
    result["mode"] = file_mode_octal(path)
    result["size_bytes"] = int(info.st_size)
    result["mtime_epoch"] = int(info.st_mtime)
    result["uid"] = int(info.st_uid)
    result["gid"] = int(info.st_gid)

    return result


def collect_directory_state(path: Path) -> Dict[str, Any]:
    """
    Collect deterministic state for a directory.

    Returned keys:
        - path
        - exists
        - is_dir
        - mode
        - mtime_epoch
        - uid
        - gid
    """
    result: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": False,
        "mode": None,
        "mtime_epoch": None,
        "uid": None,
        "gid": None,
    }

    if not path.exists():
        return result

    if not path.is_dir():
        return result

    info = path.stat()

    result["is_dir"] = True
    result["mode"] = file_mode_octal(path)
    result["mtime_epoch"] = int(info.st_mtime)
    result["uid"] = int(info.st_uid)
    result["gid"] = int(info.st_gid)

    return result


def safe_sha256_file(path: Path) -> Optional[str]:
    """
    Return SHA-256 for a file, or None if it cannot be computed.
    """
    try:
        return sha256_file(path)
    except Exception:
        return None


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/hash_utils.py
#
# Current role:
#   - computes file hashes
#   - collects deterministic file and directory metadata
#   - supports baseline/probe logic
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/sqlite_utils.py
#
# Signature:
#   Sentinel Core v1
#   Hash and file-state helper layer
# ==========================================================
