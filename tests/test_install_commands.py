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


def test_cli_rejects_a_relative_hook_executable(tmp_path: Path) -> None:
    actual = _run_cli(
        "plan",
        "--codex-home",
        str(tmp_path),
        "--hook-executable",
        "relative-hook",
    )

    assert actual.returncode == 2
    assert "--hook-executable" in actual.stderr
    assert "must be an absolute path" in actual.stderr


def test_cli_plan_is_read_only_and_machine_readable(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)
    standalone_agent = tmp_path / "agents" / "user-owned.toml"
    standalone_agent.parent.mkdir()
    standalone_agent.write_text(
        'name = "user_owned"\n'
        'description = "Unmanaged agent"\n'
        'developer_instructions = "Remain user owned."\n'
    )

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
        ],
        "hook_events_to_add": [
            "PreToolUse",
            "SessionStart",
            "SubagentStart",
        ],
        "conflicts": [],
        "standalone_agent_files_to_preserve": ["agents/user-owned.toml"],
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


def test_cli_uninstall_restores_user_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_before = b'model = "user-owned"\n'
    config_path.write_bytes(config_before)
    config_path.chmod(0o640)
    hooks_path = tmp_path / "hooks.json"
    hooks_before = (
        b'{"hooks":{"Notification":[{"matcher":"","hooks":'
        b'[{"type":"command","command":"/user/hook","timeout":5}]}]}}\n'
    )
    hooks_path.write_bytes(hooks_before)
    hooks_path.chmod(0o644)
    hook_executable = _hook_executable(tmp_path)
    common = ("--codex-home", str(tmp_path))
    install = _run_cli(
        "install",
        *common,
        "--hook-executable",
        str(hook_executable),
    )
    assert install.returncode == 0

    uninstall = _run_cli("uninstall", *common)

    assert uninstall.returncode == 0
    assert json.loads(uninstall.stdout) == {
        "codex_home": str(tmp_path),
        "config_action": "updated",
        "hooks_action": "updated",
    }
    assert config_path.read_bytes() == config_before
    assert config_path.stat().st_mode & 0o7777 == 0o640
    assert hooks_path.read_bytes() == hooks_before
    assert hooks_path.stat().st_mode & 0o7777 == 0o644
    assert not (tmp_path / "codex-subagent-router").exists()


def test_cli_doctor_reports_project_agent_shadowing_without_writing(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_agent = project_directory / ".codex" / "agents" / "reviewer.toml"
    project_agent.parent.mkdir(parents=True)
    project_agent.write_text(
        'name = "reviewer"\n'
        'description = "Project reviewer"\n'
        'developer_instructions = "Override the user role."\n'
    )
    hook_executable = _hook_executable(tmp_path)
    install = _run_cli(
        "install",
        "--codex-home",
        str(codex_home),
        "--hook-executable",
        str(hook_executable),
    )
    assert install.returncode == 0
    before = (
        (codex_home / "config.toml").read_bytes(),
        (codex_home / "hooks.json").read_bytes(),
        project_agent.read_bytes(),
    )

    doctor = _run_cli(
        "doctor",
        "--codex-home",
        str(codex_home),
        "--project-dir",
        str(project_directory),
    )

    assert doctor.returncode == 1
    assert json.loads(doctor.stdout) == {
        "codex_home": str(codex_home),
        "project_directory": str(project_directory),
        "installation_state": "installed",
        "healthy": False,
        "issues": [
            "project standalone agent file '.codex/agents/reviewer.toml' "
            "declares managed role 'reviewer' and shadows the user-level "
            "router role; change its declared name or move it out of the "
            "active project agents directory"
        ],
        "user_standalone_agent_files": [],
        "project_standalone_agent_files": [
            ".codex/agents/reviewer.toml",
        ],
    }
    assert (codex_home / "config.toml").read_bytes() == before[0]
    assert (codex_home / "hooks.json").read_bytes() == before[1]
    assert project_agent.read_bytes() == before[2]


def test_cli_plans_and_applies_a_user_level_hook_launcher_update(
    tmp_path: Path,
) -> None:
    old_hook_executable = _hook_executable(tmp_path)
    common = ("--codex-home", str(tmp_path))
    install = _run_cli(
        "install",
        *common,
        "--hook-executable",
        str(old_hook_executable),
    )
    assert install.returncode == 0
    new_hook_executable = tmp_path / "new-bin" / "codex-subagent-router-hook"
    new_hook_executable.parent.mkdir()
    new_hook_executable.write_text("#!/bin/sh\n")
    new_hook_executable.chmod(0o755)
    hooks_before = (tmp_path / "hooks.json").read_bytes()
    manifest_before = (
        tmp_path / "codex-subagent-router" / "installation.json"
    ).read_bytes()

    plan = _run_cli(
        "update",
        *common,
        "--hook-executable",
        str(new_hook_executable),
        "--dry-run",
    )
    assert (tmp_path / "hooks.json").read_bytes() == hooks_before
    assert (
        tmp_path / "codex-subagent-router" / "installation.json"
    ).read_bytes() == manifest_before
    update = _run_cli(
        "update",
        *common,
        "--hook-executable",
        str(new_hook_executable),
    )

    assert plan.returncode == 0
    assert json.loads(plan.stdout) == {
        "codex_home": str(tmp_path),
        "hooks_action": "update",
        "hook_events_to_update": [
            "PreToolUse",
            "SessionStart",
            "SubagentStart",
        ],
        "conflicts": [],
        "requires_hook_review": True,
        "requires_new_session": True,
    }
    assert update.returncode == 0
    assert json.loads(update.stdout) == {
        "codex_home": str(tmp_path),
        "config_path": str(tmp_path / "config.toml"),
        "hooks_path": str(tmp_path / "hooks.json"),
        "manifest_path": str(tmp_path / "codex-subagent-router" / "installation.json"),
        "requires_hook_review": True,
        "requires_new_session": True,
    }


def test_cli_user_installation_lifecycle_end_to_end(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_directory.mkdir()
    config_path = codex_home / "config.toml"
    config_before = b'model = "user-owned"\n'
    config_path.write_bytes(config_before)
    config_path.chmod(0o640)
    hooks_path = codex_home / "hooks.json"
    hooks_before = b'{"hooks": {}}\n'
    hooks_path.write_bytes(hooks_before)
    hooks_path.chmod(0o644)
    first_hook = _hook_executable(tmp_path)
    second_hook = tmp_path / "updated-bin" / "codex-subagent-router-hook"
    second_hook.parent.mkdir()
    second_hook.write_text("#!/bin/sh\n")
    second_hook.chmod(0o755)
    common = ("--codex-home", str(codex_home))

    plan = _run_cli(
        "plan",
        *common,
        "--hook-executable",
        str(first_hook),
    )
    install = _run_cli(
        "install",
        *common,
        "--hook-executable",
        str(first_hook),
    )
    update_plan = _run_cli(
        "update",
        *common,
        "--hook-executable",
        str(second_hook),
        "--dry-run",
    )
    update = _run_cli(
        "update",
        *common,
        "--hook-executable",
        str(second_hook),
    )
    doctor = _run_cli(
        "doctor",
        *common,
        "--project-dir",
        str(project_directory),
    )
    uninstall = _run_cli("uninstall", *common)
    status = _run_cli("status", *common)

    assert [
        plan.returncode,
        install.returncode,
        update_plan.returncode,
        update.returncode,
        doctor.returncode,
        uninstall.returncode,
        status.returncode,
    ] == [0, 0, 0, 0, 0, 0, 0]
    assert json.loads(plan.stdout)["config_action"] == "update"
    assert json.loads(update_plan.stdout)["hooks_action"] == "update"
    assert json.loads(doctor.stdout)["healthy"] is True
    assert json.loads(uninstall.stdout) == {
        "codex_home": str(codex_home),
        "config_action": "updated",
        "hooks_action": "updated",
    }
    assert json.loads(status.stdout)["state"] == "not-installed"
    assert config_path.read_bytes() == config_before
    assert config_path.stat().st_mode & 0o7777 == 0o640
    assert hooks_path.read_bytes() == hooks_before
    assert hooks_path.stat().st_mode & 0o7777 == 0o644
    assert not (codex_home / "codex-subagent-router").exists()
