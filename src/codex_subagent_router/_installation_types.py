"""Value types shared by the public installation seam and private storage."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class InstallationFileAction(StrEnum):
    """A planned user-configuration file action."""

    CREATE = "create"
    UPDATE = "update"
    UNCHANGED = "unchanged"


class InstallationState(StrEnum):
    """Observed state of the managed user configuration."""

    NOT_INSTALLED = "not-installed"
    INSTALLED = "installed"
    MODIFIED = "modified"
    INCOMPLETE = "incomplete"


class RollbackFileAction(StrEnum):
    """A completed rollback action for one user configuration file."""

    REMOVED = "removed"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class InstallationPlan:
    """A read-only description of an installation transition."""

    codex_home: Path
    config_action: InstallationFileAction
    hooks_action: InstallationFileAction
    roles_to_add: tuple[str, ...]
    hook_events_to_add: tuple[str, ...]
    conflicts: tuple[str, ...]
    requires_hook_review: bool
    requires_new_session: bool
    standalone_agent_files_to_preserve: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InstallationUpdatePlan:
    """A read-only description of one installed Hook launcher update."""

    codex_home: Path
    hooks_action: InstallationFileAction
    hook_events_to_update: tuple[str, ...]
    conflicts: tuple[str, ...]
    requires_hook_review: bool
    requires_new_session: bool


@dataclass(frozen=True, slots=True)
class InstallationResult:
    """Paths and follow-up requirements for a completed installation."""

    codex_home: Path
    config_path: Path
    hooks_path: Path
    manifest_path: Path
    requires_hook_review: bool
    requires_new_session: bool


@dataclass(frozen=True, slots=True)
class InstallationStatus:
    """Observed installation state and any actionable details."""

    codex_home: Path
    state: InstallationState
    details: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RollbackResult:
    """User configuration actions completed by a rollback."""

    codex_home: Path
    config_action: RollbackFileAction
    hooks_action: RollbackFileAction


class InstallationViolation(ValueError):
    """Raised when a user configuration cannot be changed safely."""
