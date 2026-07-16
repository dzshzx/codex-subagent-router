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
        "collaborationspawn_agent",
        "spawn_agent",
    }
)
_ROUTED_SPAWN_GUIDANCE_FIELDS = ("model", "reasoning_effort")
# Stable MultiAgent V1 and MultiAgent V2 register the same hook tool name,
# so the variant is identified by shape: only V2 carries task_name and
# fork_turns, while only V1 carries items and fork_context.
_V2_MARKER_FIELDS = frozenset({"task_name", "fork_turns"})
_V2_REQUIRED_FIELDS = frozenset(
    ("message", "task_name", "fork_turns", *_ROUTED_SPAWN_GUIDANCE_FIELDS)
)
_V2_FIELDS = _V2_REQUIRED_FIELDS | {"agent_type", "service_tier"}
_V1_REQUIRED_FIELDS = frozenset(_ROUTED_SPAWN_GUIDANCE_FIELDS)
_V1_FIELDS = _V1_REQUIRED_FIELDS | {
    "agent_type",
    "message",
    "items",
    "service_tier",
    "fork_context",
}
_INDEPENDENT_FORK_TURNS = "none"


def is_spawn_tool_name(tool_name: str) -> bool:
    """Return whether a hook-visible tool name is a routed spawn tool."""
    return tool_name in _SPAWN_AGENT_TOOL_NAMES


def routed_spawn_guidance_rules() -> tuple[str, ...]:
    """Return parent-facing rules owned by spawn validation."""
    explicit_fields = " and ".join(_ROUTED_SPAWN_GUIDANCE_FIELDS)
    return (
        f"Choose every routed child explicitly with {explicit_fields}.",
        "Set agent_type when a suitable declared role exists; omit it otherwise.",
        "On MultiAgent V2, also set task_name (lowercase letters, digits, "
        "and underscores only) and "
        f'fork_turns="{_INDEPENDENT_FORK_TURNS}" for independent work or a '
        "positive integer string for limited recent context; do not use "
        "full-history all with explicit routing.",
        "On stable MultiAgent V1, leave fork_context false or omitted; do "
        "not spawn full-history forks with explicit routing.",
        "Do not omit routed fields or silently rewrite them.",
    )


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
    tool_input = cast(dict[str, object], hook_input.tool_input)
    if tool_input.keys() & _V2_MARKER_FIELDS:
        denial = _validate_v2_shape(tool_input)
    else:
        denial = _validate_v1_shape(tool_input)
    if denial is not None:
        return denial
    return _validate_routed_compute(tool_input)


def _validate_v2_shape(
    tool_input: dict[str, object],
) -> PreToolUseDenyOutput | None:
    unknown_fields = sorted(tool_input.keys() - _V2_FIELDS)
    if unknown_fields:
        return PreToolUseDenyOutput(
            reason=f"unknown spawn_agent fields: {', '.join(unknown_fields)}"
        )
    missing_fields = sorted(_V2_REQUIRED_FIELDS - tool_input.keys())
    if missing_fields:
        return PreToolUseDenyOutput(
            reason=f"missing required spawn_agent fields: {', '.join(missing_fields)}"
        )
    for field_name in sorted(_V2_REQUIRED_FIELDS):
        value = tool_input[field_name]
        if not isinstance(value, str) or not value.strip():
            return PreToolUseDenyOutput(
                reason=(f"spawn_agent field {field_name!r} must be a non-empty string")
            )
    fork_turns = cast(str, tool_input["fork_turns"])
    is_positive_integer = (
        fork_turns.isascii()
        and fork_turns.isdigit()
        and any(digit != "0" for digit in fork_turns)
    )
    if fork_turns != _INDEPENDENT_FORK_TURNS and not is_positive_integer:
        return PreToolUseDenyOutput(
            reason="fork_turns must be 'none' or a positive integer string"
        )
    return None


def _validate_v1_shape(
    tool_input: dict[str, object],
) -> PreToolUseDenyOutput | None:
    unknown_fields = sorted(tool_input.keys() - _V1_FIELDS)
    if unknown_fields:
        return PreToolUseDenyOutput(
            reason=f"unknown spawn_agent fields: {', '.join(unknown_fields)}"
        )
    missing_fields = sorted(_V1_REQUIRED_FIELDS - tool_input.keys())
    if missing_fields:
        return PreToolUseDenyOutput(
            reason=f"missing required spawn_agent fields: {', '.join(missing_fields)}"
        )
    for field_name in sorted(_V1_REQUIRED_FIELDS):
        value = tool_input[field_name]
        if not isinstance(value, str) or not value.strip():
            return PreToolUseDenyOutput(
                reason=(f"spawn_agent field {field_name!r} must be a non-empty string")
            )
    if ("message" in tool_input) == ("items" in tool_input):
        return PreToolUseDenyOutput(
            reason="spawn_agent requires exactly one of message or items"
        )
    if "message" in tool_input:
        message = tool_input["message"]
        if not isinstance(message, str) or not message.strip():
            return PreToolUseDenyOutput(
                reason="spawn_agent field 'message' must be a non-empty string"
            )
    if "items" in tool_input:
        items = tool_input["items"]
        if not isinstance(items, list) or not items:
            return PreToolUseDenyOutput(
                reason="spawn_agent field 'items' must be a non-empty array"
            )
    if "fork_context" in tool_input:
        fork_context = tool_input["fork_context"]
        if not isinstance(fork_context, bool):
            return PreToolUseDenyOutput(
                reason=(
                    "spawn_agent field 'fork_context' must be a boolean when present"
                )
            )
        if fork_context:
            return PreToolUseDenyOutput(
                reason=(
                    "fork_context must be false or omitted; full-history forks "
                    "inherit parent routing"
                )
            )
    return None


def _validate_routed_compute(
    tool_input: dict[str, object],
) -> PreToolUseDenyOutput | None:
    for optional_field in ("agent_type", "service_tier"):
        if optional_field in tool_input:
            value = tool_input[optional_field]
            if not isinstance(value, str) or not value.strip():
                return PreToolUseDenyOutput(
                    reason=(
                        f"spawn_agent field {optional_field!r} must be a "
                        "non-empty string when present"
                    )
                )
    reasoning_effort = cast(str, tool_input["reasoning_effort"])
    try:
        validate_child_effort(reasoning_effort)
    except PolicyViolation as error:
        return PreToolUseDenyOutput(reason=str(error))
    model = cast(str, tool_input["model"])
    supported_profiles = routine_routes() + conditional_routes()
    if not any(
        profile.model == model and profile.effort == reasoning_effort
        for profile in supported_profiles
    ):
        return PreToolUseDenyOutput(
            reason=f"unsupported child profile: {model} / {reasoning_effort}"
        )
    return None
