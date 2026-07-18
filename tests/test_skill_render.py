from codex_subagent_router import render_skill_markdown, skill_name


def test_skill_name_is_stable() -> None:
    assert skill_name() == "codex-subagent-routing"


def test_skill_document_starts_with_frontmatter() -> None:
    document = render_skill_markdown()

    assert document.startswith(
        """---
name: codex-subagent-routing
description: Route Codex subagent spawns with explicit model and reasoning effort. Use when delegating work to subagents, choosing task-aware compute, parallelizing reads or reviews, or writing a child task packet.
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


def test_skill_document_renders_independent_model_and_effort_guidance() -> None:
    document = render_skill_markdown()

    assert (
        "| gpt-5.6-luna | Simple, low-risk, self-contained lookup, "
        "enumeration, and mechanical extraction. |" in document
    )
    assert (
        "| gpt-5.6-sol | Complex multi-step implementation, critical review, "
        "adjudication, hard debugging, and high-risk work. |" in document
    )
    assert (
        "| low | Straightforward work with a clear path, few steps, and cheap "
        "verification. | no |" in document
    )
    assert (
        "| xhigh | Exceptionally hard reasoning after high is insufficient. "
        "| yes |" in document
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
    assert "## Dynamic route planning" in document
    assert (
        "Choose reasoning_effort independently from reasoning depth, ambiguity, "
        "and verification needs." in document
    )
    assert "A higher effort does not compensate for a model" in document


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
    assert "one higher-capability model or effort" in document
