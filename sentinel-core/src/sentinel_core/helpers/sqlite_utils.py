#!/usr/bin/env python3
"""
README
======

Filename:
    sqlite_utils.py

Project:
    Sentinel Core v1

Purpose:
    SQLite helper utilities for Sentinel Core.

This module is responsible for:

    - opening SQLite connections safely
    - enabling deterministic connection settings
    - providing transaction helpers
    - returning rows in dictionary-friendly form
    - creating parent directories for DB paths when needed

Design notes:

    - standard library only
    - keep connection behavior explicit
    - use Row factory for readable column access
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable, Optional, Sequence


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """
    Open a SQLite connection with Sentinel defaults.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    return connection


@contextmanager
def sqlite_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """
    Context-managed SQLite connection.
    """
    connection = connect_sqlite(db_path)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def sqlite_transaction(connection: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """
    Context-managed transaction wrapper.

    Commits on success and rolls back on failure.
    """
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def execute_script(connection: sqlite3.Connection, sql_script: str) -> None:
    """
    Execute a SQL script and commit immediately.
    """
    connection.executescript(sql_script)
    connection.commit()


def execute_many(
    connection: sqlite3.Connection,
    sql: str,
    rows: Iterable[Sequence[object]],
) -> None:
    """
    Execute a parameterized executemany call and commit immediately.
    """
    connection.executemany(sql, rows)
    connection.commit()


def fetch_one(
    connection: sqlite3.Connection,
    sql: str,
    params: Optional[Sequence[object]] = None,
) -> Optional[sqlite3.Row]:
    """
    Fetch a single row.
    """
    cursor = connection.execute(sql, tuple(params or ()))
    return cursor.fetchone()


def fetch_all(
    connection: sqlite3.Connection,
    sql: str,
    params: Optional[Sequence[object]] = None,
) -> list[sqlite3.Row]:
    """
    Fetch all rows.
    """
    cursor = connection.execute(sql, tuple(params or ()))
    return cursor.fetchall()


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/sqlite_utils.py
#
# Current role:
#   - opens SQLite connections with Sentinel defaults
#   - provides transaction and query helpers
#
# Next required file:
#   sentinel-core/src/sentinel_core/db_store.py
#
# Signature:
#   Sentinel Core v1
#   SQLite helper layer
# ==========================================================
