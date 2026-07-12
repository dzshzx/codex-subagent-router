"""Stable routing policy exposed to hook protocol adapters."""

from dataclasses import dataclass


SUPPORTED_CHILD_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max"})


class PolicyViolation(ValueError):
    """Raised when a requested child configuration violates routing policy."""


@dataclass(frozen=True, slots=True)
class Route:
    """One automatic model and effort choice with its routing intent."""

    name: str
    model: str
    effort: str
    intent: str


_ROUTINE_ROUTES = (
    Route(
        name="bounded-economy",
        model="gpt-5.6-terra",
        effort="medium",
        intent="Batch work with clear boundaries and quickly verifiable results.",
    ),
    Route(
        name="bounded-fast-quality",
        model="gpt-5.6-sol",
        effort="low",
        intent="Interactive bounded work that needs stronger first-pass reliability.",
    ),
    Route(
        name="routine",
        model="gpt-5.6-terra",
        effort="high",
        intent="Routine coding, research, and review.",
    ),
    Route(
        name="deep",
        model="gpt-5.6-sol",
        effort="medium",
        intent="Cross-file work with multiple dependencies or sustained reasoning.",
    ),
    Route(
        name="critical",
        model="gpt-5.6-sol",
        effort="high",
        intent="High-impact, high-error-cost, or long-horizon work.",
    ),
)

_CONDITIONAL_ROUTES = (
    Route(
        name="escalate",
        model="gpt-5.6-sol",
        effort="xhigh",
        intent="Critical work that needs higher reliability or has concrete failure evidence.",
    ),
    Route(
        name="ceiling",
        model="gpt-5.6-sol",
        effort="max",
        intent="Work explicitly requiring the highest observed reliability.",
    ),
)


def routine_routes() -> tuple[Route, ...]:
    """Return routine automatic routes in ascending capability order."""
    return _ROUTINE_ROUTES


def conditional_routes() -> tuple[Route, ...]:
    """Return conditional escalation routes in ascending capability order."""
    return _CONDITIONAL_ROUTES


def validate_child_effort(effort: str) -> str:
    """Return a supported child effort or raise a clear policy error."""
    if effort == "ultra":
        raise PolicyViolation("child reasoning effort 'ultra' is prohibited")
    if effort not in SUPPORTED_CHILD_EFFORTS:
        raise PolicyViolation(f"unsupported child reasoning effort: {effort}")
    return effort
