"""Render routing policy and dispatch guidance as one agent-skill document."""

from .policy import routing_policy
from .roles import role_contracts
from .skill_source import (
    delegation_signals,
    keep_local_signals,
    result_contract_rules,
    task_packet_template,
)
from .validator import routed_spawn_guidance_rules

_SKILL_NAME = "codex-subagent-routing"
_SKILL_DESCRIPTION = (
    "Route Codex subagent spawns with explicit model and reasoning effort. "
    "Use when delegating work to subagents, choosing task-aware compute, "
    "parallelizing reads or reviews, or writing a child task packet."
)


def skill_name() -> str:
    """Return the stable name of the generated skill document."""
    return _SKILL_NAME


def render_skill_markdown() -> str:
    """Return the complete generated skill document."""
    sections = (
        _frontmatter(),
        _header(),
        _delegation_section(),
        _dynamic_routing_section(),
        _role_section(),
        _spawn_contract_section(),
        _task_packet_section(),
        _result_contract_section(),
    )
    return "\n\n".join(sections) + "\n"


def _frontmatter() -> str:
    return f"""---
name: {_SKILL_NAME}
description: {_SKILL_DESCRIPTION}
---"""


def _header() -> str:
    return (
        "# Codex subagent routing\n\n"
        "Generated from codex_subagent_router policy sources; do not edit "
        "by hand.\nRegenerate with: codex-subagent-router render-skill"
    )


def _delegation_section() -> str:
    delegate = "\n".join(f"- {signal}" for signal in delegation_signals())
    keep = "\n".join(f"- {signal}" for signal in keep_local_signals())
    return (
        "## When to delegate\n\n"
        f"Delegate when any signal holds:\n{delegate}\n\n"
        f"Keep in the parent thread:\n{keep}"
    )


def _dynamic_routing_section() -> str:
    policy = routing_policy()
    model_rows = "\n".join(
        f"| {guide.model} | {guide.purpose} |" for guide in policy.models
    )
    effort_rows = "\n".join(
        "| "
        f"{guide.reasoning_effort} | {guide.purpose} | "
        f"{'yes' if guide.requires_concrete_reason else 'no'} |"
        for guide in policy.efforts
    )
    rules = "\n".join(f"- {rule}" for rule in policy.rules)
    return (
        "## Dynamic route planning\n\n"
        "Choose model by the capability the task requires:\n\n"
        "| Model | Use for |\n|---|---|\n"
        f"{model_rows}\n\n"
        "Choose reasoning_effort independently by reasoning depth:\n\n"
        "| Effort | Use for | Concrete reason required |\n|---|---|---|\n"
        f"{effort_rows}\n\n"
        f"Decision rules:\n{rules}"
    )


def _role_section() -> str:
    roles = "\n".join(
        f"- {contract.agent_type}: {contract.description}"
        for contract in role_contracts()
    )
    return (
        "## Managed roles (optional layer)\n\n"
        "Use these agent_type values only when the roles are declared in "
        "the active configuration; otherwise omit agent_type and route by "
        f"model and effort alone.\n\n{roles}"
    )


def _spawn_contract_section() -> str:
    rules = "\n".join(f"- {rule}" for rule in routed_spawn_guidance_rules())
    return f"## Spawn contract\n\n{rules}"


def _task_packet_section() -> str:
    return (
        "## Task packet template\n\n"
        "Fill this skeleton for every child message:\n\n"
        f"```markdown\n{task_packet_template()}\n```"
    )


def _result_contract_section() -> str:
    rules = "\n".join(f"- {rule}" for rule in result_contract_rules())
    return f"## Result contract\n\n{rules}"
