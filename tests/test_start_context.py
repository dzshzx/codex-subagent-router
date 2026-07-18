import json

import pytest

from codex_subagent_router import (
    RoleContract,
    SessionStartInput,
    SessionStartOutput,
    SubagentStartInput,
    SubagentStartOutput,
    parse_hook_input,
    role_contracts,
    session_start_context,
    subagent_start_context,
)


def _subagent_start(agent_type: str) -> SubagentStartInput:
    document = json.dumps(
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "agent_id": "child-1",
            "agent_type": agent_type,
            "transcript_path": None,
            "cwd": "/workspace/project",
            "hook_event_name": "SubagentStart",
            "model": "gpt-5.6-sol",
            "permission_mode": "plan",
        }
    )
    parsed = parse_hook_input(document)
    assert isinstance(parsed, SubagentStartInput)
    return parsed


def _session_start(source: str) -> SessionStartInput:
    document = json.dumps(
        {
            "session_id": "session-1",
            "transcript_path": None,
            "cwd": "/workspace/project",
            "hook_event_name": "SessionStart",
            "model": "gpt-5.6-sol",
            "permission_mode": "plan",
            "source": source,
        }
    )
    parsed = parse_hook_input(document)
    assert isinstance(parsed, SessionStartInput)
    return parsed


def test_managed_identity_contracts_match_the_project_identities() -> None:
    assert role_contracts() == (
        RoleContract(
            agent_type="researcher",
            description=(
                "Primary-source researcher for external documentation, APIs, "
                "specifications, and upstream code."
            ),
            additional_context="""You are the researcher for this delegated task.

- Investigate external documentation, specifications, APIs, upstream source, and necessary local evidence.
- Prefer primary and authoritative sources.
- Distinguish verified facts, source-based inferences, and open questions.
- Cite material claims near each claim.
- Write only the specifically requested research artifact when required.
- Do not make unrelated project changes.

Complete when the question is answered with enough evidence for a later implementation or decision.""",
        ),
        RoleContract(
            agent_type="reviewer",
            description="Read-only reviewer for one bounded diff axis.",
            additional_context="""You are the reviewer for one bounded, read-only diff axis.

- Respect the fixed point, diff scope, standards sources, specification, and axis in the task brief.
- Review exactly one axis, such as Standards or Spec.
- Report only actionable findings supported by file, hunk, standard, or specification evidence.
- Rank findings by severity and explain the observable impact.
- Do not edit files or broaden the review into implementation.

Standards and Spec use separate reviewer instances; the task brief defines the temporary axis.""",
        ),
    )


def test_subagent_start_injects_the_exact_managed_role_contract() -> None:
    hook_input = _subagent_start("reviewer")

    assert subagent_start_context(hook_input) == SubagentStartOutput(
        additional_context="""You are the reviewer for one bounded, read-only diff axis.

- Respect the fixed point, diff scope, standards sources, specification, and axis in the task brief.
- Review exactly one axis, such as Standards or Spec.
- Report only actionable findings supported by file, hunk, standard, or specification evidence.
- Rank findings by severity and explain the observable impact.
- Do not edit files or broaden the review into implementation.

Standards and Spec use separate reviewer instances; the task brief defines the temporary axis."""
    )


@pytest.mark.parametrize(
    "agent_type",
    ("researcher", "reviewer"),
)
def test_every_managed_identity_has_subagent_start_context(agent_type: str) -> None:
    assert subagent_start_context(_subagent_start(agent_type)) is not None


@pytest.mark.parametrize(
    "agent_type",
    (
        "default",
        "architecture_explorer",
    ),
)
def test_subagent_start_does_not_override_unmanaged_identities(agent_type: str) -> None:
    assert subagent_start_context(_subagent_start(agent_type)) is None


def test_session_start_injects_routing_guidance_derived_from_project_sources() -> None:
    hook_input = _session_start("startup")

    assert session_start_context(hook_input) == SessionStartOutput(
        additional_context="""Codex subagent routing policy for this root session:

Choose every routed child explicitly with model and reasoning_effort.

Managed identities:
- researcher: Primary-source researcher for external documentation, APIs, specifications, and upstream code.
- reviewer: Read-only reviewer for one bounded diff axis.

Models:
- gpt-5.6-luna: Lightweight model.
- gpt-5.6-terra: General-purpose model.
- gpt-5.6-sol: Highest-capability model.

Reasoning efforts:
- low: Low reasoning depth.
- medium: Medium reasoning depth.
- high: High reasoning depth.
- xhigh: Extra-high reasoning depth.
- max: Maximum reasoning depth.

Prohibited child reasoning efforts: ultra.

Set agent_type when a suitable declared role exists; omit it otherwise. On MultiAgent V2, also set task_name (lowercase letters, digits, and underscores only) and fork_turns="none" for independent work or a positive integer string for limited recent context; do not use full-history all with explicit routing. On stable MultiAgent V1, leave fork_context false or omitted; do not spawn full-history forks with explicit routing. Do not omit routed fields or silently rewrite them."""
    )


@pytest.mark.parametrize("source", ("resume", "clear", "compact"))
def test_session_start_ignores_non_startup_sources(source: str) -> None:
    hook_input = _session_start(source)

    assert session_start_context(hook_input) is None
