import json
import shutil
import subprocess
from pathlib import Path


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("codex-subagent-router")
    assert executable is not None
    return subprocess.run(
        [executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_requires_an_explicit_codex_home() -> None:
    actual = _run_cli("status")

    assert actual.returncode == 2
    assert "--codex-home" in actual.stderr


def test_cli_rejects_a_blank_codex_home() -> None:
    for blank in ("", "   "):
        actual = _run_cli("status", "--codex-home", blank)

        assert actual.returncode == 2
        assert "--codex-home" in actual.stderr
        assert "must not be blank" in actual.stderr


def test_cli_plan_is_read_only_and_machine_readable(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)

    actual = _run_cli(
        "plan",
        "--codex-home",
        str(tmp_path),
        "--hook-executable",
        str(hook_executable),
    )

    assert actual.returncode == 0
    assert json.loads(actual.stdout) == {
        "codex_home": str(tmp_path),
        "config_action": "create",
        "hooks_action": "create",
        "roles_to_add": [
            "researcher",
            "reviewer",
            "architecture_explorer",
            "interface_designer",
        ],
        "hook_events_to_add": [
            "PreToolUse",
            "SessionStart",
            "SubagentStart",
        ],
        "conflicts": [],
        "requires_hook_review": True,
        "requires_new_session": True,
    }
    assert not (tmp_path / "config.toml").exists()
    assert not (tmp_path / "hooks.json").exists()


def test_cli_install_status_and_rollback_use_the_transaction_api(
    tmp_path: Path,
) -> None:
    hook_executable = _hook_executable(tmp_path)
    common = ("--codex-home", str(tmp_path))

    install = _run_cli(
        "install",
        *common,
        "--hook-executable",
        str(hook_executable),
    )
    assert install.returncode == 0
    assert json.loads(install.stdout) == {
        "codex_home": str(tmp_path),
        "config_path": str(tmp_path / "config.toml"),
        "hooks_path": str(tmp_path / "hooks.json"),
        "manifest_path": str(tmp_path / "codex-subagent-router" / "installation.json"),
        "requires_hook_review": True,
        "requires_new_session": True,
    }

    status = _run_cli("status", *common)
    assert status.returncode == 0
    assert json.loads(status.stdout) == {
        "codex_home": str(tmp_path),
        "state": "installed",
        "details": [],
    }

    rollback = _run_cli("rollback", *common)
    assert rollback.returncode == 0
    assert json.loads(rollback.stdout) == {
        "codex_home": str(tmp_path),
        "config_action": "removed",
        "hooks_action": "removed",
    }
    assert not (tmp_path / "config.toml").exists()
    assert not (tmp_path / "hooks.json").exists()
