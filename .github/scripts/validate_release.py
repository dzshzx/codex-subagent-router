"""Fail closed unless a release event, tag, commit, and project version agree."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path


class ReleaseValidationError(ValueError):
    pass


def _release_tag(environment: Mapping[str, str]) -> str:
    event = environment.get("GITHUB_EVENT_NAME", "")
    if event == "push":
        if environment.get("GITHUB_REF_TYPE") != "tag":
            raise ReleaseValidationError("A release push must target a tag.")
        return environment.get("GITHUB_REF_NAME", "")
    if event == "workflow_dispatch":
        return environment.get("DISPATCH_TAG", "")
    raise ReleaseValidationError("Unsupported release event.")


def _tag_exists(repository: Path, reference: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", reference],
        cwd=repository,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise ReleaseValidationError("Git could not inspect the release tag.")
    return result.returncode == 0


def _git_revision(repository: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", revision],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ReleaseValidationError("Git could not resolve a release revision.")
    return result.stdout.strip()


def _project_version(repository: Path) -> str:
    path = repository / "pyproject.toml"
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ReleaseValidationError("pyproject.toml is not readable TOML.") from error
    project = document.get("project")
    if not isinstance(project, dict):
        raise ReleaseValidationError("pyproject.toml has no project table.")
    version = project.get("version")
    if not isinstance(version, str) or not version:
        raise ReleaseValidationError("The project version is not a non-empty string.")
    return version


def validate_release(repository: Path, environment: Mapping[str, str]) -> None:
    release_tag = _release_tag(environment)
    if not release_tag.startswith("v"):
        raise ReleaseValidationError('The release tag must start with "v".')

    tag_reference = f"refs/tags/{release_tag}"
    if not _tag_exists(repository, tag_reference):
        raise ReleaseValidationError("The release tag does not exist in this checkout.")

    tag_commit = _git_revision(repository, f"{tag_reference}^{{commit}}")
    head_commit = _git_revision(repository, "HEAD^{commit}")
    if head_commit != tag_commit:
        raise ReleaseValidationError(
            "The checked-out commit does not match the release tag."
        )

    if release_tag != f"v{_project_version(repository)}":
        raise ReleaseValidationError(
            "The release tag does not match the project version."
        )


def main() -> int:
    try:
        validate_release(Path.cwd(), os.environ)
    except ReleaseValidationError as error:
        print(f"release validation error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
