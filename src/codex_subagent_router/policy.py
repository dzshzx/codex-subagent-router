"""Stable routing policy exposed to hook protocol adapters."""

from dataclasses import dataclass


class PolicyViolation(ValueError):
    """Raised when a requested child configuration violates routing policy."""


@dataclass(frozen=True, slots=True)
class ModelGuide:
    """One child model and the task capability it is intended to provide."""

    model: str
    purpose: str


@dataclass(frozen=True, slots=True)
class EffortGuide:
    """One reasoning depth and the task conditions that justify it."""

    reasoning_effort: str
    purpose: str
    requires_concrete_reason: bool


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Independent model and effort choices plus dynamic selection guidance."""

    models: tuple[ModelGuide, ...]
    efforts: tuple[EffortGuide, ...]
    rules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoutedCompute:
    """One explicitly validated model and reasoning-effort decision."""

    model: str
    reasoning_effort: str


_ROUTING_POLICY = RoutingPolicy(
    models=(
        ModelGuide(
            model="gpt-5.6-luna",
            purpose=(
                "Simple, low-risk, self-contained lookup, enumeration, "
                "and mechanical extraction."
            ),
        ),
        ModelGuide(
            model="gpt-5.6-terra",
            purpose=(
                "Routine bounded execution, focused code changes, "
                "cross-file reading, synthesis, and analysis."
            ),
        ),
        ModelGuide(
            model="gpt-5.6-sol",
            purpose=(
                "Complex multi-step implementation, critical review, "
                "adjudication, hard debugging, and high-risk work."
            ),
        ),
    ),
    efforts=(
        EffortGuide(
            reasoning_effort="low",
            purpose=(
                "Straightforward work with a clear path, few steps, and "
                "cheap verification."
            ),
            requires_concrete_reason=False,
        ),
        EffortGuide(
            reasoning_effort="medium",
            purpose=(
                "Routine multi-step work with a known approach and normal verification."
            ),
            requires_concrete_reason=False,
        ),
        EffortGuide(
            reasoning_effort="high",
            purpose=(
                "Ambiguous, cross-cutting, risk-sensitive, or verification-heavy work."
            ),
            requires_concrete_reason=False,
        ),
        EffortGuide(
            reasoning_effort="xhigh",
            purpose="Exceptionally hard reasoning after high is insufficient.",
            requires_concrete_reason=True,
        ),
        EffortGuide(
            reasoning_effort="max",
            purpose=(
                "Explicit highest-quality work after lower effort is insufficient."
            ),
            requires_concrete_reason=True,
        ),
    ),
    rules=(
        "Choose model from task capability, risk, and type: Luna for simple, "
        "low-risk, self-contained work; Terra for routine execution and "
        "analysis; Sol for complex implementation, critical review, hard "
        "debugging, and high-risk work.",
        "Choose reasoning_effort independently from reasoning depth, ambiguity, "
        "and verification needs.",
        "A higher effort does not compensate for a model that lacks the required "
        "capability.",
        "Use the lowest-capability model and lowest effort that remain credible "
        "for the task.",
        "Use xhigh or max only when the task requires it and state a concrete reason.",
        "Child effort ultra is prohibited.",
    ),
)
_SUPPORTED_MODELS = frozenset(guide.model for guide in _ROUTING_POLICY.models)
_SUPPORTED_CHILD_EFFORTS = frozenset(
    guide.reasoning_effort for guide in _ROUTING_POLICY.efforts
)
_PROHIBITED_CHILD_EFFORT = "ultra"


def routing_policy() -> RoutingPolicy:
    """Return independent model and effort choices with selection guidance."""

    return _ROUTING_POLICY


def validate_routed_compute(model: str, reasoning_effort: str) -> RoutedCompute:
    """Validate one explicit dynamic model and effort decision."""

    if model not in _SUPPORTED_MODELS:
        raise PolicyViolation(f"unsupported child model: {model}")
    if reasoning_effort == _PROHIBITED_CHILD_EFFORT:
        raise PolicyViolation(
            f"child reasoning effort {_PROHIBITED_CHILD_EFFORT!r} is prohibited"
        )
    if reasoning_effort not in _SUPPORTED_CHILD_EFFORTS:
        raise PolicyViolation(f"unsupported child reasoning effort: {reasoning_effort}")
    return RoutedCompute(model=model, reasoning_effort=reasoning_effort)
