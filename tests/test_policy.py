import unittest

from codex_subagent_router import (
    PolicyViolation,
    conditional_routes,
    routine_routes,
    validate_child_effort,
)


class RoutingPolicyTests(unittest.TestCase):
    def test_routine_routes_match_the_initial_policy(self) -> None:
        actual = tuple(
            (route.name, route.model, route.effort) for route in routine_routes()
        )

        self.assertEqual(
            actual,
            (
                ("bounded-economy", "gpt-5.6-terra", "medium"),
                ("bounded-fast-quality", "gpt-5.6-sol", "low"),
                ("routine", "gpt-5.6-terra", "high"),
                ("deep", "gpt-5.6-sol", "medium"),
                ("critical", "gpt-5.6-sol", "high"),
            ),
        )

    def test_conditional_routes_match_the_initial_policy(self) -> None:
        actual = tuple(
            (route.name, route.model, route.effort)
            for route in conditional_routes()
        )

        self.assertEqual(
            actual,
            (
                ("escalate", "gpt-5.6-sol", "xhigh"),
                ("ceiling", "gpt-5.6-sol", "max"),
            ),
        )

    def test_supported_child_efforts_are_accepted(self) -> None:
        efforts = ("low", "medium", "high", "xhigh", "max")

        self.assertEqual(
            tuple(validate_child_effort(effort) for effort in efforts),
            efforts,
        )

    def test_ultra_child_effort_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            PolicyViolation,
            "child reasoning effort 'ultra' is prohibited",
        ):
            validate_child_effort("ultra")

    def test_unknown_child_effort_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            PolicyViolation,
            "unsupported child reasoning effort: turbo",
        ):
            validate_child_effort("turbo")


if __name__ == "__main__":
    unittest.main()
