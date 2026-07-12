"""JSON document adapters for Codex command hooks."""

from .protocol import (
    PreToolUseInput,
    ProtocolViolation,
    SessionStartInput,
    SubagentStartInput,
    encode_hook_output,
    parse_hook_input,
)
from .start_context import session_start_context, subagent_start_context
from .validator import validate_pre_tool_use


def handle_pre_tool_use_document(document: str) -> str:
    """Validate one ``PreToolUse`` JSON document and encode any denial."""
    hook_input = parse_hook_input(document)
    if not isinstance(hook_input, PreToolUseInput):
        raise ProtocolViolation(
            f"expected PreToolUse input, got {type(hook_input).__name__}"
        )
    output = validate_pre_tool_use(hook_input)
    return "" if output is None else encode_hook_output(output)


def handle_session_start_document(document: str) -> str:
    """Derive startup guidance from one ``SessionStart`` JSON document."""
    hook_input = parse_hook_input(document)
    if not isinstance(hook_input, SessionStartInput):
        raise ProtocolViolation(
            f"expected SessionStart input, got {type(hook_input).__name__}"
        )
    output = session_start_context(hook_input)
    return "" if output is None else encode_hook_output(output)


def handle_subagent_start_document(document: str) -> str:
    """Derive role context from one ``SubagentStart`` JSON document."""
    hook_input = parse_hook_input(document)
    if not isinstance(hook_input, SubagentStartInput):
        raise ProtocolViolation(
            f"expected SubagentStart input, got {type(hook_input).__name__}"
        )
    output = subagent_start_context(hook_input)
    return "" if output is None else encode_hook_output(output)
