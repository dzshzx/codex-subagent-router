"""Thin command-line boundary for explicit user installation transactions."""

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn, cast

from .installation import (
    InstallationPlan,
    InstallationResult,
    InstallationStatus,
    InstallationViolation,
    RollbackResult,
    install_user_config,
    installation_status,
    plan_user_installation,
    rollback_user_config,
)


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
    for operation in ("plan", "install"):
        subparser = subparsers.add_parser(operation)
        _add_codex_home_argument(subparser)
        subparser.add_argument(
            "--hook-executable",
            type=_absolute_path_argument,
            help="absolute hook executable path (defaults to PATH lookup)",
        )
    for operation in ("status", "rollback"):
        subparser = subparsers.add_parser(operation)
        _add_codex_home_argument(subparser)
    return parser


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


def _status_document(status: InstallationStatus) -> dict[str, object]:
    return {
        "codex_home": str(status.codex_home),
        "state": status.state.value,
        "details": list(status.details),
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
