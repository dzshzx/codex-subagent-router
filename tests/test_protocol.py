from typing import cast

import pytest

from codex_subagent_router import (
    PermissionMode,
    PreToolUseDenyOutput,
    PreToolUseInput,
    ProtocolViolation,
    SessionSource,
    SessionStartInput,
    SessionStartOutput,
    SubagentStartInput,
    SubagentStartOutput,
    encode_hook_output,
    parse_hook_input,
)


def test_pre_tool_use_input_is_parsed_from_its_public_json_contract() -> None:
    document = """{
        "session_id": "session-1",
        "turn_id": "turn-1",
        "agent_id": "parent-agent-1",
        "agent_type": "reviewer",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_input": {
            "message": "Review the bounded diff",
            "task_name": "review_spec",
            "reasoning_effort": "high",
            "fork_turns": "none"
        },
        "tool_use_id": "tool-use-1"
    }"""

    actual = parse_hook_input(document)

    assert actual == PreToolUseInput(
        session_id="session-1",
        turn_id="turn-1",
        agent_id="parent-agent-1",
        agent_type="reviewer",
        transcript_path=None,
        cwd="/workspace/project",
        model="gpt-5.6-sol",
        permission_mode=PermissionMode.PLAN,
        tool_name="spawn_agent",
        tool_input={
            "message": "Review the bounded diff",
            "task_name": "review_spec",
            "reasoning_effort": "high",
            "fork_turns": "none",
        },
        tool_use_id="tool-use-1",
    )


def test_subagent_start_input_is_parsed_from_its_public_json_contract() -> None:
    document = """{
        "session_id": "session-2",
        "turn_id": "turn-2",
        "agent_id": "child-agent-1",
        "agent_type": "researcher",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/workspace/project",
        "hook_event_name": "SubagentStart",
        "model": "gpt-5.6-sol",
        "permission_mode": "dontAsk"
    }"""

    actual = parse_hook_input(document)

    assert actual == SubagentStartInput(
        session_id="session-2",
        turn_id="turn-2",
        agent_id="child-agent-1",
        agent_type="researcher",
        transcript_path="/tmp/transcript.jsonl",
        cwd="/workspace/project",
        model="gpt-5.6-sol",
        permission_mode=PermissionMode.DONT_ASK,
    )


def test_session_start_input_is_parsed_from_its_public_json_contract() -> None:
    document = """{
        "session_id": "session-3",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "SessionStart",
        "model": "gpt-5.6-sol",
        "permission_mode": "default",
        "source": "startup"
    }"""

    actual = parse_hook_input(document)

    assert actual == SessionStartInput(
        session_id="session-3",
        transcript_path=None,
        cwd="/workspace/project",
        model="gpt-5.6-sol",
        permission_mode=PermissionMode.DEFAULT,
        source=SessionSource.STARTUP,
    )


def test_unknown_pre_tool_use_input_fields_are_rejected() -> None:
    document = """{
        "session_id": "session-1",
        "turn_id": "turn-1",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_input": {},
        "tool_use_id": "tool-use-1",
        "future_field": true
    }"""

    with pytest.raises(ProtocolViolation, match="unknown fields: future_field"):
        parse_hook_input(document)


def test_missing_required_input_field_is_reported_explicitly() -> None:
    document = """{
        "session_id": "session-1",
        "turn_id": "turn-1",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_use_id": "tool-use-1"
    }"""

    with pytest.raises(ProtocolViolation, match="missing required field: tool_input"):
        parse_hook_input(document)


def test_duplicate_json_fields_are_rejected() -> None:
    document = """{
        "session_id": "first-session",
        "session_id": "second-session",
        "turn_id": "turn-1",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_input": {},
        "tool_use_id": "tool-use-1"
    }"""

    with pytest.raises(ProtocolViolation, match="duplicate JSON field: session_id"):
        parse_hook_input(document)


def test_non_json_numeric_constants_are_rejected() -> None:
    document = """{
        "session_id": "session-1",
        "turn_id": "turn-1",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_input": {"timeout": NaN},
        "tool_use_id": "tool-use-1"
    }"""

    with pytest.raises(ProtocolViolation, match="invalid JSON number: NaN"):
        parse_hook_input(document)


def test_pre_tool_use_denial_is_encoded_as_the_supported_wire_contract() -> None:
    output = PreToolUseDenyOutput(reason="child reasoning effort 'ultra' is prohibited")

    actual = encode_hook_output(output)

    assert actual == (
        '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
        '"permissionDecision":"deny","permissionDecisionReason":'
        "\"child reasoning effort 'ultra' is prohibited\"}}"
    )


def test_pre_tool_use_denial_requires_a_non_empty_reason() -> None:
    with pytest.raises(ProtocolViolation, match="denial reason must not be empty"):
        PreToolUseDenyOutput(reason="  ")


def test_subagent_start_context_is_encoded_as_the_supported_wire_contract() -> None:
    output = SubagentStartOutput(
        additional_context="Review one bounded axis and do not edit files."
    )

    actual = encode_hook_output(output)

    assert actual == (
        '{"hookSpecificOutput":{"hookEventName":"SubagentStart",'
        '"additionalContext":"Review one bounded axis and do not edit files."}}'
    )


def test_session_start_context_is_encoded_as_the_supported_wire_contract() -> None:
    output = SessionStartOutput(
        additional_context="Choose an explicit routed profile for each child."
    )

    actual = encode_hook_output(output)

    assert actual == (
        '{"hookSpecificOutput":{"hookEventName":"SessionStart",'
        '"additionalContext":"Choose an explicit routed profile for each child."}}'
    )


def test_unknown_hook_output_type_is_rejected_without_an_event_fallback() -> None:
    output = cast(SessionStartOutput, object())

    with pytest.raises(ProtocolViolation, match="unsupported hook output type: object"):
        encode_hook_output(output)


def test_subagent_start_context_must_not_be_empty() -> None:
    with pytest.raises(ProtocolViolation, match="additional context must not be empty"):
        SubagentStartOutput(additional_context="\n")


def test_optional_subagent_identity_must_be_a_string_when_present() -> None:
    document = """{
        "session_id": "session-1",
        "turn_id": "turn-1",
        "agent_id": null,
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_input": {},
        "tool_use_id": "tool-use-1"
    }"""

    with pytest.raises(ProtocolViolation, match="field 'agent_id' must be a string"):
        parse_hook_input(document)


def test_pre_tool_use_denial_reason_must_be_a_string() -> None:
    with pytest.raises(ProtocolViolation, match="denial reason must be a string"):
        PreToolUseDenyOutput(reason=cast(str, 1))


def test_subagent_start_context_must_be_a_string() -> None:
    with pytest.raises(ProtocolViolation, match="additional context must be a string"):
        SubagentStartOutput(additional_context=cast(str, None))


def test_json_numbers_that_overflow_to_infinity_are_rejected() -> None:
    document = """{
        "session_id": "session-1",
        "turn_id": "turn-1",
        "transcript_path": null,
        "cwd": "/workspace/project",
        "hook_event_name": "PreToolUse",
        "model": "gpt-5.6-sol",
        "permission_mode": "plan",
        "tool_name": "spawn_agent",
        "tool_input": {"ratio": 1e400},
        "tool_use_id": "tool-use-1"
    }"""

    with pytest.raises(ProtocolViolation, match="JSON number is outside finite range"):
        parse_hook_input(document)
