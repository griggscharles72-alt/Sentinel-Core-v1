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

    - parsing CLI arguments
    - routing commands to the correct module handlers
    - returning stable exit codes
    - keeping the command ladder deterministic

Supported commands:

    - doctor
    - baseline
    - check
    - report
    - restore-plan
    - restore-apply
    - all

Design notes:

    - explicit command map only
    - no hidden behavior
    - command chaining for 'all' is fixed:
        doctor -> check -> report
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Dict

from sentinel_core import __version__
from sentinel_core.baseline_build import run_baseline
from sentinel_core.doctor_env import run_doctor
from sentinel_core.drift_check import (
    EXIT_DRIFT_DETECTED,
    EXIT_NO_BASELINE,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_SEVERE_DRIFT,
    run_check,
)
from sentinel_core.report_summary import run_report
from sentinel_core.restore_apply import run_restore_apply
from sentinel_core.restore_decide import run_restore_plan


EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3
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
    return run_doctor()


def command_baseline() -> int:
    """
    Create or refresh the active baseline.
    """
    return run_baseline()


def command_check() -> int:
    """
    Run drift detection against the active baseline.
    """
    return run_check()


def command_report() -> int:
    """
    Generate reports from the latest check run.
    """
    return run_report()


def command_restore_plan() -> int:
    """
    Generate a restore plan from the latest drift state.
    """
    return run_restore_plan()


def command_restore_apply() -> int:
    """
    Apply the latest restore plan.
    """
    return run_restore_apply()


def command_all() -> int:
    """
    Run the fixed chain:

        doctor -> check -> report

    Behavior:
        - if doctor fails, stop immediately
        - if check returns drift, still run report
        - if report fails, return report failure
        - final return preserves drift signal when report succeeds
    """
    doctor_result = command_doctor()
    if doctor_result != EXIT_OK:
        return doctor_result

    check_result = command_check()
    if check_result not in (EXIT_OK, EXIT_DRIFT_DETECTED, EXIT_SEVERE_DRIFT):
        return check_result

    report_result = command_report()
    if report_result != EXIT_OK:
        return report_result

    return check_result


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
# Current role:
#   - routes all Sentinel Core commands
#   - wires doctor, baseline, check, report, restore-plan, restore-apply
#   - supports the fixed 'all' execution chain
#
# Next required file:
#   sentinel-core/scripts/bootstrap.sh
#
# Signature:
#   Sentinel Core v1
#   Main command router
# ==========================================================
