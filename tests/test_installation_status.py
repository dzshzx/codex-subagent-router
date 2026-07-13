import json
from pathlib import Path

import pytest

from codex_subagent_router import (
    InstallationState,
    InstallationStatus,
    InstallationViolation,
    install_user_config,
    installation_status,
    rollback_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def test_status_reports_modified_when_a_managed_role_changes(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    config = installed.config_path.read_text().replace(
        "Read-only reviewer for one bounded diff axis.",
        "user replacement",
    )
    installed.config_path.write_text(config)

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.MODIFIED,
        details=("managed role block is missing or modified",),
    )
    with pytest.raises(
        InstallationViolation,
        match="managed role block is missing or modified",
    ):
        rollback_user_config(tmp_path)


def test_status_reports_modified_when_a_managed_hook_group_changes(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    hooks = json.loads(installed.hooks_path.read_text())
    hooks["hooks"]["SessionStart"].clear()
    installed.hooks_path.write_text(json.dumps(hooks) + "\n")

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.MODIFIED,
        details=("managed hook groups are missing or modified",),
    )


def test_status_attributes_invalid_toml_to_user_configuration(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    installed.config_path.write_text(installed.config_path.read_text() + "[broken\n")

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.MODIFIED,
        details=("config.toml is not valid TOML",),
    )


def test_status_attributes_invalid_json_to_user_configuration(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    installed.hooks_path.write_text('{"hooks":')

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.MODIFIED,
        details=("hooks.json is not valid JSON",),
    )


def test_status_reports_an_operation_lock_as_incomplete(tmp_path: Path) -> None:
    lock_path = tmp_path / "codex-subagent-router" / "operation.lock"
    lock_path.mkdir(parents=True)

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.INCOMPLETE,
        details=("installation operation is in progress",),
    )


def test_status_refuses_to_follow_a_symlinked_state_directory(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external-state"
    external.mkdir()
    (tmp_path / "codex-subagent-router").symlink_to(external, target_is_directory=True)

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.INCOMPLETE,
        details=("installation state directory must not be a symbolic link",),
    )
