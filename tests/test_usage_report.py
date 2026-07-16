import json
from pathlib import Path

import pytest

from codex_subagent_router import UsageReportViolation, usage_report


def _rollout_line(record_type: str, payload: dict[str, object]) -> str:
    return json.dumps({"type": record_type, "payload": payload})


def _spawn_line(tool_name: str, arguments: dict[str, object]) -> str:
    return _rollout_line(
        "response_item",
        {
            "type": "function_call",
            "name": tool_name,
            "arguments": json.dumps(arguments),
        },
    )


def _v2_arguments(**overrides: str) -> dict[str, object]:
    arguments: dict[str, object] = {
        "task_name": "probe_child",
        "agent_type": "reviewer",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "fork_turns": "none",
        "message": "sentinel",
    }
    arguments.update(overrides)
    return arguments


def _write_rollout(directory: Path, name: str, lines: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_usage_report_requires_an_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageReportViolation, match="does not exist"):
        usage_report(tmp_path / "missing")


def test_usage_report_rejects_invalid_rollout_json(tmp_path: Path) -> None:
    _write_rollout(tmp_path, "rollout-1-bad.jsonl", ["{not json"])

    with pytest.raises(UsageReportViolation, match="rollout-1-bad.jsonl:1"):
        usage_report(tmp_path)


def test_usage_report_aggregates_spawns_and_replays_validation(
    tmp_path: Path,
) -> None:
    day = tmp_path / "2026" / "07" / "16"
    _write_rollout(
        day,
        "rollout-1-root.jsonl",
        [
            _rollout_line("session_meta", {"id": "root-1"}),
            _rollout_line(
                "response_item",
                {"type": "function_call", "name": "shell", "arguments": "{}"},
            ),
            _spawn_line("spawn_agent", _v2_arguments()),
            _spawn_line(
                "spawn_agent",
                _v2_arguments(task_name="deep_probe", reasoning_effort="ultra"),
            ),
        ],
    )
    _write_rollout(
        day,
        "rollout-2-quiet.jsonl",
        [_rollout_line("session_meta", {"id": "quiet-1"})],
    )

    report = usage_report(tmp_path)

    assert report.sessions_scanned == 2
    assert report.sessions_with_spawns == 1
    assert report.denied_calls == 1
    assert report.route_distribution == (
        ("gpt-5.6-sol/low", 1),
        ("gpt-5.6-sol/ultra", 1),
    )
    accepted, denied = report.spawn_calls
    assert accepted.tool_name == "spawn_agent"
    assert accepted.task_name == "probe_child"
    assert accepted.agent_type == "reviewer"
    assert accepted.model == "gpt-5.6-sol"
    assert accepted.reasoning_effort == "low"
    assert accepted.fork_turns == "none"
    assert accepted.deny_reason is None
    assert denied.deny_reason == "child reasoning effort 'ultra' is prohibited"


def test_usage_report_marks_unparseable_spawn_arguments(tmp_path: Path) -> None:
    _write_rollout(
        tmp_path,
        "rollout-3-broken-args.jsonl",
        [
            _rollout_line(
                "response_item",
                {
                    "type": "function_call",
                    "name": "spawn_agent",
                    "arguments": "{not json",
                },
            )
        ],
    )

    report = usage_report(tmp_path)

    (call,) = report.spawn_calls
    assert call.deny_reason == "spawn arguments are not valid JSON"
    assert call.model is None
    assert report.denied_calls == 1
    assert report.route_distribution == (("?/?", 1),)


def test_usage_report_counts_namespaced_spawn_tool_names(tmp_path: Path) -> None:
    _write_rollout(
        tmp_path,
        "rollout-4-namespaced.jsonl",
        [_spawn_line("agentsspawn_agent", _v2_arguments(model="gpt-5.6-terra"))],
    )

    report = usage_report(tmp_path)

    (call,) = report.spawn_calls
    assert call.tool_name == "agentsspawn_agent"
    assert call.deny_reason == "unsupported child profile: gpt-5.6-terra / low"
