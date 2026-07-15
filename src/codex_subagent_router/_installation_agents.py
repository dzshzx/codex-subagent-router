"""Standalone custom-agent checks for user installation."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .roles import role_contracts


@dataclass(frozen=True, slots=True)
class StandaloneAgentInspection:
    """Read-only findings for the active user-level standalone agent tree."""

    files_to_preserve: tuple[str, ...]
    issues: tuple[str, ...]


def _standalone_agent_files(
    codex_home: Path,
    agents_directory: Path,
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
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
                f"standalone agent directory {relative_directory!r} could not be read"
            )
            continue
        for path in entries:
            if path.suffix == ".toml":
                standalone_files.append(path)
            elif path.is_symlink() and path.is_dir():
                relative_path = path.relative_to(codex_home).as_posix()
                issues.append(
                    f"standalone agent directory {relative_path!r} must not be "
                    "a symbolic link"
                )
            elif path.is_dir():
                pending_directories.append(path)

    standalone_files.sort(key=lambda path: path.relative_to(codex_home).as_posix())
    return tuple(standalone_files), tuple(issues)


def inspect_standalone_agents(codex_home: Path) -> StandaloneAgentInspection:
    """Inspect active standalone agents without taking ownership of them."""
    agents_directory = codex_home / "agents"
    if agents_directory.is_symlink():
        return StandaloneAgentInspection(
            files_to_preserve=(),
            issues=("standalone agent directory 'agents' must not be a symbolic link",),
        )
    if not agents_directory.exists():
        return StandaloneAgentInspection(files_to_preserve=(), issues=())
    if not agents_directory.is_dir():
        return StandaloneAgentInspection(
            files_to_preserve=(),
            issues=("standalone agent directory 'agents' must be a directory",),
        )

    managed_roles = {contract.agent_type for contract in role_contracts()}
    standalone_files, directory_issues = _standalone_agent_files(
        codex_home,
        agents_directory,
    )
    files_to_preserve = tuple(
        path.relative_to(codex_home).as_posix() for path in standalone_files
    )
    issues = list(directory_issues)
    for path in standalone_files:
        relative_path = path.relative_to(codex_home).as_posix()
        if path.is_symlink():
            issues.append(
                f"standalone agent file {relative_path!r} must not be a symbolic link"
            )
            continue
        if not path.is_file():
            issues.append(
                f"standalone agent file {relative_path!r} must be a regular file"
            )
            continue
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError:
            issues.append(f"standalone agent file {relative_path!r} could not be read")
            continue
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            issues.append(f"standalone agent file {relative_path!r} is not valid TOML")
            continue
        name = document.get("name")
        if not isinstance(name, str) or not name.strip():
            issues.append(
                f"standalone agent file {relative_path!r} field 'name' must be "
                "a non-empty string"
            )
            continue
        normalized_name = name.strip()
        if normalized_name in managed_roles:
            issues.append(
                f"standalone agent file {relative_path!r} declares managed role "
                f"{normalized_name!r}; change its declared name or move it out "
                "of the active agents directory before installation; the "
                "installer will leave the file unchanged"
            )
    return StandaloneAgentInspection(
        files_to_preserve=files_to_preserve,
        issues=tuple(issues),
    )
