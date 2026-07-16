"""Stable routing policy exposed to hook protocol adapters."""

from dataclasses import dataclass


class PolicyViolation(ValueError):
    """Raised when a requested child configuration violates routing policy."""


@dataclass(frozen=True, slots=True)
class Profile:
    """One named automatic model and effort choice."""

    name: str
    model: str
    effort: str
    purpose: str


_ROUTINE_ROUTES = (
    Profile(
        name="scout",
        model="gpt-5.6-terra",
        effort="medium",
        purpose="Broad reads, enumeration, and mechanical extraction.",
    ),
    Profile(
        name="worker",
        model="gpt-5.6-sol",
        effort="low",
        purpose="Routine bounded execution with fast turnaround.",
    ),
    Profile(
        name="analyst",
        model="gpt-5.6-terra",
        effort="high",
        purpose="Wide reading, digestion, and first drafts on the budget model.",
    ),
    Profile(
        name="builder",
        model="gpt-5.6-sol",
        effort="medium",
        purpose="Standard implementation and multi-step changes.",
    ),
    Profile(
        name="judge",
        model="gpt-5.6-sol",
        effort="high",
        purpose="Critical review, adjudication, and hard debugging.",
    ),
)

_CONDITIONAL_ROUTES = (
    Profile(
        name="escalation_xhigh",
        model="gpt-5.6-sol",
        effort="xhigh",
        purpose="Escalation when judge-level work needs deeper reasoning.",
    ),
    Profile(
        name="escalation_max",
        model="gpt-5.6-sol",
        effort="max",
        purpose="Maximum effort; requires a stated concrete reason.",
    ),
)

_PROHIBITED_CHILD_EFFORT = "ultra"

_SUPPORTED_CHILD_EFFORTS = frozenset(
    profile.effort for profile in _ROUTINE_ROUTES + _CONDITIONAL_ROUTES
)


def routine_routes() -> tuple[Profile, ...]:
    """Return routine automatic routes in ascending capability order."""
    return _ROUTINE_ROUTES


def conditional_routes() -> tuple[Profile, ...]:
    """Return conditional escalation routes in ascending capability order."""
    return _CONDITIONAL_ROUTES


def validate_child_effort(effort: str) -> str:
    """Return a supported child effort or raise a clear policy error."""
    if effort == _PROHIBITED_CHILD_EFFORT:
        raise PolicyViolation(
            f"child reasoning effort {_PROHIBITED_CHILD_EFFORT!r} is prohibited"
        )
    if effort not in _SUPPORTED_CHILD_EFFORTS:
        raise PolicyViolation(f"unsupported child reasoning effort: {effort}")
    return effort


def routing_guidance_rules() -> tuple[str, ...]:
    """Return parent-facing selection rules derived from routing policy."""
    conditional_efforts = " or ".join(profile.effort for profile in _CONDITIONAL_ROUTES)
    return (
        "Pick the profile whose purpose matches the task; do not default "
        "to the parent session's compute.",
        f"Escalate to {conditional_efforts} only when the task requires it.",
        f"Child effort {_PROHIBITED_CHILD_EFFORT} is prohibited.",
    )
