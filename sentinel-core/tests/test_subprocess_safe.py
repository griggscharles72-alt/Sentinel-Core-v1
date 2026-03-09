from sentinel_core.helpers.subprocess_safe import (
    CommandExecutionError,
    command_exists,
    run_checked_command,
    run_command,
)


def test_run_command_success() -> None:
    result = run_command(["python3", "-c", "print('ok')"], timeout=10)

    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
    assert result.timed_out is False


def test_run_command_failure() -> None:
    result = run_command(["python3", "-c", "import sys; sys.exit(5)"], timeout=10)

    assert result.ok is False
    assert result.returncode == 5
    assert result.timed_out is False


def test_run_command_timeout() -> None:
    result = run_command(
        ["python3", "-c", "import time; time.sleep(2)"],
        timeout=0.1,
    )

    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode == 124


def test_run_checked_command_success() -> None:
    result = run_checked_command(["python3", "-c", "print('checked')"], timeout=10)

    assert result.ok is True
    assert result.stdout.strip() == "checked"


def test_run_checked_command_raises_on_failure() -> None:
    try:
        run_checked_command(["python3", "-c", "import sys; sys.exit(9)"], timeout=10)
        assert False, "expected CommandExecutionError"
    except CommandExecutionError:
        assert True


def test_command_exists_for_python3() -> None:
    assert command_exists("python3") is True


def test_command_exists_for_fake_binary() -> None:
    assert command_exists("definitely_not_a_real_binary_name_12345") is False
