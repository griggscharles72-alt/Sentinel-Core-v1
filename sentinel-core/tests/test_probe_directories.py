from pathlib import Path

from sentinel_core.probes.probe_directories import probe_directory, probe_directories


def test_probe_directory_existing_directory(tmp_path: Path) -> None:
    result = probe_directory(str(tmp_path), must_exist=True)

    assert result["object_type"] == "directory"
    assert result["exists"] is True
    assert result["is_dir"] is True
    assert result["status"] == "ok"
    assert result["must_exist"] is True


def test_probe_directory_missing_required_directory(tmp_path: Path) -> None:
    target = tmp_path / "missing-dir"

    result = probe_directory(str(target), must_exist=True)

    assert result["exists"] is False
    assert result["status"] == "missing"
    assert result["must_exist"] is True


def test_probe_directory_missing_optional_directory(tmp_path: Path) -> None:
    target = tmp_path / "optional-dir"

    result = probe_directory(str(target), must_exist=False)

    assert result["exists"] is False
    assert result["status"] == "absent_allowed"
    assert result["must_exist"] is False


def test_probe_directory_path_is_file(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("hello\n", encoding="utf-8")

    result = probe_directory(str(target), must_exist=True)

    assert result["exists"] is True
    assert result["is_dir"] is False
    assert result["status"] == "not_a_directory"


def test_probe_directories_multiple_entries(tmp_path: Path) -> None:
    existing = tmp_path / "present-dir"
    existing.mkdir()

    missing = tmp_path / "missing-dir"

    results = probe_directories(
        [
            {
                "path": str(existing),
                "must_exist": True,
            },
            {
                "path": str(missing),
                "must_exist": True,
            },
        ]
    )

    assert len(results) == 2
    assert results[0]["status"] == "ok"
    assert results[1]["status"] == "missing"
