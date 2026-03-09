from pathlib import Path

from sentinel_core.probes.probe_files import probe_file, probe_files


def test_probe_file_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "example.txt"
    target.write_text("hello\n", encoding="utf-8")

    result = probe_file(str(target), must_exist=True)

    assert result["object_type"] == "file"
    assert result["exists"] is True
    assert result["is_file"] is True
    assert result["status"] == "ok"
    assert result["must_exist"] is True
    assert result["sha256"] is not None


def test_probe_file_missing_required_file(tmp_path: Path) -> None:
    target = tmp_path / "missing.txt"

    result = probe_file(str(target), must_exist=True)

    assert result["exists"] is False
    assert result["status"] == "missing"
    assert result["must_exist"] is True


def test_probe_file_missing_optional_file(tmp_path: Path) -> None:
    target = tmp_path / "optional.txt"

    result = probe_file(str(target), must_exist=False)

    assert result["exists"] is False
    assert result["status"] == "absent_allowed"
    assert result["must_exist"] is False


def test_probe_file_path_is_directory(tmp_path: Path) -> None:
    result = probe_file(str(tmp_path), must_exist=True)

    assert result["exists"] is True
    assert result["is_file"] is False
    assert result["status"] == "not_a_file"


def test_probe_files_multiple_entries(tmp_path: Path) -> None:
    existing = tmp_path / "present.txt"
    existing.write_text("present\n", encoding="utf-8")

    missing = tmp_path / "missing.txt"

    results = probe_files(
        [
            {
                "path": str(existing),
                "must_exist": True,
                "restore_allowed": True,
            },
            {
                "path": str(missing),
                "must_exist": True,
                "restore_allowed": False,
            },
        ]
    )

    assert len(results) == 2
    assert results[0]["status"] == "ok"
    assert results[0]["restore_allowed"] is True
    assert results[1]["status"] == "missing"
    assert results[1]["restore_allowed"] is False
