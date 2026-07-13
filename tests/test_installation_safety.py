import base64
import json
from pathlib import Path

import pytest

from codex_subagent_router import (
    InstallationFileAction,
    InstallationState,
    InstallationViolation,
    RollbackFileAction,
    install_user_config,
    installation_status,
    plan_user_installation,
    rollback_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


@pytest.mark.parametrize("file_name", ["config.toml", "hooks.json"])
def test_plan_refuses_user_configuration_symlinks(
    tmp_path: Path,
    file_name: str,
) -> None:
    external = tmp_path / "external"
    external.write_text("{}\n" if file_name == "hooks.json" else "")
    (tmp_path / file_name).symlink_to(external)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (f"{file_name} must not be a symbolic link",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert external.read_text() == ("{}\n" if file_name == "hooks.json" else "")


@pytest.mark.parametrize("file_name", ["config.toml", "hooks.json"])
def test_plan_refuses_non_file_configuration_targets(
    tmp_path: Path,
    file_name: str,
) -> None:
    (tmp_path / file_name).mkdir()

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (f"{file_name} must be a regular file",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_install_refuses_a_symlinked_installation_directory(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external-state"
    external.mkdir()
    (tmp_path / "codex-subagent-router").symlink_to(external, target_is_directory=True)

    with pytest.raises(
        InstallationViolation,
        match="installation state directory must not be a symbolic link",
    ):
        install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))

    assert list(external.iterdir()) == []
    assert not (tmp_path / "config.toml").exists()
    assert not (tmp_path / "hooks.json").exists()


def test_install_refuses_when_another_operation_holds_the_lock(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "codex-subagent-router" / "operation.lock"
    lock_path.mkdir(parents=True)

    with pytest.raises(
        InstallationViolation,
        match="another installation operation is in progress",
    ):
        install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))

    assert lock_path.is_dir()
    assert not (tmp_path / "config.toml").exists()
    assert not (tmp_path / "hooks.json").exists()


def test_rollback_refuses_when_another_operation_holds_the_lock(
    tmp_path: Path,
) -> None:
    install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    lock_path = tmp_path / "codex-subagent-router" / "operation.lock"
    lock_path.mkdir()

    with pytest.raises(
        InstallationViolation,
        match="another installation operation is in progress",
    ):
        rollback_user_config(tmp_path)

    assert lock_path.is_dir()
    assert (tmp_path / "config.toml").exists()
    assert (tmp_path / "hooks.json").exists()


def test_reinstall_refuses_to_replace_the_original_rollback_snapshot(
    tmp_path: Path,
) -> None:
    first_executable = _hook_executable(tmp_path)
    installed = install_user_config(tmp_path, (str(first_executable),))
    before = (
        installed.config_path.read_bytes(),
        installed.hooks_path.read_bytes(),
        installed.manifest_path.read_bytes(),
    )
    second_executable = tmp_path / "bin" / "replacement-hook"
    second_executable.write_text("#!/bin/sh\n")
    second_executable.chmod(0o755)

    with pytest.raises(
        InstallationViolation,
        match="existing installation differs from the requested configuration",
    ):
        install_user_config(tmp_path, (str(second_executable),))

    assert installed.config_path.read_bytes() == before[0]
    assert installed.hooks_path.read_bytes() == before[1]
    assert installed.manifest_path.read_bytes() == before[2]


def test_plan_reports_an_incompatible_managed_hook_matcher(
    tmp_path: Path,
) -> None:
    hooks = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "^(Agent|.*spawn_agent.*)$",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/user/owned-hook",
                        }
                    ],
                }
            ]
        }
    }
    (tmp_path / "hooks.json").write_text(json.dumps(hooks) + "\n")

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.hook_events_to_add == ("SessionStart", "SubagentStart")
    assert actual.conflicts == (
        "managed hook event 'PreToolUse' matcher already exists with "
        "incompatible configuration",
    )


def test_reinstall_refuses_an_invalid_existing_manifest(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)
    installed = install_user_config(tmp_path, (str(hook_executable),))
    installed.manifest_path.write_text("{}\n")
    before = (
        installed.config_path.read_bytes(),
        installed.hooks_path.read_bytes(),
        installed.manifest_path.read_bytes(),
    )

    with pytest.raises(
        InstallationViolation,
        match="existing installation state is not healthy",
    ):
        install_user_config(tmp_path, (str(hook_executable),))

    assert installed.config_path.read_bytes() == before[0]
    assert installed.hooks_path.read_bytes() == before[1]
    assert installed.manifest_path.read_bytes() == before[2]


def test_install_owns_only_missing_hook_groups(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)
    existing_group = {
        "matcher": "^(Agent|.*spawn_agent.*)$",
        "hooks": [
            {
                "type": "command",
                "command": f"{hook_executable} pre-tool-use",
                "timeout": 10,
            }
        ],
    }
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps({"hooks": {"PreToolUse": [existing_group]}}) + "\n"
    )

    installed = install_user_config(tmp_path, (str(hook_executable),))

    hooks = json.loads(hooks_path.read_text())
    assert hooks["hooks"]["PreToolUse"] == [existing_group]
    manifest = json.loads(installed.manifest_path.read_text())
    assert set(manifest["hooks"]["managed_groups"]) == {
        "SessionStart",
        "SubagentStart",
    }


def test_install_can_adopt_compatible_configuration_without_owning_it(
    tmp_path: Path,
) -> None:
    hook_executable = _hook_executable(tmp_path)
    source_home = tmp_path / "source-home"
    target_home = tmp_path / "target-home"
    source_home.mkdir()
    target_home.mkdir()
    source = install_user_config(source_home, (str(hook_executable),))
    config_document = source.config_path.read_bytes()
    hooks_document = source.hooks_path.read_bytes()
    (target_home / "config.toml").write_bytes(config_document)
    (target_home / "hooks.json").write_bytes(hooks_document)

    adopted = install_user_config(target_home, (str(hook_executable),))

    manifest = json.loads(adopted.manifest_path.read_text())
    assert manifest["config"]["changed"] is False
    assert manifest["hooks"]["changed"] is False
    assert adopted.config_path.read_bytes() == config_document
    assert adopted.hooks_path.read_bytes() == hooks_document

    rolled_back = rollback_user_config(target_home)

    assert rolled_back.config_action is RollbackFileAction.UNCHANGED
    assert rolled_back.hooks_action is RollbackFileAction.UNCHANGED
    assert adopted.config_path.read_bytes() == config_document
    assert adopted.hooks_path.read_bytes() == hooks_document


def test_rollback_reports_an_invalid_transaction_journal(tmp_path: Path) -> None:
    transaction_path = tmp_path / "codex-subagent-router" / "transaction.json"
    transaction_path.parent.mkdir()
    transaction_path.write_text("{invalid")

    with pytest.raises(
        InstallationViolation,
        match="installation transaction journal is invalid",
    ):
        rollback_user_config(tmp_path)

    assert transaction_path.read_text() == "{invalid"


def test_status_and_rollback_refuse_configuration_symlinks(
    tmp_path: Path,
) -> None:
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    config_document = installed.config_path.read_bytes()
    external = tmp_path / "external-config.toml"
    external.write_bytes(config_document)
    installed.config_path.unlink()
    installed.config_path.symlink_to(external)

    status = installation_status(tmp_path)

    assert status.state is InstallationState.MODIFIED
    assert status.details == ("config.toml must not be a symbolic link",)
    with pytest.raises(
        InstallationViolation,
        match="config.toml must not be a symbolic link",
    ):
        rollback_user_config(tmp_path)
    assert installed.config_path.is_symlink()
    assert external.read_bytes() == config_document


def test_status_and_rollback_reject_corrupt_rollback_metadata(
    tmp_path: Path,
) -> None:
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    manifest = json.loads(installed.manifest_path.read_text())
    manifest["config"]["original_mode"] = 0o644
    installed.manifest_path.write_text(json.dumps(manifest) + "\n")
    config_before = installed.config_path.read_bytes()
    hooks_before = installed.hooks_path.read_bytes()

    status = installation_status(tmp_path)

    assert status.state is InstallationState.INCOMPLETE
    assert status.details == ("installation manifest is invalid",)
    with pytest.raises(
        InstallationViolation,
        match="installation manifest is invalid",
    ):
        rollback_user_config(tmp_path)
    assert installed.config_path.read_bytes() == config_before
    assert installed.hooks_path.read_bytes() == hooks_before


@pytest.mark.parametrize(
    ("file_name", "replacement"),
    [
        ("config", b'model = "tampered"\n'),
        ("hooks", b'{"hooks":{"UserOwned":[]}}\n'),
    ],
)
def test_status_and_rollback_reject_inconsistent_original_snapshot(
    tmp_path: Path,
    file_name: str,
    replacement: bytes,
) -> None:
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    config_path.write_text('model = "gpt-5.6"\n')
    hooks_path.write_text('{"hooks":{}}\n')
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    manifest = json.loads(installed.manifest_path.read_text())
    manifest[file_name]["original_bytes"] = base64.b64encode(replacement).decode()
    installed.manifest_path.write_text(json.dumps(manifest) + "\n")
    config_before = installed.config_path.read_bytes()
    hooks_before = installed.hooks_path.read_bytes()

    status = installation_status(tmp_path)

    assert status.state is InstallationState.INCOMPLETE
    assert status.details == ("installation manifest is invalid",)
    with pytest.raises(
        InstallationViolation,
        match="installation manifest is invalid",
    ):
        rollback_user_config(tmp_path)
    assert installed.config_path.read_bytes() == config_before
    assert installed.hooks_path.read_bytes() == hooks_before


def test_status_and_rollback_reject_an_inconsistent_original_mode(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('model = "gpt-5.6"\n')
    config_path.chmod(0o640)
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    manifest = json.loads(installed.manifest_path.read_text())
    manifest["config"]["original_mode"] = 0o600
    installed.manifest_path.write_text(json.dumps(manifest) + "\n")
    config_before = installed.config_path.read_bytes()
    hooks_before = installed.hooks_path.read_bytes()

    status = installation_status(tmp_path)

    assert status.state is InstallationState.MODIFIED
    assert status.details == ("config.toml mode is modified",)
    with pytest.raises(
        InstallationViolation,
        match="config.toml mode is modified",
    ):
        rollback_user_config(tmp_path)
    assert installed.config_path.read_bytes() == config_before
    assert installed.hooks_path.read_bytes() == hooks_before
