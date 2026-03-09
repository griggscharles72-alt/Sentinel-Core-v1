#!/usr/bin/env python3
"""
README
======

Filename:
    db_store.py

Project:
    Sentinel Core v1

Purpose:
    SQLite schema and storage helpers for Sentinel Core.

This module is responsible for:

    - creating the Sentinel database schema
    - storing baseline run metadata
    - storing check run metadata
    - storing drift events
    - storing restore run metadata
    - storing restore events
    - exposing small deterministic DB helper functions

Design notes:

    - standard library only
    - keep schema creation centralized
    - keep inserts explicit
    - avoid ORM complexity
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sentinel_core.helpers.sqlite_utils import (
    fetch_all,
    fetch_one,
    sqlite_connection,
    sqlite_transaction,
)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS baseline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    config_hash TEXT,
    note TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS watched_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    must_exist INTEGER NOT NULL,
    expected_sha256 TEXT,
    expected_mode TEXT,
    expected_uid INTEGER,
    expected_gid INTEGER,
    size_bytes INTEGER,
    mtime_epoch INTEGER,
    baseline_copy_path TEXT,
    FOREIGN KEY (baseline_run_id) REFERENCES baseline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watched_directories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    must_exist INTEGER NOT NULL,
    expected_mode TEXT,
    expected_uid INTEGER,
    expected_gid INTEGER,
    FOREIGN KEY (baseline_run_id) REFERENCES baseline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watched_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id INTEGER NOT NULL,
    unit_name TEXT NOT NULL,
    must_exist INTEGER NOT NULL,
    expected_enabled INTEGER NOT NULL,
    expected_active INTEGER NOT NULL,
    unit_file_path TEXT,
    unit_file_sha256 TEXT,
    FOREIGN KEY (baseline_run_id) REFERENCES baseline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watched_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id INTEGER NOT NULL,
    package_name TEXT NOT NULL,
    must_be_installed INTEGER NOT NULL,
    version_string TEXT,
    FOREIGN KEY (baseline_run_id) REFERENCES baseline_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS check_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    baseline_run_id INTEGER,
    status TEXT,
    drift_count INTEGER NOT NULL DEFAULT 0,
    severe_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (baseline_run_id) REFERENCES baseline_runs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS drift_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_run_id INTEGER NOT NULL,
    object_type TEXT NOT NULL,
    object_key TEXT,
    path_or_name TEXT NOT NULL,
    drift_type TEXT NOT NULL,
    expected_value TEXT,
    observed_value TEXT,
    severity TEXT NOT NULL,
    restorable INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (check_run_id) REFERENCES check_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restore_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    check_run_id INTEGER,
    status TEXT,
    attempted_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (check_run_id) REFERENCES check_runs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS restore_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restore_run_id INTEGER NOT NULL,
    object_type TEXT NOT NULL,
    object_key TEXT,
    action TEXT NOT NULL,
    source_path TEXT,
    target_path TEXT,
    result TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (restore_run_id) REFERENCES restore_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_baseline_runs_is_active
ON baseline_runs(is_active);

CREATE INDEX IF NOT EXISTS idx_watched_files_baseline_run_id
ON watched_files(baseline_run_id);

CREATE INDEX IF NOT EXISTS idx_watched_directories_baseline_run_id
ON watched_directories(baseline_run_id);

CREATE INDEX IF NOT EXISTS idx_watched_services_baseline_run_id
ON watched_services(baseline_run_id);

CREATE INDEX IF NOT EXISTS idx_watched_packages_baseline_run_id
ON watched_packages(baseline_run_id);

CREATE INDEX IF NOT EXISTS idx_check_runs_baseline_run_id
ON check_runs(baseline_run_id);

CREATE INDEX IF NOT EXISTS idx_drift_events_check_run_id
ON drift_events(check_run_id);

CREATE INDEX IF NOT EXISTS idx_restore_runs_check_run_id
ON restore_runs(check_run_id);

CREATE INDEX IF NOT EXISTS idx_restore_events_restore_run_id
ON restore_events(restore_run_id);
"""


def initialize_database(db_path: Path) -> None:
    """
    Create the Sentinel schema if it does not already exist.
    """
    with sqlite_connection(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.commit()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Convert a sqlite3.Row into a regular dict.
    """
    return dict(row)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    """
    Convert multiple sqlite3.Row objects into a list of dicts.
    """
    return [dict(row) for row in rows]


def deactivate_all_baselines(db_path: Path) -> None:
    """
    Mark all baseline runs as inactive.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            connection.execute("UPDATE baseline_runs SET is_active = 0")


def create_baseline_run(
    db_path: Path,
    created_at: str,
    config_hash: Optional[str] = None,
    note: Optional[str] = None,
    is_active: bool = True,
) -> int:
    """
    Create a baseline run row and return the inserted row id.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            if is_active:
                connection.execute("UPDATE baseline_runs SET is_active = 0")

            cursor = connection.execute(
                """
                INSERT INTO baseline_runs (created_at, config_hash, note, is_active)
                VALUES (?, ?, ?, ?)
                """,
                (created_at, config_hash, note, int(is_active)),
            )
            return int(cursor.lastrowid)


def get_active_baseline_run(db_path: Path) -> Optional[Dict[str, Any]]:
    """
    Return the active baseline run, if one exists.
    """
    with sqlite_connection(db_path) as connection:
        row = fetch_one(
            connection,
            """
            SELECT *
            FROM baseline_runs
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
            """,
        )
        return row_to_dict(row) if row else None


def insert_watched_file(
    db_path: Path,
    baseline_run_id: int,
    path: str,
    must_exist: bool,
    expected_sha256: Optional[str],
    expected_mode: Optional[str],
    expected_uid: Optional[int],
    expected_gid: Optional[int],
    size_bytes: Optional[int],
    mtime_epoch: Optional[int],
    baseline_copy_path: Optional[str],
) -> int:
    """
    Insert a watched file row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO watched_files (
                    baseline_run_id,
                    path,
                    must_exist,
                    expected_sha256,
                    expected_mode,
                    expected_uid,
                    expected_gid,
                    size_bytes,
                    mtime_epoch,
                    baseline_copy_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline_run_id,
                    path,
                    int(must_exist),
                    expected_sha256,
                    expected_mode,
                    expected_uid,
                    expected_gid,
                    size_bytes,
                    mtime_epoch,
                    baseline_copy_path,
                ),
            )
            return int(cursor.lastrowid)


def insert_watched_directory(
    db_path: Path,
    baseline_run_id: int,
    path: str,
    must_exist: bool,
    expected_mode: Optional[str],
    expected_uid: Optional[int],
    expected_gid: Optional[int],
) -> int:
    """
    Insert a watched directory row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO watched_directories (
                    baseline_run_id,
                    path,
                    must_exist,
                    expected_mode,
                    expected_uid,
                    expected_gid
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline_run_id,
                    path,
                    int(must_exist),
                    expected_mode,
                    expected_uid,
                    expected_gid,
                ),
            )
            return int(cursor.lastrowid)


def insert_watched_service(
    db_path: Path,
    baseline_run_id: int,
    unit_name: str,
    must_exist: bool,
    expected_enabled: bool,
    expected_active: bool,
    unit_file_path: Optional[str] = None,
    unit_file_sha256: Optional[str] = None,
) -> int:
    """
    Insert a watched service row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO watched_services (
                    baseline_run_id,
                    unit_name,
                    must_exist,
                    expected_enabled,
                    expected_active,
                    unit_file_path,
                    unit_file_sha256
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline_run_id,
                    unit_name,
                    int(must_exist),
                    int(expected_enabled),
                    int(expected_active),
                    unit_file_path,
                    unit_file_sha256,
                ),
            )
            return int(cursor.lastrowid)


def insert_watched_package(
    db_path: Path,
    baseline_run_id: int,
    package_name: str,
    must_be_installed: bool,
    version_string: Optional[str] = None,
) -> int:
    """
    Insert a watched package row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO watched_packages (
                    baseline_run_id,
                    package_name,
                    must_be_installed,
                    version_string
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    baseline_run_id,
                    package_name,
                    int(must_be_installed),
                    version_string,
                ),
            )
            return int(cursor.lastrowid)


def create_check_run(
    db_path: Path,
    started_at: str,
    baseline_run_id: Optional[int],
    status: Optional[str] = None,
) -> int:
    """
    Create a check run row and return its id.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO check_runs (
                    started_at,
                    baseline_run_id,
                    status
                )
                VALUES (?, ?, ?)
                """,
                (started_at, baseline_run_id, status),
            )
            return int(cursor.lastrowid)


def finalize_check_run(
    db_path: Path,
    check_run_id: int,
    finished_at: str,
    status: str,
    drift_count: int,
    severe_count: int,
) -> None:
    """
    Finalize a check run row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            connection.execute(
                """
                UPDATE check_runs
                SET finished_at = ?,
                    status = ?,
                    drift_count = ?,
                    severe_count = ?
                WHERE id = ?
                """,
                (finished_at, status, drift_count, severe_count, check_run_id),
            )


def insert_drift_event(
    db_path: Path,
    check_run_id: int,
    object_type: str,
    object_key: Optional[str],
    path_or_name: str,
    drift_type: str,
    expected_value: Optional[str],
    observed_value: Optional[str],
    severity: str,
    restorable: bool,
    created_at: str,
) -> int:
    """
    Insert a drift event row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO drift_events (
                    check_run_id,
                    object_type,
                    object_key,
                    path_or_name,
                    drift_type,
                    expected_value,
                    observed_value,
                    severity,
                    restorable,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check_run_id,
                    object_type,
                    object_key,
                    path_or_name,
                    drift_type,
                    expected_value,
                    observed_value,
                    severity,
                    int(restorable),
                    created_at,
                ),
            )
            return int(cursor.lastrowid)


def get_drift_events_for_check_run(db_path: Path, check_run_id: int) -> List[Dict[str, Any]]:
    """
    Return all drift events for a given check run.
    """
    with sqlite_connection(db_path) as connection:
        rows = fetch_all(
            connection,
            """
            SELECT *
            FROM drift_events
            WHERE check_run_id = ?
            ORDER BY id ASC
            """,
            (check_run_id,),
        )
        return rows_to_dicts(rows)


def get_latest_check_run(db_path: Path) -> Optional[Dict[str, Any]]:
    """
    Return the most recent check run.
    """
    with sqlite_connection(db_path) as connection:
        row = fetch_one(
            connection,
            """
            SELECT *
            FROM check_runs
            ORDER BY id DESC
            LIMIT 1
            """,
        )
        return row_to_dict(row) if row else None


def create_restore_run(
    db_path: Path,
    started_at: str,
    check_run_id: Optional[int],
    status: Optional[str] = None,
) -> int:
    """
    Create a restore run row and return its id.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO restore_runs (
                    started_at,
                    check_run_id,
                    status
                )
                VALUES (?, ?, ?)
                """,
                (started_at, check_run_id, status),
            )
            return int(cursor.lastrowid)


def finalize_restore_run(
    db_path: Path,
    restore_run_id: int,
    finished_at: str,
    status: str,
    attempted_count: int,
    success_count: int,
    failed_count: int,
) -> None:
    """
    Finalize a restore run row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            connection.execute(
                """
                UPDATE restore_runs
                SET finished_at = ?,
                    status = ?,
                    attempted_count = ?,
                    success_count = ?,
                    failed_count = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    status,
                    attempted_count,
                    success_count,
                    failed_count,
                    restore_run_id,
                ),
            )


def insert_restore_event(
    db_path: Path,
    restore_run_id: int,
    object_type: str,
    object_key: Optional[str],
    action: str,
    source_path: Optional[str],
    target_path: Optional[str],
    result: str,
    details: Optional[str],
    created_at: str,
) -> int:
    """
    Insert a restore event row.
    """
    with sqlite_connection(db_path) as connection:
        with sqlite_transaction(connection):
            cursor = connection.execute(
                """
                INSERT INTO restore_events (
                    restore_run_id,
                    object_type,
                    object_key,
                    action,
                    source_path,
                    target_path,
                    result,
                    details,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    restore_run_id,
                    object_type,
                    object_key,
                    action,
                    source_path,
                    target_path,
                    result,
                    details,
                    created_at,
                ),
            )
            return int(cursor.lastrowid)


def get_watched_files_for_baseline(db_path: Path, baseline_run_id: int) -> List[Dict[str, Any]]:
    """
    Return watched file rows for a baseline run.
    """
    with sqlite_connection(db_path) as connection:
        rows = fetch_all(
            connection,
            """
            SELECT *
            FROM watched_files
            WHERE baseline_run_id = ?
            ORDER BY id ASC
            """,
            (baseline_run_id,),
        )
        return rows_to_dicts(rows)


def get_watched_directories_for_baseline(db_path: Path, baseline_run_id: int) -> List[Dict[str, Any]]:
    """
    Return watched directory rows for a baseline run.
    """
    with sqlite_connection(db_path) as connection:
        rows = fetch_all(
            connection,
            """
            SELECT *
            FROM watched_directories
            WHERE baseline_run_id = ?
            ORDER BY id ASC
            """,
            (baseline_run_id,),
        )
        return rows_to_dicts(rows)


def get_watched_services_for_baseline(db_path: Path, baseline_run_id: int) -> List[Dict[str, Any]]:
    """
    Return watched service rows for a baseline run.
    """
    with sqlite_connection(db_path) as connection:
        rows = fetch_all(
            connection,
            """
            SELECT *
            FROM watched_services
            WHERE baseline_run_id = ?
            ORDER BY id ASC
            """,
            (baseline_run_id,),
        )
        return rows_to_dicts(rows)


def get_watched_packages_for_baseline(db_path: Path, baseline_run_id: int) -> List[Dict[str, Any]]:
    """
    Return watched package rows for a baseline run.
    """
    with sqlite_connection(db_path) as connection:
        rows = fetch_all(
            connection,
            """
            SELECT *
            FROM watched_packages
            WHERE baseline_run_id = ?
            ORDER BY id ASC
            """,
            (baseline_run_id,),
        )
        return rows_to_dicts(rows)


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/db_store.py
#
# Current role:
#   - owns SQLite schema creation
#   - stores baseline, check, drift, and restore data
#   - exposes small explicit DB access helpers
#
# Next required file:
#   sentinel-core/src/sentinel_core/probes/__init__.py
#
# Signature:
#   Sentinel Core v1
#   Database storage layer
# ==========================================================
