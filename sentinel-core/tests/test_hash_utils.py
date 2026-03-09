from pathlib import Path

from sentinel_core.helpers.hash_utils import (
    collect_directory_state,
    collect_file_state,
    file_mode_octal,
    safe_sha256_file,
    sha256_file,
)


def test_sha256_file_returns_hash(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("sentinel-core\n", encoding="utf-8")

    digest = sha256_file(target)

    assert isinstance(digest, str)
    assert len(digest) == 64


def test_safe_sha256_file_returns_none_for_missing_file(tmp_path: Path) -> None:
    target = tmp_path / "missing.txt"

    assert safe_sha256_file(target) is None


def test_collect_file_state_for_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("abc\n", encoding="utf-8")

    state = collect_file_state(target)

    assert state["exists"] is True
    assert state["is_file"] is True
    assert state["sha256"] is not None
    assert state["size_bytes"] == len("abc\n")


def test_collect_directory_state_for_existing_directory(tmp_path: Path) -> None:
    state = collect_directory_state(tmp_path)

    assert state["exists"] is True
    assert state["is_dir"] is True
    assert state["mode"] is not None


def test_file_mode_octal_returns_string(tmp_path: Path) -> None:
    target = tmp_path / "mode.txt"
    target.write_text("mode\n", encoding="utf-8")

    mode = file_mode_octal(target)

    assert isinstance(mode, str)
    assert len(mode) == 4
