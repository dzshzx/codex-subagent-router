"""Deny-only validation for routed Codex subagent spawns."""

from typing import cast

from .policy import (
    PolicyViolation,
    conditional_routes,
    routine_routes,
    validate_child_effort,
)
from .protocol import PreToolUseDenyOutput, PreToolUseInput

_SPAWN_AGENT_TOOL_NAMES = frozenset(
    {
        "Agent",
        "agentsspawn_agent",
        "spawn_agent",
    }
)
_SPAWN_AGENT_FIELDS = frozenset(
    {
        "agent_type",
        "fork_turns",
        "message",
        "model",
        "reasoning_effort",
        "service_tier",
        "task_name",
    }
)
_REQUIRED_SPAWN_AGENT_FIELDS = _SPAWN_AGENT_FIELDS - {"service_tier"}


def validate_pre_tool_use(
    hook_input: PreToolUseInput,
) -> PreToolUseDenyOutput | None:
    """Return a policy denial for an invalid spawn, otherwise no output."""
    if hook_input.tool_name not in _SPAWN_AGENT_TOOL_NAMES:
        return None
    if not isinstance(hook_input.tool_input, dict):
        return PreToolUseDenyOutput(
            reason="spawn_agent tool_input must be a JSON object"
        )
    unknown_fields = sorted(hook_input.tool_input.keys() - _SPAWN_AGENT_FIELDS)
    if unknown_fields:
        return PreToolUseDenyOutput(
            reason=f"unknown spawn_agent fields: {', '.join(unknown_fields)}"
        )
    missing_fields = sorted(_REQUIRED_SPAWN_AGENT_FIELDS - hook_input.tool_input.keys())
    if missing_fields:
        return PreToolUseDenyOutput(
            reason=f"missing required spawn_agent fields: {', '.join(missing_fields)}"
        )
    for field_name in sorted(_REQUIRED_SPAWN_AGENT_FIELDS):
        value = hook_input.tool_input[field_name]
        if not isinstance(value, str) or not value.strip():
            return PreToolUseDenyOutput(
                reason=(f"spawn_agent field {field_name!r} must be a non-empty string")
            )
    if "service_tier" in hook_input.tool_input:
        service_tier = hook_input.tool_input["service_tier"]
        if not isinstance(service_tier, str) or not service_tier.strip():
            return PreToolUseDenyOutput(
                reason=(
                    "spawn_agent field 'service_tier' must be a non-empty string "
                    "when present"
                )
            )
    reasoning_effort = cast(str, hook_input.tool_input["reasoning_effort"])
    try:
        validate_child_effort(reasoning_effort)
    except PolicyViolation as error:
        return PreToolUseDenyOutput(reason=str(error))
    model = cast(str, hook_input.tool_input["model"])
    supported_profiles = routine_routes() + conditional_routes()
    if not any(
        profile.model == model and profile.effort == reasoning_effort
        for profile in supported_profiles
    ):
        return PreToolUseDenyOutput(
            reason=f"unsupported child profile: {model} / {reasoning_effort}"
        )
    fork_turns = cast(str, hook_input.tool_input["fork_turns"])
    is_positive_integer = (
        fork_turns.isascii()
        and fork_turns.isdigit()
        and any(digit != "0" for digit in fork_turns)
    )
    if fork_turns != "none" and not is_positive_integer:
        return PreToolUseDenyOutput(
            reason="fork_turns must be 'none' or a positive integer string"
        )
    return None
