"""Private file-format and atomic-write support for user installation."""

import base64
import hashlib
import json
import os
import shlex
import stat
import tempfile
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import cast

from ._installation_types import InstallationViolation
from ._installation_v2 import (
    MULTI_AGENT_V2_MODIFICATION_DETAIL,
    inspect_multi_agent_v2_configuration,
    multi_agent_v2_settings,
    multi_agent_v2_settings_are_exact,
)
from .hook_specs import hook_command_specs
from .roles import role_contracts


def operation_lock_path(installation_directory: Path) -> Path:
    return installation_directory / "operation.lock"


def file_target_violation(path: Path) -> str | None:
    if path.is_symlink():
        return f"{path.name} must not be a symbolic link"
    if path.exists() and not path.is_file():
        return f"{path.name} must be a regular file"
    return None


def installation_state_path_violation(installation_directory: Path) -> str | None:
    if installation_directory.is_symlink():
        return "installation state directory must not be a symbolic link"
    if installation_directory.exists() and not installation_directory.is_dir():
        return "installation state directory must be a directory"
    for name in ("transaction.json", "installation.json"):
        violation = file_target_violation(installation_directory / name)
        if violation is not None:
            return f"installation state file is unsafe: {violation}"
    return None


@contextmanager
def installation_lock(installation_directory: Path) -> Iterator[None]:
    installation_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = operation_lock_path(installation_directory)
    try:
        lock_path.mkdir(mode=0o700)
    except FileExistsError as error:
        raise InstallationViolation(
            "another installation operation is in progress"
        ) from error
    try:
        yield
    finally:
        lock_path.rmdir()
        with suppress(OSError):
            installation_directory.rmdir()


def validate_recoverable_transaction(
    codex_home: Path,
    manifest: dict[str, object],
) -> None:
    for file_name, manifest_key in (
        ("config.toml", "config"),
        ("hooks.json", "hooks"),
    ):
        path = codex_home / file_name
        violation = file_target_violation(path)
        if violation is not None:
            raise InstallationViolation(violation)
        file_manifest = cast(dict[str, object], manifest[manifest_key])
        if not path.exists():
            if cast(bool, file_manifest["created"]):
                continue
            raise InstallationViolation(
                f"incomplete transaction has a missing user file: {file_name}"
            )
        current_hash = sha256(path.read_bytes())
        allowed_hashes = {cast(str, file_manifest["installed_sha256"])}
        encoded_original = file_manifest["original_bytes"]
        if isinstance(encoded_original, str):
            allowed_hashes.add(sha256(base64.b64decode(encoded_original)))
        if current_hash not in allowed_hashes:
            raise InstallationViolation(
                f"incomplete transaction has user modifications: {file_name}"
            )


def installation_manifest_is_valid(
    manifest: dict[str, object],
    expected_state: str,
) -> bool:
    try:
        schema_version = manifest.get("schema_version")
        if type(schema_version) is not int or schema_version not in (1, 2):
            return False
        if manifest.get("state") != expected_state:
            return False
        config = cast(dict[str, object], manifest["config"])
        hooks = cast(dict[str, object], manifest["hooks"])
        if not _file_snapshot_is_valid(config):
            return False
        if not _file_snapshot_is_valid(hooks):
            return False
        managed_block = config["managed_block"]
        separator = config["separator"]
        if not isinstance(managed_block, str):
            return False
        if not isinstance(separator, str):
            return False
        if cast(bool, config["changed"]) != bool(managed_block):
            return False
        if not cast(bool, config["changed"]) and separator:
            return False
        expected_roles = config["expected_roles"]
        if not isinstance(expected_roles, dict) or not all(
            isinstance(name, str) and isinstance(description, str)
            for name, description in expected_roles.items()
        ):
            return False
        if not expected_roles:
            return False
        if schema_version == 2:
            expected_multi_agent_v2 = config["expected_multi_agent_v2"]
            if not multi_agent_v2_settings_are_exact(expected_multi_agent_v2):
                return False
            managed_multi_agent_v2 = config["managed_multi_agent_v2"]
            if type(managed_multi_agent_v2) is not bool:
                return False
            if managed_multi_agent_v2 != ("[features.multi_agent_v2]" in managed_block):
                return False
        if not _config_snapshot_is_consistent(config):
            return False
        managed_groups = hooks["managed_groups"]
        if not _hook_group_map_is_valid(managed_groups):
            return False
        if cast(bool, hooks["changed"]) != bool(managed_groups):
            return False
        expected_groups = hooks["expected_groups"]
        if not _hook_group_map_is_valid(expected_groups):
            return False
        expected_group_map = cast(dict[str, list[object]], expected_groups)
        if not expected_group_map or any(
            not groups for groups in expected_group_map.values()
        ):
            return False
        managed_group_map = cast(dict[str, list[object]], managed_groups)
        if not all(
            event_name in expected_group_map
            and groups
            and all(group in expected_group_map[event_name] for group in groups)
            for event_name, groups in managed_group_map.items()
        ):
            return False
        return _hooks_snapshot_is_consistent(hooks)
    except (KeyError, TypeError, ValueError):
        return False


def _file_snapshot_is_valid(snapshot: dict[str, object]) -> bool:
    try:
        created = snapshot["created"]
        changed = snapshot["changed"]
        original_bytes = snapshot["original_bytes"]
        original_mode = snapshot["original_mode"]
        installed_sha256 = snapshot["installed_sha256"]
    except KeyError:
        return False
    if type(created) is not bool or type(changed) is not bool:
        return False
    if not is_valid_sha256(installed_sha256):
        return False
    if created:
        return changed is True and original_bytes is None and original_mode is None
    if not isinstance(original_bytes, str) or not is_valid_mode(original_mode):
        return False
    try:
        base64.b64decode(original_bytes, validate=True)
    except ValueError:
        return False
    return True


def _config_snapshot_is_consistent(snapshot: dict[str, object]) -> bool:
    original = _original_snapshot_content(snapshot)
    changed = cast(bool, snapshot["changed"])
    managed_block = cast(str, snapshot["managed_block"])
    separator = cast(str, snapshot["separator"])
    if changed:
        if separator.encode() != toml_separator(original):
            return False
        installed = original + separator.encode() + managed_block.encode()
    else:
        installed = original
    if sha256(installed) != snapshot["installed_sha256"]:
        return False
    try:
        document = tomllib.loads(installed.decode())
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return False
    agents = document.get("agents", {})
    expected_roles = cast(dict[str, str], snapshot["expected_roles"])
    roles_are_consistent = isinstance(agents, dict) and all(
        isinstance(agents.get(role_name), dict)
        and agents[role_name].get("description") == description
        and "config_file" not in agents[role_name]
        for role_name, description in expected_roles.items()
    )
    if not roles_are_consistent:
        return False
    if "expected_multi_agent_v2" not in snapshot:
        return True
    multi_agent_v2_is_present, multi_agent_v2_issue = (
        inspect_multi_agent_v2_configuration(document)
    )
    return multi_agent_v2_is_present and multi_agent_v2_issue is None


def _hooks_snapshot_is_consistent(snapshot: dict[str, object]) -> bool:
    original = _original_snapshot_content(snapshot)
    managed_groups = cast(dict[str, list[object]], snapshot["managed_groups"])
    try:
        installed = (
            merge_hook_groups(original, managed_groups)
            if cast(bool, snapshot["changed"])
            else original
        )
        document = json.loads(installed) if installed else {}
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError, TypeError):
        return False
    if sha256(installed) != snapshot["installed_sha256"]:
        return False
    if not isinstance(document, dict):
        return False
    hooks = document.get("hooks", {})
    expected_groups = cast(dict[str, list[object]], snapshot["expected_groups"])
    return isinstance(hooks, dict) and all(
        all(group in hooks.get(event_name, []) for group in groups)
        for event_name, groups in expected_groups.items()
    )


def _original_snapshot_content(snapshot: dict[str, object]) -> bytes:
    encoded = snapshot["original_bytes"]
    if encoded is None:
        return b""
    return base64.b64decode(cast(str, encoded), validate=True)


def _hook_group_map_is_valid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return all(
        isinstance(event_name, str)
        and isinstance(groups, list)
        and all(_hook_group_is_valid(group) for group in groups)
        for event_name, groups in value.items()
    )


def _hook_group_is_valid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    matcher = value.get("matcher")
    hooks = value.get("hooks")
    return (
        isinstance(matcher, str)
        and isinstance(hooks, list)
        and bool(hooks)
        and all(_hook_command_is_valid(hook) for hook in hooks)
    )


def _hook_command_is_valid(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "command"
        and isinstance(value.get("command"), str)
        and bool(value["command"])
        and type(value.get("timeout")) is int
        and cast(int, value["timeout"]) > 0
    )


def is_valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def is_valid_mode(value: object) -> bool:
    return type(value) is int and 0 <= value <= 0o7777


def expected_installed_mode(snapshot: dict[str, object]) -> int:
    if cast(bool, snapshot["created"]):
        return 0o600
    return cast(int, snapshot["original_mode"])


def installation_modifications(
    codex_home: Path,
    manifest: dict[str, object],
) -> list[str]:
    details: list[str] = []
    config_path = codex_home / "config.toml"
    config_manifest = cast(dict[str, object], manifest["config"])
    managed_block = cast(str, config_manifest["managed_block"])
    expected_roles = cast(dict[str, str], config_manifest["expected_roles"])
    config_violation = file_target_violation(config_path)
    if config_violation is not None:
        details.append(config_violation)
    elif not config_path.exists():
        details.append("managed role block is missing or modified")
    else:
        if target_mode(config_path) != expected_installed_mode(config_manifest):
            details.append("config.toml mode is modified")
        try:
            config_text = config_path.read_text(encoding="utf-8")
            config_document = tomllib.loads(config_text)
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            details.append("config.toml is not valid TOML")
        else:
            agents = config_document.get("agents", {})
            roles_are_compatible = isinstance(agents, dict) and all(
                isinstance(agents.get(role_name), dict)
                and agents[role_name].get("description") == description
                and "config_file" not in agents[role_name]
                for role_name, description in expected_roles.items()
            )
            if (managed_block and managed_block not in config_text) or not (
                roles_are_compatible
            ):
                details.append("managed role block is missing or modified")
            if manifest.get("schema_version") == 2:
                multi_agent_v2_is_present, multi_agent_v2_issue = (
                    inspect_multi_agent_v2_configuration(config_document)
                )
                if not multi_agent_v2_is_present or multi_agent_v2_issue is not None:
                    details.append(MULTI_AGENT_V2_MODIFICATION_DETAIL)

    hooks_path = codex_home / "hooks.json"
    hooks_manifest = cast(dict[str, object], manifest["hooks"])
    expected_groups = cast(dict[str, list[object]], hooks_manifest["expected_groups"])
    hooks_violation = file_target_violation(hooks_path)
    if hooks_violation is not None:
        details.append(hooks_violation)
        return details
    if not hooks_path.exists():
        details.append("managed hook groups are missing or modified")
        return details
    if target_mode(hooks_path) != expected_installed_mode(hooks_manifest):
        details.append("hooks.json mode is modified")
    try:
        hooks_document = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        details.append("hooks.json is not valid JSON")
        return details
    if not isinstance(hooks_document, dict):
        details.append("managed hook groups are missing or modified")
        return details
    existing_hooks = hooks_document.get("hooks", {})
    if not isinstance(existing_hooks, dict) or any(
        not all(group in existing_hooks.get(event_name, []) for group in groups)
        for event_name, groups in expected_groups.items()
    ):
        details.append("managed hook groups are missing or modified")
    return details


def launcher_issues(manifest: dict[str, object]) -> list[str]:
    """Report managed hook launchers that are no longer executable files."""
    issues: list[str] = []
    for executable in sorted(_receipt_hook_executables(manifest)):
        path = Path(executable)
        if not (path.is_absolute() and path.is_file() and os.access(path, os.X_OK)):
            issues.append(f"hook launcher is not an executable file: {executable}")
    return issues


def _receipt_hook_executables(manifest: dict[str, object]) -> set[str]:
    hooks_manifest = cast(dict[str, object], manifest["hooks"])
    expected_groups = cast(dict[str, list[object]], hooks_manifest["expected_groups"])
    executables: set[str] = set()
    for groups in expected_groups.values():
        for group in groups:
            hooks = cast(list[object], cast(dict[str, object], group)["hooks"])
            for hook in hooks:
                command = cast(str, cast(dict[str, object], hook)["command"])
                try:
                    argv = shlex.split(command)
                except ValueError:
                    executables.add(command)
                    continue
                if argv:
                    executables.add(argv[0])
    return executables


def validate_hook_command(hook_command: tuple[str, ...]) -> None:
    if not hook_command or not all(part for part in hook_command):
        raise InstallationViolation("hook command must contain non-empty arguments")
    executable = Path(hook_command[0])
    if not executable.is_absolute():
        raise InstallationViolation("hook executable path must be absolute")
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise InstallationViolation(
            f"hook executable is not an executable file: {executable}"
        )


def render_managed_config_block(
    role_names: tuple[str, ...],
    *,
    include_multi_agent_v2: bool,
) -> str:
    contracts = {
        contract.agent_type: contract.description for contract in role_contracts()
    }
    lines = ["# BEGIN codex-subagent-router managed configuration"]
    if include_multi_agent_v2:
        lines.append("[features.multi_agent_v2]")
        lines.extend(
            f"{name} = {json.dumps(value, ensure_ascii=False)}"
            for name, value in multi_agent_v2_settings().items()
        )
        lines.append("")
    for role_name in role_names:
        lines.extend(
            (
                f"[agents.{role_name}]",
                f"description = {json.dumps(contracts[role_name], ensure_ascii=False)}",
                "",
            )
        )
    lines.append("# END codex-subagent-router managed configuration")
    return "\n".join(lines) + "\n"


def toml_separator(existing: bytes) -> bytes:
    if not existing:
        return b""
    separator = b"" if existing.endswith(b"\n\n") else b"\n"
    if not existing.endswith(b"\n"):
        separator = b"\n\n"
    return separator


def managed_hook_groups(
    hook_command: tuple[str, ...],
) -> dict[str, list[object]]:
    groups: dict[str, list[object]] = {}
    for spec in hook_command_specs():
        groups[spec.event_name] = [
            {
                "matcher": spec.matcher,
                "hooks": [
                    {
                        "type": "command",
                        "command": shlex.join((*hook_command, spec.command_name)),
                        "timeout": spec.timeout_seconds,
                    }
                ],
            }
        ]
    return groups


def merge_hook_groups(
    existing: bytes,
    managed_groups: dict[str, list[object]],
) -> bytes:
    document = json.loads(existing) if existing else {}
    hooks = document.setdefault("hooks", {})
    for event_name, groups in managed_groups.items():
        hooks.setdefault(event_name, []).extend(groups)
    return json_document(document)


def json_document(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def encoded_original(content: bytes, existed: bool) -> str | None:
    if not existed:
        return None
    return base64.b64encode(content).decode("ascii")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def target_mode(path: Path) -> int:
    if path.exists():
        return stat.S_IMODE(path.stat().st_mode)
    return 0o600


def atomic_write(path: Path, content: bytes, mode: int) -> None:
    temporary_path = _prepared_replacement(path, content, mode)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def guarded_replace(
    path: Path,
    expected: bytes | None,
    content: bytes,
    mode: int,
) -> None:
    """Replace path atomically only while it still matches the planned snapshot.

    expected is the exact byte snapshot the change was planned against, or
    None when the file must still be absent. POSIX rename cannot exclude
    non-cooperating writers, so the target is re-verified immediately before
    the replacement; a concurrent change fails closed instead of being
    overwritten.
    """
    temporary_path = _prepared_replacement(path, content, mode)
    try:
        require_unmodified(path, expected)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def guarded_remove(path: Path, expected: bytes) -> None:
    """Remove path only while it still matches the planned snapshot."""
    require_unmodified(path, expected)
    path.unlink(missing_ok=True)


def require_unmodified(path: Path, expected: bytes | None) -> None:
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    if expected is None:
        if path.exists():
            raise InstallationViolation(f"{path.name} was created concurrently")
        return
    if not path.exists():
        raise InstallationViolation(f"{path.name} was removed concurrently")
    if path.read_bytes() != expected:
        raise InstallationViolation(f"{path.name} was modified concurrently")


def _prepared_replacement(path: Path, content: bytes, mode: int) -> Path:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path
