import json
import shutil
import subprocess
from pathlib import Path


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("codex-subagent-router")
    assert executable is not None
    return subprocess.run(
        [executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_render_skill_prints_the_generated_document() -> None:
    actual = _run_cli("render-skill")

    assert actual.returncode == 0
    assert actual.stdout.startswith("---\nname: codex-subagent-routing\n")
    assert "## Route profiles" in actual.stdout
    assert "do not edit by hand" in actual.stdout


def test_cli_render_skill_writes_the_document_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "codex-subagent-routing" / "SKILL.md"

    actual = _run_cli("render-skill", "--out", str(target))

    assert actual.returncode == 0
    document = json.loads(actual.stdout)
    assert document == {
        "skill_name": "codex-subagent-routing",
        "written_to": str(target),
    }
    written = target.read_text(encoding="utf-8")
    assert written.startswith("---\nname: codex-subagent-routing\n")
    assert written == _run_cli("render-skill").stdout


def test_cli_usage_report_requires_an_existing_directory(
    tmp_path: Path,
) -> None:
    actual = _run_cli("usage-report", "--sessions-dir", str(tmp_path / "missing"))

    assert actual.returncode == 1
    assert "does not exist" in actual.stderr


def test_cli_usage_report_emits_machine_readable_statistics(
    tmp_path: Path,
) -> None:
    arguments = json.dumps(
        {
            "task_name": "probe_child",
            "agent_type": "reviewer",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "fork_turns": "none",
            "message": "sentinel",
        }
    )
    rollout = tmp_path / "rollout-1-root.jsonl"
    rollout.write_text(
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "spawn_agent",
                    "arguments": arguments,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    actual = _run_cli("usage-report", "--sessions-dir", str(tmp_path))

    assert actual.returncode == 0
    document = json.loads(actual.stdout)
    assert document["sessions_scanned"] == 1
    assert document["sessions_with_spawns"] == 1
    assert document["denied_calls"] == 0
    assert document["route_distribution"] == {"gpt-5.6-sol/low": 1}
    assert document["spawn_calls"] == [
        {
            "session_file": "rollout-1-root.jsonl",
            "tool_name": "spawn_agent",
            "task_name": "probe_child",
            "agent_type": "reviewer",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "fork_turns": "none",
            "deny_reason": None,
        }
    ]
