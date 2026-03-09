from pathlib import Path

from sentinel_core.db_store import (
    create_baseline_run,
    create_check_run,
    create_restore_run,
    finalize_check_run,
    finalize_restore_run,
    get_active_baseline_run,
    get_drift_events_for_check_run,
    get_latest_check_run,
    get_watched_directories_for_baseline,
    get_watched_files_for_baseline,
    get_watched_packages_for_baseline,
    get_watched_services_for_baseline,
    initialize_database,
    insert_drift_event,
    insert_restore_event,
    insert_watched_directory,
    insert_watched_file,
    insert_watched_package,
    insert_watched_service,
)


def test_initialize_database_creates_db_file(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"

    initialize_database(db_path)

    assert db_path.exists() is True
    assert db_path.is_file() is True


def test_create_and_get_active_baseline_run(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        config_hash="abc123",
        note="first baseline",
        is_active=True,
    )

    row = get_active_baseline_run(db_path)

    assert row is not None
    assert int(row["id"]) == baseline_run_id
    assert row["config_hash"] == "abc123"
    assert int(row["is_active"]) == 1


def test_new_active_baseline_deactivates_old_one(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    old_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        config_hash="old",
        note="old baseline",
        is_active=True,
    )
    new_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T01:00:00Z",
        config_hash="new",
        note="new baseline",
        is_active=True,
    )

    row = get_active_baseline_run(db_path)

    assert old_id != new_id
    assert row is not None
    assert int(row["id"]) == new_id
    assert row["config_hash"] == "new"


def test_insert_and_get_watched_file(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        is_active=True,
    )

    insert_watched_file(
        db_path=db_path,
        baseline_run_id=baseline_run_id,
        path="/opt/sentinel-core/run.py",
        must_exist=True,
        expected_sha256="abc",
        expected_mode="0755",
        expected_uid=0,
        expected_gid=0,
        size_bytes=123,
        mtime_epoch=111,
        baseline_copy_path="/tmp/baselines/run.py",
    )

    rows = get_watched_files_for_baseline(db_path, baseline_run_id)

    assert len(rows) == 1
    assert rows[0]["path"] == "/opt/sentinel-core/run.py"
    assert rows[0]["expected_sha256"] == "abc"


def test_insert_and_get_watched_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        is_active=True,
    )

    insert_watched_directory(
        db_path=db_path,
        baseline_run_id=baseline_run_id,
        path="/opt/sentinel-core",
        must_exist=True,
        expected_mode="0755",
        expected_uid=0,
        expected_gid=0,
    )

    rows = get_watched_directories_for_baseline(db_path, baseline_run_id)

    assert len(rows) == 1
    assert rows[0]["path"] == "/opt/sentinel-core"


def test_insert_and_get_watched_service(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        is_active=True,
    )

    insert_watched_service(
        db_path=db_path,
        baseline_run_id=baseline_run_id,
        unit_name="sentinel-core.service",
        must_exist=True,
        expected_enabled=True,
        expected_active=True,
        unit_file_path="/etc/systemd/system/sentinel-core.service",
        unit_file_sha256="deadbeef",
    )

    rows = get_watched_services_for_baseline(db_path, baseline_run_id)

    assert len(rows) == 1
    assert rows[0]["unit_name"] == "sentinel-core.service"


def test_insert_and_get_watched_package(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        is_active=True,
    )

    insert_watched_package(
        db_path=db_path,
        baseline_run_id=baseline_run_id,
        package_name="python3",
        must_be_installed=True,
        version_string="3.12",
    )

    rows = get_watched_packages_for_baseline(db_path, baseline_run_id)

    assert len(rows) == 1
    assert rows[0]["package_name"] == "python3"
    assert rows[0]["version_string"] == "3.12"


def test_create_finalize_and_get_latest_check_run(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        is_active=True,
    )

    check_run_id = create_check_run(
        db_path=db_path,
        started_at="2026-03-10T00:10:00Z",
        baseline_run_id=baseline_run_id,
        status="running",
    )

    finalize_check_run(
        db_path=db_path,
        check_run_id=check_run_id,
        finished_at="2026-03-10T00:11:00Z",
        status="clean",
        drift_count=0,
        severe_count=0,
    )

    row = get_latest_check_run(db_path)

    assert row is not None
    assert int(row["id"]) == check_run_id
    assert row["status"] == "clean"
    assert int(row["drift_count"]) == 0


def test_insert_and_get_drift_events(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    baseline_run_id = create_baseline_run(
        db_path=db_path,
        created_at="2026-03-10T00:00:00Z",
        is_active=True,
    )
    check_run_id = create_check_run(
        db_path=db_path,
        started_at="2026-03-10T00:10:00Z",
        baseline_run_id=baseline_run_id,
        status="running",
    )

    insert_drift_event(
        db_path=db_path,
        check_run_id=check_run_id,
        object_type="file",
        object_key="/opt/sentinel-core/run.py",
        path_or_name="/opt/sentinel-core/run.py",
        drift_type="missing",
        expected_value="True",
        observed_value="False",
        severity="high",
        restorable=True,
        created_at="2026-03-10T00:10:30Z",
    )

    events = get_drift_events_for_check_run(db_path, check_run_id)

    assert len(events) == 1
    assert events[0]["object_type"] == "file"
    assert events[0]["drift_type"] == "missing"
    assert int(events[0]["restorable"]) == 1


def test_create_and_finalize_restore_run_and_event(tmp_path: Path) -> None:
    db_path = tmp_path / "sentinel.db"
    initialize_database(db_path)

    restore_run_id = create_restore_run(
        db_path=db_path,
        started_at="2026-03-10T00:20:00Z",
        check_run_id=None,
        status="running",
    )

    insert_restore_event(
        db_path=db_path,
        restore_run_id=restore_run_id,
        object_type="file",
        object_key="/opt/sentinel-core/run.py",
        action="restore_file_from_baseline",
        source_path="/tmp/baseline/run.py",
        target_path="/opt/sentinel-core/run.py",
        result="success",
        details="restored",
        created_at="2026-03-10T00:21:00Z",
    )

    finalize_restore_run(
        db_path=db_path,
        restore_run_id=restore_run_id,
        finished_at="2026-03-10T00:22:00Z",
        status="success",
        attempted_count=1,
        success_count=1,
        failed_count=0,
    )

    # No direct getter exists yet for restore rows/events.
    # This test passes by verifying the calls complete without error.
    assert restore_run_id > 0
