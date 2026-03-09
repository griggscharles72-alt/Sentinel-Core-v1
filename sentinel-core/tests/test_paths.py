from sentinel_core.helpers.paths import build_paths


def test_build_paths_repo_shape() -> None:
    paths = build_paths()

    assert paths.repo_root.name == "sentinel-core"
    assert paths.bin_dir.name == "bin"
    assert paths.config_dir.name == "config"
    assert paths.data_dir.name == "data"
    assert paths.package_dir.name == "sentinel_core"
    assert paths.helpers_dir.name == "helpers"
    assert paths.probes_dir.name == "probes"
    assert paths.db_path.name == "sentinel.db"


def test_runtime_directories_contains_expected_entries() -> None:
    paths = build_paths()
    runtime_dirs = paths.runtime_directories()

    names = {path.name for path in runtime_dirs}
    assert "data" in names
    assert "db" in names
    assert "baselines" in names
    assert "snapshots" in names
    assert "reports" in names
    assert "logs" in names


def test_config_files_contains_expected_entries() -> None:
    paths = build_paths()
    config_files = paths.config_files()

    file_names = {path.name for path in config_files}
    assert "watchlist.json" in file_names
    assert "restore.json" in file_names
    assert "thresholds.json" in file_names
