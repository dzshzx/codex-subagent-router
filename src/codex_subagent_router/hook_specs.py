"""Shared metadata for the supported executable hook commands."""

from collections.abc import Callable
from dataclasses import dataclass

from .document_handlers import (
    handle_pre_tool_use_document,
    handle_session_start_document,
    handle_subagent_start_document,
)
from .roles import role_contracts


@dataclass(frozen=True, slots=True)
class HookCommandSpec:
    """One supported hook event, command name, and document handler."""

    event_name: str
    command_name: str
    matcher: str
    timeout_seconds: int
    handler: Callable[[str], str]


def hook_command_specs() -> tuple[HookCommandSpec, ...]:
    """Return executable hook commands in installation order."""
    return (
        HookCommandSpec(
            event_name="PreToolUse",
            command_name="pre-tool-use",
            matcher="^(Agent|.*spawn_agent.*)$",
            timeout_seconds=10,
            handler=handle_pre_tool_use_document,
        ),
        HookCommandSpec(
            event_name="SessionStart",
            command_name="session-start",
            matcher="startup",
            timeout_seconds=10,
            handler=handle_session_start_document,
        ),
        HookCommandSpec(
            event_name="SubagentStart",
            command_name="subagent-start",
            matcher="|".join(contract.agent_type for contract in role_contracts()),
            timeout_seconds=10,
            handler=handle_subagent_start_document,
        ),
    )
