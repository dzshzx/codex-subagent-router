"""Executable command-line boundary for Codex command hooks."""

import sys
from collections.abc import Sequence

from .hook_specs import hook_command_specs
from .protocol import ProtocolViolation

_USAGE = (
    "usage: python -m codex_subagent_router.commands "
    "{pre-tool-use|session-start|subagent-start}"
)
_COMMANDS = {spec.command_name: spec.handler for spec in hook_command_specs()}


def main(argv: Sequence[str] | None = None) -> int:
    """Run one hook command using stdin, stdout, and stderr."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1 or arguments[0] not in _COMMANDS:
        print(_USAGE, file=sys.stderr)
        return 2
    try:
        output = _COMMANDS[arguments[0]](sys.stdin.read())
    except ProtocolViolation as error:
        print(f"hook protocol error: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
