"""Stable routing policy exposed to hook protocol adapters."""

from dataclasses import dataclass


class PolicyViolation(ValueError):
    """Raised when a requested child configuration violates routing policy."""


@dataclass(frozen=True, slots=True)
class ModelOption:
    """One supported child model and its description."""

    model: str
    description: str


@dataclass(frozen=True, slots=True)
class EffortOption:
    """One supported reasoning effort and its description."""

    reasoning_effort: str
    description: str


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Supported model and effort options."""

    models: tuple[ModelOption, ...]
    efforts: tuple[EffortOption, ...]
    prohibited_efforts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoutedCompute:
    """One explicitly validated model and reasoning-effort decision."""

    model: str
    reasoning_effort: str


_ROUTING_POLICY = RoutingPolicy(
    models=(
        ModelOption(
            model="gpt-5.6-luna",
            description="Lightweight model.",
        ),
        ModelOption(
            model="gpt-5.6-terra",
            description="General-purpose model.",
        ),
        ModelOption(
            model="gpt-5.6-sol",
            description="Highest-capability model.",
        ),
    ),
    efforts=(
        EffortOption(
            reasoning_effort="low",
            description="Low reasoning depth.",
        ),
        EffortOption(
            reasoning_effort="medium",
            description="Medium reasoning depth.",
        ),
        EffortOption(
            reasoning_effort="high",
            description="High reasoning depth.",
        ),
        EffortOption(
            reasoning_effort="xhigh",
            description="Extra-high reasoning depth.",
        ),
        EffortOption(
            reasoning_effort="max",
            description="Maximum reasoning depth.",
        ),
    ),
    prohibited_efforts=("ultra",),
)
_SUPPORTED_MODELS = frozenset(guide.model for guide in _ROUTING_POLICY.models)
_SUPPORTED_CHILD_EFFORTS = frozenset(
    guide.reasoning_effort for guide in _ROUTING_POLICY.efforts
)
_PROHIBITED_CHILD_EFFORTS = frozenset(_ROUTING_POLICY.prohibited_efforts)


def routing_policy() -> RoutingPolicy:
    """Return supported model and effort options."""

    return _ROUTING_POLICY


def validate_routed_compute(model: str, reasoning_effort: str) -> RoutedCompute:
    """Validate one explicit dynamic model and effort decision."""

    if model not in _SUPPORTED_MODELS:
        raise PolicyViolation(f"unsupported child model: {model}")
    if reasoning_effort in _PROHIBITED_CHILD_EFFORTS:
        raise PolicyViolation(
            f"child reasoning effort {reasoning_effort!r} is prohibited"
        )
    if reasoning_effort not in _SUPPORTED_CHILD_EFFORTS:
        raise PolicyViolation(f"unsupported child reasoning effort: {reasoning_effort}")
    return RoutedCompute(model=model, reasoning_effort=reasoning_effort)
