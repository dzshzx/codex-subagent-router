# Complete the user-level installation lifecycle

Category: feature
Status: resolved

## Answer

新增只读 `doctor_user_config` 与 CLI `doctor`，聚合 receipt/status、Hook launcher、
用户 standalone agents 和一个显式项目的 `.codex/agents`。项目级 managed role
遮蔽、无效目录和 unsafe `.codex` 路径会使 `healthy=false`，但不会修改项目文件。

新增 CLI `uninstall` 作为现有 rollback 事务的用户入口，不复制恢复逻辑。隔离
E2E 已覆盖 `plan → install → update --dry-run → update → doctor → uninstall →
status`，并验证首次安装前 bytes/mode 精确恢复。

## Acceptance criteria

- [x] doctor 同时报告用户安装、launcher、用户 agents 与显式项目 agents。
- [x] doctor 健康退出 0，诊断问题输出 JSON 并退出 1。
- [x] doctor 不写项目或用户配置。
- [x] uninstall 复用 rollback，保持 receipt 的首次安装恢复基线。
- [x] 完整 CLI 生命周期只使用隔离临时 `$CODEX_HOME` 验证。
- [x] 用户文档明确先 uninstall 配置、再由包管理器删除包。
