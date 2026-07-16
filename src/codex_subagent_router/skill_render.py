"""Render routing policy and dispatch guidance as one agent-skill document."""

from .policy import conditional_routes, routine_routes, routing_guidance_rules
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
    "Use when delegating work to subagents, choosing a spawn profile, "
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
        _profile_section(),
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


def _profile_section() -> str:
    table_head = "| Profile | Model | Effort | Use for |\n|---|---|---|---|"
    routine_rows = "\n".join(
        f"| {profile.name} | {profile.model} | {profile.effort} | {profile.purpose} |"
        for profile in routine_routes()
    )
    conditional_rows = "\n".join(
        f"| {profile.name} | {profile.model} | {profile.effort} | {profile.purpose} |"
        for profile in conditional_routes()
    )
    rules = " ".join(routing_guidance_rules())
    return (
        "## Route profiles\n\n"
        "Routine profiles in ascending capability order:\n\n"
        f"{table_head}\n{routine_rows}\n\n"
        "Conditional escalation profiles:\n\n"
        f"{table_head}\n{conditional_rows}\n\n"
        f"{rules}"
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
