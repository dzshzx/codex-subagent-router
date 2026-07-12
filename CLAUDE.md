# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

环境由 `uv` 管理（Python 3.11+，`src/` 布局，无运行时依赖）：

```bash
uv sync --dev                 # 创建/更新开发环境
uv run pytest                 # 全部测试
uv run pytest tests/test_policy.py::test_ultra_child_effort_is_rejected  # 单个测试
uv run ruff check .           # lint
uv run mypy                   # 严格类型检查（覆盖 src 与 tests）
uv build                      # 打包检查
```

提交前按 CONTRIBUTING.md 跑全部检查：`uv run pytest && uv run ruff check . && uv run mypy && uv build && git diff --check`。

## 架构

本仓库为 Codex 子代理开发 model / effort / role / context 路由策略。当前只交付了**稳定的 policy seam**；hook 协议适配器、deny-only `PreToolUse` 校验器、`SessionStart`/`SubagentStart` 角色契约、安装工具是后续阶段（阶段划分见 README「Delivery stages」，范围契约见 `docs/initial-scope.md`）。

核心结构：

- `src/codex_subagent_router/policy.py` 是**唯一策略事实源**：`_ROUTINE_ROUTES`（5 条常规路由）与 `_CONDITIONAL_ROUTES`（2 条条件升级路由）为私有元组，支持的 child effort 集合由路由派生。协议相关输出必须从这一处派生，不得出现第二策略源或隐藏 fallback。
- 公共 API 只经 `codex_subagent_router/__init__.py` 暴露（`Profile`、`PolicyViolation`、`routine_routes`、`conditional_routes`、`validate_child_effort`）；存储细节保持私有。
- 路由按**能力升序**排列，测试断言精确顺序——改动路由顺序即改动契约。
- 不可变策略数据用 frozen dataclass + tuple 表示；外部输入在协议边界校验并抛出显式的 `PolicyViolation`。

## 硬性约束

- child reasoning effort `ultra` 被禁止（`validate_child_effort` 对其有专门报错，测试锁定该文案）。
- 测试与包导入不得读取或修改用户级 Codex 配置（`~/.codex`）。
- 仓库代码不得包含机器专属绝对路径。

## 测试约定

- 只通过公共包接口测试可观察行为；期望值使用与书面策略独立的字面量（不要从实现导入常量来构造期望值）。
- 每个新行为先加一个聚焦测试再实现。
- 本仓库自有代码不使用 mock。

## Agent skills

### Issue tracker

Issue 以 markdown 文件形式放在仓库内 `.scratch/<feature>/` 下（local-markdown tracker）。See `docs/agents/issue-tracker.md`.

### Triage labels

使用五个默认 triage 标签：needs-triage、needs-info、ready-for-agent、ready-for-human、wontfix。See `docs/agents/triage-labels.md`.

### Domain docs

Single-context 布局：根目录 `CONTEXT.md` + `docs/adr/`。See `docs/agents/domain.md`.
