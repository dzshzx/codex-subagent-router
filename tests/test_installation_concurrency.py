import contextlib
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from codex_subagent_router import (
    InstallationState,
    InstallationViolation,
    install_user_config,
    installation_status,
    rollback_user_config,
)

_EXTERNAL_EDIT = b'{"hooks": {"user-edit": []}}\n'

_EDITOR_SCRIPT = """\
import sys
import time
from pathlib import Path

journal = Path(sys.argv[1])
manifest = Path(sys.argv[2])
hooks = Path(sys.argv[3])
ready = Path(sys.argv[4])
ready.touch()
deadline = time.monotonic() + 30.0
while time.monotonic() < deadline:
    if journal.exists() or manifest.exists():
        hooks.write_bytes(b'{"hooks": {"user-edit": []}}\\n')
        sys.exit(0)
sys.exit(1)
"""


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


def test_external_hooks_edit_survives_a_concurrent_install(tmp_path: Path) -> None:
    hook_executable = _hook_executable(tmp_path)
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    config_path.write_bytes(b'model = "gpt-5.6"\n' + b"# padding\n" * 400_000)
    hooks_path.write_bytes(b'{"hooks": {}}\n')
    state_directory = tmp_path / "codex-subagent-router"
    ready_path = tmp_path / "editor-ready"
    editor = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _EDITOR_SCRIPT,
            str(state_directory / "transaction.json"),
            str(state_directory / "installation.json"),
            str(hooks_path),
            str(ready_path),
        ]
    )
    try:
        deadline = time.monotonic() + 10.0
        while not ready_path.exists():
            assert time.monotonic() < deadline, "editor process did not start"
            time.sleep(0.001)
        with contextlib.suppress(InstallationViolation):
            install_user_config(tmp_path, (str(hook_executable),))
        editor_exit = editor.wait(timeout=30)
    finally:
        if editor.poll() is None:
            editor.kill()
            editor.wait()

    assert editor_exit == 0
    assert hooks_path.read_bytes() == _EXTERNAL_EDIT


def test_aborted_install_restores_config_and_reports_not_installed(
    tmp_path: Path,
) -> None:
    hook_executable = _hook_executable(tmp_path)
    config_path = tmp_path / "config.toml"
    hooks_path = tmp_path / "hooks.json"
    original_config = b'model = "gpt-5.6"\n' + b"# padding\n" * 400_000
    config_path.write_bytes(original_config)
    hooks_path.write_bytes(b'{"hooks": {}}\n')
    state_directory = tmp_path / "codex-subagent-router"
    ready_path = tmp_path / "editor-ready"
    editor = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _EDITOR_SCRIPT,
            str(state_directory / "transaction.json"),
            str(state_directory / "installation.json"),
            str(hooks_path),
            str(ready_path),
        ]
    )
    try:
        deadline = time.monotonic() + 10.0
        while not ready_path.exists():
            assert time.monotonic() < deadline, "editor process did not start"
            time.sleep(0.001)
        denied = False
        try:
            install_user_config(tmp_path, (str(hook_executable),))
        except InstallationViolation:
            denied = True
        editor.wait(timeout=30)
    finally:
        if editor.poll() is None:
            editor.kill()
            editor.wait()

    if denied:
        assert config_path.read_bytes() == original_config
        assert installation_status(tmp_path).state is InstallationState.NOT_INSTALLED
    else:
        assert installation_status(tmp_path).state in (
            InstallationState.INSTALLED,
            InstallationState.MODIFIED,
        )


def test_install_recovery_fails_closed_on_external_edits(tmp_path: Path) -> None:
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    transaction_path = _convert_receipt_to_install_journal(installed.manifest_path)
    config_bytes = installed.config_path.read_bytes()
    installed.hooks_path.write_bytes(_EXTERNAL_EDIT)

    with pytest.raises(
        InstallationViolation,
        match="incomplete transaction has user modifications: hooks.json",
    ):
        rollback_user_config(tmp_path)

    assert installed.hooks_path.read_bytes() == _EXTERNAL_EDIT
    assert installed.config_path.read_bytes() == config_bytes
    assert transaction_path.exists()
    assert installation_status(tmp_path).state is InstallationState.INCOMPLETE


def test_rollback_resume_fails_closed_on_external_edits(tmp_path: Path) -> None:
    installed = install_user_config(tmp_path, (str(_hook_executable(tmp_path)),))
    config_before = installed.config_path.read_bytes()
    hooks_before = installed.hooks_path.read_bytes()
    transaction_path = installed.manifest_path.with_name("transaction.json")
    transaction_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "rolling-back",
                "rollback": {
                    "config": {
                        "action": "removed",
                        "before_sha256": hashlib.sha256(config_before).hexdigest(),
                        "target_bytes": None,
                        "target_mode": None,
                    },
                    "hooks": {
                        "action": "removed",
                        "before_sha256": hashlib.sha256(hooks_before).hexdigest(),
                        "target_bytes": None,
                        "target_mode": None,
                    },
                },
            }
        )
        + "\n"
    )
    installed.hooks_path.write_bytes(_EXTERNAL_EDIT)

    with pytest.raises(
        InstallationViolation,
        match="rollback transaction has user modifications: hooks.json",
    ):
        rollback_user_config(tmp_path)

    assert installed.config_path.read_bytes() == config_before
    assert installed.hooks_path.read_bytes() == _EXTERNAL_EDIT
    assert transaction_path.exists()
