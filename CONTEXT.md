# Subagent Routing

This context describes how the router distinguishes persistent kinds of
delegated work from one-off task instructions and per-task compute choices.

## Language

**Subagent identity**:
A stable kind of delegated work with a reusable behavior and authority contract.
_Avoid_: Role profile, compute profile, nickname

**Managed identity**:
A subagent identity whose contract is owned and distributed by this router.
_Avoid_: Custom model, task type

**Platform identity**:
A subagent identity supplied by Codex and used without being redefined by this
router.
_Avoid_: Managed role, router role

**Task brief**:
The per-delegation goal, scope, inputs, ownership, output contract, and
acceptance criteria for one bounded task.
_Avoid_: Identity, role contract

**Method**:
A reusable procedure, such as testing, debugging, or interface exploration,
that an identity follows for a particular task.
_Avoid_: Identity, agent type

**Review axis**:
The particular perspective applied by a reviewer to one task, such as Standards
or Spec.
_Avoid_: Reviewer identity, reviewer variant

**Compute route**:
The model and reasoning effort selected independently for one delegated task.
_Avoid_: Identity, role

**Researcher**:
The managed identity for evidence-led investigation of external primary sources.

**Reviewer**:
The managed identity for independent, read-only assessment of one review axis.

## Identity admission rule

A candidate becomes a managed identity only when repeated workflow evidence
shows a stable behavior, authority, or output contract that cannot be expressed
by a platform identity plus a task brief and method. A nickname, compute choice,
one-off deliverable, or prompt variation is not sufficient. The current
classification is recorded in `docs/role-contracts.md`.
