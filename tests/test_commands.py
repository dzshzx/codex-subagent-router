import json
import subprocess
import sys
from collections.abc import Callable

import pytest

from codex_subagent_router import (
    ProtocolViolation,
    handle_pre_tool_use_document,
    handle_session_start_document,
    handle_subagent_start_document,
)


def _pre_tool_use_document(tool_input: object) -> str:
    return json.dumps(
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "transcript_path": None,
            "cwd": "/workspace/project",
            "hook_event_name": "PreToolUse",
            "model": "gpt-5.6-sol",
            "permission_mode": "dontAsk",
            "tool_name": "spawn_agent",
            "tool_input": tool_input,
            "tool_use_id": "tool-use-1",
        }
    )


def _session_start_document(source: str) -> str:
    return json.dumps(
        {
            "session_id": "session-1",
            "transcript_path": None,
            "cwd": "/workspace/project",
            "hook_event_name": "SessionStart",
            "model": "gpt-5.6-sol",
            "permission_mode": "dontAsk",
            "source": source,
        }
    )


def _subagent_start_document(agent_type: str) -> str:
    return json.dumps(
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "agent_id": "child-1",
            "agent_type": agent_type,
            "transcript_path": None,
            "cwd": "/workspace/project",
            "hook_event_name": "SubagentStart",
            "model": "gpt-5.6-sol",
            "permission_mode": "dontAsk",
        }
    )


def test_pre_tool_use_document_returns_the_encoded_denial() -> None:
    document = _pre_tool_use_document(
        {
            "message": "Review the bounded diff",
            "task_name": "review_spec",
            "agent_type": "reviewer",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "ultra",
            "fork_turns": "none",
        }
    )

    actual = handle_pre_tool_use_document(document)

    assert actual == (
        '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
        '"permissionDecision":"deny","permissionDecisionReason":'
        "\"child reasoning effort 'ultra' is prohibited\"}}"
    )


def test_allowed_pre_tool_use_document_has_no_output() -> None:
    document = _pre_tool_use_document(
        {
            "message": "Review the bounded diff",
            "task_name": "review_spec",
            "agent_type": "reviewer",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "fork_turns": "none",
        }
    )

    assert handle_pre_tool_use_document(document) == ""


def test_startup_session_document_returns_derived_routing_guidance() -> None:
    actual = json.loads(
        handle_session_start_document(_session_start_document("startup"))
    )

    assert actual["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    context = actual["hookSpecificOutput"]["additionalContext"]
    assert "gpt-5.6-terra / medium" in context
    assert "Child effort ultra is prohibited." in context


@pytest.mark.parametrize("source", ("resume", "clear", "compact"))
def test_non_startup_session_document_has_no_output(source: str) -> None:
    assert handle_session_start_document(_session_start_document(source)) == ""


def test_managed_subagent_document_returns_its_role_contract() -> None:
    actual = json.loads(
        handle_subagent_start_document(_subagent_start_document("reviewer"))
    )

    assert actual["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    assert actual["hookSpecificOutput"]["additionalContext"].startswith(
        "You are the reviewer for one bounded, read-only diff axis."
    )


def test_unmanaged_subagent_document_has_no_output() -> None:
    assert handle_subagent_start_document(_subagent_start_document("worker")) == ""


@pytest.mark.parametrize(
    ("handler", "document", "actual_type"),
    (
        (
            handle_pre_tool_use_document,
            _session_start_document("startup"),
            "SessionStartInput",
        ),
        (
            handle_session_start_document,
            _subagent_start_document("reviewer"),
            "SubagentStartInput",
        ),
        (handle_subagent_start_document, _pre_tool_use_document({}), "PreToolUseInput"),
    ),
)
def test_document_handlers_reject_the_wrong_event(
    handler: Callable[[str], str], document: str, actual_type: str
) -> None:
    with pytest.raises(
        ProtocolViolation,
        match=rf"expected \w+ input, got {actual_type}",
    ):
        handler(document)


def _run_command(command: str, document: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "codex_subagent_router.commands", command],
        input=document,
        capture_output=True,
        text=True,
        check=False,
    )


def test_command_process_writes_a_denial_only_to_stdout() -> None:
    document = _pre_tool_use_document(
        {
            "message": "Review the bounded diff",
            "task_name": "review_spec",
            "agent_type": "reviewer",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "ultra",
            "fork_turns": "none",
        }
    )

    completed = _run_command("pre-tool-use", document)

    assert completed.returncode == 0
    assert completed.stdout == (
        '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
        '"permissionDecision":"deny","permissionDecisionReason":'
        "\"child reasoning effort 'ultra' is prohibited\"}}"
    )
    assert completed.stderr == ""


@pytest.mark.parametrize(
    ("command", "document", "event_name", "context_fragment"),
    (
        (
            "session-start",
            _session_start_document("startup"),
            "SessionStart",
            "Child effort ultra is prohibited.",
        ),
        (
            "subagent-start",
            _subagent_start_document("reviewer"),
            "SubagentStart",
            "You are the reviewer for one bounded, read-only diff axis.",
        ),
    ),
)
def test_start_command_processes_write_encoded_context_to_stdout(
    command: str,
    document: str,
    event_name: str,
    context_fragment: str,
) -> None:
    completed = _run_command(command, document)

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == event_name
    assert context_fragment in payload["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize(
    ("command", "document"),
    (
        ("session-start", _session_start_document("resume")),
        ("subagent-start", _subagent_start_document("worker")),
    ),
)
def test_start_command_processes_write_nothing_for_no_op_documents(
    command: str,
    document: str,
) -> None:
    completed = _run_command(command, document)

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_command_process_reports_protocol_errors_without_stdout() -> None:
    completed = _run_command("session-start", "not JSON")

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert (
        completed.stderr == "hook protocol error: invalid hook JSON: Expecting value\n"
    )


def test_command_process_reports_usage_errors() -> None:
    completed = _run_command("unknown-event", "{}")

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "usage: python -m codex_subagent_router.commands "
        "{pre-tool-use|session-start|subagent-start}\n"
    )
