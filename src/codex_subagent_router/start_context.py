"""Start-hook context derived from routing and role sources."""

from .policy import routing_policy
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
    managed_identities = "\n".join(
        f"- {contract.agent_type}: {contract.description}"
        for contract in role_contracts()
    )
    policy = routing_policy()
    model_options = "\n".join(
        f"- {option.model}: {option.description}" for option in policy.models
    )
    effort_options = "\n".join(
        f"- {option.reasoning_effort}: {option.description}"
        for option in policy.efforts
    )
    prohibited_efforts = ", ".join(policy.prohibited_efforts)
    spawn_rules = routed_spawn_guidance_rules()
    closing_rules = " ".join(spawn_rules[1:])
    return SessionStartOutput(
        additional_context=(
            "Codex subagent routing policy for this root session:\n\n"
            f"{spawn_rules[0]}\n\n"
            f"Managed identities:\n{managed_identities}\n\n"
            "Models:\n"
            f"{model_options}\n\n"
            "Reasoning efforts:\n"
            f"{effort_options}\n\n"
            f"Prohibited child reasoning efforts: {prohibited_efforts}.\n\n"
            f"{closing_rules}"
        )
    )


def subagent_start_context(
    hook_input: SubagentStartInput,
) -> SubagentStartOutput | None:
    """Return managed identity context, or no output for other identities."""
    for contract in role_contracts():
        if contract.agent_type == hook_input.agent_type:
            return SubagentStartOutput(additional_context=contract.additional_context)
    return None
