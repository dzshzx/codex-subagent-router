"""Standalone custom-agent checks for user installation."""

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .roles import role_contracts


class AgentLayer(StrEnum):
    """Configuration layer whose standalone agents are being inspected."""

    USER = "user"
    PROJECT = "project"


@dataclass(frozen=True, slots=True)
class StandaloneAgentInspection:
    """Read-only findings for one active standalone-agent tree."""

    agent_files: tuple[str, ...]
    issues: tuple[str, ...]


def _standalone_agent_files(
    codex_home: Path,
    agents_directory: Path,
    layer: AgentLayer,
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    message_prefix = "project " if layer is AgentLayer.PROJECT else ""
    pending_directories = [agents_directory]
    standalone_files: list[Path] = []
    issues: list[str] = []
    directory_index = 0
    while directory_index < len(pending_directories):
        directory = pending_directories[directory_index]
        directory_index += 1
        relative_directory = directory.relative_to(codex_home).as_posix()
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            issues.append(
                f"{message_prefix}standalone agent directory "
                f"{relative_directory!r} could not be read"
            )
            continue
        for path in entries:
            if path.suffix == ".toml":
                standalone_files.append(path)
            elif path.is_symlink() and path.is_dir():
                relative_path = path.relative_to(codex_home).as_posix()
                issues.append(
                    f"{message_prefix}standalone agent directory "
                    f"{relative_path!r} must not be a symbolic link"
                )
            elif path.is_dir():
                pending_directories.append(path)

    standalone_files.sort(key=lambda path: path.relative_to(codex_home).as_posix())
    return tuple(standalone_files), tuple(issues)


def _inspect_agent_directory(
    root: Path,
    agents_directory: Path,
    layer: AgentLayer,
) -> StandaloneAgentInspection:
    message_prefix = "project " if layer is AgentLayer.PROJECT else ""
    relative_directory = agents_directory.relative_to(root).as_posix()
    if agents_directory.is_symlink():
        return StandaloneAgentInspection(
            agent_files=(),
            issues=(
                f"{message_prefix}standalone agent directory "
                f"{relative_directory!r} must not be a symbolic link",
            ),
        )
    if not agents_directory.exists():
        return StandaloneAgentInspection(agent_files=(), issues=())
    if not agents_directory.is_dir():
        return StandaloneAgentInspection(
            agent_files=(),
            issues=(
                f"{message_prefix}standalone agent directory "
                f"{relative_directory!r} must be a directory",
            ),
        )

    managed_roles = {contract.agent_type for contract in role_contracts()}
    standalone_files, directory_issues = _standalone_agent_files(
        root,
        agents_directory,
        layer,
    )
    agent_files = tuple(path.relative_to(root).as_posix() for path in standalone_files)
    issues = list(directory_issues)
    for path in standalone_files:
        relative_path = path.relative_to(root).as_posix()
        if path.is_symlink():
            issues.append(
                f"{message_prefix}standalone agent file {relative_path!r} "
                "must not be a symbolic link"
            )
            continue
        if not path.is_file():
            issues.append(
                f"{message_prefix}standalone agent file {relative_path!r} "
                "must be a regular file"
            )
            continue
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError:
            issues.append(
                f"{message_prefix}standalone agent file {relative_path!r} "
                "could not be read"
            )
            continue
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            issues.append(
                f"{message_prefix}standalone agent file {relative_path!r} "
                "is not valid TOML"
            )
            continue
        name = document.get("name")
        if not isinstance(name, str) or not name.strip():
            issues.append(
                f"{message_prefix}standalone agent file {relative_path!r} field "
                "'name' must be a non-empty string"
            )
            continue
        invalid_required_field = next(
            (
                field_name
                for field_name in ("description", "developer_instructions")
                if not isinstance(document.get(field_name), str)
                or not document[field_name].strip()
            ),
            None,
        )
        if invalid_required_field is not None:
            issues.append(
                f"{message_prefix}standalone agent file {relative_path!r} field "
                f"{invalid_required_field!r} must be a non-empty string"
            )
            continue
        normalized_name = name.strip()
        if normalized_name in managed_roles:
            if layer is AgentLayer.PROJECT:
                issues.append(
                    f"{message_prefix}standalone agent file {relative_path!r} "
                    f"declares managed role {normalized_name!r} and shadows the "
                    "user-level router role; change its declared name or move it "
                    "out of the active project agents directory"
                )
            else:
                issues.append(
                    f"standalone agent file {relative_path!r} declares managed "
                    f"role {normalized_name!r}; change its declared name or move "
                    "it out of the active agents directory before installation; "
                    "the installer will leave the file unchanged"
                )
    return StandaloneAgentInspection(
        agent_files=agent_files,
        issues=tuple(issues),
    )


def inspect_standalone_agents(codex_home: Path) -> StandaloneAgentInspection:
    """Inspect active standalone agents without taking ownership of them."""
    return _inspect_agent_directory(
        codex_home,
        codex_home / "agents",
        AgentLayer.USER,
    )


def inspect_project_agents(project_directory: Path) -> StandaloneAgentInspection:
    """Inspect one project's active standalone agents without writing it."""
    if not project_directory.exists():
        return StandaloneAgentInspection(
            agent_files=(),
            issues=("project directory does not exist",),
        )
    if not project_directory.is_dir():
        return StandaloneAgentInspection(
            agent_files=(),
            issues=("project directory must be a directory",),
        )
    codex_directory = project_directory / ".codex"
    if codex_directory.is_symlink():
        return StandaloneAgentInspection(
            agent_files=(),
            issues=("project Codex directory '.codex' must not be a symbolic link",),
        )
    if codex_directory.exists() and not codex_directory.is_dir():
        return StandaloneAgentInspection(
            agent_files=(),
            issues=("project Codex directory '.codex' must be a directory",),
        )
    return _inspect_agent_directory(
        project_directory,
        codex_directory / "agents",
        AgentLayer.PROJECT,
    )
