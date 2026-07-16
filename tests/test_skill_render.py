from codex_subagent_router import render_skill_markdown, skill_name


def test_skill_name_is_stable() -> None:
    assert skill_name() == "codex-subagent-routing"


def test_skill_document_starts_with_frontmatter() -> None:
    document = render_skill_markdown()

    assert document.startswith(
        """---
name: codex-subagent-routing
description: Route Codex subagent spawns with explicit model and reasoning effort. Use when delegating work to subagents, choosing a spawn profile, parallelizing reads or reviews, or writing a child task packet.
---
"""
    )


def test_skill_document_marks_itself_as_generated() -> None:
    document = render_skill_markdown()

    assert (
        "Generated from codex_subagent_router policy sources; do not edit by hand."
        in document
    )
    assert "Regenerate with: codex-subagent-router render-skill" in document


def test_skill_document_renders_named_route_profiles() -> None:
    document = render_skill_markdown()

    assert (
        "| scout | gpt-5.6-terra | medium "
        "| Broad reads, enumeration, and mechanical extraction. |" in document
    )
    assert (
        "| judge | gpt-5.6-sol | high "
        "| Critical review, adjudication, and hard debugging. |" in document
    )
    assert (
        "| escalation_max | gpt-5.6-sol | max "
        "| Maximum effort; requires a stated concrete reason. |" in document
    )


def test_skill_document_states_the_spawn_contract() -> None:
    document = render_skill_markdown()

    assert "Child effort ultra is prohibited." in document
    assert "task_name (lowercase letters, digits, and underscores only)" in document
    assert (
        "Choose every routed child explicitly with model and "
        "reasoning_effort." in document
    )
    assert (
        "Set agent_type when a suitable declared role exists; omit it "
        "otherwise." in document
    )
    assert (
        "Pick the profile whose purpose matches the task; do not default "
        "to the parent session's compute." in document
    )


def test_skill_document_lists_the_managed_roles_as_an_optional_layer() -> None:
    document = render_skill_markdown()

    assert "## Managed roles (optional layer)" in document
    assert "otherwise omit agent_type and route by model and effort alone." in document
    for line in (
        "- researcher: Primary-source researcher for external documentation, "
        "APIs, specifications, and upstream code.",
        "- reviewer: Read-only reviewer for one bounded diff axis.",
        "- architecture_explorer: Read-only architecture explorer for broad "
        "codebase scans and deepening opportunities.",
        "- interface_designer: Read-only module-interface designer for "
        "independent API and module-shape alternatives.",
    ):
        assert line in document


def test_skill_document_includes_delegation_and_result_guidance() -> None:
    document = render_skill_markdown()

    assert "## When to delegate" in document
    assert "Keep in the parent thread:" in document
    assert "## Task packet template" in document
    assert "Do not spawn further agents." in document
    assert "file:line evidence coordinates" in document
    assert "explicit return structure and length budget" in document
