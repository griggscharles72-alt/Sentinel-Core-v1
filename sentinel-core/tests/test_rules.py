from sentinel_core.rules import (
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    classify_directory_drift,
    classify_file_drift,
    classify_package_drift,
    classify_service_drift,
    count_severe_events,
)


def test_classify_file_drift_missing_file() -> None:
    expected = {
        "path": "/opt/sentinel-core/run.py",
        "must_exist": True,
        "expected_sha256": "abc",
        "expected_mode": "0755",
        "expected_uid": 0,
        "expected_gid": 0,
    }
    observed = {
        "exists": False,
        "is_file": False,
        "restore_allowed": True,
    }

    events = classify_file_drift(expected, observed)

    assert len(events) == 1
    assert events[0]["drift_type"] == "missing"
    assert events[0]["severity"] == SEVERITY_HIGH
    assert events[0]["restorable"] is True


def test_classify_file_drift_hash_and_mode_change() -> None:
    expected = {
        "path": "/opt/sentinel-core/run.py",
        "must_exist": True,
        "expected_sha256": "abc",
        "expected_mode": "0755",
        "expected_uid": 0,
        "expected_gid": 0,
    }
    observed = {
        "exists": True,
        "is_file": True,
        "sha256": "xyz",
        "mode": "0644",
        "uid": 0,
        "gid": 0,
        "restore_allowed": False,
    }

    events = classify_file_drift(expected, observed)

    drift_types = {event["drift_type"] for event in events}
    assert "hash_changed" in drift_types
    assert "mode_changed" in drift_types


def test_classify_directory_drift_missing() -> None:
    expected = {
        "path": "/opt/sentinel-core",
        "must_exist": True,
        "expected_mode": "0755",
        "expected_uid": 0,
        "expected_gid": 0,
    }
    observed = {
        "exists": False,
        "is_dir": False,
    }

    events = classify_directory_drift(expected, observed)

    assert len(events) == 1
    assert events[0]["drift_type"] == "directory_missing"
    assert events[0]["severity"] == SEVERITY_HIGH


def test_classify_service_drift_inactive() -> None:
    expected = {
        "unit_name": "sentinel-core.service",
        "must_exist": True,
        "expected_enabled": True,
        "expected_active": True,
    }
    observed = {
        "status": "inactive",
        "exists": True,
        "enabled": True,
        "active": False,
        "restore_allowed": True,
    }

    events = classify_service_drift(expected, observed)

    assert len(events) == 1
    assert events[0]["drift_type"] == "service_inactive"
    assert events[0]["severity"] == SEVERITY_HIGH
    assert events[0]["restorable"] is True


def test_classify_package_drift_missing() -> None:
    expected = {
        "package_name": "sqlite3",
        "must_be_installed": True,
    }
    observed = {
        "status": "missing",
        "installed": False,
    }

    events = classify_package_drift(expected, observed)

    assert len(events) == 1
    assert events[0]["drift_type"] == "package_missing"
    assert events[0]["restorable"] is False


def test_count_severe_events() -> None:
    events = [
        {"severity": SEVERITY_HIGH},
        {"severity": SEVERITY_MEDIUM},
        {"severity": SEVERITY_HIGH},
    ]

    assert count_severe_events(events) == 2
