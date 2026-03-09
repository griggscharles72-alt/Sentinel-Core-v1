#!/usr/bin/env python3
"""
README
======

Filename:
    main_wrapper.py

Project:
    Sentinel Core v1

Purpose:
    Top-level command router for Sentinel Core.

This module is responsible for:

    - Parsing CLI arguments
    - Routing commands to the correct module handlers
    - Returning stable exit codes
    - Keeping the command ladder deterministic

Supported commands:

    - doctor
    - baseline
    - check
    - report
    - restore-plan
    - restore-apply
    - all

Notes:
    - Early versions may use placeholder handlers for commands
      that are not implemented yet.
    - The 'doctor' command is expected to be the first fully
      wired operation.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Dict

from sentinel_core import __version__
from sentinel_core import doctor_env


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3
EXIT_DRIFT_DETECTED = 10
EXIT_SEVERE_DRIFT = 11
EXIT_NO_BASELINE = 12
EXIT_RESTORE_PARTIAL = 20
EXIT_RESTORE_FAILED = 21


def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level CLI parser.
    """
    parser = argparse.ArgumentParser(
        prog="sentinel-core",
        description="Sentinel Core v1 - deterministic drift detection and restore decision layer.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "doctor",
        help="Validate runtime environment and configuration readiness.",
    )

    subparsers.add_parser(
        "baseline",
        help="Create or refresh the known-good baseline.",
    )

    subparsers.add_parser(
        "check",
        help="Check current state against the active baseline.",
    )

    subparsers.add_parser(
        "report",
        help="Generate a report from the latest check results.",
    )

    subparsers.add_parser(
        "restore-plan",
        help="Generate a restore plan without making changes.",
    )

    subparsers.add_parser(
        "restore-apply",
        help="Apply an approved restore plan.",
    )

    subparsers.add_parser(
        "all",
        help="Run doctor -> check -> report.",
    )

    return parser


def command_doctor() -> int:
    """
    Run environment validation.
    """
    return doctor_env.run_doctor()


def command_baseline() -> int:
    """
    Placeholder baseline command until implementation is added.
    """
    print("INFO: baseline command is not implemented yet.")
    return EXIT_OK


def command_check() -> int:
    """
    Placeholder check command until implementation is added.
    """
    print("INFO: check command is not implemented yet.")
    return EXIT_OK


def command_report() -> int:
    """
    Placeholder report command until implementation is added.
    """
    print("INFO: report command is not implemented yet.")
    return EXIT_OK


def command_restore_plan() -> int:
    """
    Placeholder restore-plan command until implementation is added.
    """
    print("INFO: restore-plan command is not implemented yet.")
    return EXIT_OK


def command_restore_apply() -> int:
    """
    Placeholder restore-apply command until implementation is added.
    """
    print("INFO: restore-apply command is not implemented yet.")
    return EXIT_OK


def command_all() -> int:
    """
    Run the default chained workflow.

    Current behavior:
        doctor -> check -> report

    In early versions, check and report may still be placeholders.
    """
    result = command_doctor()
    if result != EXIT_OK:
        return result

    result = command_check()
    if result not in (EXIT_OK, EXIT_DRIFT_DETECTED, EXIT_SEVERE_DRIFT):
        return result

    report_result = command_report()
    if report_result != EXIT_OK:
        return report_result

    return result


def get_command_map() -> Dict[str, Callable[[], int]]:
    """
    Return the command routing table.
    """
    return {
        "doctor": command_doctor,
        "baseline": command_baseline,
        "check": command_check,
        "report": command_report,
        "restore-plan": command_restore_plan,
        "restore-apply": command_restore_apply,
        "all": command_all,
    }


def main() -> int:
    """
    Parse arguments and dispatch the selected command.
    """
    parser = build_parser()
    args = parser.parse_args()

    command_map = get_command_map()
    handler = command_map.get(args.command)

    if handler is None:
        print(f"ERROR: unsupported command: {args.command}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    try:
        return handler()
    except KeyboardInterrupt:
        print("ERROR: interrupted by user.", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: unhandled exception: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


if __name__ == "__main__":
    raise SystemExit(main())


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/main_wrapper.py
#
# This file is intended to work with:
#   sentinel-core/bin/sentinel-core
#
# Current status:
#   - doctor is the first real wired command
#   - all other commands are safe placeholders for now
#
# Next required file:
#   sentinel-core/src/sentinel_core/doctor_env.py
#
# Signature:
#   Sentinel Core v1
#   Main command router
# ==========================================================
