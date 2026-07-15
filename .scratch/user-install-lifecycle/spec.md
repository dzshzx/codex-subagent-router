# User-level installation lifecycle

来源：2026-07-15 用户确认本项目采用用户级安装，而不是 Trellis 的项目级
安装。目标是借鉴 Trellis 的 plan/update/migrate/uninstall 生命周期，同时把
唯一写入目标保持为显式 `$CODEX_HOME`。

## Installation seam

当前 `plan/install/status/rollback` 继续作为用户级 public interface。第一批
新增：

- `plan_user_update(codex_home, hook_command)`：只读规划健康安装的 Hook
  launcher 更新；
- `update_user_config(codex_home, hook_command)`：事务性应用该计划；
- CLI `update --dry-run` / `update`：上述 Python interface 的薄 adapter。

所有调用继续要求显式 `codex_home`。项目目录不是安装目标，安装器不得写入
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
- schema 1 receipt、通用 role/policy migration、项目级冲突诊断不在第一批。

## Planned follow-ups

1. 在 versioned receipt 上增加通用配置 migration graph。
2. 增加只读 project doctor，报告当前项目对用户级 managed roles 的遮蔽。
3. 给 `rollback` 增加面向用户的 `uninstall` CLI alias；包本身仍由包管理器删除。
