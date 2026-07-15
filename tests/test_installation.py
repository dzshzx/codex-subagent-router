import hashlib
import json
import stat
import tomllib
from pathlib import Path

import pytest

from codex_subagent_router import (
    InstallationFileAction,
    InstallationPlan,
    InstallationResult,
    InstallationState,
    InstallationStatus,
    InstallationViolation,
    RollbackFileAction,
    RollbackResult,
    install_user_config,
    installation_status,
    plan_user_installation,
    rollback_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir(exist_ok=True)
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def test_empty_codex_home_plan_creates_managed_roles_and_hooks(
    tmp_path: Path,
) -> None:
    hook_executable = _hook_executable(tmp_path)

    actual = plan_user_installation(tmp_path, (str(hook_executable),))

    assert actual == InstallationPlan(
        codex_home=tmp_path,
        config_action=InstallationFileAction.CREATE,
        hooks_action=InstallationFileAction.CREATE,
        roles_to_add=(
            "researcher",
            "reviewer",
            "architecture_explorer",
            "interface_designer",
        ),
        hook_events_to_add=("PreToolUse", "SessionStart", "SubagentStart"),
        conflicts=(),
        requires_hook_review=True,
        requires_new_session=True,
    )
    assert not (tmp_path / "config.toml").exists()
    assert not (tmp_path / "hooks.json").exists()


def test_plan_preserves_existing_compatible_roles_and_unrelated_hooks(
    tmp_path: Path,
) -> None:
    config_document = """model = "gpt-5.6-sol"

[agents.reviewer]
description = "Read-only reviewer for one bounded diff axis."
"""
    hooks_document = """{
  "description": "existing user hooks",
  "hooks": {
    "Stop": []
  }
}
"""
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    config_path.write_text(config_document)
    hooks_path.write_text(hooks_document)

    actual = plan_user_installation(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )

    assert actual == InstallationPlan(
        codex_home=tmp_path,
        config_action=InstallationFileAction.UPDATE,
        hooks_action=InstallationFileAction.UPDATE,
        roles_to_add=(
            "researcher",
            "architecture_explorer",
            "interface_designer",
        ),
        hook_events_to_add=("PreToolUse", "SessionStart", "SubagentStart"),
        conflicts=(),
        requires_hook_review=True,
        requires_new_session=True,
    )
    assert config_path.read_text() == config_document
    assert hooks_path.read_text() == hooks_document


def test_install_adds_v2_when_all_managed_roles_already_exist(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """[agents.researcher]
description = "Primary-source researcher for external documentation, APIs, specifications, and upstream code."

[agents.reviewer]
description = "Read-only reviewer for one bounded diff axis."

[agents.architecture_explorer]
description = "Read-only architecture explorer for broad codebase scans and deepening opportunities."

[agents.interface_designer]
description = "Read-only module-interface designer for independent API and module-shape alternatives."
"""
    )
    hook_command = (str(_hook_executable(tmp_path)),)

    plan = plan_user_installation(tmp_path, hook_command)
    install_user_config(tmp_path, hook_command)

    assert plan.config_action is InstallationFileAction.UPDATE
    assert plan.roles_to_add == ()
    config = tomllib.loads(config_path.read_text())
    assert config["features"]["multi_agent_v2"] == {
        "enabled": True,
        "hide_spawn_agent_metadata": False,
        "tool_namespace": "agents",
    }


def test_plan_reports_an_incompatible_managed_role_without_overwriting_it(
    tmp_path: Path,
) -> None:
    (tmp_path / "config.toml").write_text(
        """[agents.reviewer]
description = "User-owned reviewer"
config_file = "./agents/reviewer.toml"
"""
    )

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.roles_to_add == (
        "researcher",
        "architecture_explorer",
        "interface_designer",
    )
    assert actual.conflicts == (
        "managed role 'reviewer' already exists with incompatible configuration",
    )


@pytest.mark.parametrize(
    ("config_document", "expected_conflict"),
    (
        (
            """[features.multi_agent_v2]
enabled = false
hide_spawn_agent_metadata = false
tool_namespace = "agents"
""",
            "MultiAgent V2 already exists with incompatible configuration",
        ),
        (
            """[features.multi_agent_v2]
enabled = true
""",
            "MultiAgent V2 already exists with incompatible configuration",
        ),
        (
            'features = "user value"\n',
            "config.toml field 'features' must be a table",
        ),
    ),
)
def test_plan_rejects_incompatible_v2_configuration(
    tmp_path: Path,
    config_document: str,
    expected_conflict: str,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (expected_conflict,)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert config_path.read_text() == config_document


def test_plan_rejects_config_that_cannot_be_extended_with_v2(
    tmp_path: Path,
) -> None:
    config_document = "features = { existing_flag = true }\n"
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "config.toml cannot be safely extended with managed configuration",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert config_path.read_text() == config_document


def test_plan_rejects_agents_max_threads_when_enabling_v2(
    tmp_path: Path,
) -> None:
    config_document = """[agents]
max_threads = 8
"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == (
        "config.toml field 'agents.max_threads' is incompatible with MultiAgent V2",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert config_path.read_text() == config_document


def test_install_preserves_compatible_user_owned_v2_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """[features.multi_agent_v2]
enabled = true
hide_spawn_agent_metadata = false
tool_namespace = "agents"

[agents.reviewer]
description = "Read-only reviewer for one bounded diff axis."
"""
    )

    install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))

    config_text = config_path.read_text()
    assert config_text.count("[features.multi_agent_v2]") == 1
    config = tomllib.loads(config_text)
    assert config["features"]["multi_agent_v2"] == {
        "enabled": True,
        "hide_spawn_agent_metadata": False,
        "tool_namespace": "agents",
    }
    assert set(config["agents"]) == {
        "researcher",
        "reviewer",
        "architecture_explorer",
        "interface_designer",
    }


def test_install_into_empty_codex_home_writes_private_managed_configuration(
    tmp_path: Path,
) -> None:
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)

    actual = install_user_config(tmp_path, (str(hook_executable),))

    assert actual == InstallationResult(
        codex_home=tmp_path,
        config_path=tmp_path / "config.toml",
        hooks_path=tmp_path / "hooks.json",
        manifest_path=(tmp_path / "codex-subagent-router" / "installation.json"),
        requires_hook_review=True,
        requires_new_session=True,
    )
    config = tomllib.loads((tmp_path / "config.toml").read_text())
    assert config["features"]["multi_agent_v2"] == {
        "enabled": True,
        "hide_spawn_agent_metadata": False,
        "tool_namespace": "agents",
    }
    assert config["agents"] == {
        "researcher": {
            "description": (
                "Primary-source researcher for external documentation, APIs, "
                "specifications, and upstream code."
            )
        },
        "reviewer": {"description": "Read-only reviewer for one bounded diff axis."},
        "architecture_explorer": {
            "description": (
                "Read-only architecture explorer for broad codebase scans and "
                "deepening opportunities."
            )
        },
        "interface_designer": {
            "description": (
                "Read-only module-interface designer for independent API and "
                "module-shape alternatives."
            )
        },
    }
    hooks = json.loads((tmp_path / "hooks.json").read_text())
    assert hooks == {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "^(Agent|.*spawn_agent.*)$",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{hook_executable} pre-tool-use",
                            "timeout": 10,
                        }
                    ],
                }
            ],
            "SessionStart": [
                {
                    "matcher": "startup",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{hook_executable} session-start",
                            "timeout": 10,
                        }
                    ],
                }
            ],
            "SubagentStart": [
                {
                    "matcher": (
                        "researcher|reviewer|architecture_explorer|interface_designer"
                    ),
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{hook_executable} subagent-start",
                            "timeout": 10,
                        }
                    ],
                }
            ],
        }
    }
    assert stat.S_IMODE((tmp_path / "config.toml").stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "hooks.json").stat().st_mode) == 0o600
    assert actual.manifest_path.exists()


def test_plan_after_installation_is_unchanged(
    tmp_path: Path,
) -> None:
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)
    hook_command = (str(hook_executable),)
    install_user_config(tmp_path, hook_command)

    actual = plan_user_installation(tmp_path, hook_command)

    assert actual == InstallationPlan(
        codex_home=tmp_path,
        config_action=InstallationFileAction.UNCHANGED,
        hooks_action=InstallationFileAction.UNCHANGED,
        roles_to_add=(),
        hook_events_to_add=(),
        conflicts=(),
        requires_hook_review=True,
        requires_new_session=True,
    )


def test_schema_one_installation_without_v2_is_modified_but_rollbackable(
    tmp_path: Path,
) -> None:
    hook_command = (str(_hook_executable(tmp_path)),)
    installed = install_user_config(tmp_path, hook_command)
    current_config = installed.config_path.read_text()
    roles = current_config[current_config.index("[agents.researcher]") :]
    old_config = (
        "# BEGIN codex-subagent-router managed roles\n"
        + roles.replace(
            "# END codex-subagent-router managed configuration",
            "# END codex-subagent-router managed roles",
        )
    ).encode()
    manifest = json.loads(installed.manifest_path.read_text())
    manifest["schema_version"] = 1
    manifest["config"].pop("expected_multi_agent_v2", None)
    manifest["config"]["managed_block"] = old_config.decode()
    manifest["config"]["installed_sha256"] = hashlib.sha256(old_config).hexdigest()
    installed.config_path.write_bytes(old_config)
    installed.manifest_path.write_text(json.dumps(manifest) + "\n")

    status = installation_status(tmp_path)
    plan = plan_user_installation(tmp_path, hook_command)
    rolled_back = rollback_user_config(tmp_path)

    assert status == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.MODIFIED,
        details=("managed MultiAgent V2 configuration is missing or modified",),
    )
    assert plan.conflicts == (
        "existing installation state is not healthy: managed MultiAgent V2 "
        "configuration is missing or modified",
    )
    assert rolled_back.config_action is RollbackFileAction.REMOVED
    assert rolled_back.hooks_action is RollbackFileAction.REMOVED


def test_reinstall_with_the_same_command_is_idempotent(
    tmp_path: Path,
) -> None:
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)
    hook_command = (str(hook_executable),)
    first = install_user_config(tmp_path, hook_command)
    installed_documents = {
        path: path.read_bytes()
        for path in (first.config_path, first.hooks_path, first.manifest_path)
    }

    second = install_user_config(tmp_path, hook_command)

    assert second == first
    assert {
        path: path.read_bytes() for path in installed_documents
    } == installed_documents


def test_status_reports_a_complete_installation(
    tmp_path: Path,
) -> None:
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)
    install_user_config(tmp_path, (str(hook_executable),))

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.INSTALLED,
        details=(),
    )


def test_status_rejects_wrong_typed_v2_settings_in_the_receipt(
    tmp_path: Path,
) -> None:
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    manifest = json.loads(installed.manifest_path.read_text())
    manifest["config"]["expected_multi_agent_v2"]["enabled"] = 1
    installed.manifest_path.write_text(json.dumps(manifest) + "\n")

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.INCOMPLETE,
        details=("installation manifest is invalid",),
    )


def test_status_reports_modified_user_owned_v2_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    user_config = """[features.multi_agent_v2]
enabled = true
hide_spawn_agent_metadata = false
tool_namespace = "agents"
"""
    config_path.write_text(user_config)
    install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    modified_user_config = user_config.replace("enabled = true", "enabled = false")
    config_path.write_text(
        config_path.read_text().replace("enabled = true", "enabled = false")
    )

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.MODIFIED,
        details=("managed MultiAgent V2 configuration is missing or modified",),
    )

    rolled_back = rollback_user_config(tmp_path)

    assert rolled_back.config_action is RollbackFileAction.UPDATED
    assert config_path.read_text() == modified_user_config


def test_rollback_removes_files_that_did_not_exist_before_installation(
    tmp_path: Path,
) -> None:
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)
    installed = install_user_config(tmp_path, (str(hook_executable),))

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.REMOVED,
        hooks_action=RollbackFileAction.REMOVED,
    )
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not installed.manifest_path.exists()
    assert not installed.manifest_path.parent.exists()
    assert installation_status(tmp_path) == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.NOT_INSTALLED,
        details=(),
    )


def test_rollback_reports_that_the_router_is_not_installed(tmp_path: Path) -> None:
    with pytest.raises(
        InstallationViolation,
        match="installation cannot be rolled back: not-installed",
    ):
        rollback_user_config(tmp_path)


def test_rollback_restores_existing_files_byte_for_byte_and_preserves_modes(
    tmp_path: Path,
) -> None:
    config_document = (
        b'model = "gpt-5.6-sol"\n\n'
        b"[agents.reviewer]\n"
        b'description = "Read-only reviewer for one bounded diff axis."\n'
    )
    hooks_document = b'{"description":"keep","hooks":{"Stop":[]}}\n'
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    config_path.write_bytes(config_document)
    hooks_path.write_bytes(hooks_document)
    config_path.chmod(0o1640)
    hooks_path.chmod(0o2644)
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)
    install_user_config(tmp_path, (str(hook_executable),))
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o1640
    assert stat.S_IMODE(hooks_path.stat().st_mode) == 0o2644

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.UPDATED,
        hooks_action=RollbackFileAction.UPDATED,
    )
    assert config_path.read_bytes() == config_document
    assert hooks_path.read_bytes() == hooks_document
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o1640
    assert stat.S_IMODE(hooks_path.stat().st_mode) == 0o2644


def test_rollback_preserves_compatible_user_owned_v2_configuration(
    tmp_path: Path,
) -> None:
    config_document = b"""[features.multi_agent_v2]
enabled = true
hide_spawn_agent_metadata = false
tool_namespace = "agents"
"""
    config_path = tmp_path / "config.toml"
    config_path.write_bytes(config_document)
    install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))

    actual = rollback_user_config(tmp_path)

    assert actual.config_action is RollbackFileAction.UPDATED
    assert config_path.read_bytes() == config_document


def test_install_rejects_a_non_file_state_target_before_changing_files(
    tmp_path: Path,
) -> None:
    config_document = b'model = "gpt-5.6-sol"\n'
    hooks_document = b'{"hooks":{"Stop":[]}}\n'
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    config_path.write_bytes(config_document)
    hooks_path.write_bytes(hooks_document)
    config_path.chmod(0o640)
    hooks_path.chmod(0o644)
    blocked_manifest = tmp_path / "codex-subagent-router" / "installation.json"
    blocked_manifest.mkdir(parents=True)
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)

    with pytest.raises(
        InstallationViolation,
        match="installation state file is unsafe: installation.json must be a regular file",
    ):
        install_user_config(tmp_path, (str(hook_executable),))

    assert config_path.read_bytes() == config_document
    assert hooks_path.read_bytes() == hooks_document
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o640
    assert stat.S_IMODE(hooks_path.stat().st_mode) == 0o644
    assert blocked_manifest.is_dir()


def test_status_reports_an_incomplete_persisted_transaction(
    tmp_path: Path,
) -> None:
    transaction_path = tmp_path / "codex-subagent-router" / "transaction.json"
    transaction_path.parent.mkdir()
    transaction_path.write_text("{}\n")

    actual = installation_status(tmp_path)

    assert actual == InstallationStatus(
        codex_home=tmp_path,
        state=InstallationState.INCOMPLETE,
        details=("installation transaction is not complete",),
    )


def test_rollback_recovers_a_persisted_incomplete_installation(
    tmp_path: Path,
) -> None:
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)
    installed = install_user_config(tmp_path, (str(hook_executable),))
    journal = json.loads(installed.manifest_path.read_text())
    journal["state"] = "installing"
    transaction_path = installed.manifest_path.with_name("transaction.json")
    transaction_path.write_text(json.dumps(journal) + "\n")
    installed.manifest_path.unlink()

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.REMOVED,
        hooks_action=RollbackFileAction.REMOVED,
    )
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not transaction_path.exists()
    assert not transaction_path.parent.exists()


def test_install_refuses_to_overwrite_an_incomplete_transaction(
    tmp_path: Path,
) -> None:
    transaction_path = tmp_path / "codex-subagent-router" / "transaction.json"
    transaction_path.parent.mkdir()
    transaction_document = b'{"state":"installing"}\n'
    transaction_path.write_bytes(transaction_document)
    hook_executable = tmp_path / "bin" / "codex-subagent-router-hook"
    hook_executable.parent.mkdir()
    hook_executable.write_text("#!/bin/sh\n")
    hook_executable.chmod(0o755)

    with pytest.raises(
        InstallationViolation,
        match="incomplete installation transaction must be rolled back",
    ):
        install_user_config(tmp_path, (str(hook_executable),))

    assert transaction_path.read_bytes() == transaction_document
    assert not (tmp_path / "config.toml").exists()
    assert not (tmp_path / "hooks.json").exists()


def test_plan_reports_invalid_toml_without_proposing_partial_changes(
    tmp_path: Path,
) -> None:
    config_document = b"[agents.reviewer\n"
    (tmp_path / "config.toml").write_bytes(config_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual == InstallationPlan(
        codex_home=tmp_path,
        config_action=InstallationFileAction.UNCHANGED,
        hooks_action=InstallationFileAction.UNCHANGED,
        roles_to_add=(),
        hook_events_to_add=(),
        conflicts=("config.toml is not valid TOML",),
        requires_hook_review=True,
        requires_new_session=True,
    )
    assert (tmp_path / "config.toml").read_bytes() == config_document


def test_plan_reports_invalid_json_without_proposing_partial_changes(
    tmp_path: Path,
) -> None:
    hooks_document = b'{"hooks":'
    (tmp_path / "hooks.json").write_bytes(hooks_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual == InstallationPlan(
        codex_home=tmp_path,
        config_action=InstallationFileAction.UNCHANGED,
        hooks_action=InstallationFileAction.UNCHANGED,
        roles_to_add=(),
        hook_events_to_add=(),
        conflicts=("hooks.json is not valid JSON",),
        requires_hook_review=True,
        requires_new_session=True,
    )
    assert (tmp_path / "hooks.json").read_bytes() == hooks_document


def test_plan_rejects_a_non_table_agents_value(tmp_path: Path) -> None:
    config_document = b'agents = "user value"\n'
    (tmp_path / "config.toml").write_bytes(config_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == ("config.toml field 'agents' must be a table",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert (tmp_path / "config.toml").read_bytes() == config_document


def test_plan_rejects_a_non_object_hooks_document(tmp_path: Path) -> None:
    hooks_document = b"[]\n"
    (tmp_path / "hooks.json").write_bytes(hooks_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == ("hooks.json root must be an object",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert (tmp_path / "hooks.json").read_bytes() == hooks_document


def test_plan_rejects_a_non_object_hooks_field(tmp_path: Path) -> None:
    hooks_document = b'{"hooks": []}\n'
    (tmp_path / "hooks.json").write_bytes(hooks_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == ("hooks.json field 'hooks' must be an object",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert (tmp_path / "hooks.json").read_bytes() == hooks_document


def test_plan_rejects_a_non_array_managed_hook_event(tmp_path: Path) -> None:
    hooks_document = b'{"hooks": {"PreToolUse": {}}}\n'
    (tmp_path / "hooks.json").write_bytes(hooks_document)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == ("hooks.json event 'PreToolUse' must be an array",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
    assert actual.roles_to_add == ()
    assert actual.hook_events_to_add == ()
    assert (tmp_path / "hooks.json").read_bytes() == hooks_document


def test_plan_reports_a_leftover_transaction_journal(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)
    installed = install_user_config(tmp_path, (str(hook_executable),))
    journal = json.loads(installed.manifest_path.read_text())
    journal["state"] = "installing"
    transaction_path = installed.manifest_path.with_name("transaction.json")
    transaction_path.write_text(json.dumps(journal) + "\n")
    installed.manifest_path.unlink()

    actual = plan_user_installation(tmp_path, (str(hook_executable),))

    assert actual.conflicts == (
        "incomplete installation transaction must be rolled back",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_plan_reports_a_held_operation_lock(tmp_path: Path) -> None:
    (tmp_path / "codex-subagent-router" / "operation.lock").mkdir(parents=True)

    actual = plan_user_installation(
        tmp_path,
        (str(tmp_path / "bin" / "codex-subagent-router-hook"),),
    )

    assert actual.conflicts == ("another installation operation is in progress",)
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_plan_reports_an_unhealthy_existing_receipt(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)
    installed = install_user_config(tmp_path, (str(hook_executable),))
    installed.manifest_path.write_text("{}\n")

    actual = plan_user_installation(tmp_path, (str(hook_executable),))

    assert actual.conflicts == (
        "existing installation state is not healthy: installation manifest is invalid",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_plan_requires_rollback_before_a_different_reinstall(tmp_path: Path) -> None:
    first_executable = _hook_executable(tmp_path)
    install_user_config(tmp_path, (str(first_executable),))
    second_executable = tmp_path / "bin" / "replacement-hook"
    second_executable.write_text("#!/bin/sh\n")
    second_executable.chmod(0o755)

    actual = plan_user_installation(tmp_path, (str(second_executable),))

    assert actual.conflicts == (
        "existing installation differs from the requested configuration; "
        "roll it back before reinstalling",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED


def test_plan_reports_a_missing_hook_launcher(tmp_path: Path) -> None:
    missing_executable = tmp_path / "bin" / "codex-subagent-router-hook"

    actual = plan_user_installation(tmp_path, (str(missing_executable),))

    assert actual.conflicts == (
        f"hook executable is not an executable file: {missing_executable}",
    )
    assert actual.config_action is InstallationFileAction.UNCHANGED
    assert actual.hooks_action is InstallationFileAction.UNCHANGED
