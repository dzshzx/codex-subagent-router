# ADR-0006: Layer advisory guidance over optional enforcement

- Status: Accepted
- Date: 2026-07-16

## Context

The routing goal is fitness, not frugality: every child should run on the
profile whose purpose matches the task — neither inheriting the parent
session's high compute by default nor starving hard work on a cheap
profile. The guidance must stay useful independent of any specific
workflow, so role identities cannot be a prerequisite for routing.

The policy source now feeds two derived surfaces beyond the hooks: a
generated agent-skill document (`render-skill`) and an offline usage report
(`usage-report`) that replays recorded spawn calls through the deny-only
validator. Real-backend evidence
([`codex-0.144.4-v2-real-backend-evidence.md`](../research/codex-0.144.4-v2-real-backend-evidence.md))
confirms that explicit V2 routing works end to end with only user-owned
configuration and no hooks installed.

The hook deployment carries recurring costs that conflict with an
unobtrusive daily setup: manual trust review, a machine-specific launcher,
per-release probe obligations, and — most important for stability — silent
fail-open absence when a hook is skipped or breaks. Static declarations
(configuration and skill files) load deterministically every session.

Field comparison supports an advisory-first posture: a leading agent harness
(mindfold-ai/Trellis) distributes role contracts as platform-native agent
definition files, constrains behavior through prompt guidance and capability
removal rather than call interception, and manages generated files with
content-hash tracking. It uses `PreToolUse` only to inject context, never to
deny.

## Decision

Deploy in two tiers, both derived from the same policy, role, validator, and
dispatch-guidance sources:

- **Tier A — advisory (default starting point).** The generated skill
  document plus the minimal user-owned configuration: the exact V2 table
  from ADR-0005. No hooks, no trust flow, no deny, no `SubagentStart`
  contract injection. Routing is by model and effort; `agent_type` is
  optional. The four description-only inline roles are an optional layer
  for workflows that use them — when declared, children receive the role
  description and the parent's task packet only.
- **Tier B — managed.** The full hook deployment specified by ADR-0001.
  ADR-0001 remains accepted as the implementation contract for this tier.

Movement between tiers is decided by observed data, not preference:
`usage-report` violation rates over real sessions are the factual basis for
adding or removing the enforcement layer.

The rendered skill document is a generated artifact. The repository does not
commit a rendered snapshot; installed copies are produced by `render-skill`
and are to be managed by the installer with hash tracking and
user-modification detection, reusing the ADR-0003 transaction semantics.

Role-contract delivery in Tier A stays limited to descriptions and task
packets until an isolated probe verifies whether an instructions-only
standalone role file (declaring `developer_instructions` but no model or
effort) preserves per-spawn compute. Only with that evidence may standalone
files become the Tier A contract channel, because ADR-0002's separation of
role identity from compute is non-negotiable.

## Consequences

- Tier A has no pre-creation denial and no injected contracts; violations
  are visible only afterwards through `usage-report`. This trade is
  deliberate and recorded.
- The observer depends on the rollout file format; version drift obligations
  move partly from the hook schema to that format rather than disappearing.
- Running Tier B adds the SessionStart guidance on top of the skill document;
  both render from the same sources, so the duplication is consistent but
  redundant. Component-aware installation resolves it later.
- Upgrading to Tier B keeps its existing requirements: hook trust review and
  a fresh session.
- The deny-only validator, protocol, and hook specs remain maintained and
  release-gated; Tier B stays deployable at any time.

## Rejected alternatives

- Keeping the full hook deployment as the recommended default: trust
  friction and silent fail-open contradict the stability goal, and no
  violation-rate data justifies the recurring cost today.
- Retiring the enforcement surface entirely: it is verified capability, and
  observation may prove it necessary.
- Embedding all four role contracts in the skill document for parents to
  copy into task packets: repeated token cost per dispatch; the native
  channel should be probed first.
- Committing a rendered skill snapshot to this repository: it would be a
  third copy drifting against both the sources and the installed file;
  hash-tracked management belongs at the installation target.
- Adopting instructions-only standalone files now: no 0.144.4 evidence that
  they preserve per-spawn compute; fail closed until probed.
