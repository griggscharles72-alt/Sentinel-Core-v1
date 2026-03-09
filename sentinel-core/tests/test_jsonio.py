import json
from pathlib import Path

from sentinel_core.helpers.jsonio import (
    atomic_write_json_file,
    read_json_file,
    write_json_file,
)


def test_write_and_read_json_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.json"
    payload = {"b": 2, "a": 1}

    write_json_file(target, payload)
    loaded = read_json_file(target)

    assert loaded == payload


def test_atomic_write_json_file(tmp_path: Path) -> None:
    target = tmp_path / "atomic.json"
    payload = {"name": "sentinel", "enabled": True}

    atomic_write_json_file(target, payload)
    loaded = read_json_file(target)

    assert loaded == payload


def test_read_json_file_rejects_non_object(tmp_path: Path) -> None:
    target = tmp_path / "bad.json"
    target.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    try:
        read_json_file(target)
        assert False, "expected ValueError"
    except ValueError:
        assert True
