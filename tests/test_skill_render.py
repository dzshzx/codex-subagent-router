from codex_subagent_router import render_skill_markdown, skill_name


def test_skill_name_is_stable() -> None:
    assert skill_name() == "codex-subagent-routing"


def test_skill_document_starts_with_frontmatter() -> None:
    document = render_skill_markdown()

    assert document.startswith(
        """---
name: codex-subagent-routing
description: Route Codex subagent spawns with explicit model and reasoning effort. Use when delegating work, parallelizing tasks, or writing a child task packet.
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


def test_skill_document_renders_independent_model_and_effort_options() -> None:
    document = render_skill_markdown()

    assert "Models:" in document
    assert "Reasoning efforts:" in document
    assert "| gpt-5.6-luna | Lightweight model. |" in document
    assert "| gpt-5.6-terra | General-purpose model. |" in document
    assert "| gpt-5.6-sol | Highest-capability model. |" in document
    assert "| low | Low reasoning depth. |" in document
    assert "| xhigh | Extra-high reasoning depth. |" in document
    assert "| max | Maximum reasoning depth. |" in document
    assert "Prohibited child reasoning efforts: ultra." in document


def test_skill_document_states_the_spawn_contract() -> None:
    document = render_skill_markdown()

    assert "task_name (lowercase letters, digits, and underscores only)" in document
    assert (
        "Choose every routed child explicitly with model and "
        "reasoning_effort." in document
    )
    assert (
        "Set agent_type when a suitable declared role exists; omit it "
        "otherwise." in document
    )
    assert "## Route options" in document


def test_skill_document_lists_the_managed_identities_as_an_optional_layer() -> None:
    document = render_skill_markdown()

    assert "## Managed identities (optional layer)" in document
    assert (
        "Use these agent_type values only when the identities are declared "
        "in the active configuration" in document
    )
    assert "otherwise omit agent_type and route by model and effort alone." in document
    for line in (
        "- researcher: Primary-source researcher for external documentation, "
        "APIs, specifications, and upstream code.",
        "- reviewer: Read-only reviewer for one bounded diff axis.",
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
    assert "Retry one failed child at most once" in document
