#!/usr/bin/env python3
"""
README
======

Filename:
    doctor_env.py

Project:
    Sentinel Core v1

Purpose:
    Runtime environment and configuration validation for Sentinel Core.

This module is responsible for:

    - verifying required directories can be created or written
    - verifying required config files exist and are readable
    - verifying required external tools are present
    - performing early sanity checks before baseline/check/report work

Design notes:

    - keep this deterministic and boring
    - return stable exit codes
    - report what failed clearly
    - avoid side effects beyond safe directory creation

Current scope:

    - validate repo-relative runtime paths
    - validate config presence and JSON readability
    - validate python3, sha256sum, sqlite3
    - validate rsync if restore is enabled
    - validate systemctl if service watches exist

This is intended to be the first fully wired command.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3


def _repo_root() -> Path:
    """
    Resolve repo root from this file location.

    Expected file location:
        sentinel-core/src/sentinel_core/doctor_env.py

    Repo root is therefore:
        parents[2]
    """
    return Path(__file__).resolve().parents[2]


def _config_dir(repo_root: Path) -> Path:
    return repo_root / "config"


def _data_dir(repo_root: Path) -> Path:
    return repo_root / "data"


def _required_runtime_directories(repo_root: Path) -> List[Path]:
    data_dir = _data_dir(repo_root)
    return [
        data_dir,
        data_dir / "db",
        data_dir / "baselines",
        data_dir / "baselines" / "files",
        data_dir / "baselines" / "manifests",
        data_dir / "snapshots",
        data_dir / "reports",
        data_dir / "logs",
    ]


def _required_config_files(repo_root: Path) -> List[Path]:
    config_dir = _config_dir(repo_root)
    return [
        config_dir / "watchlist.json",
        config_dir / "restore.json",
        config_dir / "thresholds.json",
    ]


def _load_json_file(path: Path) -> Dict[str, Any]:
    """
    Load a JSON object from disk.

    Raises:
        FileNotFoundError
        PermissionError
        json.JSONDecodeError
        ValueError
    """
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object in {path}")

    return data


def _check_tool(tool_name: str) -> bool:
    """
    Return True if the tool exists in PATH.
    """
    return shutil.which(tool_name) is not None


def _safe_create_directory(path: Path) -> Tuple[bool, str]:
    """
    Ensure a directory exists and is writable.

    Returns:
        (success, message)
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return False, f"failed to create directory: {path} ({exc})"

    if not path.is_dir():
        return False, f"path is not a directory: {path}"

    if not os_access_write(path):
        return False, f"directory is not writable: {path}"

    return True, f"ok: {path}"


def os_access_write(path: Path) -> bool:
    """
    Conservative writability test.

    Uses a temporary file creation attempt rather than os.access alone.
    """
    probe_file = path / ".sentinel_write_test.tmp"
    try:
        with probe_file.open("w", encoding="utf-8") as handle:
            handle.write("sentinel-core-write-test\n")
        probe_file.unlink(missing_ok=True)
        return True
    except Exception:
        try:
            probe_file.unlink(missing_ok=True)
        except Exception:
            pass
        return False


def _watchlist_declares_services(watchlist: Dict[str, Any]) -> bool:
    services = watchlist.get("services", [])
    return isinstance(services, list) and len(services) > 0


def _restore_enabled(restore_cfg: Dict[str, Any]) -> bool:
    return bool(restore_cfg.get("enabled", False))


def _print_header() -> None:
    print("INFO: Sentinel Core v1 — doctor start")


def _print_ok(message: str) -> None:
    print(f"OK: {message}")


def _print_error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def run_doctor() -> int:
    """
    Run deterministic environment and configuration validation.

    Exit codes:
        0  success
        2  config error
        3  dependency error
        1  runtime error
    """
    _print_header()

    repo_root = _repo_root()
    _print_ok(f"repo root resolved: {repo_root}")

    config_files = _required_config_files(repo_root)
    runtime_dirs = _required_runtime_directories(repo_root)

    config_errors: List[str] = []
    dependency_errors: List[str] = []
    runtime_errors: List[str] = []

    watchlist: Dict[str, Any] = {}
    restore_cfg: Dict[str, Any] = {}
    thresholds_cfg: Dict[str, Any] = {}

    for directory in runtime_dirs:
        success, message = _safe_create_directory(directory)
        if success:
            _print_ok(message)
        else:
            runtime_errors.append(message)

    for config_path in config_files:
        if not config_path.exists():
            config_errors.append(f"missing config file: {config_path}")
            continue

        if not config_path.is_file():
            config_errors.append(f"config path is not a file: {config_path}")
            continue

        try:
            data = _load_json_file(config_path)
            _print_ok(f"config readable: {config_path.name}")

            if config_path.name == "watchlist.json":
                watchlist = data
            elif config_path.name == "restore.json":
                restore_cfg = data
            elif config_path.name == "thresholds.json":
                thresholds_cfg = data

        except json.JSONDecodeError as exc:
            config_errors.append(f"invalid JSON in {config_path}: {exc}")
        except ValueError as exc:
            config_errors.append(str(exc))
        except PermissionError:
            config_errors.append(f"permission denied reading config: {config_path}")
        except Exception as exc:
            config_errors.append(f"failed reading config {config_path}: {exc}")

    if thresholds_cfg:
        _print_ok("thresholds config loaded")

    required_tools = [
        "python3",
        "sha256sum",
        "sqlite3",
    ]

    for tool in required_tools:
        if _check_tool(tool):
            _print_ok(f"dependency present: {tool}")
        else:
            dependency_errors.append(f"required tool not found in PATH: {tool}")

    if _restore_enabled(restore_cfg):
        if _check_tool("rsync"):
            _print_ok("dependency present: rsync")
        else:
            dependency_errors.append("restore enabled but rsync not found in PATH")

    if _watchlist_declares_services(watchlist):
        if _check_tool("systemctl"):
            _print_ok("dependency present: systemctl")
        else:
            dependency_errors.append("services declared in watchlist but systemctl not found in PATH")

    if config_errors:
        for message in config_errors:
            _print_error(message)
        return EXIT_CONFIG_ERROR

    if dependency_errors:
        for message in dependency_errors:
            _print_error(message)
        return EXIT_DEPENDENCY_ERROR

    if runtime_errors:
        for message in runtime_errors:
            _print_error(message)
        return EXIT_RUNTIME_ERROR

    print("INFO: Sentinel Core v1 — doctor success")
    return EXIT_OK


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/doctor_env.py
#
# This file is used by:
#   sentinel-core/src/sentinel_core/main_wrapper.py
#
# Current behavior:
#   - creates runtime directories if missing
#   - validates config files exist and contain JSON objects
#   - checks required tool presence
#   - returns stable exit codes
#
# Next required file:
#   sentinel-core/src/sentinel_core/schema.py
#
# Signature:
#   Sentinel Core v1
#   Environment doctor
# ==========================================================
