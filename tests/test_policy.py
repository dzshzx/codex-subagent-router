from dataclasses import fields

import pytest

from codex_subagent_router import (
    EffortOption,
    ModelOption,
    PolicyViolation,
    RoutedCompute,
    RoutingPolicy,
    routing_policy,
    validate_routed_compute,
)


def test_routing_policy_lists_model_options_independently() -> None:
    assert routing_policy().models == (
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
    )


def test_routing_policy_lists_reasoning_depths_independently() -> None:
    assert routing_policy().efforts == (
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
    )


@pytest.mark.parametrize(
    ("model", "effort"),
    (
        ("gpt-5.6-luna", "high"),
        ("gpt-5.6-terra", "xhigh"),
        ("gpt-5.6-sol", "max"),
    ),
)
def test_model_and_effort_are_validated_independently(
    model: str,
    effort: str,
) -> None:
    assert validate_routed_compute(model, effort) == RoutedCompute(
        model=model,
        reasoning_effort=effort,
    )


def test_routing_policy_interface_contains_only_supported_options() -> None:
    assert tuple(field.name for field in fields(RoutingPolicy)) == (
        "models",
        "efforts",
        "prohibited_efforts",
    )


def test_routing_policy_lists_prohibited_efforts() -> None:
    assert routing_policy().prohibited_efforts == ("ultra",)


def test_ultra_child_effort_is_rejected() -> None:
    with pytest.raises(
        PolicyViolation,
        match="child reasoning effort 'ultra' is prohibited",
    ):
        validate_routed_compute("gpt-5.6-sol", "ultra")


def test_unknown_child_effort_is_rejected() -> None:
    with pytest.raises(
        PolicyViolation,
        match="unsupported child reasoning effort: turbo",
    ):
        validate_routed_compute("gpt-5.6-terra", "turbo")


def test_unknown_child_model_is_rejected() -> None:
    with pytest.raises(
        PolicyViolation,
        match="unsupported child model: gpt-5.6-nebula",
    ):
        validate_routed_compute("gpt-5.6-nebula", "medium")
