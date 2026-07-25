# Issue tracker: Local Markdown (XDG)

Issues and specs (you may know a spec as a PRD) for this repo live as markdown
files **outside the repo**, in the per-repo agent workfiles directory:

`~/.local/share/agent-workfiles/codex-subagent-router/tracker/`

- `<repo>` 解析规则：取主 worktree 目录名——`git rev-parse --path-format=absolute --git-common-dir` 的结果，basename 为 `.git` 时取其父目录 basename；任意 worktree 中解析结果一致。
- Override：凡技能文本（`to-tickets`、`ask-matt`、`setup-matt-pocock-skills` 模板等）称 local tracker 位于仓内 `.scratch/`，本仓一律改按上述 XDG 路径执行。仓内 `.scratch/` 是纯临时草稿区，整体 gitignore、可随时清理，不承载 tracker 或任何常备文件。
- tracker 是一次性工作态：不入库、不备份、不跨机同步；effort 完结即可删除。重要结论在得出当轮写进 commit message 或 owner 文档，不依赖 tracker 存续。

External PRs are not a triage surface for this local-markdown tracker.

## Conventions

- One feature per directory: `<tracker>/<feature-slug>/`
- The spec is `<tracker>/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `<tracker>/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` — never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `<tracker>/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `<tracker>/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `<tracker>/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `<tracker>/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
