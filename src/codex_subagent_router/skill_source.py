"""Dispatch-guidance text owned by the skill rendering surface."""


def delegation_signals() -> tuple[str, ...]:
    """Return signals that favor delegating work to a routed child."""
    return (
        "Two or more independent workstreams can run in parallel.",
        "A broad read, search, or enumeration would flood the parent "
        "context with intermediate noise.",
        "The work spans several files or sources but returns a compact conclusion.",
        "An independent check or review would reduce the parent's "
        "self-confirmation bias.",
    )


def keep_local_signals() -> tuple[str, ...]:
    """Return signals that keep work in the parent thread."""
    return (
        "A simple question, status query, or single-file small edit.",
        "Strongly sequential work where each step depends on the previous result.",
        "Anything the parent can answer from context it already loaded.",
        "Publishing, payments, deletion, account, or production changes.",
    )


def result_contract_rules() -> tuple[str, ...]:
    """Return parent-facing rules for child results and dispatch economy."""
    return (
        "Ask children for conclusions plus file:line evidence coordinates, "
        "not pasted file bodies; read coordinates on demand.",
        "Give every child an explicit return structure and length budget.",
        "Split parallel children across disjoint files, modules, or topics.",
        "Escalate one failed child at most once — a follow-up or one "
        "higher-capability model or effort — then take the work back into "
        "the parent.",
        "Each child costs a fixed startup overhead; do not delegate work "
        "smaller than that overhead.",
    )


def task_packet_template() -> str:
    """Return the reusable child task packet skeleton."""
    return """# Task identity
You are the {agent_type} for this delegated task. Do not spawn further agents.

## Goal
- Overall goal:
- Your bounded subgoal:

## Boundaries
- May read:
- May write (if any):
- Do not touch:

## Return contract
- Return conclusions with file:line evidence coordinates and confidence.
- Do not paste large source excerpts.
- Structure and length budget:

## Acceptance
- Done when:
- Required verification:
- On missing information: report the gap; do not guess."""
