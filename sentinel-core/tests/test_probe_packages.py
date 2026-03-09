from sentinel_core.probes.probe_packages import probe_package, probe_packages


def test_probe_package_returns_expected_shape() -> None:
    result = probe_package("python3", must_be_installed=True)

    assert result["object_type"] == "package"
    assert result["package_name"] == "python3"
    assert "installed" in result
    assert "status" in result
    assert "dpkg_query_available" in result


def test_probe_package_missing_optional_package() -> None:
    result = probe_package(
        "definitely-not-a-real-package-name-12345",
        must_be_installed=False,
    )

    assert result["package_name"] == "definitely-not-a-real-package-name-12345"
    assert result["must_be_installed"] is False

    if result["dpkg_query_available"]:
        assert result["status"] == "absent_allowed"
    else:
        assert result["status"] == "dpkg_query_unavailable"


def test_probe_packages_multiple_entries() -> None:
    results = probe_packages(
        [
            {
                "package_name": "python3",
                "must_be_installed": True,
            },
            {
                "package_name": "definitely-not-a-real-package-name-12345",
                "must_be_installed": False,
            },
        ]
    )

    assert len(results) == 2
    assert results[0]["object_type"] == "package"
    assert results[0]["package_name"] == "python3"
    assert results[1]["object_type"] == "package"
    assert results[1]["package_name"] == "definitely-not-a-real-package-name-12345"
