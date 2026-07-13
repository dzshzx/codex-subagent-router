import os
import subprocess
import sys
from pathlib import Path

import pytest

_VALIDATOR = Path(__file__).parents[1] / ".github" / "scripts" / "validate_release.py"


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(tmp_path: Path, *, version: str = "1.2.3") -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "pyproject.toml").write_text(
        f'[project]\nname = "example"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    _git(repository, "init", "-b", "master")
    _git(repository, "config", "user.name", "Release Test")
    _git(repository, "config", "user.email", "release-test@example.invalid")
    _git(repository, "add", "pyproject.toml")
    _git(repository, "commit", "-m", "initial")
    _git(repository, "tag", f"v{version}")
    return repository


def _run_validator(
    repository: Path,
    *,
    event: str,
    ref_type: str = "",
    ref_name: str = "",
    dispatch_tag: str = "",
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GITHUB_EVENT_NAME": event,
            "GITHUB_REF_TYPE": ref_type,
            "GITHUB_REF_NAME": ref_name,
            "DISPATCH_TAG": dispatch_tag,
        }
    )
    return subprocess.run(
        [sys.executable, str(_VALIDATOR)],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_release_validator_accepts_a_tag_push(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    actual = _run_validator(
        repository,
        event="push",
        ref_type="tag",
        ref_name="v1.2.3",
    )

    assert actual.returncode == 0
    assert actual.stdout == ""
    assert actual.stderr == ""


def test_release_validator_accepts_an_explicit_dispatch_tag(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    actual = _run_validator(
        repository,
        event="workflow_dispatch",
        dispatch_tag="v1.2.3",
    )

    assert actual.returncode == 0
    assert actual.stdout == ""
    assert actual.stderr == ""


@pytest.mark.parametrize(
    ("event", "ref_type", "message"),
    (
        ("schedule", "", "unsupported release event"),
        ("push", "branch", "release push must target a tag"),
    ),
)
def test_release_validator_rejects_an_unsupported_trigger(
    tmp_path: Path,
    event: str,
    ref_type: str,
    message: str,
) -> None:
    repository = _repository(tmp_path)

    actual = _run_validator(
        repository,
        event=event,
        ref_type=ref_type,
        ref_name="v1.2.3",
    )

    assert actual.returncode == 1
    assert actual.stdout == ""
    assert message in actual.stderr.lower()


@pytest.mark.parametrize(
    ("tag", "message"),
    (
        ("1.2.3", 'must start with "v"'),
        ("v9.9.9", "does not exist"),
    ),
)
def test_release_validator_rejects_an_invalid_or_missing_tag(
    tmp_path: Path,
    tag: str,
    message: str,
) -> None:
    repository = _repository(tmp_path)

    actual = _run_validator(
        repository,
        event="workflow_dispatch",
        dispatch_tag=tag,
    )

    assert actual.returncode == 1
    assert actual.stdout == ""
    assert message in actual.stderr.lower()


def test_release_validator_rejects_a_head_after_the_tag(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "later.txt").write_text("later\n", encoding="utf-8")
    _git(repository, "add", "later.txt")
    _git(repository, "commit", "-m", "later")

    actual = _run_validator(
        repository,
        event="push",
        ref_type="tag",
        ref_name="v1.2.3",
    )

    assert actual.returncode == 1
    assert actual.stdout == ""
    assert "checked-out commit does not match" in actual.stderr.lower()


def test_release_validator_rejects_a_version_mismatch(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _git(repository, "tag", "v1.2.4")

    actual = _run_validator(
        repository,
        event="workflow_dispatch",
        dispatch_tag="v1.2.4",
    )

    assert actual.returncode == 1
    assert actual.stdout == ""
    assert "does not match the project version" in actual.stderr.lower()
