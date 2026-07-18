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
    managed_roles = "\n".join(
        f"- {contract.agent_type}: {contract.description}"
        for contract in role_contracts()
    )
    policy = routing_policy()
    model_guidance = "\n".join(
        f"- {guide.model}: {guide.purpose}" for guide in policy.models
    )
    effort_guidance = "\n".join(
        f"- {guide.reasoning_effort}: {guide.purpose}"
        + (" State a concrete reason." if guide.requires_concrete_reason else "")
        for guide in policy.efforts
    )
    spawn_rules = routed_spawn_guidance_rules()
    closing_rules = " ".join(policy.rules + spawn_rules[1:])
    return SessionStartOutput(
        additional_context=(
            "Codex subagent routing policy for this root session:\n\n"
            f"{spawn_rules[0]}\n\n"
            f"Managed roles:\n{managed_roles}\n\n"
            "Choose model by task capability:\n"
            f"{model_guidance}\n\n"
            "Choose reasoning_effort independently by reasoning depth:\n"
            f"{effort_guidance}\n\n"
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
