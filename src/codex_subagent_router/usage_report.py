"""Offline spawn-routing usage report from Codex session rollouts."""

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .protocol import JsonValue, PermissionMode, PreToolUseInput
from .validator import is_spawn_tool_name, validate_pre_tool_use

_ROLLOUT_GLOB = "rollout-*.jsonl"
_ROUTE_FIELDS = (
    "task_name",
    "agent_type",
    "model",
    "reasoning_effort",
    "fork_turns",
)


class UsageReportViolation(ValueError):
    """Raised when session rollouts cannot be read as usage evidence."""


@dataclass(frozen=True, slots=True)
class SpawnCall:
    """One spawn tool call observed in a session rollout."""

    session_file: str
    tool_name: str
    task_name: str | None
    agent_type: str | None
    model: str | None
    reasoning_effort: str | None
    fork_turns: str | None
    deny_reason: str | None


@dataclass(frozen=True, slots=True)
class UsageReport:
    """Aggregated spawn-routing usage over scanned session rollouts."""

    sessions_scanned: int
    sessions_with_spawns: int
    spawn_calls: tuple[SpawnCall, ...]
    route_distribution: tuple[tuple[str, int], ...]
    denied_calls: int


def usage_report(sessions_root: Path) -> UsageReport:
    """Scan rollout files below an explicit directory and replay validation."""
    if not sessions_root.is_dir():
        raise UsageReportViolation(
            f"sessions directory does not exist: {sessions_root}"
        )
    spawn_calls: list[SpawnCall] = []
    sessions_scanned = 0
    sessions_with_spawns = 0
    for rollout_path in sorted(sessions_root.rglob(_ROLLOUT_GLOB)):
        sessions_scanned += 1
        calls = _spawn_calls_in_rollout(rollout_path)
        if calls:
            sessions_with_spawns += 1
            spawn_calls.extend(calls)
    distribution = Counter(
        f"{call.model or '?'}/{call.reasoning_effort or '?'}" for call in spawn_calls
    )
    return UsageReport(
        sessions_scanned=sessions_scanned,
        sessions_with_spawns=sessions_with_spawns,
        spawn_calls=tuple(spawn_calls),
        route_distribution=tuple(
            sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
        ),
        denied_calls=sum(1 for call in spawn_calls if call.deny_reason),
    )


def _spawn_calls_in_rollout(rollout_path: Path) -> tuple[SpawnCall, ...]:
    calls: list[SpawnCall] = []
    for line_number, line in enumerate(
        rollout_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        record = _parse_record(rollout_path, line_number, line)
        payload = record.get("payload")
        if record.get("type") != "response_item" or not isinstance(payload, dict):
            continue
        tool_name = payload.get("name")
        if payload.get("type") != "function_call" or not isinstance(tool_name, str):
            continue
        if not is_spawn_tool_name(tool_name):
            continue
        calls.append(_spawn_call(rollout_path, tool_name, payload.get("arguments")))
    return tuple(calls)


def _parse_record(rollout_path: Path, line_number: int, line: str) -> dict[str, object]:
    try:
        record = json.loads(line)
    except json.JSONDecodeError as error:
        raise UsageReportViolation(
            f"invalid rollout JSON at {rollout_path.name}:{line_number}: {error}"
        ) from error
    if not isinstance(record, dict):
        raise UsageReportViolation(
            f"rollout record is not an object at {rollout_path.name}:{line_number}"
        )
    return record


def _spawn_call(rollout_path: Path, tool_name: str, arguments: object) -> SpawnCall:
    tool_input, argument_error = _parse_arguments(arguments)
    deny_reason: str | None = argument_error
    if argument_error is None:
        denial = validate_pre_tool_use(
            _replay_input(rollout_path, tool_name, tool_input)
        )
        deny_reason = None if denial is None else denial.reason
    route_fields = {
        field: value
        for field in _ROUTE_FIELDS
        if isinstance(value := tool_input.get(field), str)
    }
    return SpawnCall(
        session_file=rollout_path.name,
        tool_name=tool_name,
        task_name=route_fields.get("task_name"),
        agent_type=route_fields.get("agent_type"),
        model=route_fields.get("model"),
        reasoning_effort=route_fields.get("reasoning_effort"),
        fork_turns=route_fields.get("fork_turns"),
        deny_reason=deny_reason,
    )


def _parse_arguments(arguments: object) -> tuple[dict[str, object], str | None]:
    if not isinstance(arguments, str):
        return {}, "spawn arguments are not recorded as a string"
    try:
        tool_input = json.loads(arguments)
    except json.JSONDecodeError:
        return {}, "spawn arguments are not valid JSON"
    if not isinstance(tool_input, dict):
        return {}, "spawn arguments are not a JSON object"
    return tool_input, None


def _replay_input(
    rollout_path: Path, tool_name: str, tool_input: dict[str, object]
) -> PreToolUseInput:
    # Synthetic session metadata: the deny-only validator reads only the
    # tool name and tool input, but the protocol type keeps its full shape.
    return PreToolUseInput(
        session_id=rollout_path.stem,
        turn_id="replay",
        transcript_path=None,
        cwd=str(rollout_path.parent),
        model="replay",
        permission_mode=PermissionMode.DEFAULT,
        tool_name=tool_name,
        tool_input=cast(JsonValue, tool_input),
        tool_use_id="replay",
    )
