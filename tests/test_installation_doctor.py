from pathlib import Path

from codex_subagent_router import (
    InstallationDoctorReport,
    InstallationState,
    doctor_user_config,
    install_user_config,
)


def _hook_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "bin" / "codex-subagent-router-hook"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def _standalone_agent(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'name = "{name}"\n'
        'description = "User-managed agent"\n'
        'developer_instructions = "Remain user managed."\n'
    )


def test_doctor_reports_a_healthy_user_installation_and_project(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_directory.mkdir()
    _standalone_agent(codex_home / "agents" / "user-owned.toml", "user_owned")
    _standalone_agent(
        project_directory / ".codex" / "agents" / "project-owned.toml",
        "project_owned",
    )
    install_user_config(codex_home, (str(_hook_executable(tmp_path)),))

    actual = doctor_user_config(codex_home, project_directory)

    assert actual == InstallationDoctorReport(
        codex_home=codex_home,
        project_directory=project_directory,
        installation_state=InstallationState.INSTALLED,
        healthy=True,
        issues=(),
        user_standalone_agent_files=("agents/user-owned.toml",),
        project_standalone_agent_files=(".codex/agents/project-owned.toml",),
    )


def test_doctor_reports_a_missing_project_directory(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    install_user_config(codex_home, (str(_hook_executable(tmp_path)),))
    project_directory = tmp_path / "missing-project"

    actual = doctor_user_config(codex_home, project_directory)

    assert actual == InstallationDoctorReport(
        codex_home=codex_home,
        project_directory=project_directory,
        installation_state=InstallationState.INSTALLED,
        healthy=False,
        issues=("project directory does not exist",),
        user_standalone_agent_files=(),
        project_standalone_agent_files=(),
    )


def test_doctor_reports_a_non_directory_project_path(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    install_user_config(codex_home, (str(_hook_executable(tmp_path)),))
    project_directory = tmp_path / "project-file"
    project_directory.write_text("not a directory\n")

    actual = doctor_user_config(codex_home, project_directory)

    assert actual.healthy is False
    assert actual.issues == ("project directory must be a directory",)
    assert project_directory.read_text() == "not a directory\n"


def test_doctor_reports_a_non_directory_project_codex_path(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_directory.mkdir()
    install_user_config(codex_home, (str(_hook_executable(tmp_path)),))
    codex_path = project_directory / ".codex"
    codex_path.write_text("not a directory\n")

    actual = doctor_user_config(codex_home, project_directory)

    assert actual.healthy is False
    assert actual.issues == ("project Codex directory '.codex' must be a directory",)
    assert codex_path.read_text() == "not a directory\n"


def test_doctor_reports_a_missing_user_installation(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_directory.mkdir()

    actual = doctor_user_config(codex_home, project_directory)

    assert actual.installation_state is InstallationState.NOT_INSTALLED
    assert actual.healthy is False
    assert actual.issues == ("installation is not installed",)


def test_doctor_reports_a_missing_hook_launcher(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_directory.mkdir()
    hook_executable = _hook_executable(tmp_path)
    install_user_config(codex_home, (str(hook_executable),))
    hook_executable.unlink()

    actual = doctor_user_config(codex_home, project_directory)

    assert actual.installation_state is InstallationState.INSTALLED
    assert actual.healthy is False
    assert actual.issues == (
        f"hook launcher is not an executable file: {hook_executable}",
    )


def test_doctor_reports_project_agent_without_developer_instructions(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"
    project_directory = tmp_path / "project"
    codex_home.mkdir()
    project_agent = project_directory / ".codex" / "agents" / "invalid.toml"
    project_agent.parent.mkdir(parents=True)
    project_agent.write_text(
        'name = "project_owned"\ndescription = "Missing its required instructions"\n'
    )
    install_user_config(codex_home, (str(_hook_executable(tmp_path)),))

    actual = doctor_user_config(codex_home, project_directory)

    assert actual.healthy is False
    assert actual.issues == (
        "project standalone agent file '.codex/agents/invalid.toml' field "
        "'developer_instructions' must be a non-empty string",
    )
    assert project_agent.read_text() == (
        'name = "project_owned"\ndescription = "Missing its required instructions"\n'
    )
