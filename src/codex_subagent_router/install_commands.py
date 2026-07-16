"""Thin command-line boundary for explicit user installation transactions."""

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn, cast

from .installation import (
    InstallationDoctorReport,
    InstallationPlan,
    InstallationResult,
    InstallationStatus,
    InstallationUpdatePlan,
    InstallationViolation,
    RollbackResult,
    doctor_user_config,
    install_user_config,
    installation_status,
    plan_user_installation,
    plan_user_update,
    rollback_user_config,
    update_user_config,
)
from .skill_render import render_skill_markdown, skill_name
from .usage_report import UsageReport, UsageReportViolation, usage_report


class _UsageViolation(ValueError):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _UsageViolation(message)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one explicit installation operation."""
    parser = _build_parser()
    try:
        arguments = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except _UsageViolation as error:
        parser.print_usage(sys.stderr)
        print(f"codex-subagent-router: error: {error}", file=sys.stderr)
        return 2

    operation = cast(str, arguments.operation)
    if operation == "render-skill":
        return _run_render_skill(arguments)
    if operation == "usage-report":
        return _run_usage_report(arguments)
    codex_home = cast(Path, arguments.codex_home).absolute()
    try:
        if operation == "plan":
            plan = plan_user_installation(
                codex_home,
                (_hook_executable(arguments),),
            )
            _print_json(_plan_document(plan))
            return 1 if plan.conflicts else 0
        if operation == "install":
            result = install_user_config(
                codex_home,
                (_hook_executable(arguments),),
            )
            _print_json(_result_document(result))
            return 0
        if operation == "update":
            if cast(bool, arguments.dry_run):
                update_plan = plan_user_update(
                    codex_home,
                    (_hook_executable(arguments),),
                )
                _print_json(_update_plan_document(update_plan))
                return 1 if update_plan.conflicts else 0
            update_result = update_user_config(
                codex_home,
                (_hook_executable(arguments),),
            )
            _print_json(_result_document(update_result))
            return 0
        if operation == "doctor":
            project_directory = cast(Path, arguments.project_directory).absolute()
            report = doctor_user_config(codex_home, project_directory)
            _print_json(_doctor_document(report))
            return 0 if report.healthy else 1
        if operation == "status":
            _print_json(_status_document(installation_status(codex_home)))
            return 0
        rollback_result = rollback_user_config(codex_home)
        _print_json(_rollback_document(rollback_result))
        return 0
    except InstallationViolation as error:
        print(f"installation error: {error}", file=sys.stderr)
        return 1


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="codex-subagent-router")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("plan", "install", "update"):
        subparser = subparsers.add_parser(operation)
        _add_codex_home_argument(subparser)
        subparser.add_argument(
            "--hook-executable",
            type=_absolute_path_argument,
            help="absolute hook executable path (defaults to PATH lookup)",
        )
        if operation == "update":
            subparser.add_argument(
                "--dry-run",
                action="store_true",
                help="plan the update without writing files",
            )
    doctor_parser = subparsers.add_parser("doctor")
    _add_codex_home_argument(doctor_parser)
    doctor_parser.add_argument(
        "--project-dir",
        dest="project_directory",
        type=_codex_home_argument,
        default=Path.cwd(),
        help="project directory to inspect (defaults to the current directory)",
    )
    for operation in ("status", "rollback", "uninstall"):
        subparser = subparsers.add_parser(operation)
        _add_codex_home_argument(subparser)
    render_parser = subparsers.add_parser("render-skill")
    render_parser.add_argument(
        "--out",
        type=_codex_home_argument,
        help="write the generated skill document here instead of stdout",
    )
    report_parser = subparsers.add_parser("usage-report")
    report_parser.add_argument(
        "--sessions-dir",
        dest="sessions_dir",
        required=True,
        type=_codex_home_argument,
        help="explicit Codex sessions directory to scan",
    )
    return parser


def _run_render_skill(arguments: argparse.Namespace) -> int:
    document = render_skill_markdown()
    out = cast(Path | None, arguments.out)
    if out is None:
        print(document, end="")
        return 0
    target = out.absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    _print_json({"skill_name": skill_name(), "written_to": str(target)})
    return 0


def _run_usage_report(arguments: argparse.Namespace) -> int:
    sessions_dir = cast(Path, arguments.sessions_dir).absolute()
    try:
        report = usage_report(sessions_dir)
    except UsageReportViolation as error:
        print(f"usage report error: {error}", file=sys.stderr)
        return 1
    _print_json(_usage_report_document(report))
    return 0


def _usage_report_document(report: UsageReport) -> dict[str, object]:
    return {
        "sessions_scanned": report.sessions_scanned,
        "sessions_with_spawns": report.sessions_with_spawns,
        "denied_calls": report.denied_calls,
        "route_distribution": dict(report.route_distribution),
        "spawn_calls": [
            {
                "session_file": call.session_file,
                "tool_name": call.tool_name,
                "task_name": call.task_name,
                "agent_type": call.agent_type,
                "model": call.model,
                "reasoning_effort": call.reasoning_effort,
                "fork_turns": call.fork_turns,
                "deny_reason": call.deny_reason,
            }
            for call in report.spawn_calls
        ],
    }


def _add_codex_home_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--codex-home", required=True, type=_codex_home_argument)


def _codex_home_argument(value: str) -> Path:
    # An empty string would silently resolve to the current working
    # directory; reject it while the original argument text is still known.
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be blank")
    return Path(value)


def _absolute_path_argument(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("must be an absolute path")
    return path


def _hook_executable(arguments: argparse.Namespace) -> str:
    explicit = cast(Path | None, arguments.hook_executable)
    if explicit is not None:
        return str(explicit)
    discovered = shutil.which("codex-subagent-router-hook")
    if discovered is None:
        raise InstallationViolation(
            "codex-subagent-router-hook is not installed on PATH; "
            "pass --hook-executable"
        )
    return str(Path(discovered).absolute())


def _plan_document(plan: InstallationPlan) -> dict[str, object]:
    return {
        "codex_home": str(plan.codex_home),
        "config_action": plan.config_action.value,
        "hooks_action": plan.hooks_action.value,
        "roles_to_add": list(plan.roles_to_add),
        "hook_events_to_add": list(plan.hook_events_to_add),
        "conflicts": list(plan.conflicts),
        "standalone_agent_files_to_preserve": list(
            plan.standalone_agent_files_to_preserve
        ),
        "requires_hook_review": plan.requires_hook_review,
        "requires_new_session": plan.requires_new_session,
    }


def _result_document(result: InstallationResult) -> dict[str, object]:
    return {
        "codex_home": str(result.codex_home),
        "config_path": str(result.config_path),
        "hooks_path": str(result.hooks_path),
        "manifest_path": str(result.manifest_path),
        "requires_hook_review": result.requires_hook_review,
        "requires_new_session": result.requires_new_session,
    }


def _update_plan_document(plan: InstallationUpdatePlan) -> dict[str, object]:
    return {
        "codex_home": str(plan.codex_home),
        "hooks_action": plan.hooks_action.value,
        "hook_events_to_update": list(plan.hook_events_to_update),
        "conflicts": list(plan.conflicts),
        "requires_hook_review": plan.requires_hook_review,
        "requires_new_session": plan.requires_new_session,
    }


def _status_document(status: InstallationStatus) -> dict[str, object]:
    return {
        "codex_home": str(status.codex_home),
        "state": status.state.value,
        "details": list(status.details),
    }


def _doctor_document(report: InstallationDoctorReport) -> dict[str, object]:
    return {
        "codex_home": str(report.codex_home),
        "project_directory": str(report.project_directory),
        "installation_state": report.installation_state.value,
        "healthy": report.healthy,
        "issues": list(report.issues),
        "user_standalone_agent_files": list(report.user_standalone_agent_files),
        "project_standalone_agent_files": list(report.project_standalone_agent_files),
    }


def _rollback_document(result: RollbackResult) -> dict[str, object]:
    return {
        "codex_home": str(result.codex_home),
        "config_action": result.config_action.value,
        "hooks_action": result.hooks_action.value,
    }


def _print_json(document: dict[str, object]) -> None:
    print(json.dumps(document, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
