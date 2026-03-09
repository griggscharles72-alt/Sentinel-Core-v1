from sentinel_core.probes.probe_services import probe_service, probe_services


def test_probe_service_returns_expected_shape() -> None:
    result = probe_service(
        "definitely-not-a-real-service-12345.service",
        must_exist=False,
        expected_enabled=False,
        expected_active=False,
    )

    assert result["object_type"] == "service"
    assert result["unit_name"] == "definitely-not-a-real-service-12345.service"
    assert "exists" in result
    assert "status" in result
    assert "systemctl_available" in result


def test_probe_service_missing_optional_service() -> None:
    result = probe_service(
        "definitely-not-a-real-service-12345.service",
        must_exist=False,
        expected_enabled=False,
        expected_active=False,
    )

    if result["systemctl_available"]:
        assert result["status"] == "absent_allowed"
    else:
        assert result["status"] == "systemctl_unavailable"


def test_probe_services_multiple_entries() -> None:
    results = probe_services(
        [
            {
                "unit_name": "definitely-not-a-real-service-12345.service",
                "must_exist": False,
                "expected_enabled": False,
                "expected_active": False,
                "restore_allowed": False,
            },
            {
                "unit_name": "definitely-not-a-real-service-67890.service",
                "must_exist": False,
                "expected_enabled": False,
                "expected_active": False,
                "restore_allowed": True,
            },
        ]
    )

    assert len(results) == 2
    assert results[0]["object_type"] == "service"
    assert results[0]["unit_name"] == "definitely-not-a-real-service-12345.service"
    assert results[0]["restore_allowed"] is False
    assert results[1]["object_type"] == "service"
    assert results[1]["unit_name"] == "definitely-not-a-real-service-67890.service"
    assert results[1]["restore_allowed"] is True
