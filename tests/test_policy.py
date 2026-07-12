import pytest

from codex_subagent_router import (
    PolicyViolation,
    conditional_routes,
    routine_routes,
    validate_child_effort,
)


def test_routine_routes_match_the_initial_policy() -> None:
    actual = tuple((route.model, route.effort) for route in routine_routes())

    assert actual == (
        ("gpt-5.6-terra", "medium"),
        ("gpt-5.6-sol", "low"),
        ("gpt-5.6-terra", "high"),
        ("gpt-5.6-sol", "medium"),
        ("gpt-5.6-sol", "high"),
    )


def test_conditional_routes_match_the_initial_policy() -> None:
    actual = tuple((route.model, route.effort) for route in conditional_routes())

    assert actual == (
        ("gpt-5.6-sol", "xhigh"),
        ("gpt-5.6-sol", "max"),
    )


def test_supported_child_efforts_are_accepted() -> None:
    efforts = ("low", "medium", "high", "xhigh", "max")

    assert tuple(validate_child_effort(effort) for effort in efforts) == efforts


def test_ultra_child_effort_is_rejected() -> None:
    with pytest.raises(
        PolicyViolation,
        match="child reasoning effort 'ultra' is prohibited",
    ):
        validate_child_effort("ultra")


def test_unknown_child_effort_is_rejected() -> None:
    with pytest.raises(
        PolicyViolation,
        match="unsupported child reasoning effort: turbo",
    ):
        validate_child_effort("turbo")
