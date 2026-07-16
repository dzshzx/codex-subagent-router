"""Start-hook context derived from routing and role sources."""

from .policy import conditional_routes, routine_routes, routing_guidance_rules
from .protocol import (
    SessionSource,
    SessionStartInput,
    SessionStartOutput,
    SubagentStartInput,
    SubagentStartOutput,
)
from .roles import role_contracts
from .validator import routed_spawn_guidance_rules


def session_start_context(hook_input: SessionStartInput) -> SessionStartOutput | None:
    """Return routing guidance for a root session startup."""
    if hook_input.source is not SessionSource.STARTUP:
        return None
    managed_roles = "\n".join(
        f"- {contract.agent_type}: {contract.description}"
        for contract in role_contracts()
    )
    routine_profiles = "\n".join(
        f"- {profile.name}: {profile.model} / {profile.effort} — {profile.purpose}"
        for profile in routine_routes()
    )
    conditional_profiles = "\n".join(
        f"- {profile.name}: {profile.model} / {profile.effort} — {profile.purpose}"
        for profile in conditional_routes()
    )
    spawn_rules = routed_spawn_guidance_rules()
    closing_rules = " ".join(routing_guidance_rules() + spawn_rules[1:])
    return SessionStartOutput(
        additional_context=(
            "Codex subagent routing policy for this root session:\n\n"
            f"{spawn_rules[0]}\n\n"
            f"Managed roles:\n{managed_roles}\n\n"
            "Routine profiles in ascending capability order:\n"
            f"{routine_profiles}\n\n"
            "Conditional escalation profiles in ascending capability order:\n"
            f"{conditional_profiles}\n\n"
            f"{closing_rules}"
        )
    )


def subagent_start_context(
    hook_input: SubagentStartInput,
) -> SubagentStartOutput | None:
    """Return managed role context for a child, or no output for other roles."""
    for contract in role_contracts():
        if contract.agent_type == hook_input.agent_type:
            return SubagentStartOutput(additional_context=contract.additional_context)
    return None
