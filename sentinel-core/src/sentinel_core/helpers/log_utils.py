#!/usr/bin/env python3
"""
README
======

Filename:
    log_utils.py

Project:
    Sentinel Core v1

Purpose:
    Logging helpers for Sentinel Core.

This module is responsible for:

    - creating a consistent logger
    - writing logs to console and file
    - keeping log formatting deterministic
    - creating log directories safely when needed

Design notes:

    - standard library only
    - no color formatting
    - no hidden global mutation outside logger setup
    - safe to call multiple times without duplicating handlers
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


DEFAULT_LOGGER_NAME = "sentinel_core"


def _build_formatter() -> logging.Formatter:
    """
    Return the canonical log formatter for Sentinel Core.
    """
    return logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _has_handler_type(logger: logging.Logger, handler_type: type) -> bool:
    """
    Return True if the logger already has a handler of the given type.
    """
    return any(isinstance(handler, handler_type) for handler in logger.handlers)


def get_logger(
    name: str = DEFAULT_LOGGER_NAME,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Build or return a configured logger.

    Behavior:
        - adds a console handler once
        - adds a file handler once if log_file is provided
        - prevents duplicate handlers on repeated calls
        - uses deterministic formatting
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = _build_formatter()

    if not _has_handler_type(logger, logging.StreamHandler):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        existing_file_handler = False
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler_path = getattr(handler, "baseFilename", None)
                if handler_path and Path(handler_path) == log_file:
                    existing_file_handler = True
                    break

        if not existing_file_handler:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def reset_logger(name: str = DEFAULT_LOGGER_NAME) -> None:
    """
    Remove and close all handlers for a logger.

    Useful for tests or controlled reconfiguration.
    """
    logger = logging.getLogger(name)

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/log_utils.py
#
# Current role:
#   - provides consistent console/file logging
#   - avoids duplicate handlers
#   - keeps formatting stable
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/time_utils.py
#
# Signature:
#   Sentinel Core v1
#   Logging helper layer
# ==========================================================
