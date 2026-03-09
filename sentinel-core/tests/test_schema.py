from sentinel_core.schema import (
    SchemaValidationError,
    validate_all_configs,
    validate_restore_config,
    validate_thresholds_config,
    validate_watchlist_config,
)


def test_validate_watchlist_config_minimal() -> None:
    result = validate_watchlist_config(
        {
            "files": [],
            "directories": [],
            "services": [],
            "packages": [],
        }
    )

    assert result["files"] == []
    assert result["directories"] == []
    assert result["services"] == []
    assert result["packages"] == []


def test_validate_watchlist_config_with_entries() -> None:
    result = validate_watchlist_config(
        {
            "files": [
                {
                    "path": "/opt/sentinel-core/run.py",
                    "must_exist": True,
                    "restore_allowed": True,
                }
            ],
            "directories": [
                {
                    "path": "/opt/sentinel-core",
                    "must_exist": True,
                }
            ],
            "services": [
                {
                    "unit_name": "sentinel-core.service",
                    "must_exist": True,
                    "expected_enabled": True,
                    "expected_active": True,
                    "restore_allowed": False,
                }
            ],
            "packages": [
                {
                    "package_name": "python3",
                    "must_be_installed": True,
                }
            ],
        }
    )

    assert result["files"][0]["path"] == "/opt/sentinel-core/run.py"
    assert result["files"][0]["restore_allowed"] is True
    assert result["directories"][0]["path"] == "/opt/sentinel-core"
    assert result["services"][0]["unit_name"] == "sentinel-core.service"
    assert result["packages"][0]["package_name"] == "python3"


def test_validate_watchlist_config_rejects_bad_file_path() -> None:
    try:
        validate_watchlist_config(
            {
                "files": [
                    {
                        "path": "",
                        "must_exist": True,
                        "restore_allowed": False,
                    }
                ]
            }
        )
        assert False, "expected SchemaValidationError"
    except SchemaValidationError:
        assert True


def test_validate_restore_config_defaults() -> None:
    result = validate_restore_config({})

    assert result["enabled"] is False
    assert result["file_restore_backend"] == "rsync"
    assert result["service_actions_enabled"] is False
    assert result["package_actions_enabled"] is False
    assert result["require_explicit_apply"] is True


def test_validate_restore_config_rejects_bad_backend() -> None:
    try:
        validate_restore_config(
            {
                "file_restore_backend": "tar",
            }
        )
        assert False, "expected SchemaValidationError"
    except SchemaValidationError:
        assert True


def test_validate_thresholds_config_defaults() -> None:
    result = validate_thresholds_config({})

    assert result["high_drift_count_alert"] == 1
    assert result["medium_drift_count_alert"] == 3
    assert result["treat_missing_protected_file_as_high"] is True


def test_validate_thresholds_config_rejects_negative_values() -> None:
    try:
        validate_thresholds_config(
            {
                "high_drift_count_alert": -1,
            }
        )
        assert False, "expected SchemaValidationError"
    except SchemaValidationError:
        assert True


def test_validate_all_configs_bundle() -> None:
    result = validate_all_configs(
        watchlist_raw={
            "files": [],
            "directories": [],
            "services": [],
            "packages": [],
        },
        restore_raw={
            "enabled": False,
            "file_restore_backend": "rsync",
        },
        thresholds_raw={
            "high_drift_count_alert": 1,
            "medium_drift_count_alert": 3,
        },
    )

    assert "watchlist" in result
    assert "restore" in result
    assert "thresholds" in result
    assert result["restore"]["file_restore_backend"] == "rsync"
