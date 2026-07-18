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
阶段 1–6 已全部交付：稳定 policy seam、严格 hook JSON protocol、
deny-only `PreToolUse` validator、start-context handlers、隔离端到端探针，
以及显式的用户级安装、状态查询与可恢复回滚工具。阶段划分见 `README.md`，
范围契约见 `docs/initial-scope.md`。

- `src/codex_subagent_router/policy.py` 是唯一策略事实源。私有的不可变
  `_ROUTING_POLICY` 分别保存按能力升序排列的 model catalog、按推理深度
  排列的 effort catalog 与动态选择规则；支持集合从中派生，不得新增第二
  策略源、固定 model/effort 配对表或隐藏 fallback。
- `src/codex_subagent_router/protocol.py` 是 hook wire boundary：严格解析
  `PreToolUse` / `SessionStart` / `SubagentStart` 输入，并只编码项目支持的
  deny、routing-guidance 与 role-context 输出。它不承担 routing policy 或
  handler 行为。
- `src/codex_subagent_router/validator.py` 只负责 routed `spawn_agent` 的
  deny-only 校验：非 spawn 调用无输出，合法调用返回 `None`，不合法调用
  返回 `PreToolUseDenyOutput`。model 与 effort 必须从 `policy.py` 独立校验，
  不得在 validator 中复制 catalog、引入配对 allowlist 或静默 rewrite。
- `src/codex_subagent_router/roles.py` 是四个 managed role 合同的唯一可执行
  来源；合同只描述稳定行为，不得写入 model、effort、service tier 或 fork。
- `src/codex_subagent_router/start_context.py` 从 `policy.py`、`validator.py`
  与 `roles.py` 派生 root `startup` guidance，并为 managed `SubagentStart`
  精确选择合同；非 startup source 与 unmanaged role 返回 `None`，不得隐藏
  fallback。
- `src/codex_subagent_router/document_handlers.py` 组合严格解析、对应的纯
  handler 与输出编码，形成三个 JSON document adapter；event 类型不匹配时
  显式失败，无输出场景返回空字符串。
- `src/codex_subagent_router/hook_specs.py` 是可执行 Hook 的 event、command、
  matcher、timeout 与 handler 元数据唯一来源；`commands.py` 只是 stdin /
  stdout / stderr 和退出码边界，不复制 Hook 规格或 handler 路由。
- `src/codex_subagent_router/installation.py` 编排针对显式 `codex_home` 的
  plan / install / update / status / doctor / rollback 与事务状态转换。`_installation_types.py`
  保存公共安装 value types，`_installation_files.py` 封装私有文件格式、
  receipt 校验、锁、原子写入与 Hook/角色渲染，`_installation_update.py`
  负责 owned Hook launcher 更新的规划、应用、journal 与恢复，`_installation_doctor.py`
  只读聚合用户安装和显式项目 agent 层，`_installation_rollback.py`
  负责回滚计划、journal、校验与应用；私有存储细节不得泄露为第二公共 seam。
- `src/codex_subagent_router/skill_source.py` 是派发指导文本（委派信号、
  任务包模板、结果契约）的唯一来源；`src/codex_subagent_router/skill_render.py`
  从 policy、roles、validator 与 skill_source 派生生成 agent-skill markdown，
  输出是生成物，不得手改或形成第二策略源。
- `src/codex_subagent_router/usage_report.py` 对显式 sessions 目录只读扫描
  rollout 文件，提取 spawn 调用并重放 deny-only validator，聚合路由分布与
  违规计数；它不隐式读取用户 Codex home。
- `src/codex_subagent_router/install_commands.py` 是项目统一薄 CLI：安装操作
  要求 `--codex-home`，解析 plan / install / update / status / doctor /
  rollback / uninstall，另提供 `render-skill` 与要求显式 `--sessions-dir` 的
  `usage-report`，输出稳定 JSON 与明确退出码；它不隐式选择用户 Codex home。
- `src/codex_subagent_router/__init__.py` 是公共 API 边界，对外暴露
  `RoutingPolicy`、model/effort guide、`routing_policy()`、
  `validate_routed_compute()` 与 protocol value types、`parse_hook_input`、
  `encode_hook_output`；同时暴露 validator、role source、start-context 与
  document handlers、
  skill 渲染（`render_skill_markdown` / `skill_name`）、usage report value
  types 与 `usage_report`，以及安装 value types 和 plan / install / update /
  status / doctor / rollback API；Hook 规格、command wiring、派发指导文本源
  和安装存储/回滚辅助实现保持私有。
- `tests/` 通过公共接口验证可观察行为。独立 model catalog、effort catalog
  的顺序和动态选择规则由测试精确锁定，修改即修改契约；安装测试只使用
  显式的临时 `codex_home`，并锁定冲突、
  文件模式、receipt、恢复、doctor 与回滚行为；项目检查只读使用临时目录。

## 编码规范

- 使用四空格缩进、Python 3.11 语法和 88 字符行宽。
- Ruff 负责 pycodestyle、Pyflakes、import 排序、pyupgrade、bugbear 和
  simplification 规则；mypy 对 `src/` 与 `tests/` 启用 strict 模式。
- 使用清晰的领域命名，如 `RoutingPolicy`、`ModelGuide`、
  `PolicyViolation` 和 `validate_routed_compute`。
- 不可变策略数据使用 frozen dataclass 和 tuple；外部输入在协议边界
  校验，并通过显式异常暴露失败。
- 仓库代码不得包含机器专属绝对路径。

## 硬性策略约束

- child reasoning effort `ultra` 被 `validate_routed_compute()` 禁止；专门的
  `PolicyViolation` 文案属于受测试保护的行为。
- 协议输出必须从唯一策略事实源派生，不得复制 model/effort catalog 或
  增加固定配对 allowlist。
- managed role 合同与 description 只能来自 `roles.py`；Hook event、matcher、
  timeout 与 handler 元数据只能来自 `hook_specs.py`，安装配置必须从这两个
  来源派生，不得复制角色或 Hook 表。
- 所有安装 Python API 与 CLI 调用都必须显式提供 `codex_home`；包导入、
  测试和命令不得隐式读取或写入 `~/.codex`。
- 安装与回滚必须保持可恢复。symlink、非普通文件等 unsafe path，损坏或
  不一致的 receipt/journal，以及并发 operation lock 必须 fail closed；不得
  覆盖不兼容配置、用户后续改动或不健康安装状态。
- Hook trust 审核与安装后的新 session 由用户显式完成；安装器不得写 trust
  state、启用绕过 trust 的选项，或声称普通配置会被当前 session 热加载。
- 版本变更默认只允许 patch 级 `+0.0.1`；minor 或 major bump 必须由用户明确
  提出，不得根据功能规模、API 变化或发布准备状态自行推断。

## 测试约定

- 测试函数命名为 `test_<behavior>`，只通过公共包接口验证行为。
- 期望值使用与实现独立的字面量，不从私有常量构造预期结果。
- 每项新行为先添加一个聚焦的失败测试，再实现使其通过。
- 仓库自有代码不使用 mock。
- 安装行为在 `tmp_path` 下通过公共 API/CLI 测试；覆盖只读 plan、幂等安装、
  status、精确 bytes/mode 恢复、部分用户改动保留、崩溃恢复与 fail-closed
  安全边界，不以真实 `~/.codex` 作为 fixture。

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
