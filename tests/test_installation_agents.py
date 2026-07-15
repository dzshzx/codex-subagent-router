from pathlib import Path

import pytest

from codex_subagent_router import (
    InstallationFileAction,
    InstallationViolation,
    install_user_config,
    plan_user_installation,
    plan_user_update,
    rollback_user_config,
    update_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir(exist_ok=True)
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def test_plan_reports_standalone_agent_conflict_by_declared_name(
    tmp_path: Path,
) -> None:
    agents_directory = tmp_path / "agents"
    agents_directory.mkdir()
    standalone_agent = agents_directory / "custom-review.toml"
    standalone_agent.write_text(
        'name = "reviewer"\n'
        'description = "User-owned reviewer"\n'
        'developer_instructions = "Review independently."\n'
    )

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "standalone agent file 'agents/custom-review.toml' declares managed "
        "role 'reviewer'; change its declared name or move it out of the active "
        "agents directory before installation; the installer will leave the "
        "file unchanged",
    )
    assert actual.standalone_agent_files_to_preserve == ("agents/custom-review.toml",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert standalone_agent.read_text() == (
        'name = "reviewer"\n'
        'description = "User-owned reviewer"\n'
        'developer_instructions = "Review independently."\n'
    )


def test_plan_normalizes_a_standalone_agent_declared_name(tmp_path: Path) -> None:
    standalone_agent = tmp_path / "agents" / "custom-review.toml"
    standalone_agent.parent.mkdir()
    standalone_agent.write_text(
        'name = " reviewer "\n'
        'description = "User-owned reviewer"\n'
        'developer_instructions = "Review independently."\n'
    )

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "standalone agent file 'agents/custom-review.toml' declares managed "
        "role 'reviewer'; change its declared name or move it out of the active "
        "agents directory before installation; the installer will leave the "
        "file unchanged",
    )


def test_plan_reports_nested_standalone_agent_conflict(tmp_path: Path) -> None:
    standalone_agent = tmp_path / "agents" / "team" / "custom-review.toml"
    standalone_agent.parent.mkdir(parents=True)
    standalone_agent.write_text(
        'name = "reviewer"\n'
        'description = "Nested user-owned reviewer"\n'
        'developer_instructions = "Review independently."\n'
    )

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "standalone agent file 'agents/team/custom-review.toml' declares managed "
        "role 'reviewer'; change its declared name or move it out of the active "
        "agents directory before installation; the installer will leave the "
        "file unchanged",
    )


def test_plan_ignores_a_disabled_standalone_agent_definition(tmp_path: Path) -> None:
    standalone_agent = tmp_path / "agents" / "reviewer.toml.disabled"
    standalone_agent.parent.mkdir()
    standalone_agent.write_text(
        'name = "reviewer"\n'
        'description = "Disabled reviewer"\n'
        'developer_instructions = "Do not load this file."\n'
    )

    actual = plan_user_installation(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )

    assert actual.conflicts == ()
    assert actual.roles_to_add == (
        "researcher",
        "reviewer",
        "architecture_explorer",
        "interface_designer",
    )


def test_plan_reports_each_standalone_managed_role_conflict(
    tmp_path: Path,
) -> None:
    agents_directory = tmp_path / "agents"
    agents_directory.mkdir()
    (agents_directory / "a.toml").write_text(
        'name = "reviewer"\n'
        'description = "User-owned reviewer"\n'
        'developer_instructions = "Review independently."\n'
    )
    (agents_directory / "z.toml").write_text(
        'name = "researcher"\n'
        'description = "User-owned researcher"\n'
        'developer_instructions = "Research independently."\n'
    )

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "standalone agent file 'agents/a.toml' declares managed role 'reviewer'; "
        "change its declared name or move it out of the active agents directory "
        "before installation; the installer will leave the file unchanged",
        "standalone agent file 'agents/z.toml' declares managed role "
        "'researcher'; change its declared name or move it out of the active "
        "agents directory before installation; the installer will leave the "
        "file unchanged",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_plan_reports_invalid_standalone_agent_toml(tmp_path: Path) -> None:
    agents_directory = tmp_path / "agents"
    agents_directory.mkdir()
    standalone_agent = agents_directory / "broken.toml"
    standalone_agent.write_bytes(b'name = "reviewer"\ndescription = [\n')

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "standalone agent file 'agents/broken.toml' is not valid TOML",
    )
    assert actual.standalone_agent_files_to_preserve == ("agents/broken.toml",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert standalone_agent.read_bytes() == b'name = "reviewer"\ndescription = [\n'


def test_plan_reports_standalone_agent_without_a_valid_name(tmp_path: Path) -> None:
    agents_directory = tmp_path / "agents"
    agents_directory.mkdir()
    standalone_agent = agents_directory / "unnamed.toml"
    standalone_agent.write_text(
        'description = "Missing its required name"\n'
        'developer_instructions = "Do something."\n'
    )

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "standalone agent file 'agents/unnamed.toml' field 'name' must be a "
        "non-empty string",
    )
    assert actual.standalone_agent_files_to_preserve == ("agents/unnamed.toml",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_unmanaged_standalone_agent_does_not_conflict_or_get_modified(
    tmp_path: Path,
) -> None:
    standalone_agent = tmp_path / "agents" / "user-owned.toml"
    standalone_agent.parent.mkdir()
    standalone_document = (
        b'name = "user_owned"\n'
        b'description = "Unmanaged agent"\n'
        b'developer_instructions = "Remain user owned."\n'
    )
    standalone_agent.write_bytes(standalone_document)
    standalone_agent.chmod(0o640)
    hook_executable = _hook_executable(tmp_path)

    plan = plan_user_installation(tmp_path, (str(hook_executable),))
    installed = install_user_config(tmp_path, (str(hook_executable),))

    assert plan.conflicts == ()
    assert plan.standalone_agent_files_to_preserve == ("agents/user-owned.toml",)
    assert installed.manifest_path.exists()
    assert standalone_agent.read_bytes() == standalone_document
    assert standalone_agent.stat().st_mode & 0o7777 == 0o640

    rollback_user_config(tmp_path)

    assert standalone_agent.read_bytes() == standalone_document
    assert standalone_agent.stat().st_mode & 0o7777 == 0o640
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not installed.manifest_path.parent.exists()


def test_blocked_plan_still_reports_standalone_files_to_preserve(
    tmp_path: Path,
) -> None:
    standalone_agent = tmp_path / "agents" / "user-owned.toml"
    standalone_agent.parent.mkdir()
    standalone_agent.write_text(
        'name = "user_owned"\n'
        'description = "Unmanaged agent"\n'
        'developer_instructions = "Remain user owned."\n'
    )
    (tmp_path / "codex-subagent-router" / "operation.lock").mkdir(parents=True)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == ("another installation operation is in progress",)
    assert actual.standalone_agent_files_to_preserve == ("agents/user-owned.toml",)


def test_update_refuses_a_new_standalone_managed_role_conflict(
    tmp_path: Path,
) -> None:
    old_hook_executable = _hook_executable(tmp_path)
    installed = install_user_config(tmp_path, (str(old_hook_executable),))
    hooks_before = installed.hooks_path.read_bytes()
    standalone_agent = tmp_path / "agents" / "custom-review.toml"
    standalone_agent.parent.mkdir()
    standalone_agent.write_text(
        'name = "reviewer"\n'
        'description = "User-owned reviewer"\n'
        'developer_instructions = "Review independently."\n'
    )
    new_hook_executable = tmp_path / "new-bin" / "codex-subagent-router-hook"
    new_hook_executable.parent.mkdir()
    new_hook_executable.write_text("#!/bin/sh\n")
    new_hook_executable.chmod(0o755)

    plan = plan_user_update(tmp_path, (str(new_hook_executable),))

    expected_conflict = (
        "standalone agent file 'agents/custom-review.toml' declares managed role "
        "'reviewer'; change its declared name or move it out of the active agents "
        "directory before installation; the installer will leave the file unchanged"
    )
    assert plan.conflicts == (expected_conflict,)
    with pytest.raises(InstallationViolation, match="standalone agent file"):
        update_user_config(tmp_path, (str(new_hook_executable),))
    assert installed.hooks_path.read_bytes() == hooks_before
