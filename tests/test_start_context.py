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


def test_managed_role_contracts_match_the_project_roles() -> None:
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
        RoleContract(
            agent_type="architecture_explorer",
            description=(
                "Read-only architecture explorer for broad codebase scans and "
                "deepening opportunities."
            ),
            additional_context="""You are the architecture explorer for this delegated codebase scan.

- Read relevant domain context and architecture decisions before judging the design.
- Trace responsibilities, seams, adapters, invariants, and dependency direction across modules.
- Identify deepening opportunities with concrete file evidence and downstream leverage.
- Return candidates and their trade-offs only.
- Do not produce the final report, design a replacement interface, or implement a refactor.

This role is broader than the built-in explorer used for specific, well-scoped questions.""",
        ),
        RoleContract(
            agent_type="interface_designer",
            description=(
                "Read-only module-interface designer for independent API and "
                "module-shape alternatives."
            ),
            additional_context="""You are the interface designer for one independent module or API alternative.

- Generate one genuinely distinct design from the supplied technical brief.
- State invariants, ordering, error modes, usage, and hidden implementation.
- Define dependency adapters and explain the design's trade-offs.
- Use project domain vocabulary and respect existing architecture decisions.
- Stay independent of parallel designs so the alternatives differ materially.
- Do not edit files or implement the design.

The task brief supplies the constraint that distinguishes this alternative.""",
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
    ("researcher", "reviewer", "architecture_explorer", "interface_designer"),
)
def test_every_managed_role_has_subagent_start_context(agent_type: str) -> None:
    assert subagent_start_context(_subagent_start(agent_type)) is not None


@pytest.mark.parametrize("agent_type", ("worker", "explorer", "custom_role"))
def test_subagent_start_does_not_override_unmanaged_roles(agent_type: str) -> None:
    assert subagent_start_context(_subagent_start(agent_type)) is None


def test_session_start_injects_routing_guidance_derived_from_project_sources() -> None:
    hook_input = _session_start("startup")

    assert session_start_context(hook_input) == SessionStartOutput(
        additional_context="""Codex subagent routing policy for this root session:

Choose every routed child explicitly with model and reasoning_effort.

Managed roles:
- researcher: Primary-source researcher for external documentation, APIs, specifications, and upstream code.
- reviewer: Read-only reviewer for one bounded diff axis.
- architecture_explorer: Read-only architecture explorer for broad codebase scans and deepening opportunities.
- interface_designer: Read-only module-interface designer for independent API and module-shape alternatives.

Choose model by task capability:
- gpt-5.6-luna: Simple, low-risk, self-contained lookup, enumeration, and mechanical extraction.
- gpt-5.6-terra: Routine bounded execution, focused code changes, cross-file reading, synthesis, and analysis.
- gpt-5.6-sol: Complex multi-step implementation, critical review, adjudication, hard debugging, and high-risk work.

Choose reasoning_effort independently by reasoning depth:
- low: Straightforward work with a clear path, few steps, and cheap verification.
- medium: Routine multi-step work with a known approach and normal verification.
- high: Ambiguous, cross-cutting, risk-sensitive, or verification-heavy work.
- xhigh: Exceptionally hard reasoning after high is insufficient. State a concrete reason.
- max: Explicit highest-quality work after lower effort is insufficient. State a concrete reason.

Choose model from task capability, risk, and type: Luna for simple, low-risk, self-contained work; Terra for routine execution and analysis; Sol for complex implementation, critical review, hard debugging, and high-risk work. Choose reasoning_effort independently from reasoning depth, ambiguity, and verification needs. A higher effort does not compensate for a model that lacks the required capability. Use the lowest-capability model and lowest effort that remain credible for the task. Use xhigh or max only when the task requires it and state a concrete reason. Child effort ultra is prohibited. Set agent_type when a suitable declared role exists; omit it otherwise. On MultiAgent V2, also set task_name (lowercase letters, digits, and underscores only) and fork_turns="none" for independent work or a positive integer string for limited recent context; do not use full-history all with explicit routing. On stable MultiAgent V1, leave fork_context false or omitted; do not spawn full-history forks with explicit routing. Do not omit routed fields or silently rewrite them."""
    )


@pytest.mark.parametrize("source", ("resume", "clear", "compact"))
def test_session_start_ignores_non_startup_sources(source: str) -> None:
    hook_input = _session_start(source)

    assert session_start_context(hook_input) is None
