import json
from pathlib import Path

from codex_subagent_router import (
    RollbackFileAction,
    RollbackResult,
    install_user_config,
    rollback_user_config,
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
