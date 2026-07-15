"""Private update journaling, validation, and recovery."""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ._installation_files import (
    file_target_violation,
    guarded_replace,
    is_valid_mode,
    is_valid_sha256,
    sha256,
)
from ._installation_types import InstallationViolation, RollbackFileAction


@dataclass(frozen=True, slots=True)
class UpdateRecoveryTarget:
    before: bytes
    before_mode: int
    after_sha256: str


def update_journal_document(
    hooks_before: bytes,
    hooks_mode: int,
    hooks_after: bytes,
    manifest_before: bytes,
    manifest_mode: int,
    manifest_after: bytes,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "state": "updating",
        "update": {
            "hooks": _target_document(hooks_before, hooks_mode, hooks_after),
            "manifest": _target_document(
                manifest_before,
                manifest_mode,
                manifest_after,
            ),
        },
    }


def parse_update_recovery_targets(
    journal: dict[str, object],
) -> tuple[UpdateRecoveryTarget, UpdateRecoveryTarget]:
    try:
        if journal.get("schema_version") != 1:
            raise ValueError
        if journal.get("state") != "updating":
            raise ValueError
        update = cast(dict[str, object], journal["update"])
        return (
            _parse_target(cast(dict[str, object], update["hooks"])),
            _parse_target(cast(dict[str, object], update["manifest"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise InstallationViolation(
            "installation update transaction journal is invalid"
        ) from error


def update_recovery_action(
    path: Path,
    target: UpdateRecoveryTarget,
) -> RollbackFileAction:
    _validate_target(path, target)
    return (
        RollbackFileAction.UNCHANGED
        if path.read_bytes() == target.before
        else RollbackFileAction.UPDATED
    )


def apply_update_recovery_target(
    path: Path,
    target: UpdateRecoveryTarget,
) -> None:
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    if not path.exists():
        raise InstallationViolation(
            f"installation update transaction has a missing user file: {path.name}"
        )
    current = path.read_bytes()
    if current == target.before:
        return
    if sha256(current) != target.after_sha256:
        raise InstallationViolation(
            f"installation update transaction has user modifications: {path.name}"
        )
    guarded_replace(path, current, target.before, target.before_mode)


def _validate_target(path: Path, target: UpdateRecoveryTarget) -> None:
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    if not path.exists():
        raise InstallationViolation(
            f"installation update transaction has a missing user file: {path.name}"
        )
    current = path.read_bytes()
    if current != target.before and sha256(current) != target.after_sha256:
        raise InstallationViolation(
            f"installation update transaction has user modifications: {path.name}"
        )


def _target_document(before: bytes, mode: int, after: bytes) -> dict[str, object]:
    return {
        "before_bytes": base64.b64encode(before).decode("ascii"),
        "before_mode": mode,
        "after_sha256": sha256(after),
    }


def _parse_target(document: dict[str, object]) -> UpdateRecoveryTarget:
    encoded_before = document["before_bytes"]
    before_mode = document["before_mode"]
    after_sha256 = document["after_sha256"]
    if (
        not isinstance(encoded_before, str)
        or not is_valid_mode(before_mode)
        or not is_valid_sha256(after_sha256)
    ):
        raise ValueError
    before = base64.b64decode(encoded_before, validate=True)
    return UpdateRecoveryTarget(
        before=before,
        before_mode=cast(int, before_mode),
        after_sha256=cast(str, after_sha256),
    )
