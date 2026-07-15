"""Read-only aggregation for user installation and project agent health."""

from pathlib import Path

from ._installation_agents import inspect_project_agents, inspect_standalone_agents
from ._installation_types import (
    InstallationDoctorReport,
    InstallationState,
    InstallationStatus,
)


def build_doctor_report(
    codex_home: Path,
    project_directory: Path,
    status: InstallationStatus,
) -> InstallationDoctorReport:
    """Combine installation status with active standalone-agent layers."""
    user_agents = inspect_standalone_agents(codex_home)
    project_agents = inspect_project_agents(project_directory)
    issues = list(status.details)
    if status.state is InstallationState.NOT_INSTALLED:
        issues.append("installation is not installed")
    for issue in (*user_agents.issues, *project_agents.issues):
        if issue not in issues:
            issues.append(issue)
    return InstallationDoctorReport(
        codex_home=codex_home,
        project_directory=project_directory,
        installation_state=status.state,
        healthy=status.state is InstallationState.INSTALLED and not issues,
        issues=tuple(issues),
        user_standalone_agent_files=user_agents.agent_files,
        project_standalone_agent_files=project_agents.agent_files,
    )
