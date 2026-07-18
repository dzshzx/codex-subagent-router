# Codex 0.144.4 V2 parent to Luna child evidence

- Date: 2026-07-18 Asia/Shanghai
- CLI: `codex-cli 0.144.4`
- Provider: OpenAI real backend
- Scope: one explicit routed leaf child; no router Hooks installed

## Probe

The root session ran `gpt-5.6-sol/xhigh` with MultiAgent V2. It issued one
`spawn_agent` call with:

```text
task_name=luna_route_probe
agent_type=default
model=gpt-5.6-luna
reasoning_effort=low
fork_turns=none
```

The child was instructed to call no tools and return exactly
`LUNA_ROUTE_OK`.

## Observed result

| Evidence | Observation |
|---|---|
| Root rollout | The spawn call recorded Luna/low and `fork_turns=none`. |
| Child session metadata | The child linked to the root as `/root/luna_route_probe`, using CLI `0.144.4` and the OpenAI provider. |
| Child `turn_context` | `model=gpt-5.6-luna`, `effort=low`, `multi_agent_version=v2`. |
| Child result | Exactly `LUNA_ROUTE_OK`. |

The raw evidence is in
`rollout-2026-07-18T18-43-16-019f74d2-bf5b-7151-9f8f-d8bfeb156c47.jsonl:300`
and
`rollout-2026-07-18T19-11-53-019f74ec-f099-7a52-9db9-14086b4fad44.jsonl:8`.

## Conclusion and limits

The real backend honored an explicit Luna/low child override from a Sol V2
parent; the child did not inherit the parent's Sol/xhigh compute. This confirms
that the independent Luna model and low-effort choices work together on the
probed path.

This single probe does not benchmark Luna quality, latency, or cost. It also
does not verify a Luna root spawning descendants, managed Hook enforcement, or
Codex versions other than `0.144.4`.
