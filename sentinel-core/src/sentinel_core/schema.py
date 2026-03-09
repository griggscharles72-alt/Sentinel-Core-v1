#!/usr/bin/env python3
"""
README
======

Filename:
    schema.py

Project:
    Sentinel Core v1

Purpose:
    Central configuration validation and normalization for Sentinel Core.

This module validates and normalizes:

    - config/watchlist.json
    - config/restore.json
    - config/thresholds.json

Design goals:

    - deterministic behavior
    - standard-library only
    - explicit error messages
    - no hidden defaults beyond documented normalization

Validation scope for v1:

    - root object types
    - required field presence
    - basic field types
    - conservative normalization
"""

from __future__ import annotations

from typing import Any, Dict, List


class SchemaValidationError(ValueError):
    """
    Raised when configuration validation fails.
    """


def _require_dict(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaValidationError(f"{label} must be a JSON object")
    return value


def _require_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise SchemaValidationError(f"{label} must be a list")
    return value


def _require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(f"{label} must be a boolean")
    return value


def _require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SchemaValidationError(f"{label} must be an integer")
    return value


def validate_watchlist_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize watchlist.json.
    """
    data = _require_dict(raw, "watchlist")

    normalized: Dict[str, Any] = {
        "files": [],
        "directories": [],
        "services": [],
        "packages": [],
    }

    for root_key in normalized.keys():
        items = _require_list(data.get(root_key, []), f"watchlist.{root_key}")

        for index, item in enumerate(items):
            entry = _require_dict(item, f"watchlist.{root_key}[{index}]")

            if root_key == "files":
                normalized["files"].append(
                    {
                        "path": _require_str(entry.get("path"), f"watchlist.files[{index}].path"),
                        "must_exist": _require_bool(entry.get("must_exist", True), f"watchlist.files[{index}].must_exist"),
                        "restore_allowed": _require_bool(entry.get("restore_allowed", False), f"watchlist.files[{index}].restore_allowed"),
                    }
                )

            elif root_key == "directories":
                normalized["directories"].append(
                    {
                        "path": _require_str(entry.get("path"), f"watchlist.directories[{index}].path"),
                        "must_exist": _require_bool(entry.get("must_exist", True), f"watchlist.directories[{index}].must_exist"),
                    }
                )

            elif root_key == "services":
                normalized["services"].append(
                    {
                        "unit_name": _require_str(entry.get("unit_name"), f"watchlist.services[{index}].unit_name"),
                        "must_exist": _require_bool(entry.get("must_exist", True), f"watchlist.services[{index}].must_exist"),
                        "expected_enabled": _require_bool(entry.get("expected_enabled", True), f"watchlist.services[{index}].expected_enabled"),
                        "expected_active": _require_bool(entry.get("expected_active", True), f"watchlist.services[{index}].expected_active"),
                        "restore_allowed": _require_bool(entry.get("restore_allowed", False), f"watchlist.services[{index}].restore_allowed"),
                    }
                )

            elif root_key == "packages":
                normalized["packages"].append(
                    {
                        "package_name": _require_str(entry.get("package_name"), f"watchlist.packages[{index}].package_name"),
                        "must_be_installed": _require_bool(entry.get("must_be_installed", True), f"watchlist.packages[{index}].must_be_installed"),
                    }
                )

    return normalized


def validate_restore_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize restore.json.
    """
    data = _require_dict(raw, "restore")

    backend = _require_str(data.get("file_restore_backend", "rsync"), "restore.file_restore_backend")
    allowed_backends = {"rsync"}
    if backend not in allowed_backends:
        raise SchemaValidationError(
            f"restore.file_restore_backend must be one of: {', '.join(sorted(allowed_backends))}"
        )

    normalized = {
        "enabled": _require_bool(data.get("enabled", False), "restore.enabled"),
        "file_restore_backend": backend,
        "service_actions_enabled": _require_bool(
            data.get("service_actions_enabled", False),
            "restore.service_actions_enabled",
        ),
        "package_actions_enabled": _require_bool(
            data.get("package_actions_enabled", False),
            "restore.package_actions_enabled",
        ),
        "require_explicit_apply": _require_bool(
            data.get("require_explicit_apply", True),
            "restore.require_explicit_apply",
        ),
    }

    return normalized


def validate_thresholds_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize thresholds.json.
    """
    data = _require_dict(raw, "thresholds")

    normalized = {
        "high_drift_count_alert": _require_int(
            data.get("high_drift_count_alert", 1),
            "thresholds.high_drift_count_alert",
        ),
        "medium_drift_count_alert": _require_int(
            data.get("medium_drift_count_alert", 3),
            "thresholds.medium_drift_count_alert",
        ),
        "treat_missing_protected_file_as_high": _require_bool(
            data.get("treat_missing_protected_file_as_high", True),
            "thresholds.treat_missing_protected_file_as_high",
        ),
        "treat_inactive_expected_service_as_high": _require_bool(
            data.get("treat_inactive_expected_service_as_high", True),
            "thresholds.treat_inactive_expected_service_as_high",
        ),
        "treat_missing_required_package_as_high": _require_bool(
            data.get("treat_missing_required_package_as_high", True),
            "thresholds.treat_missing_required_package_as_high",
        ),
        "treat_missing_watched_directory_as_high": _require_bool(
            data.get("treat_missing_watched_directory_as_high", True),
            "thresholds.treat_missing_watched_directory_as_high",
        ),
    }

    if normalized["high_drift_count_alert"] < 0:
        raise SchemaValidationError("thresholds.high_drift_count_alert must be >= 0")

    if normalized["medium_drift_count_alert"] < 0:
        raise SchemaValidationError("thresholds.medium_drift_count_alert must be >= 0")

    return normalized


def validate_all_configs(
    watchlist_raw: Dict[str, Any],
    restore_raw: Dict[str, Any],
    thresholds_raw: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Validate all three config objects and return normalized versions.
    """
    return {
        "watchlist": validate_watchlist_config(watchlist_raw),
        "restore": validate_restore_config(restore_raw),
        "thresholds": validate_thresholds_config(thresholds_raw),
    }


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/schema.py
#
# Current role:
#   - validates and normalizes all Sentinel JSON configs
#   - raises SchemaValidationError on invalid input
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/__init__.py
#
# Signature:
#   Sentinel Core v1
#   Config schema layer
# ==========================================================
