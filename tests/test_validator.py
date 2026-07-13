import json

import pytest

from codex_subagent_router import (
    PreToolUseDenyOutput,
    PreToolUseInput,
    parse_hook_input,
    validate_pre_tool_use,
)


def _pre_tool_use(
    tool_input: object,
    *,
    tool_name: str = "spawn_agent",
) -> PreToolUseInput:
    document = json.dumps(
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "transcript_path": None,
            "cwd": "/workspace/project",
            "hook_event_name": "PreToolUse",
            "model": "gpt-5.6-sol",
            "permission_mode": "plan",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_use_id": "tool-use-1",
        }
    )
    parsed = parse_hook_input(document)
    assert isinstance(parsed, PreToolUseInput)
    return parsed


def _valid_spawn_input(**overrides: object) -> dict[str, object]:
    tool_input: dict[str, object] = {
        "message": "Review the bounded diff",
        "task_name": "review_spec",
        "agent_type": "reviewer",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "fork_turns": "none",
    }
    tool_input.update(overrides)
    return tool_input


@pytest.mark.parametrize(
    ("model", "effort", "fork_turns"),
    (
        ("gpt-5.6-terra", "medium", "none"),
        ("gpt-5.6-sol", "low", "3"),
        ("gpt-5.6-terra", "high", "none"),
        ("gpt-5.6-sol", "medium", "none"),
        ("gpt-5.6-sol", "high", "none"),
        ("gpt-5.6-sol", "xhigh", "none"),
        ("gpt-5.6-sol", "max", "none"),
    ),
)
def test_supported_explicit_spawn_is_allowed_without_output(
    model: str,
    effort: str,
    fork_turns: str,
) -> None:
    hook_input = _pre_tool_use(
        _valid_spawn_input(
            model=model,
            reasoning_effort=effort,
            fork_turns=fork_turns,
        )
    )

    assert validate_pre_tool_use(hook_input) is None


def test_spawn_tool_input_must_be_an_object() -> None:
    hook_input = _pre_tool_use("not-an-object")

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="spawn_agent tool_input must be a JSON object"
    )


def test_non_spawn_tool_is_ignored_without_inspecting_its_input() -> None:
    hook_input = _pre_tool_use("opaque-input", tool_name="read_file")

    assert validate_pre_tool_use(hook_input) is None


@pytest.mark.parametrize(
    "tool_name",
    ("Agent", "agentsspawn_agent", "collaborationspawn_agent"),
)
def test_verified_spawn_tool_names_use_the_same_validator(tool_name: str) -> None:
    hook_input = _pre_tool_use("not-an-object", tool_name=tool_name)

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="spawn_agent tool_input must be a JSON object"
    )


def test_unknown_spawn_fields_are_denied() -> None:
    hook_input = _pre_tool_use(_valid_spawn_input(fork_context=False))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="unknown spawn_agent fields: fork_context"
    )


def test_missing_explicit_spawn_fields_are_denied() -> None:
    tool_input = _valid_spawn_input()
    del tool_input["model"]
    hook_input = _pre_tool_use(tool_input)

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="missing required spawn_agent fields: model"
    )


def test_required_spawn_fields_must_be_non_empty_strings() -> None:
    hook_input = _pre_tool_use(_valid_spawn_input(model=56))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="spawn_agent field 'model' must be a non-empty string"
    )


@pytest.mark.parametrize(
    ("effort", "reason"),
    (
        ("ultra", "child reasoning effort 'ultra' is prohibited"),
        ("turbo", "unsupported child reasoning effort: turbo"),
    ),
)
def test_invalid_child_effort_is_denied_with_the_policy_reason(
    effort: str,
    reason: str,
) -> None:
    hook_input = _pre_tool_use(
        _valid_spawn_input(
            model="gpt-5.6-sol",
            reasoning_effort=effort,
        )
    )

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(reason=reason)


def test_unlisted_model_effort_profile_is_denied() -> None:
    hook_input = _pre_tool_use(
        _valid_spawn_input(
            model="gpt-5.6-terra",
            reasoning_effort="low",
        )
    )

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="unsupported child profile: gpt-5.6-terra / low"
    )


def test_full_history_fork_is_denied_for_explicit_compute() -> None:
    hook_input = _pre_tool_use(_valid_spawn_input(fork_turns="all"))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="fork_turns must be 'none' or a positive integer string"
    )


def test_very_large_positive_fork_turns_is_allowed_without_integer_conversion() -> None:
    hook_input = _pre_tool_use(_valid_spawn_input(fork_turns="1" * 5000))

    assert validate_pre_tool_use(hook_input) is None


def test_service_tier_must_be_a_non_empty_string_when_present() -> None:
    hook_input = _pre_tool_use(_valid_spawn_input(service_tier=None))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason=(
            "spawn_agent field 'service_tier' must be a non-empty string when present"
        )
    )


def _valid_v1_spawn_input(**overrides: object) -> dict[str, object]:
    tool_input: dict[str, object] = {
        "message": "Review the bounded diff",
        "agent_type": "reviewer",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
    }
    tool_input.update(overrides)
    return tool_input


@pytest.mark.parametrize(
    ("model", "effort"),
    (
        ("gpt-5.6-terra", "medium"),
        ("gpt-5.6-sol", "low"),
        ("gpt-5.6-terra", "high"),
        ("gpt-5.6-sol", "medium"),
        ("gpt-5.6-sol", "high"),
        ("gpt-5.6-sol", "xhigh"),
        ("gpt-5.6-sol", "max"),
    ),
)
def test_supported_explicit_v1_spawn_is_allowed_without_output(
    model: str,
    effort: str,
) -> None:
    hook_input = _pre_tool_use(
        _valid_v1_spawn_input(model=model, reasoning_effort=effort)
    )

    assert validate_pre_tool_use(hook_input) is None


def test_v1_spawn_with_items_is_allowed() -> None:
    tool_input = _valid_v1_spawn_input()
    del tool_input["message"]
    tool_input["items"] = [{"type": "text", "text": "Review the bounded diff"}]

    assert validate_pre_tool_use(_pre_tool_use(tool_input)) is None


def test_v1_spawn_with_false_fork_context_is_allowed() -> None:
    hook_input = _pre_tool_use(_valid_v1_spawn_input(fork_context=False))

    assert validate_pre_tool_use(hook_input) is None


def test_v1_full_history_fork_is_denied_for_explicit_compute() -> None:
    hook_input = _pre_tool_use(_valid_v1_spawn_input(fork_context=True))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason=(
            "fork_context must be false or omitted; full-history forks "
            "inherit parent routing"
        )
    )


def test_v1_fork_context_must_be_a_boolean() -> None:
    hook_input = _pre_tool_use(_valid_v1_spawn_input(fork_context="false"))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="spawn_agent field 'fork_context' must be a boolean when present"
    )


def test_v1_spawn_requires_exactly_one_of_message_or_items() -> None:
    both = _valid_v1_spawn_input(items=[{"type": "text", "text": "x"}])
    neither = _valid_v1_spawn_input()
    del neither["message"]

    for tool_input in (both, neither):
        assert validate_pre_tool_use(_pre_tool_use(tool_input)) == (
            PreToolUseDenyOutput(
                reason="spawn_agent requires exactly one of message or items"
            )
        )


def test_v1_items_must_be_a_non_empty_array() -> None:
    tool_input = _valid_v1_spawn_input()
    del tool_input["message"]
    tool_input["items"] = []

    assert validate_pre_tool_use(_pre_tool_use(tool_input)) == PreToolUseDenyOutput(
        reason="spawn_agent field 'items' must be a non-empty array"
    )


def test_v1_missing_routed_fields_are_denied() -> None:
    tool_input = _valid_v1_spawn_input()
    del tool_input["model"]
    del tool_input["reasoning_effort"]

    assert validate_pre_tool_use(_pre_tool_use(tool_input)) == PreToolUseDenyOutput(
        reason="missing required spawn_agent fields: model, reasoning_effort"
    )


def test_v1_unknown_spawn_fields_are_denied() -> None:
    hook_input = _pre_tool_use(_valid_v1_spawn_input(sandbox="off"))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="unknown spawn_agent fields: sandbox"
    )


def test_v1_ultra_effort_is_denied_with_the_policy_reason() -> None:
    hook_input = _pre_tool_use(
        _valid_v1_spawn_input(model="gpt-5.6-sol", reasoning_effort="ultra")
    )

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="child reasoning effort 'ultra' is prohibited"
    )


def test_fork_turns_without_task_name_is_validated_as_v2() -> None:
    hook_input = _pre_tool_use(_valid_v1_spawn_input(fork_turns="none"))

    assert validate_pre_tool_use(hook_input) == PreToolUseDenyOutput(
        reason="missing required spawn_agent fields: task_name"
    )
