"""Planning and state transitions for explicit user-level installation."""

import json
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import cast

from ._installation_agents import (
    inspect_standalone_agents as _inspect_standalone_agents,
)
from ._installation_files import (
    atomic_write as _atomic_write,
)
from ._installation_files import (
    encoded_original as _encoded_original,
)
from ._installation_files import (
    file_target_violation as _file_target_violation,
)
from ._installation_files import (
    guarded_replace as _guarded_replace,
)
from ._installation_files import (
    installation_lock as _installation_lock,
)
from ._installation_files import (
    installation_manifest_has_supported_schema as _installation_manifest_has_supported_schema,
)
from ._installation_files import (
    installation_manifest_is_valid as _installation_manifest_is_valid,
)
from ._installation_files import (
    installation_modifications as _installation_modifications,
)
from ._installation_files import (
    installation_modifications_allow_rollback as _installation_modifications_allow_rollback,
)
from ._installation_files import (
    installation_state_path_violation as _installation_state_path_violation,
)
from ._installation_files import (
    json_document as _json_document,
)
from ._installation_files import (
    launcher_issues as _launcher_issues,
)
from ._installation_files import (
    managed_hook_groups as _managed_hook_groups,
)
from ._installation_files import (
    merge_hook_groups as _merge_hook_groups,
)
from ._installation_files import (
    operation_lock_path as _operation_lock_path,
)
from ._installation_files import (
    render_managed_config_block as _render_managed_config_block,
)
from ._installation_files import (
    sha256 as _sha256,
)
from ._installation_files import (
    target_mode as _target_mode,
)
from ._installation_files import (
    toml_separator as _toml_separator,
)
from ._installation_files import (
    validate_hook_command as _validate_hook_command,
)
from ._installation_files import (
    validate_recoverable_transaction as _validate_recoverable_transaction,
)
from ._installation_rollback import (
    RollbackTarget as _RollbackTarget,
)
from ._installation_rollback import (
    apply_rollback_target as _apply_rollback_target,
)
from ._installation_rollback import (
    parse_rollback_targets as _parse_rollback_targets,
)
from ._installation_rollback import (
    plan_config_rollback as _plan_config_rollback,
)
from ._installation_rollback import (
    plan_hooks_rollback as _plan_hooks_rollback,
)
from ._installation_rollback import (
    plan_install_recovery as _plan_install_recovery,
)
from ._installation_rollback import (
    rollback_journal_document as _rollback_journal_document,
)
from ._installation_rollback import (
    undo_written_file as _undo_written_file,
)
from ._installation_rollback import (
    validate_rollback_target as _validate_rollback_target,
)
from ._installation_types import (
    InstallationFileAction as InstallationFileAction,
)
from ._installation_types import InstallationPlan as InstallationPlan
from ._installation_types import InstallationResult as InstallationResult
from ._installation_types import InstallationState as InstallationState
from ._installation_types import InstallationStatus as InstallationStatus
from ._installation_types import InstallationUpdatePlan as InstallationUpdatePlan
from ._installation_types import (
    InstallationViolation as InstallationViolation,
)
from ._installation_types import RollbackFileAction as RollbackFileAction
from ._installation_types import RollbackResult as RollbackResult
from ._installation_update import (
    apply_hook_launcher_update as _apply_hook_launcher_update,
)
from ._installation_update import blocked_update_plan as _blocked_update_plan
from ._installation_update import (
    capture_hook_update_snapshots as _capture_hook_update_snapshots,
)
from ._installation_update import (
    plan_hook_launcher_update as _plan_hook_launcher_update,
)
from ._installation_update import (
    recover_update_transaction as _recover_update_transaction,
)
from ._installation_v2 import (
    inspect_multi_agent_v2_configuration as _inspect_multi_agent_v2_configuration,
)
from ._installation_v2 import multi_agent_v2_settings as _multi_agent_v2_settings
from .roles import role_contracts

_INSTALLATION_DIRECTORY = "codex-subagent-router"
_MANIFEST_NAME = "installation.json"
_TRANSACTION_NAME = "transaction.json"


def plan_user_installation(
    codex_home: Path,
    hook_command: tuple[str, ...],
) -> InstallationPlan:
    """Plan installation into one explicit Codex home without writing files."""
    standalone_inspection = _inspect_standalone_agents(codex_home)
    standalone_files = standalone_inspection.files_to_preserve

    def blocked_plan(
        conflict: str,
        *additional_conflicts: str,
    ) -> InstallationPlan:
        return _blocked_plan(
            codex_home,
            conflict,
            *additional_conflicts,
            standalone_agent_files_to_preserve=standalone_files,
        )

    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    state_violation = _installation_state_path_violation(installation_directory)
    if state_violation is not None:
        return blocked_plan(state_violation)
    lock_path = _operation_lock_path(installation_directory)
    if lock_path.exists() or lock_path.is_symlink():
        return blocked_plan("another installation operation is in progress")
    if (installation_directory / _TRANSACTION_NAME).exists():
        return blocked_plan(
            "incomplete installation transaction must be rolled back",
        )
    manifest_path = installation_directory / _MANIFEST_NAME
    has_healthy_installation = False
    if manifest_path.is_file():
        status = _installation_status_without_lock(codex_home)
        if status.state is not InstallationState.INSTALLED:
            detail = "; ".join(status.details) if status.details else status.state.value
            return blocked_plan(
                f"existing installation state is not healthy: {detail}",
            )
        has_healthy_installation = True
    config_path = codex_home / "config.toml"
    hooks_path = codex_home / "hooks.json"
    violation = _first_target_violation(config_path, hooks_path)
    if violation is not None:
        return blocked_plan(violation)
    if standalone_inspection.issues:
        return blocked_plan(
            standalone_inspection.issues[0],
            *standalone_inspection.issues[1:],
        )
    plan = replace(
        _plan_from_snapshots(
            codex_home,
            hook_command,
            _snapshot(config_path),
            _snapshot(hooks_path),
        ),
        standalone_agent_files_to_preserve=standalone_files,
    )
    if has_healthy_installation and (
        plan.conflicts
        or plan.config_action is not InstallationFileAction.UNCHANGED
        or plan.hooks_action is not InstallationFileAction.UNCHANGED
    ):
        return blocked_plan(
            "existing installation differs from the requested configuration; "
            "roll it back before reinstalling",
        )
    # install validates the hook command after its conflict checks; mirror
    # that order so plan surfaces the same blocker instead of a clean plan.
    if not plan.conflicts:
        try:
            _validate_hook_command(hook_command)
        except InstallationViolation as violation:
            return blocked_plan(str(violation))
    return plan


def _first_target_violation(*paths: Path) -> str | None:
    for path in paths:
        violation = _file_target_violation(path)
        if violation is not None:
            return violation
    return None


def _snapshot(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def _plan_from_snapshots(
    codex_home: Path,
    hook_command: tuple[str, ...],
    config_snapshot: bytes | None,
    hooks_snapshot: bytes | None,
) -> InstallationPlan:
    """Derive the plan from the exact snapshots a transaction commits against."""
    config: dict[str, object] = {}
    existing_roles: dict[str, object] = {}
    if config_snapshot is not None:
        try:
            config = tomllib.loads(config_snapshot.decode("utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            return _blocked_plan(codex_home, "config.toml is not valid TOML")
        agents = config.get("agents")
        if agents is not None and not isinstance(agents, dict):
            return _blocked_plan(
                codex_home,
                "config.toml field 'agents' must be a table",
            )
        if isinstance(agents, dict):
            existing_roles = cast(dict[str, object], agents)
    multi_agent_v2_is_present, multi_agent_v2_issue = (
        _inspect_multi_agent_v2_configuration(config)
    )
    if multi_agent_v2_issue is not None:
        return _blocked_plan(codex_home, multi_agent_v2_issue)
    roles_to_add: list[str] = []
    conflicts: list[str] = []
    for contract in role_contracts():
        if contract.agent_type not in existing_roles:
            roles_to_add.append(contract.agent_type)
            continue
        existing_role = existing_roles[contract.agent_type]
        if (
            isinstance(existing_role, dict)
            and existing_role.get("description") == contract.description
            and "config_file" not in existing_role
        ):
            continue
        conflicts.append(
            f"managed role {contract.agent_type!r} already exists with "
            "incompatible configuration"
        )
    config_needs_update = bool(roles_to_add or not multi_agent_v2_is_present)
    if config_needs_update:
        original = config_snapshot if config_snapshot is not None else b""
        managed_block = _render_managed_config_block(
            tuple(roles_to_add),
            include_multi_agent_v2=not multi_agent_v2_is_present,
        )
        candidate = original + _toml_separator(original) + managed_block.encode()
        try:
            tomllib.loads(candidate.decode("utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            return _blocked_plan(
                codex_home,
                "config.toml cannot be safely extended with managed configuration",
            )
    managed_hook_groups = _managed_hook_groups(hook_command)
    hook_events_to_add = list(managed_hook_groups)
    if hooks_snapshot is not None:
        try:
            hooks_document = json.loads(hooks_snapshot.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _blocked_plan(codex_home, "hooks.json is not valid JSON")
        if not isinstance(hooks_document, dict):
            return _blocked_plan(codex_home, "hooks.json root must be an object")
        existing_hooks = hooks_document.get("hooks", {})
        if not isinstance(existing_hooks, dict):
            return _blocked_plan(
                codex_home,
                "hooks.json field 'hooks' must be an object",
            )
        for event_name in managed_hook_groups:
            event_groups = existing_hooks.get(event_name, [])
            if not isinstance(event_groups, list):
                return _blocked_plan(
                    codex_home,
                    f"hooks.json event {event_name!r} must be an array",
                )
        hook_events_to_add = []
        for event_name, groups in managed_hook_groups.items():
            event_groups = cast(list[object], existing_hooks.get(event_name, []))
            if all(group in event_groups for group in groups):
                continue
            managed_group = cast(dict[str, object], groups[0])
            matcher = managed_group["matcher"]
            if any(
                isinstance(existing_group, dict)
                and existing_group.get("matcher") == matcher
                for existing_group in event_groups
            ):
                conflicts.append(
                    f"managed hook event {event_name!r} matcher already exists "
                    "with incompatible configuration"
                )
                continue
            hook_events_to_add.append(event_name)
    return InstallationPlan(
        codex_home=codex_home,
        config_action=(
            (
                InstallationFileAction.UPDATE
                if config_snapshot is not None
                else InstallationFileAction.CREATE
            )
            if config_needs_update
            else InstallationFileAction.UNCHANGED
        ),
        hooks_action=(
            (
                InstallationFileAction.UPDATE
                if hooks_snapshot is not None
                else InstallationFileAction.CREATE
            )
            if hook_events_to_add
            else InstallationFileAction.UNCHANGED
        ),
        roles_to_add=tuple(roles_to_add),
        hook_events_to_add=tuple(hook_events_to_add),
        conflicts=tuple(conflicts),
        requires_hook_review=True,
        requires_new_session=True,
    )


def _blocked_plan(
    codex_home: Path,
    conflict: str,
    *additional_conflicts: str,
    standalone_agent_files_to_preserve: tuple[str, ...] = (),
) -> InstallationPlan:
    return InstallationPlan(
        codex_home=codex_home,
        config_action=InstallationFileAction.UNCHANGED,
        hooks_action=InstallationFileAction.UNCHANGED,
        roles_to_add=(),
        hook_events_to_add=(),
        conflicts=(conflict, *additional_conflicts),
        requires_hook_review=True,
        requires_new_session=True,
        standalone_agent_files_to_preserve=standalone_agent_files_to_preserve,
    )


def plan_user_update(
    codex_home: Path,
    hook_command: tuple[str, ...],
) -> InstallationUpdatePlan:
    """Plan an owned Hook launcher update without writing user files."""
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    state_violation = _installation_state_path_violation(installation_directory)
    if state_violation is not None:
        return _blocked_update_plan(codex_home, state_violation)
    lock_path = _operation_lock_path(installation_directory)
    if lock_path.exists() or lock_path.is_symlink():
        return _blocked_update_plan(
            codex_home,
            "another installation operation is in progress",
        )
    return _plan_user_update_without_lock(codex_home, hook_command)


def _plan_user_update_without_lock(
    codex_home: Path,
    hook_command: tuple[str, ...],
    manifest_snapshot: bytes | None = None,
) -> InstallationUpdatePlan:
    standalone_inspection = _inspect_standalone_agents(codex_home)
    if standalone_inspection.issues:
        return _blocked_update_plan(
            codex_home,
            standalone_inspection.issues[0],
            *standalone_inspection.issues[1:],
        )
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    transaction_path = installation_directory / _TRANSACTION_NAME
    if transaction_path.exists() or transaction_path.is_symlink():
        return _blocked_update_plan(
            codex_home,
            "incomplete installation transaction must be rolled back",
        )
    manifest_path = installation_directory / _MANIFEST_NAME
    if not manifest_path.is_file():
        return _blocked_update_plan(codex_home, "installation is not installed")
    if _target_mode(manifest_path) != 0o600:
        return _blocked_update_plan(
            codex_home,
            "installation manifest mode is modified",
        )
    status = _installation_status_without_lock(codex_home)
    if status.state is not InstallationState.INSTALLED:
        detail = "; ".join(status.details) if status.details else status.state.value
        return _blocked_update_plan(
            codex_home,
            f"existing installation state is not healthy: {detail}",
        )
    try:
        manifest_document = json.loads(
            manifest_snapshot
            if manifest_snapshot is not None
            else manifest_path.read_bytes()
        )
        if not isinstance(manifest_document, dict):
            raise TypeError
        manifest = cast(dict[str, object], manifest_document)
        if manifest.get("schema_version") != 2:
            return _blocked_update_plan(
                codex_home,
                "installed receipt must be rolled back before update",
            )
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, TypeError):
        return _blocked_update_plan(codex_home, "installation manifest is invalid")
    return _plan_hook_launcher_update(codex_home, hook_command, manifest)


def update_user_config(
    codex_home: Path,
    hook_command: tuple[str, ...],
) -> InstallationResult:
    """Update receipt-owned Hook launchers in one explicit Codex home."""
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    violation = _installation_state_path_violation(installation_directory)
    if violation is not None:
        raise InstallationViolation(violation)
    with _installation_lock(installation_directory):
        plan = _plan_user_update_without_lock(codex_home, hook_command)
        if plan.conflicts:
            raise InstallationViolation("; ".join(plan.conflicts))
        manifest_path = installation_directory / _MANIFEST_NAME
        snapshots = _capture_hook_update_snapshots(codex_home, manifest_path)
        plan = _plan_user_update_without_lock(
            codex_home,
            hook_command,
            snapshots.manifest.content,
        )
        if plan.conflicts:
            raise InstallationViolation("; ".join(plan.conflicts))
        result = InstallationResult(
            codex_home=codex_home,
            config_path=codex_home / "config.toml",
            hooks_path=codex_home / "hooks.json",
            manifest_path=manifest_path,
            requires_hook_review=plan.requires_hook_review,
            requires_new_session=plan.requires_new_session,
        )
        if plan.hooks_action is InstallationFileAction.UNCHANGED:
            return result
        _apply_hook_launcher_update(
            codex_home,
            hook_command,
            snapshots,
            installation_directory / _TRANSACTION_NAME,
        )
        return result


def install_user_config(
    codex_home: Path,
    hook_command: tuple[str, ...],
) -> InstallationResult:
    """Install managed roles and hooks into one explicit Codex home."""
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    violation = _installation_state_path_violation(installation_directory)
    if violation is not None:
        raise InstallationViolation(violation)
    with _installation_lock(installation_directory):
        return _install_user_config_locked(codex_home, hook_command)


def _install_user_config_locked(
    codex_home: Path,
    hook_command: tuple[str, ...],
) -> InstallationResult:
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    transaction_path = installation_directory / _TRANSACTION_NAME
    manifest_path = installation_directory / _MANIFEST_NAME
    if transaction_path.exists():
        raise InstallationViolation(
            "incomplete installation transaction must be rolled back"
        )
    if manifest_path.is_file():
        status = _installation_status_without_lock(codex_home)
        if status.state is not InstallationState.INSTALLED:
            detail = "; ".join(status.details) if status.details else status.state.value
            raise InstallationViolation(
                f"existing installation state is not healthy: {detail}"
            )
    standalone_inspection = _inspect_standalone_agents(codex_home)
    if standalone_inspection.issues:
        raise InstallationViolation("; ".join(standalone_inspection.issues))
    config_path = codex_home / "config.toml"
    hooks_path = codex_home / "hooks.json"
    target_violation = _first_target_violation(config_path, hooks_path)
    if target_violation is not None:
        config_before: bytes | None = None
        hooks_before: bytes | None = None
        plan = _blocked_plan(codex_home, target_violation)
    else:
        config_before = _snapshot(config_path)
        hooks_before = _snapshot(hooks_path)
        plan = _plan_from_snapshots(
            codex_home,
            hook_command,
            config_before,
            hooks_before,
        )
    if manifest_path.is_file() and (
        plan.conflicts
        or plan.config_action is not InstallationFileAction.UNCHANGED
        or plan.hooks_action is not InstallationFileAction.UNCHANGED
    ):
        raise InstallationViolation(
            "existing installation differs from the requested configuration; "
            "roll it back before reinstalling"
        )
    if plan.conflicts:
        raise InstallationViolation("; ".join(plan.conflicts))
    _validate_hook_command(hook_command)

    result = InstallationResult(
        codex_home=codex_home,
        config_path=config_path,
        hooks_path=hooks_path,
        manifest_path=manifest_path,
        requires_hook_review=True,
        requires_new_session=True,
    )
    if (
        plan.config_action is InstallationFileAction.UNCHANGED
        and plan.hooks_action is InstallationFileAction.UNCHANGED
        and manifest_path.exists()
    ):
        return result
    config_existed = config_before is not None
    hooks_existed = hooks_before is not None
    config_original = config_before if config_before is not None else b""
    hooks_original = hooks_before if hooks_before is not None else b""
    config_mode = _target_mode(config_path)
    hooks_mode = _target_mode(hooks_path)
    config_changed = plan.config_action is not InstallationFileAction.UNCHANGED
    hooks_changed = plan.hooks_action is not InstallationFileAction.UNCHANGED
    multi_agent_v2_is_present, _ = _inspect_multi_agent_v2_configuration(
        tomllib.loads(config_original.decode("utf-8")) if config_original else {}
    )
    managed_config_block = (
        _render_managed_config_block(
            plan.roles_to_add,
            include_multi_agent_v2=not multi_agent_v2_is_present,
        )
        if config_changed
        else ""
    )
    config_separator = _toml_separator(config_original) if config_changed else b""
    config_after = (
        config_original + config_separator + managed_config_block.encode("utf-8")
    )
    all_hook_groups = _managed_hook_groups(hook_command)
    expected_roles = {
        contract.agent_type: contract.description for contract in role_contracts()
    }
    hook_groups = {
        event_name: all_hook_groups[event_name]
        for event_name in plan.hook_events_to_add
    }
    hooks_after = (
        _merge_hook_groups(hooks_original, hook_groups)
        if hooks_changed
        else hooks_original
    )
    manifest = {
        "schema_version": 2,
        "state": "installed",
        "config": {
            "created": not config_existed,
            "changed": config_changed,
            "managed_block": managed_config_block,
            "expected_multi_agent_v2": _multi_agent_v2_settings(),
            "managed_multi_agent_v2": not multi_agent_v2_is_present,
            "expected_roles": expected_roles,
            "separator": config_separator.decode(),
            "original_bytes": _encoded_original(config_original, config_existed),
            "original_mode": (config_mode if config_existed else None),
            "installed_sha256": _sha256(config_after),
        },
        "hooks": {
            "created": not hooks_existed,
            "changed": hooks_changed,
            "managed_groups": hook_groups,
            "expected_groups": all_hook_groups,
            "original_bytes": _encoded_original(hooks_original, hooks_existed),
            "original_mode": hooks_mode if hooks_existed else None,
            "installed_sha256": _sha256(hooks_after),
        },
    }
    journal = {**manifest, "state": "installing"}

    config_written = False
    hooks_written = False
    try:
        _atomic_write(transaction_path, _json_document(journal), 0o600)
        if config_changed:
            _guarded_replace(config_path, config_before, config_after, config_mode)
            config_written = True
        if hooks_changed:
            _guarded_replace(hooks_path, hooks_before, hooks_after, hooks_mode)
            hooks_written = True
        _atomic_write(manifest_path, _json_document(manifest), 0o600)
    except (OSError, InstallationViolation) as error:
        preserved = _abort_failed_installation(
            (
                (
                    config_path,
                    config_before,
                    config_mode,
                    config_after if config_written else None,
                ),
                (
                    hooks_path,
                    hooks_before,
                    hooks_mode,
                    hooks_after if hooks_written else None,
                ),
            ),
            manifest_path,
            transaction_path,
        )
        detail = f"installation transaction failed: {error}"
        if preserved:
            detail = (
                detail
                + "; "
                + "; ".join(preserved)
                + "; the transaction journal was preserved for recovery"
            )
        raise InstallationViolation(detail) from error
    try:
        transaction_path.unlink()
    except OSError as error:
        raise InstallationViolation(
            "installation succeeded but its transaction journal could not be "
            f"removed: {error}"
        ) from error
    return result


def _abort_failed_installation(
    written_files: tuple[tuple[Path, bytes | None, int, bytes | None], ...],
    manifest_path: Path,
    transaction_path: Path,
) -> tuple[str, ...]:
    """Undo a failed transaction without overwriting concurrent modifications.

    Returns the files that had to be left in place; the transaction journal
    is kept for recovery exactly when that tuple is not empty.
    """
    details: list[str] = []
    for path, original, original_mode, written in written_files:
        if written is None:
            continue
        try:
            detail = _undo_written_file(path, original, original_mode, written)
        except OSError as error:
            detail = f"{path.name} could not be restored: {error}"
        if detail is not None:
            details.append(detail)
    if details:
        return tuple(details)
    try:
        if manifest_path.is_file():
            manifest_path.unlink()
        if transaction_path.is_file():
            transaction_path.unlink()
    except OSError as error:
        return (f"installation state could not be cleaned up: {error}",)
    return ()


def installation_status(codex_home: Path) -> InstallationStatus:
    """Inspect one explicit Codex home without modifying it."""
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    violation = _installation_state_path_violation(installation_directory)
    if violation is not None:
        return InstallationStatus(
            codex_home=codex_home,
            state=InstallationState.INCOMPLETE,
            details=(violation,),
        )
    lock_path = _operation_lock_path(installation_directory)
    if lock_path.exists() or lock_path.is_symlink():
        return InstallationStatus(
            codex_home=codex_home,
            state=InstallationState.INCOMPLETE,
            details=("installation operation is in progress",),
        )
    status = _installation_status_without_lock(codex_home)
    if status.state not in (InstallationState.INSTALLED, InstallationState.MODIFIED):
        return status
    standalone_inspection = _inspect_standalone_agents(codex_home)
    if not standalone_inspection.issues:
        return status
    return InstallationStatus(
        codex_home=codex_home,
        state=InstallationState.MODIFIED,
        details=(*status.details, *standalone_inspection.issues),
    )


def _installation_status_without_lock(codex_home: Path) -> InstallationStatus:
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    transaction_path = installation_directory / _TRANSACTION_NAME
    manifest_path = installation_directory / _MANIFEST_NAME
    for path in (transaction_path, manifest_path):
        if path.is_symlink():
            return InstallationStatus(
                codex_home=codex_home,
                state=InstallationState.INCOMPLETE,
                details=(f"installation state file is a symbolic link: {path.name}",),
            )
    if transaction_path.exists():
        return InstallationStatus(
            codex_home=codex_home,
            state=InstallationState.INCOMPLETE,
            details=("installation transaction is not complete",),
        )
    if not manifest_path.exists():
        return InstallationStatus(
            codex_home=codex_home,
            state=InstallationState.NOT_INSTALLED,
            details=(),
        )
    try:
        manifest_document = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(
            manifest_document, dict
        ) or not _installation_manifest_has_supported_schema(manifest_document):
            raise TypeError("installation manifest is unsupported")
        manifest = cast(dict[str, object], manifest_document)
        if manifest.get("state") != "installed":
            return InstallationStatus(
                codex_home=codex_home,
                state=InstallationState.INCOMPLETE,
                details=("installation transaction is not complete",),
            )
        if not _installation_manifest_is_valid(manifest, "installed"):
            raise TypeError("installation manifest is invalid")
        details = _installation_modifications(codex_home, manifest)
        launcher_details = _launcher_issues(manifest)
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
        KeyError,
        TypeError,
        AttributeError,
    ):
        return InstallationStatus(
            codex_home=codex_home,
            state=InstallationState.INCOMPLETE,
            details=("installation manifest is invalid",),
        )
    # A launcher that disappeared after installation is an environment
    # problem, not a user modification; it must not block rollback.
    return InstallationStatus(
        codex_home=codex_home,
        state=(InstallationState.MODIFIED if details else InstallationState.INSTALLED),
        details=(*details, *launcher_details),
    )


def rollback_user_config(codex_home: Path) -> RollbackResult:
    """Remove unchanged managed entries while preserving user-owned content."""
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    violation = _installation_state_path_violation(installation_directory)
    if violation is not None:
        raise InstallationViolation(violation)
    for path in (codex_home / "config.toml", codex_home / "hooks.json"):
        violation = _file_target_violation(path)
        if violation is not None:
            raise InstallationViolation(violation)
    with _installation_lock(installation_directory):
        return _rollback_user_config_locked(codex_home)


def _rollback_user_config_locked(codex_home: Path) -> RollbackResult:
    installation_directory = codex_home / _INSTALLATION_DIRECTORY
    manifest_path = installation_directory / _MANIFEST_NAME
    transaction_path = installation_directory / _TRANSACTION_NAME
    if transaction_path.exists():
        try:
            transaction_document = json.loads(
                transaction_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            raise InstallationViolation(
                "installation transaction journal is invalid"
            ) from error
        if not isinstance(transaction_document, dict):
            raise InstallationViolation("installation transaction journal is invalid")
        journal = cast(dict[str, object], transaction_document)
        if journal.get("state") == "updating":
            return _recover_update_transaction(
                codex_home,
                journal,
                manifest_path,
                transaction_path,
            )
        if journal.get("state") == "rolling-back":
            return _resume_rollback_transaction(
                codex_home,
                journal,
                manifest_path,
                transaction_path,
            )
        if not _installation_manifest_is_valid(journal, "installing"):
            raise InstallationViolation("installation transaction journal is invalid")
        try:
            _validate_recoverable_transaction(codex_home, journal)
        except (KeyError, TypeError, AttributeError) as error:
            raise InstallationViolation(
                "installation transaction journal is invalid"
            ) from error
        config_manifest = cast(dict[str, object], journal["config"])
        hooks_manifest = cast(dict[str, object], journal["hooks"])
        config_target = _plan_install_recovery(
            codex_home / "config.toml", config_manifest
        )
        hooks_target = _plan_install_recovery(codex_home / "hooks.json", hooks_manifest)
        return _finish_rollback_transaction(
            codex_home,
            config_target,
            hooks_target,
            manifest_path,
            transaction_path,
        )
    status = _installation_status_without_lock(codex_home)
    if status.state not in (InstallationState.INSTALLED, InstallationState.MODIFIED):
        detail = "; ".join(status.details) if status.details else status.state.value
        raise InstallationViolation(f"installation cannot be rolled back: {detail}")
    manifest = cast(
        dict[str, object],
        json.loads(manifest_path.read_text(encoding="utf-8")),
    )
    config_manifest = cast(dict[str, object], manifest["config"])
    modifications_allow_rollback = (
        status.state is InstallationState.MODIFIED
        and _installation_modifications_allow_rollback(codex_home, manifest)
    )
    if (
        status.state is not InstallationState.INSTALLED
        and not modifications_allow_rollback
    ):
        detail = "; ".join(status.details) if status.details else status.state.value
        raise InstallationViolation(f"installation cannot be rolled back: {detail}")
    config_target = _plan_config_rollback(
        codex_home / "config.toml",
        config_manifest,
    )
    hooks_target = _plan_hooks_rollback(
        codex_home / "hooks.json",
        cast(dict[str, object], manifest["hooks"]),
    )
    try:
        _atomic_write(
            transaction_path,
            _json_document(_rollback_journal_document(config_target, hooks_target)),
            0o600,
        )
    except OSError as error:
        raise InstallationViolation(
            f"rollback transaction could not start: {error}"
        ) from error
    return _finish_rollback_transaction(
        codex_home,
        config_target,
        hooks_target,
        manifest_path,
        transaction_path,
    )


def _resume_rollback_transaction(
    codex_home: Path,
    journal: dict[str, object],
    manifest_path: Path,
    transaction_path: Path,
) -> RollbackResult:
    config_target, hooks_target = _parse_rollback_targets(journal)
    return _finish_rollback_transaction(
        codex_home,
        config_target,
        hooks_target,
        manifest_path,
        transaction_path,
    )


def _finish_rollback_transaction(
    codex_home: Path,
    config_target: _RollbackTarget,
    hooks_target: _RollbackTarget,
    manifest_path: Path,
    transaction_path: Path,
) -> RollbackResult:
    _validate_rollback_target(codex_home / "config.toml", config_target)
    _validate_rollback_target(codex_home / "hooks.json", hooks_target)
    try:
        if config_target.action is not RollbackFileAction.UNCHANGED:
            _apply_rollback_target(codex_home / "config.toml", config_target)
        if hooks_target.action is not RollbackFileAction.UNCHANGED:
            _apply_rollback_target(codex_home / "hooks.json", hooks_target)
        manifest_path.unlink(missing_ok=True)
        transaction_path.unlink(missing_ok=True)
    except OSError as error:
        raise InstallationViolation(
            f"rollback transaction is incomplete: {error}"
        ) from error
    return RollbackResult(
        codex_home=codex_home,
        config_action=config_target.action,
        hooks_action=hooks_target.action,
    )
