"""Private MultiAgent V2 configuration contract for user installation."""

_MULTI_AGENT_V2_SETTINGS: tuple[tuple[str, object], ...] = (
    ("enabled", True),
    ("hide_spawn_agent_metadata", False),
    ("tool_namespace", "agents"),
)
MULTI_AGENT_V2_MODIFICATION_DETAIL = (
    "managed MultiAgent V2 configuration is missing or modified"
)


def multi_agent_v2_settings() -> dict[str, object]:
    return dict(_MULTI_AGENT_V2_SETTINGS)


def multi_agent_v2_settings_are_exact(value: object) -> bool:
    return (
        isinstance(value, dict)
        and len(value) == len(_MULTI_AGENT_V2_SETTINGS)
        and all(
            name in value
            and type(value[name]) is type(expected)
            and value[name] == expected
            for name, expected in _MULTI_AGENT_V2_SETTINGS
        )
    )


def inspect_multi_agent_v2_configuration(
    document: dict[str, object],
) -> tuple[bool, str | None]:
    """Return whether V2 is present and any incompatibility in its path."""
    features = document.get("features")
    if features is None:
        multi_agent_v2_is_present = False
    elif not isinstance(features, dict):
        return True, "config.toml field 'features' must be a table"
    else:
        multi_agent_v2 = features.get("multi_agent_v2")
        if multi_agent_v2 is None:
            multi_agent_v2_is_present = False
        elif not isinstance(multi_agent_v2, dict):
            return (
                True,
                "config.toml field 'features.multi_agent_v2' must be a table",
            )
        else:
            multi_agent_v2_is_present = True
            if any(
                type(multi_agent_v2.get(name)) is not type(value)
                or multi_agent_v2.get(name) != value
                for name, value in _MULTI_AGENT_V2_SETTINGS
            ):
                return (
                    True,
                    "MultiAgent V2 already exists with incompatible configuration",
                )
    agents = document.get("agents")
    if isinstance(agents, dict) and "max_threads" in agents:
        return (
            multi_agent_v2_is_present,
            "config.toml field 'agents.max_threads' is incompatible with MultiAgent V2",
        )
    return multi_agent_v2_is_present, None
