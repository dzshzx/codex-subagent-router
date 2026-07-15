import base64
import hashlib
import json
from pathlib import Path

from codex_subagent_router import (
    InstallationState,
    RollbackFileAction,
    RollbackResult,
    install_user_config,
    installation_status,
    rollback_user_config,
    update_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def _convert_receipt_to_install_journal(manifest_path: Path) -> Path:
    journal = json.loads(manifest_path.read_text())
    journal["state"] = "installing"
    transaction_path = manifest_path.with_name("transaction.json")
    transaction_path.write_text(json.dumps(journal) + "\n")
    manifest_path.unlink()
    return transaction_path


def _removed_target(content: bytes) -> dict[str, object]:
    return {
        "action": "removed",
        "before_sha256": hashlib.sha256(content).hexdigest(),
        "target_bytes": None,
        "target_mode": None,
    }


def test_install_recovery_accepts_both_created_files_still_missing(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    transaction_path = _convert_receipt_to_install_journal(installed.manifest_path)
    installed.config_path.unlink()
    installed.hooks_path.unlink()

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.UNCHANGED,
        hooks_action=RollbackFileAction.UNCHANGED,
    )
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not transaction_path.parent.exists()


def test_install_recovery_accepts_a_crash_between_file_replacements(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    transaction_path = _convert_receipt_to_install_journal(installed.manifest_path)
    installed.hooks_path.unlink()

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.REMOVED,
        hooks_action=RollbackFileAction.UNCHANGED,
    )
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not transaction_path.parent.exists()


def test_rollback_resumes_after_the_first_file_was_removed(
    tmp_path: Path,
) -> None:
    installed = install_user_config(
        tmp_path,
        (str(_hook_executable(tmp_path)),),
    )
    config_before = installed.config_path.read_bytes()
    hooks_before = installed.hooks_path.read_bytes()
    transaction_path = installed.manifest_path.with_name("transaction.json")
    transaction_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "rolling-back",
                "rollback": {
                    "config": _removed_target(config_before),
                    "hooks": _removed_target(hooks_before),
                },
            }
        )
        + "\n"
    )
    installed.config_path.unlink()

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.REMOVED,
        hooks_action=RollbackFileAction.REMOVED,
    )
    assert not installed.config_path.exists()
    assert not installed.hooks_path.exists()
    assert not installed.manifest_path.exists()
    assert not transaction_path.parent.exists()


def test_update_recovery_restores_the_previous_healthy_installation(
    tmp_path: Path,
) -> None:
    old_hook_executable = _hook_executable(tmp_path)
    installed = install_user_config(tmp_path, (str(old_hook_executable),))
    hooks_before = installed.hooks_path.read_bytes()
    manifest_before = installed.manifest_path.read_bytes()
    hooks_mode = installed.hooks_path.stat().st_mode & 0o7777
    manifest_mode = installed.manifest_path.stat().st_mode & 0o7777
    new_hook_executable = tmp_path / "new-bin" / "codex-subagent-router-hook"
    new_hook_executable.parent.mkdir()
    new_hook_executable.write_text("#!/bin/sh\n")
    new_hook_executable.chmod(0o755)
    update_user_config(tmp_path, (str(new_hook_executable),))
    hooks_after = installed.hooks_path.read_bytes()
    manifest_after = installed.manifest_path.read_bytes()
    installed.manifest_path.write_bytes(manifest_before)
    transaction_path = installed.manifest_path.with_name("transaction.json")
    transaction_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "updating",
                "update": {
                    "hooks": {
                        "before_bytes": base64.b64encode(hooks_before).decode(),
                        "before_mode": hooks_mode,
                        "after_sha256": hashlib.sha256(hooks_after).hexdigest(),
                    },
                    "manifest": {
                        "before_bytes": base64.b64encode(manifest_before).decode(),
                        "before_mode": manifest_mode,
                        "after_sha256": hashlib.sha256(manifest_after).hexdigest(),
                    },
                },
            }
        )
        + "\n"
    )

    actual = rollback_user_config(tmp_path)

    assert actual == RollbackResult(
        codex_home=tmp_path,
        config_action=RollbackFileAction.UNCHANGED,
        hooks_action=RollbackFileAction.UPDATED,
    )
    assert installed.hooks_path.read_bytes() == hooks_before
    assert installed.manifest_path.read_bytes() == manifest_before
    assert installation_status(tmp_path).state is InstallationState.INSTALLED
    assert not transaction_path.exists()
