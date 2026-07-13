"""Private rollback planning, journaling, validation, and application."""

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ._installation_files import (
    file_target_violation,
    guarded_remove,
    guarded_replace,
    is_valid_mode,
    is_valid_sha256,
    json_document,
    sha256,
    target_mode,
)
from ._installation_types import InstallationViolation, RollbackFileAction


@dataclass(frozen=True, slots=True)
class RollbackTarget:
    action: RollbackFileAction
    before_sha256: str
    content: bytes | None
    mode: int | None


def plan_config_rollback(
    path: Path,
    manifest: dict[str, object],
) -> RollbackTarget:
    content = path.read_bytes()
    mode = target_mode(path)
    installed = sha256(content) == manifest["installed_sha256"]
    if not cast(bool, manifest["changed"]):
        return RollbackTarget(
            RollbackFileAction.UNCHANGED,
            sha256(content),
            content,
            mode,
        )
    if cast(bool, manifest["created"]) and installed:
        return RollbackTarget(
            RollbackFileAction.REMOVED,
            sha256(content),
            None,
            None,
        )
    if installed:
        return RollbackTarget(
            RollbackFileAction.UPDATED,
            sha256(content),
            _original_content(manifest),
            cast(int, manifest["original_mode"]),
        )
    owned_content = (
        cast(str, manifest["separator"]) + cast(str, manifest["managed_block"])
    ).encode("utf-8")
    if owned_content not in content:
        raise InstallationViolation("managed role block is missing or modified")
    return RollbackTarget(
        RollbackFileAction.UPDATED,
        sha256(content),
        content.replace(owned_content, b"", 1),
        mode,
    )


def plan_install_recovery(
    path: Path,
    manifest: dict[str, object],
) -> RollbackTarget:
    if not path.exists():
        return RollbackTarget(
            RollbackFileAction.UNCHANGED,
            cast(str, manifest["installed_sha256"]),
            None,
            None,
        )
    content = path.read_bytes()
    mode = target_mode(path)
    if sha256(content) != manifest["installed_sha256"]:
        return RollbackTarget(
            RollbackFileAction.UNCHANGED,
            sha256(content),
            content,
            mode,
        )
    if not cast(bool, manifest["changed"]):
        return RollbackTarget(
            RollbackFileAction.UNCHANGED,
            sha256(content),
            content,
            mode,
        )
    if cast(bool, manifest["created"]):
        return RollbackTarget(
            RollbackFileAction.REMOVED,
            sha256(content),
            None,
            None,
        )
    return RollbackTarget(
        RollbackFileAction.UPDATED,
        sha256(content),
        _original_content(manifest),
        cast(int, manifest["original_mode"]),
    )


def plan_hooks_rollback(
    path: Path,
    manifest: dict[str, object],
) -> RollbackTarget:
    content = path.read_bytes()
    mode = target_mode(path)
    installed = sha256(content) == manifest["installed_sha256"]
    if not cast(bool, manifest["changed"]):
        return RollbackTarget(
            RollbackFileAction.UNCHANGED,
            sha256(content),
            content,
            mode,
        )
    if cast(bool, manifest["created"]) and installed:
        return RollbackTarget(
            RollbackFileAction.REMOVED,
            sha256(content),
            None,
            None,
        )
    if installed:
        return RollbackTarget(
            RollbackFileAction.UPDATED,
            sha256(content),
            _original_content(manifest),
            cast(int, manifest["original_mode"]),
        )
    document = json.loads(content)
    hooks = document["hooks"]
    managed_groups = cast(dict[str, list[object]], manifest["managed_groups"])
    try:
        for event_name, groups in managed_groups.items():
            event_groups = hooks[event_name]
            for group in groups:
                event_groups.remove(group)
            if not event_groups:
                del hooks[event_name]
    except (KeyError, TypeError, ValueError) as error:
        raise InstallationViolation(
            "managed hook groups are missing or modified"
        ) from error
    return RollbackTarget(
        RollbackFileAction.UPDATED,
        sha256(content),
        json_document(document),
        mode,
    )


def rollback_journal_document(
    config_target: RollbackTarget,
    hooks_target: RollbackTarget,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "state": "rolling-back",
        "rollback": {
            "config": _rollback_target_document(config_target),
            "hooks": _rollback_target_document(hooks_target),
        },
    }


def parse_rollback_targets(
    journal: dict[str, object],
) -> tuple[RollbackTarget, RollbackTarget]:
    try:
        if journal.get("schema_version") != 1:
            raise ValueError
        if journal.get("state") != "rolling-back":
            raise ValueError
        rollback = cast(dict[str, object], journal["rollback"])
        return (
            _parse_rollback_target(cast(dict[str, object], rollback["config"])),
            _parse_rollback_target(cast(dict[str, object], rollback["hooks"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise InstallationViolation(
            "rollback transaction journal is invalid"
        ) from error


def validate_rollback_target(path: Path, target: RollbackTarget) -> None:
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    if not path.exists():
        if target.content is None:
            return
        raise InstallationViolation(
            f"rollback transaction has a missing user file: {path.name}"
        )
    current_hash = sha256(path.read_bytes())
    allowed_hashes = {target.before_sha256}
    if target.content is not None:
        allowed_hashes.add(sha256(target.content))
    if current_hash not in allowed_hashes:
        raise InstallationViolation(
            f"rollback transaction has user modifications: {path.name}"
        )


def apply_rollback_target(path: Path, target: RollbackTarget) -> None:
    """Apply one rollback target, re-verifying the file at commit time.

    The pre-flight validation and this commit-time check are separated by
    other file operations, so the current content is read again immediately
    before the change; anything that is neither the recorded before-state nor
    the already-applied target fails closed.
    """
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    current = path.read_bytes() if path.exists() else None
    if target.content is None:
        if current is None:
            return
        if sha256(current) != target.before_sha256:
            raise InstallationViolation(
                f"rollback transaction has user modifications: {path.name}"
            )
        guarded_remove(path, current)
        return
    if current == target.content:
        return
    if current is None:
        raise InstallationViolation(
            f"rollback transaction has a missing user file: {path.name}"
        )
    if sha256(current) != target.before_sha256:
        raise InstallationViolation(
            f"rollback transaction has user modifications: {path.name}"
        )
    guarded_replace(path, current, target.content, cast(int, target.mode))


def undo_written_file(
    path: Path,
    original: bytes | None,
    original_mode: int,
    written: bytes,
) -> str | None:
    """Undo one file replacement made by a failed installation transaction.

    Returns a detail string when the file was left untouched because its
    current content is no longer the transaction's own replacement.
    """
    violation = file_target_violation(path)
    if violation is not None:
        return f"{path.name} was left in place: {violation}"
    current = path.read_bytes() if path.exists() else None
    if current == original:
        return None
    if current != written:
        return f"{path.name} was modified concurrently and was left in place"
    try:
        if original is None:
            guarded_remove(path, written)
        else:
            guarded_replace(path, written, original, original_mode)
    except InstallationViolation:
        return f"{path.name} was modified concurrently and was left in place"
    return None


def _original_content(manifest: dict[str, object]) -> bytes:
    return base64.b64decode(cast(str, manifest["original_bytes"]), validate=True)


def _rollback_target_document(target: RollbackTarget) -> dict[str, object]:
    return {
        "action": target.action.value,
        "before_sha256": target.before_sha256,
        "target_bytes": (
            None
            if target.content is None
            else base64.b64encode(target.content).decode("ascii")
        ),
        "target_mode": target.mode,
    }


def _parse_rollback_target(document: dict[str, object]) -> RollbackTarget:
    action = RollbackFileAction(cast(str, document["action"]))
    before_sha256 = document["before_sha256"]
    if not is_valid_sha256(before_sha256):
        raise ValueError
    encoded_content = document["target_bytes"]
    mode = document["target_mode"]
    if encoded_content is None:
        if mode is not None or action is not RollbackFileAction.REMOVED:
            raise ValueError
        content = None
    else:
        if (
            action is RollbackFileAction.REMOVED
            or not isinstance(encoded_content, str)
            or not is_valid_mode(mode)
        ):
            raise ValueError
        content = base64.b64decode(encoded_content, validate=True)
        if action is RollbackFileAction.UNCHANGED and sha256(content) != before_sha256:
            raise ValueError
    return RollbackTarget(
        action=action,
        before_sha256=cast(str, before_sha256),
        content=content,
        mode=cast(int | None, mode),
    )
