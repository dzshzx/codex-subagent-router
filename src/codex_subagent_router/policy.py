"""Stable routing policy exposed to hook protocol adapters."""

from dataclasses import dataclass


class PolicyViolation(ValueError):
    """Raised when a requested child configuration violates routing policy."""


@dataclass(frozen=True, slots=True)
class Profile:
    """One automatic model and effort choice."""

    model: str
    effort: str


_ROUTINE_ROUTES = (
    Profile(
        model="gpt-5.6-terra",
        effort="medium",
    ),
    Profile(
        model="gpt-5.6-sol",
        effort="low",
    ),
    Profile(
        model="gpt-5.6-terra",
        effort="high",
    ),
    Profile(
        model="gpt-5.6-sol",
        effort="medium",
    ),
    Profile(
        model="gpt-5.6-sol",
        effort="high",
    ),
)

_CONDITIONAL_ROUTES = (
    Profile(
        model="gpt-5.6-sol",
        effort="xhigh",
    ),
    Profile(
        model="gpt-5.6-sol",
        effort="max",
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
        "Use the lowest credible routine profile.",
        f"Escalate to {conditional_efforts} only when the task requires it.",
        f"Child effort {_PROHIBITED_CHILD_EFFORT} is prohibited.",
    )
