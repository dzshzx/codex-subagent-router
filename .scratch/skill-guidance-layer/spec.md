# Skill guidance layer and offline usage report

Date: 2026-07-16

## Goal

Make the router practical, portable, and unobtrusive: the policy remains the
single executable source, and two new derived surfaces make daily use lighter.

1. Named route profiles: every route gains a stable semantic name and purpose
   so guidance reads as a small set of packages instead of a model×effort
   matrix. Route count, order, and compute stay unchanged.
2. Generated skill document: `render-skill` renders the routing policy, role
   descriptions, spawn contract, delegation signals, task packet template, and
   result contract into one agent-skill markdown file. The output is a
   generated artifact, never a second source of truth.
3. Offline usage report: `usage-report` scans an explicit sessions directory,
   extracts spawn calls from rollout files (route fields are plaintext), and
   replays each call through the deny-only validator. The violation rate is
   the data that later decides whether the PreToolUse hook stays mandatory.

## Evidence base

- `docs/research/codex-0.144.4-v2-real-backend-evidence.md`: real backend
  accepts explicit-metadata V2 spawns; child compute is honored;
  `task_name` must match `[a-z0-9_]+`; rollout keeps route fields plaintext.

## Issues

- 01: named route profiles in policy and start context — done in this change.
- 02: skill source text and renderer with CLI `render-skill` — done in this
  change.
- 03: offline usage report with CLI `usage-report` — done in this change.
- 04 (open): calibration after two weeks of real usage — revisit profile set,
  delegation signals, and PreToolUse necessity with `usage-report` data.
- 05 (open): installer awareness of the skill surface (avoid double guidance
  when both SessionStart hook and skill document are active).
