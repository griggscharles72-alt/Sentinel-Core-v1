#!/usr/bin/env python3
"""
README
======

Filename:
    paths.py

Project:
    Sentinel Core v1

Purpose:
    Canonical repo-relative path handling for Sentinel Core.

This module is responsible for:

    - Resolving the repo root
    - Defining all important config/data/docs/script paths
    - Creating required runtime directories when requested
    - Keeping path handling location-independent

Design notes:

    - All paths are derived from this file location
    - No hardcoded absolute machine paths
    - Runtime directory creation is explicit and safe
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class SentinelPaths:
    """
    Canonical path container for Sentinel Core.
    """

    repo_root: Path
    bin_dir: Path
    config_dir: Path
    data_dir: Path
    db_dir: Path
    baselines_dir: Path
    baseline_files_dir: Path
    baseline_manifests_dir: Path
    snapshots_dir: Path
    reports_dir: Path
    logs_dir: Path
    docs_dir: Path
    scripts_dir: Path
    src_dir: Path
    package_dir: Path
    helpers_dir: Path
    probes_dir: Path
    tests_dir: Path
    db_path: Path
    watchlist_config: Path
    restore_config: Path
    thresholds_config: Path

    def runtime_directories(self) -> List[Path]:
        """
        Return runtime directories that should exist for operation.
        """
        return [
            self.data_dir,
            self.db_dir,
            self.baselines_dir,
            self.baseline_files_dir,
            self.baseline_manifests_dir,
            self.snapshots_dir,
            self.reports_dir,
            self.logs_dir,
        ]

    def config_files(self) -> List[Path]:
        """
        Return required config file paths.
        """
        return [
            self.watchlist_config,
            self.restore_config,
            self.thresholds_config,
        ]


def get_repo_root() -> Path:
    """
    Resolve repo root from this file.

    Expected path:
        sentinel-core/src/sentinel_core/helpers/paths.py

    Repo root:
        parents[3]
    """
    return Path(__file__).resolve().parents[3]


def build_paths() -> SentinelPaths:
    """
    Build and return the canonical Sentinel path map.
    """
    repo_root = get_repo_root()

    bin_dir = repo_root / "bin"
    config_dir = repo_root / "config"
    data_dir = repo_root / "data"
    db_dir = data_dir / "db"
    baselines_dir = data_dir / "baselines"
    baseline_files_dir = baselines_dir / "files"
    baseline_manifests_dir = baselines_dir / "manifests"
    snapshots_dir = data_dir / "snapshots"
    reports_dir = data_dir / "reports"
    logs_dir = data_dir / "logs"
    docs_dir = repo_root / "docs"
    scripts_dir = repo_root / "scripts"
    src_dir = repo_root / "src"
    package_dir = src_dir / "sentinel_core"
    helpers_dir = package_dir / "helpers"
    probes_dir = package_dir / "probes"
    tests_dir = repo_root / "tests"

    return SentinelPaths(
        repo_root=repo_root,
        bin_dir=bin_dir,
        config_dir=config_dir,
        data_dir=data_dir,
        db_dir=db_dir,
        baselines_dir=baselines_dir,
        baseline_files_dir=baseline_files_dir,
        baseline_manifests_dir=baseline_manifests_dir,
        snapshots_dir=snapshots_dir,
        reports_dir=reports_dir,
        logs_dir=logs_dir,
        docs_dir=docs_dir,
        scripts_dir=scripts_dir,
        src_dir=src_dir,
        package_dir=package_dir,
        helpers_dir=helpers_dir,
        probes_dir=probes_dir,
        tests_dir=tests_dir,
        db_path=db_dir / "sentinel.db",
        watchlist_config=config_dir / "watchlist.json",
        restore_config=config_dir / "restore.json",
        thresholds_config=config_dir / "thresholds.json",
    )


def ensure_directories(paths_to_create: Iterable[Path]) -> None:
    """
    Create directories if missing.
    """
    for directory in paths_to_create:
        directory.mkdir(parents=True, exist_ok=True)


def ensure_runtime_directories(paths: SentinelPaths) -> None:
    """
    Create all required runtime directories.
    """
    ensure_directories(paths.runtime_directories())


# ==========================================================
# INSTRUCTIONS
# ==========================================================
# Save as:
#   sentinel-core/src/sentinel_core/helpers/paths.py
#
# Current role:
#   - defines canonical repo-relative paths
#   - provides runtime directory creation helpers
#
# Next required file:
#   sentinel-core/src/sentinel_core/helpers/jsonio.py
#
# Signature:
#   Sentinel Core v1
#   Path resolution layer
# ==========================================================
