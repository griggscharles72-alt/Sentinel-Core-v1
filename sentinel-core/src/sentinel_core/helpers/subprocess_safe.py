#!/usr/bin/env python3
"""
README
======

Filename:
    subprocess_safe.py

Project:
    Sentinel Core v1

Purpose:
    Controlled subprocess execution helpers for Sentinel Core.

This module is responsible for:

    - running external commands safely
    - capturing stdout and stderr deterministically
    - avoiding shell=True
    - returning structured command results
    - providing optional checked execution behavior

Design notes:

    - standard library only
    - list-based command execution only
    - no shell string execution
    - predictable timeout handling
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class CommandResult:
    """
    Structured command result for subprocess calls.
    """

    args: List[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class CommandExecutionError(RuntimeError):
    """
    Raised when a checked command execution fails.
    """


def _normalize_args(args: Sequence[str]) -> List[str]:
    """
    Validate and normalize a command argument sequence.
    """
    if not args:
        raise ValueError("command args must not be empty")

    normalized = [str(part) for part in args]

    for index, part in enumerate(normalized):
        if not part:
            raise ValueError(f"command arg at index {index} must not be empty")

    return normalized


def run_command(
    args: Sequence[str],
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
) -> CommandResult:
    """
    Run a subprocess command and capture stdout/stderr.

    Returns:
        CommandResult
    """
    command = _normalize_args(args)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
        return CommandResult(
            args=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(
            args=command,
            returncode=124,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )


def run_checked_command(
    args: Sequence[str],
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
) -> CommandResult:
    """
    Run a subprocess command and raise if it fails.
    """
    result = run_command(args=args, timeout=timeout, cwd=cwd)

    if not result.ok:
        raise CommandExecutionError(
            "command failed: "
            f"args={result.args!r} "
            f"returncode={result.returncode} "
            f"timed_out={result.timed_out} "
            f"stderr={result.stderr.strip()!r}"
        )

    return result


def command_exists(binary_name: str) -> bool:
    """
    Return True if a binary is available in PATH.

    Uses 'command -v' semantics via the platform PATH search in subprocess
    by relying on direct execution attempt of 'which' alternatives being
    unnecessary here. This helper is kept lightweight and conservative.
    """
    if not binary_name or not str(binary_name).strip():
        return False

    from shutil import which

    return which(str(binary_name).strip()) is not None


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/subprocess_safe.py
#
# Current role:
#   - safely runs external commands
#   - captures stdout/stderr in a structured result
#   - provides checked and unchecked execution helpers
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/hash_utils.py
#
# Signature:
#   Sentinel Core v1
#   Subprocess helper layer
# ==========================================================
