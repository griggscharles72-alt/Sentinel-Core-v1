#!/usr/bin/env python3
"""
README
======

Filename:
    time_utils.py

Project:
    Sentinel Core v1

Purpose:
    Deterministic time helpers for Sentinel Core.

This module is responsible for:

    - generating UTC timestamps
    - generating ISO-8601-like strings
    - generating filename-safe time strings
    - centralizing time formatting for reports, logs, and DB records

Design notes:

    - use UTC consistently
    - keep formatting stable
    - avoid hidden locale behavior
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return the current UTC datetime as an aware datetime object.
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Return current UTC time in a stable ISO-like format.

    Example:
        2026-03-09T08:15:30Z
    """
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_compact() -> str:
    """
    Return current UTC time in a filename-safe compact format.

    Example:
        20260309T081530Z
    """
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def datetime_to_iso(value: datetime) -> str:
    """
    Convert a datetime to a stable UTC ISO-like string.

    Naive datetimes are treated as UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def datetime_to_compact(value: datetime) -> str:
    """
    Convert a datetime to a compact UTC filename-safe string.

    Naive datetimes are treated as UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.strftime("%Y%m%dT%H%M%SZ")


def epoch_seconds_utc() -> int:
    """
    Return current UTC epoch seconds as an integer.
    """
    return int(utc_now().timestamp())


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/time_utils.py
#
# Current role:
#   - provides UTC time helpers
#   - standardizes timestamps for logs, reports, and DB records
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/subprocess_safe.py
#
# Signature:
#   Sentinel Core v1
#   Time helper layer
# ==========================================================
