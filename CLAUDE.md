# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

环境由 `uv` 管理（Python 3.11+，`src/` 布局，无运行时依赖）：

```bash
uv sync --dev                 # 创建/更新开发环境
uv run pytest                 # 全部测试
uv run pytest tests/test_policy.py::test_ultra_child_effort_is_rejected  # 单个测试
uv run ruff check .           # lint
uv run ruff format --check .  # 仅检查格式，不修改文件
uv run mypy                   # 严格类型检查（覆盖 src 与 tests）
uv build                      # 打包检查
```

提交前按 CONTRIBUTING.md 跑全部检查：`uv run pytest && uv run ruff check . && uv run mypy && uv build && git diff --check`。

提交信息沿用仓库历史的 Conventional Commit 前缀（`feat:`、`refactor:`、`docs:` 等）。

## 架构

本仓库为 Codex 子代理开发 model / effort / role / context 路由策略。README
「Delivery stages」中的阶段 1–6 已全部交付，包括稳定 policy seam、严格
hook JSON protocol、deny-only `PreToolUse` 校验、启动 context、隔离端到端
探针，以及显式的用户级安装、状态查询和可恢复回滚。范围契约见
`docs/initial-scope.md`。

核心结构：

- `src/codex_subagent_router/policy.py` 是**唯一策略事实源**：`_ROUTINE_ROUTES`（5 条常规路由）与 `_CONDITIONAL_ROUTES`（2 条条件升级路由）为私有元组，支持的 child effort 集合由路由派生。协议相关输出必须从这一处派生，不得出现第二策略源或隐藏 fallback。
- `protocol.py` 严格解析 `PreToolUse` / `SessionStart` / `SubagentStart` 输入，并只编码项目支持的 deny、routing-guidance 与 role-context 输出；它不承担路由策略或 handler 行为。
- `validator.py` 只做 routed `spawn_agent` 的 deny-only 校验；合法或非 spawn 调用不产生 Hook 输出，不合法调用返回明确 deny，且 profile / effort 必须由 `policy.py` 派生。
- `roles.py` 是四个 managed role 合同和 description 的唯一可执行来源；合同只描述稳定行为，不包含 model、effort、service tier 或 fork 配置。`start_context.py` 从 policy、validator 与 role 来源派生 root `startup` guidance，并只为 managed role 注入精确合同。
- `document_handlers.py` 把严格解析、对应的纯 handler 和编码组合成三个 JSON document adapter；event 类型不匹配时抛出 `ProtocolViolation`，无输出时返回空字符串。
- `hook_specs.py` 集中拥有可执行 Hook 的 event、command、matcher、timeout 和 handler 元数据，并从 `roles.py` 派生 managed role matcher；`commands.py` 只是 Hook 进程的 stdin / stdout / stderr 与退出码适配层。
- `installation.py` 编排针对显式 `codex_home` 的只读 plan、install、status、rollback 与事务状态转换。`_installation_types.py` 定义公开的不可变安装 value types；`_installation_files.py` 处理私有文件格式、receipt 校验、安全路径、operation lock、原子写入和配置渲染；`_installation_rollback.py` 处理回滚目标、journal、恢复校验与应用。
- `install_commands.py` 是安装 API 的薄 CLI，要求 `--codex-home`，为 plan / install / status / rollback 输出机器可读 JSON 和明确退出码，不自行推断 Codex home。
- 公共 API 只经 `codex_subagent_router/__init__.py` 暴露：policy / protocol value types 与解析编码函数、validator、role source、start-context / document handlers，以及安装 value types 和 plan / install / status / rollback 函数。Hook 规格、命令 wiring、receipt 格式和安装/回滚辅助实现保持私有。
- 路由按**能力升序**排列，测试断言精确顺序——改动路由顺序即改动契约。
- 不可变策略数据用 frozen dataclass + tuple 表示；外部输入在协议边界校验并抛出显式的 `PolicyViolation`。

## 硬性约束

- child reasoning effort `ultra` 被禁止（`validate_child_effort` 对其有专门报错，测试锁定该文案）。
- managed role 合同/description 只能来自 `roles.py`；Hook event、matcher、timeout 与 handler 元数据只能来自 `hook_specs.py`。安装输出必须从这两个事实源派生，不复制角色表或 Hook 表。
- 所有安装 Python API 与 CLI 调用必须显式传入 `codex_home`；测试、包导入和命令不得隐式读取或修改 `~/.codex`。
- 安装与回滚必须可恢复，并对 unsafe path（包括 symlink 和非普通文件）、损坏或不一致的 receipt/journal、并发 operation lock、不兼容配置和用户后续修改 fail closed。不得静默接管既有兼容条目或覆盖不健康状态。
- Hook trust 审核和安装后的新 session 必须由用户显式完成；安装器不写 trust state、不启用绕过 trust 的选项，也不假设当前 session 会热加载普通配置。
- 仓库代码不得包含机器专属绝对路径。

## 测试约定

- 只通过公共包接口测试可观察行为；期望值使用与书面策略独立的字面量（不要从实现导入常量来构造期望值）。
- 每个新行为先加一个聚焦测试再实现。
- 本仓库自有代码不使用 mock。
- 安装测试只在 `tmp_path` 下使用显式 `codex_home`，并覆盖只读 plan、冲突、幂等安装、status、bytes/mode 精确恢复、保留用户后续改动、崩溃恢复、receipt 完整性和并发/unsafe-path 拒绝；真实 `~/.codex` 不得作为 fixture。

## Agent skills

### Issue tracker

Issue 以 markdown 文件形式放在仓库内 `.scratch/<feature>/` 下（local-markdown tracker）。See `docs/agents/issue-tracker.md`.

### Triage labels

使用五个默认 triage 标签：needs-triage、needs-info、ready-for-agent、ready-for-human、wontfix。See `docs/agents/triage-labels.md`.

### Domain docs

Single-context 布局：根目录 `CONTEXT.md` 与 `docs/adr/` 按需创建。See `docs/agents/domain.md`.
