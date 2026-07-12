"""Public API for Codex subagent routing policy and hook handlers."""

from .document_handlers import (
    handle_pre_tool_use_document,
    handle_session_start_document,
    handle_subagent_start_document,
)
from .policy import (
    PolicyViolation,
    Profile,
    conditional_routes,
    routine_routes,
    validate_child_effort,
)
from .protocol import (
    PermissionMode,
    PreToolUseDenyOutput,
    PreToolUseInput,
    ProtocolViolation,
    SessionSource,
    SessionStartInput,
    SessionStartOutput,
    SubagentStartInput,
    SubagentStartOutput,
    encode_hook_output,
    parse_hook_input,
)
from .roles import RoleContract, role_contracts
from .start_context import session_start_context, subagent_start_context
from .validator import validate_pre_tool_use

__all__ = (
    "PolicyViolation",
    "Profile",
    "PermissionMode",
    "PreToolUseDenyOutput",
    "PreToolUseInput",
    "ProtocolViolation",
    "RoleContract",
    "SessionSource",
    "SessionStartInput",
    "SessionStartOutput",
    "SubagentStartInput",
    "SubagentStartOutput",
    "conditional_routes",
    "encode_hook_output",
    "handle_pre_tool_use_document",
    "handle_session_start_document",
    "handle_subagent_start_document",
    "parse_hook_input",
    "role_contracts",
    "routine_routes",
    "session_start_context",
    "subagent_start_context",
    "validate_child_effort",
    "validate_pre_tool_use",
)
