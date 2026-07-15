# Update a user-level installation's owned Hook launcher

Category: feature
Status: ready-for-human

## Answer

新增 `plan_user_update` / `update_user_config` 与 CLI
`update --dry-run` / `update`。第一批只允许改变 Hook command 的绝对可执行
路径；其余参数、Hook subcommand、matcher、timeout 或事件结构变化都要求未来
显式 migration。update 只替换 receipt-owned exact groups，保留首次安装快照、
无关用户 Hook、V2、roles 与 standalone agents。

update 在同一 operation lock 内重新按精确 snapshots 规划，候选写入继续通过
hash guard、原子替换与 durable journal；中断时 rollback 恢复更新前完整安装，
无效 journal、receipt、unsafe path、standalone 冲突和 adopted groups 均 fail
closed。最终 rollback 仍恢复首次安装前 bytes/mode。

## Agent Brief

实现 spec 中第一批 user-level update seam。测试只通过 public Python interface
与 CLI 验证真实临时文件行为，不 mock 私有 implementation。

## Acceptance criteria

- [x] `plan_user_update` 只读报告 owned Hook launcher 的变化与冲突。
- [x] `update_user_config` 只替换 receipt-owned Hook groups 并保留 unrelated
      Hook 内容。
- [x] 新 launcher 缺失、非绝对或不可执行时在写入前拒绝。
- [x] 旧 launcher 已缺失时仍可修复健康的受管配置。
- [x] adopted/user-owned Hook groups 不被修改或收养。
- [x] update 幂等，并在 owned 内容漂移时 fail closed。
- [x] update 后 `status` 健康，且 `rollback` 仍恢复首次安装前 bytes/mode。
- [x] CLI `update --dry-run` / `update` 要求显式 `--codex-home` 并输出稳定 JSON。
- [x] 中断、并发修改、unsafe path 和无效 receipt 继续 fail closed 或可恢复。

## Out of scope

- 通用 role、V2、matcher、timeout 或 protocol migration
- schema 1 receipt migration
- 项目级安装或项目文件修改
- 包管理器级自卸载
