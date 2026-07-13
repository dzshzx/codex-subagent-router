"""Strict value types for the Codex hook JSON boundary."""

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn, TypeAlias, cast

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_BASE_INPUT_FIELDS = frozenset(
    {
        "session_id",
        "transcript_path",
        "cwd",
        "hook_event_name",
        "model",
        "permission_mode",
    }
)
_TURN_SCOPED_INPUT_FIELDS = _BASE_INPUT_FIELDS | {"turn_id"}
_PRE_TOOL_USE_INPUT_FIELDS = _TURN_SCOPED_INPUT_FIELDS | {
    "agent_id",
    "agent_type",
    "tool_name",
    "tool_input",
    "tool_use_id",
}
_SUBAGENT_START_INPUT_FIELDS = _TURN_SCOPED_INPUT_FIELDS | {
    "agent_id",
    "agent_type",
}
_SESSION_START_INPUT_FIELDS = _BASE_INPUT_FIELDS | {"source"}


class ProtocolViolation(ValueError):
    """Raised when a hook document does not match the supported wire contract."""


class PermissionMode(StrEnum):
    """Permission modes accepted by the supported Codex hook contract."""

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    DONT_ASK = "dontAsk"
    BYPASS_PERMISSIONS = "bypassPermissions"


class SessionSource(StrEnum):
    """Sources accepted by the supported Codex ``SessionStart`` contract."""

    STARTUP = "startup"
    RESUME = "resume"
    CLEAR = "clear"
    COMPACT = "compact"


@dataclass(frozen=True, slots=True)
class PreToolUseInput:
    """Validated input for a Codex ``PreToolUse`` command hook."""

    session_id: str
    turn_id: str
    transcript_path: str | None
    cwd: str
    model: str
    permission_mode: PermissionMode
    tool_name: str
    tool_input: JsonValue
    tool_use_id: str
    agent_id: str | None = None
    agent_type: str | None = None


@dataclass(frozen=True, slots=True)
class SubagentStartInput:
    """Validated input for a Codex ``SubagentStart`` command hook."""

    session_id: str
    turn_id: str
    agent_id: str
    agent_type: str
    transcript_path: str | None
    cwd: str
    model: str
    permission_mode: PermissionMode


@dataclass(frozen=True, slots=True)
class SessionStartInput:
    """Validated input for a Codex ``SessionStart`` command hook."""

    session_id: str
    transcript_path: str | None
    cwd: str
    model: str
    permission_mode: PermissionMode
    source: SessionSource


HookInput: TypeAlias = PreToolUseInput | SubagentStartInput | SessionStartInput


def _validate_additional_context(value: object) -> None:
    if not isinstance(value, str):
        raise ProtocolViolation("additional context must be a string")
    if not value.strip():
        raise ProtocolViolation("additional context must not be empty")


@dataclass(frozen=True, slots=True)
class PreToolUseDenyOutput:
    """A policy denial emitted before a tool is allowed to run."""

    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str):
            raise ProtocolViolation("denial reason must be a string")
        if not self.reason.strip():
            raise ProtocolViolation("denial reason must not be empty")


@dataclass(frozen=True, slots=True)
class SubagentStartOutput:
    """Developer context emitted before a subagent's first model request."""

    additional_context: str

    def __post_init__(self) -> None:
        _validate_additional_context(self.additional_context)


@dataclass(frozen=True, slots=True)
class SessionStartOutput:
    """Routing guidance emitted before a root session's first request."""

    additional_context: str

    def __post_init__(self) -> None:
        _validate_additional_context(self.additional_context)


HookOutput: TypeAlias = PreToolUseDenyOutput | SubagentStartOutput | SessionStartOutput


def parse_hook_input(document: str) -> HookInput:
    """Parse one supported Codex hook input JSON document."""
    try:
        value = cast(
            object,
            json.loads(
                document,
                object_pairs_hook=_object_without_duplicates,
                parse_constant=_reject_non_json_number,
            ),
        )
    except json.JSONDecodeError as error:
        raise ProtocolViolation(f"invalid hook JSON: {error.msg}") from error

    _validate_json_value(value)
    fields = _require_object(value)
    event_name = _require_string(fields, "hook_event_name")
    if event_name not in {"PreToolUse", "SessionStart", "SubagentStart"}:
        raise ProtocolViolation(f"unsupported hook_event_name: {event_name}")
    if event_name == "PreToolUse":
        allowed_fields = _PRE_TOOL_USE_INPUT_FIELDS
    elif event_name == "SubagentStart":
        allowed_fields = _SUBAGENT_START_INPUT_FIELDS
    else:
        allowed_fields = _SESSION_START_INPUT_FIELDS
    _reject_unknown_fields(fields, allowed_fields)

    permission_mode_value = _require_string(fields, "permission_mode")
    try:
        permission_mode = PermissionMode(permission_mode_value)
    except ValueError as error:
        raise ProtocolViolation(
            f"unsupported permission_mode: {permission_mode_value}"
        ) from error

    if event_name == "SessionStart":
        source_value = _require_string(fields, "source")
        try:
            source = SessionSource(source_value)
        except ValueError as error:
            raise ProtocolViolation(
                f"unsupported SessionStart source: {source_value}"
            ) from error
        return SessionStartInput(
            session_id=_require_string(fields, "session_id"),
            transcript_path=_require_nullable_string(fields, "transcript_path"),
            cwd=_require_string(fields, "cwd"),
            model=_require_string(fields, "model"),
            permission_mode=permission_mode,
            source=source,
        )

    if event_name == "SubagentStart":
        return SubagentStartInput(
            session_id=_require_string(fields, "session_id"),
            turn_id=_require_string(fields, "turn_id"),
            agent_id=_require_string(fields, "agent_id"),
            agent_type=_require_string(fields, "agent_type"),
            transcript_path=_require_nullable_string(fields, "transcript_path"),
            cwd=_require_string(fields, "cwd"),
            model=_require_string(fields, "model"),
            permission_mode=permission_mode,
        )

    return PreToolUseInput(
        session_id=_require_string(fields, "session_id"),
        turn_id=_require_string(fields, "turn_id"),
        transcript_path=_require_nullable_string(fields, "transcript_path"),
        cwd=_require_string(fields, "cwd"),
        model=_require_string(fields, "model"),
        permission_mode=permission_mode,
        tool_name=_require_string(fields, "tool_name"),
        tool_input=cast(JsonValue, _require_field(fields, "tool_input")),
        tool_use_id=_require_string(fields, "tool_use_id"),
        agent_id=_optional_string(fields, "agent_id"),
        agent_type=_optional_string(fields, "agent_type"),
    )


def encode_hook_output(output: HookOutput) -> str:
    """Encode one supported hook output as a compact JSON document."""
    if isinstance(output, PreToolUseDenyOutput):
        hook_specific_output: JsonValue = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": output.reason,
        }
    elif isinstance(output, SubagentStartOutput):
        hook_specific_output = {
            "hookEventName": "SubagentStart",
            "additionalContext": output.additional_context,
        }
    elif isinstance(output, SessionStartOutput):
        hook_specific_output = {
            "hookEventName": "SessionStart",
            "additionalContext": output.additional_context,
        }
    else:
        raise ProtocolViolation(
            f"unsupported hook output type: {type(output).__name__}"
        )
    payload: JsonValue = {
        "hookSpecificOutput": hook_specific_output,
    }
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _object_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolViolation(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_non_json_number(value: str) -> NoReturn:
    raise ProtocolViolation(f"invalid JSON number: {value}")


def _validate_json_value(value: object) -> None:
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProtocolViolation("JSON number is outside finite range")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _validate_json_value(item)
        return
    raise ProtocolViolation("hook input contains a non-JSON value")


def _require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ProtocolViolation("hook input must be a JSON object")
    return cast(dict[str, object], value)


def _reject_unknown_fields(
    fields: dict[str, object], allowed_fields: frozenset[str]
) -> None:
    unknown_fields = sorted(fields.keys() - allowed_fields)
    if unknown_fields:
        raise ProtocolViolation(f"unknown fields: {', '.join(unknown_fields)}")


def _require_string(fields: dict[str, object], name: str) -> str:
    value = _require_field(fields, name)
    if not isinstance(value, str):
        raise ProtocolViolation(f"field {name!r} must be a string")
    return value


def _require_nullable_string(fields: dict[str, object], name: str) -> str | None:
    value = _require_field(fields, name)
    if value is not None and not isinstance(value, str):
        raise ProtocolViolation(f"field {name!r} must be a string or null")
    return value


def _require_field(fields: dict[str, object], name: str) -> object:
    if name not in fields:
        raise ProtocolViolation(f"missing required field: {name}")
    return fields[name]


def _optional_string(fields: dict[str, object], name: str) -> str | None:
    if name not in fields:
        return None
    value = fields[name]
    if not isinstance(value, str):
        raise ProtocolViolation(f"field {name!r} must be a string")
    return value
