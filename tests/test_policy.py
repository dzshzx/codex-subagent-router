import pytest

from codex_subagent_router import (
    EffortGuide,
    ModelGuide,
    PolicyViolation,
    RoutedCompute,
    routing_policy,
    validate_routed_compute,
)


def test_routing_policy_lists_model_capabilities_independently() -> None:
    assert routing_policy().models == (
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
    )


def test_routing_policy_lists_reasoning_depths_independently() -> None:
    assert routing_policy().efforts == (
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
            purpose=("Exceptionally hard reasoning after high is insufficient."),
            requires_concrete_reason=True,
        ),
        EffortGuide(
            reasoning_effort="max",
            purpose=(
                "Explicit highest-quality work after lower effort is insufficient."
            ),
            requires_concrete_reason=True,
        ),
    )


@pytest.mark.parametrize(
    ("model", "effort"),
    (
        ("gpt-5.6-luna", "high"),
        ("gpt-5.6-terra", "xhigh"),
        ("gpt-5.6-sol", "low"),
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


def test_routing_policy_locks_dynamic_selection_rules() -> None:
    assert routing_policy().rules == (
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
    )


def test_every_routing_option_states_a_purpose() -> None:
    policy = routing_policy()

    for option in policy.models + policy.efforts:
        assert option.purpose.strip()


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
