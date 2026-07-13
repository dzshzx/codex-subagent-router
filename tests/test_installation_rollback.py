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
