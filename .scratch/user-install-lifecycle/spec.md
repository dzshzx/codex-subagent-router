# User-level installation lifecycle

来源：2026-07-15 用户确认本项目采用用户级安装，而不是 Trellis 的项目级
安装。目标是借鉴 Trellis 的 plan/update/migrate/uninstall 生命周期，同时把
唯一写入目标保持为显式 `$CODEX_HOME`。

## Installation seam

当前 `plan/install/update/status/doctor/uninstall` 构成用户级 public
interface。第一批新增：

- `plan_user_update(codex_home, hook_command)`：只读规划健康安装的 Hook
  launcher 更新；
- `update_user_config(codex_home, hook_command)`：事务性应用该计划；
- CLI `update --dry-run` / `update`：上述 Python interface 的薄 adapter。

第二批新增：

- `doctor_user_config(codex_home, project_directory)` 与 CLI `doctor`：只读聚合
  用户安装健康度、用户 standalone agents 与一个显式项目的 `.codex/agents`；
- CLI `uninstall`：`rollback` 的用户友好别名，复用同一恢复事务；
- 隔离 `$CODEX_HOME` 的 `plan → install → update → doctor → uninstall` E2E。

所有安装调用继续要求显式 `codex_home`。项目目录不是安装目标，安装器不得写入
项目 `.codex/`、`.agents/` 或 `AGENTS.md`。

## First-batch invariants

- 第一批只替换 receipt-owned Hook groups 的绝对 launcher 路径。
- 首次安装 receipt 中的 `created`、`original_bytes` 和 `original_mode` 是永久
  卸载基线；update 不得用更新前状态覆盖它们。
- 用户原有或 adopted Hook groups 不得被 update 收养或改写。
- `config.toml`、V2 设置、managed roles 与 `$CODEX_HOME/agents` 不变。
- 更新前 receipt-owned groups 必须仍与 receipt 精确一致；用户后续修改时
  fail closed。
- 新 launcher 必须是绝对、普通、可执行文件；旧 launcher 可已不存在。
- unrelated Hook edits必须保留。
- 更新必须受同一 operation lock、journal、hash 重验和原子替换约束。
- 更新后的 rollback 仍精确恢复首次安装前 bytes/mode，或删除首次安装创建的
  文件。
- schema 1 receipt 与通用 role/policy migration 不在第一批。

## Lifecycle-completion invariants

- doctor 对用户和项目 agent 层只读，不把项目文件纳入 receipt。
- 项目级 managed-role 遮蔽、无效 agent 文件与 unsafe `.codex` 路径明确报告。
- doctor 只有在安装健康且两层均无问题时返回 `healthy=true`。
- uninstall 不删除包，只恢复本项目拥有的用户配置；随后才由包管理器删除包。
- rollback 保留为恢复/运维名称，uninstall 与它共用唯一实现。

## Planned follow-ups

在出现第二种实际配置迁移需求后，再为 versioned receipt 增加通用 migration
graph；不提前抽象尚不存在的迁移路径。
