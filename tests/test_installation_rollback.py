import json
from pathlib import Path

from codex_subagent_router import (
    RollbackFileAction,
    RollbackResult,
    install_user_config,
    rollback_user_config,
    update_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def test_rollback_preserves_unrelated_changes_made_after_installation(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    installed.config_path.write_text(
        installed.config_path.read_text()
        + '\n[agents.user_owned]\ndescription = "keep me"\n'
    )
    hooks = json.loads(installed.hooks_path.read_text())
    hooks["hooks"]["Stop"] = [{"matcher": "user-owned", "hooks": []}]
    installed.hooks_path.write_text(json.dumps(hooks, indent=2) + "\n")

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.UPDATED,
        hooks_action=RollbackFileAction.UPDATED,
    )
    assert installed.config_path.read_text() == (
        '\n[agents.user_owned]\ndescription = "keep me"\n'
    )
    assert json.loads(installed.hooks_path.read_text()) == {
        "hooks": {"Stop": [{"matcher": "user-owned", "hooks": []}]}
    }
    assert not installed.manifest_path.parent.exists()


def test_rollback_after_update_restores_the_first_installation_snapshot(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    original_config = b'model = "gpt-5.6-sol"\n'
    original_hooks = b'{"description":"user hooks","hooks":{"Stop":[]}}\n'
    config_path.write_bytes(original_config)
    hooks_path.write_bytes(original_hooks)
    config_path.chmod(0o640)
    hooks_path.chmod(0o644)
    old_hook_executable = _hook_executable(tmp_path)
    install_user_config(tmp_path, (str(old_hook_executable),))
    new_hook_executable = tmp_path / "new-bin" / "codex-subagent-router-hook"
    new_hook_executable.parent.mkdir()
    new_hook_executable.write_text("#!/bin/sh\n")
    new_hook_executable.chmod(0o755)
    update_user_config(tmp_path, (str(new_hook_executable),))

    rollback_user_config(tmp_path)

    assert config_path.read_bytes() == original_config
    assert hooks_path.read_bytes() == original_hooks
    assert config_path.stat().st_mode & 0o7777 == 0o640
    assert hooks_path.stat().st_mode & 0o7777 == 0o644
    assert not (tmp_path / "codex-subagent-router").exists()


def test_rollback_preserves_standalone_agent_files(tmp_path: Path) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    standalone_agent = tmp_path / "agents" / "custom-review.toml"
    standalone_agent.parent.mkdir()
    standalone_document = (
        b'name = "reviewer"\n'
        b'description = "User-owned reviewer"\n'
        b'developer_instructions = "Review independently."\n'
    )
    standalone_agent.write_bytes(standalone_document)
    standalone_agent.chmod(0o640)

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.REMOVED,
        hooks_action=RollbackFileAction.REMOVED,
    )
    assert standalone_agent.read_bytes() == standalone_document
    assert standalone_agent.stat().st_mode & 0o7777 == 0o640
    assert standalone_agent.parent.is_dir()
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not installed.manifest_path.parent.exists()
