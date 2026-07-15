"""Private planning, application, journaling, and recovery for updates."""

import base64
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ._installation_files import (
    atomic_write,
    file_target_violation,
    guarded_replace,
    installation_manifest_is_valid,
    installation_modifications,
    installation_snapshot_is_healthy,
    installed_hooks_sha256,
    is_valid_mode,
    is_valid_sha256,
    json_document,
    managed_hook_groups,
    sha256,
    target_mode,
    validate_hook_command,
)
from ._installation_types import (
    InstallationFileAction,
    InstallationUpdatePlan,
    InstallationViolation,
    RollbackFileAction,
    RollbackResult,
)


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    path: Path
    content: bytes
    mode: int


@dataclass(frozen=True, slots=True)
class HookUpdateSnapshots:
    hooks: FileSnapshot
    manifest: FileSnapshot


@dataclass(frozen=True, slots=True)
class FileTransition:
    before: FileSnapshot
    after: bytes


@dataclass(frozen=True, slots=True)
class UpdateRecoveryTarget:
    before: bytes
    before_mode: int
    after_sha256: str


def blocked_update_plan(
    codex_home: Path,
    conflict: str,
    *additional_conflicts: str,
) -> InstallationUpdatePlan:
    return InstallationUpdatePlan(
        codex_home=codex_home,
        hooks_action=InstallationFileAction.UNCHANGED,
        hook_events_to_update=(),
        conflicts=(conflict, *additional_conflicts),
        requires_hook_review=True,
        requires_new_session=True,
    )


def plan_hook_launcher_update(
    codex_home: Path,
    hook_command: tuple[str, ...],
    manifest: dict[str, object],
) -> InstallationUpdatePlan:
    try:
        validate_hook_command(hook_command)
        hooks_manifest = cast(dict[str, object], manifest["hooks"])
        managed_groups = cast(dict[str, list[object]], hooks_manifest["managed_groups"])
        expected_groups = cast(
            dict[str, list[object]], hooks_manifest["expected_groups"]
        )
    except (KeyError, TypeError):
        return blocked_update_plan(codex_home, "installation manifest is invalid")
    except InstallationViolation as violation:
        return blocked_update_plan(codex_home, str(violation))
    desired_groups = managed_hook_groups(hook_command)
    if desired_groups == expected_groups:
        return InstallationUpdatePlan(
            codex_home=codex_home,
            hooks_action=InstallationFileAction.UNCHANGED,
            hook_events_to_update=(),
            conflicts=(),
            requires_hook_review=False,
            requires_new_session=False,
        )
    if managed_groups != expected_groups:
        return blocked_update_plan(
            codex_home,
            "Hook launcher update would modify user-owned compatible hook groups",
        )
    if not _hook_groups_differ_only_in_commands(expected_groups, desired_groups):
        return blocked_update_plan(
            codex_home,
            "installed Hook specification requires an explicit migration",
        )
    return InstallationUpdatePlan(
        codex_home=codex_home,
        hooks_action=InstallationFileAction.UPDATE,
        hook_events_to_update=tuple(desired_groups),
        conflicts=(),
        requires_hook_review=True,
        requires_new_session=True,
    )


def capture_hook_update_snapshots(
    codex_home: Path,
    manifest_path: Path,
) -> HookUpdateSnapshots:
    return HookUpdateSnapshots(
        hooks=_capture_file(codex_home / "hooks.json"),
        manifest=_capture_file(manifest_path),
    )


def apply_hook_launcher_update(
    codex_home: Path,
    hook_command: tuple[str, ...],
    snapshots: HookUpdateSnapshots,
    transaction_path: Path,
) -> None:
    try:
        manifest_document = json.loads(snapshots.manifest.content)
        if not isinstance(manifest_document, dict):
            raise TypeError
        manifest = cast(dict[str, object], manifest_document)
        if not installation_manifest_is_valid(manifest, "installed"):
            raise TypeError
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise InstallationViolation("installation manifest is invalid") from error
    details = installation_modifications(codex_home, manifest)
    if details:
        raise InstallationViolation(
            f"existing installation state is not healthy: {'; '.join(details)}"
        )
    plan = plan_hook_launcher_update(codex_home, hook_command, manifest)
    if plan.conflicts:
        raise InstallationViolation("; ".join(plan.conflicts))
    if plan.hooks_action is InstallationFileAction.UNCHANGED:
        return
    desired_groups = managed_hook_groups(hook_command)
    hooks_manifest = cast(dict[str, object], manifest["hooks"])
    current_groups = cast(dict[str, list[object]], hooks_manifest["managed_groups"])
    hooks_after = _replace_owned_hook_groups(
        snapshots.hooks.content,
        current_groups,
        desired_groups,
    )
    hooks_manifest["managed_groups"] = desired_groups
    hooks_manifest["expected_groups"] = desired_groups
    hooks_manifest["installed_sha256"] = installed_hooks_sha256(
        hooks_manifest,
        desired_groups,
    )
    manifest_after = json_document(manifest)
    hooks_transition = FileTransition(
        before=snapshots.hooks,
        after=hooks_after,
    )
    manifest_transition = FileTransition(
        before=snapshots.manifest,
        after=manifest_after,
    )
    journal = update_journal_document(hooks_transition, manifest_transition)
    try:
        atomic_write(transaction_path, json_document(journal), 0o600)
        _apply_file_transition(hooks_transition)
        _apply_file_transition(manifest_transition)
    except (OSError, InstallationViolation) as error:
        detail = f"installation update transaction failed: {error}"
        try:
            recover_update_transaction(
                codex_home,
                journal,
                snapshots.manifest.path,
                transaction_path,
            )
        except (OSError, InstallationViolation) as recovery_error:
            detail += f"; update recovery failed: {recovery_error}"
        raise InstallationViolation(detail) from error
    try:
        transaction_path.unlink()
    except OSError as error:
        raise InstallationViolation(
            "installation update succeeded but its transaction journal could not "
            f"be removed: {error}"
        ) from error


def recover_update_transaction(
    codex_home: Path,
    journal: dict[str, object],
    manifest_path: Path,
    transaction_path: Path,
) -> RollbackResult:
    hooks_path = codex_home / "hooks.json"
    hooks_target, manifest_target = parse_update_recovery_targets(journal)
    if not installation_snapshot_is_healthy(
        codex_home,
        manifest_target.before,
        manifest_target.before_mode,
        hooks_target.before,
        hooks_target.before_mode,
    ):
        raise InstallationViolation(
            "installation update transaction journal is invalid"
        )
    hooks_action = update_recovery_action(hooks_path, hooks_target)
    update_recovery_action(manifest_path, manifest_target)
    apply_update_recovery_target(manifest_path, manifest_target)
    apply_update_recovery_target(hooks_path, hooks_target)
    try:
        transaction_path.unlink()
    except OSError as error:
        raise InstallationViolation(
            "installation update recovery succeeded but its transaction journal "
            f"could not be removed: {error}"
        ) from error
    return RollbackResult(
        codex_home=codex_home,
        config_action=RollbackFileAction.UNCHANGED,
        hooks_action=hooks_action,
    )


def update_journal_document(
    hooks: FileTransition,
    manifest: FileTransition,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "state": "updating",
        "update": {
            "hooks": _target_document(hooks),
            "manifest": _target_document(manifest),
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
    current = _validated_current(path, target)
    return (
        RollbackFileAction.UNCHANGED
        if current == target.before
        else RollbackFileAction.UPDATED
    )


def apply_update_recovery_target(
    path: Path,
    target: UpdateRecoveryTarget,
) -> None:
    current = _validated_current(path, target)
    if current == target.before:
        return
    guarded_replace(path, current, target.before, target.before_mode)


def _apply_file_transition(transition: FileTransition) -> None:
    guarded_replace(
        transition.before.path,
        transition.before.content,
        transition.after,
        transition.before.mode,
    )


def _capture_file(path: Path) -> FileSnapshot:
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    if not path.exists():
        raise InstallationViolation(f"installation update file is missing: {path.name}")
    return FileSnapshot(path=path, content=path.read_bytes(), mode=target_mode(path))


def _validated_current(path: Path, target: UpdateRecoveryTarget) -> bytes:
    violation = file_target_violation(path)
    if violation is not None:
        raise InstallationViolation(violation)
    if not path.exists():
        raise InstallationViolation(
            f"installation update transaction has a missing user file: {path.name}"
        )
    current = path.read_bytes()
    content_is_expected = (
        current == target.before or sha256(current) == target.after_sha256
    )
    if target_mode(path) != target.before_mode or not content_is_expected:
        raise InstallationViolation(
            f"installation update transaction has user modifications: {path.name}"
        )
    return current


def _replace_owned_hook_groups(
    hooks_before: bytes,
    current_groups: dict[str, list[object]],
    desired_groups: dict[str, list[object]],
) -> bytes:
    try:
        hooks_document = json.loads(hooks_before)
        if not isinstance(hooks_document, dict):
            raise TypeError
        hooks = cast(dict[str, list[object]], hooks_document["hooks"])
        for event_name, old_groups in current_groups.items():
            event_groups = hooks[event_name]
            for old_group, new_group in zip(
                old_groups,
                desired_groups[event_name],
                strict=True,
            ):
                event_groups[event_groups.index(old_group)] = new_group
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError):
        raise InstallationViolation(
            "managed hook groups are missing or modified"
        ) from None
    return json_document(hooks_document)


def _hook_groups_differ_only_in_commands(
    current: dict[str, list[object]],
    desired: dict[str, list[object]],
) -> bool:
    def without_launcher(
        groups: dict[str, list[object]],
    ) -> dict[str, list[object]] | None:
        normalized = cast(
            dict[str, list[object]],
            json.loads(json.dumps(groups)),
        )
        try:
            for event_groups in normalized.values():
                for group in event_groups:
                    hooks = cast(
                        list[object],
                        cast(dict[str, object], group)["hooks"],
                    )
                    for hook in hooks:
                        hook_document = cast(dict[str, object], hook)
                        command = cast(str, hook_document["command"])
                        argv = shlex.split(command)
                        if not argv:
                            return None
                        argv[0] = "<launcher>"
                        hook_document["command"] = shlex.join(argv)
        except (KeyError, TypeError, ValueError):
            return None
        return normalized

    current_without_launcher = without_launcher(current)
    return (
        current_without_launcher is not None
        and current_without_launcher == without_launcher(desired)
    )


def _target_document(transition: FileTransition) -> dict[str, object]:
    return {
        "before_bytes": base64.b64encode(transition.before.content).decode("ascii"),
        "before_mode": transition.before.mode,
        "after_sha256": sha256(transition.after),
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
