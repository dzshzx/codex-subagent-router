# Repository Guidelines

本文件为 Codex 在本仓库工作时提供项目级指引。

## 常用命令

环境由 `uv` 管理（Python 3.11+、`src/` 布局、无运行时依赖）：

```bash
uv sync --dev                 # 创建或更新开发环境
uv run pytest                 # 运行全部测试
uv run pytest tests/test_policy.py::test_ultra_child_effort_is_rejected  # 运行单个测试
uv run ruff check .           # lint 与 import 顺序检查
uv run ruff format --check .  # 仅检查格式，不修改文件
uv run mypy                   # 严格类型检查 src 与 tests
uv build                      # 验证源码包和 wheel 构建
```

提交前运行：

```bash
uv run pytest
uv run ruff check .
uv run mypy
uv build
git diff --check
```

## 架构与项目结构

本仓库用于开发 Codex 子代理的 model、effort、role 和 context 路由策略。
当前只交付稳定的 policy seam；hook 协议适配器、deny-only `PreToolUse`
校验器、`SessionStart` / `SubagentStart` 角色契约和安装工具属于后续阶段。
阶段划分见 `README.md`，范围契约见 `docs/initial-scope.md`。

- `src/codex_subagent_router/policy.py` 是唯一策略事实源。私有元组
  `_ROUTINE_ROUTES` 和 `_CONDITIONAL_ROUTES` 按能力升序排列，支持的
  child effort 集合从中派生；不得新增第二策略源或隐藏 fallback。
- `src/codex_subagent_router/__init__.py` 是公共 API 边界，对外暴露
  `Profile`、`PolicyViolation`、`routine_routes`、`conditional_routes`
  和 `validate_child_effort`；存储细节保持私有。
- `tests/` 通过公共接口验证可观察行为。路由顺序由测试精确锁定，修改
  顺序即修改契约。

## 编码规范

- 使用四空格缩进、Python 3.11 语法和 88 字符行宽。
- Ruff 负责 pycodestyle、Pyflakes、import 排序、pyupgrade、bugbear 和
  simplification 规则；mypy 对 `src/` 与 `tests/` 启用 strict 模式。
- 使用清晰的领域命名，如 `Profile`、`PolicyViolation` 和
  `validate_child_effort`。
- 不可变策略数据使用 frozen dataclass 和 tuple；外部输入在协议边界
  校验，并通过显式异常暴露失败。
- 仓库代码不得包含机器专属绝对路径。

## 硬性策略约束

- child reasoning effort `ultra` 被禁止；专门的 `PolicyViolation` 文案
  属于受测试保护的行为。
- 协议输出必须从唯一策略事实源派生，不得复制路由表。
- 包导入和测试必须保持隔离，不得触碰 `~/.codex`。

## 测试约定

- 测试函数命名为 `test_<behavior>`，只通过公共包接口验证行为。
- 期望值使用与实现独立的字面量，不从私有常量构造预期结果。
- 每项新行为先添加一个聚焦的失败测试，再实现使其通过。
- 仓库自有代码不使用 mock。

## 提交与 Pull Request

提交沿用仓库历史中的 Conventional Commit 前缀，例如 `feat:`、
`refactor:` 和 `docs:`。提交 Pull Request 前运行 `CONTRIBUTING.md`
列出的全部检查；描述中概述改动和验证结果，涉及公共 API 或路由顺序
时明确说明契约变化。

## Agent skills

### Issue tracker

Issue 使用 local-markdown tracker，存放在 `.scratch/<feature>/`。具体约定
见 `docs/agents/issue-tracker.md`。

### Triage labels

默认标签为 `needs-triage`、`needs-info`、`ready-for-agent`、
`ready-for-human` 和 `wontfix`。映射规则见
`docs/agents/triage-labels.md`。

### Domain docs

采用 single-context 布局：根目录 `CONTEXT.md` 与 `docs/adr/` 按需创建。
消费规则见 `docs/agents/domain.md`。
