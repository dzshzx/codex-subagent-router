# Update a user-level installation's owned Hook launcher

Category: feature
Status: ready-for-agent

## Agent Brief

实现 spec 中第一批 user-level update seam。测试只通过 public Python interface
与 CLI 验证真实临时文件行为，不 mock 私有 implementation。

## Acceptance criteria

- [ ] `plan_user_update` 只读报告 owned Hook launcher 的变化与冲突。
- [ ] `update_user_config` 只替换 receipt-owned Hook groups 并保留 unrelated
      Hook 内容。
- [ ] 新 launcher 缺失、非绝对或不可执行时在写入前拒绝。
- [ ] 旧 launcher 已缺失时仍可修复健康的受管配置。
- [ ] adopted/user-owned Hook groups 不被修改或收养。
- [ ] update 幂等，并在 owned 内容漂移时 fail closed。
- [ ] update 后 `status` 健康，且 `rollback` 仍恢复首次安装前 bytes/mode。
- [ ] CLI `update --dry-run` / `update` 要求显式 `--codex-home` 并输出稳定 JSON。
- [ ] 中断、并发修改、unsafe path 和无效 receipt 继续 fail closed 或可恢复。

## Out of scope

- 通用 role、V2、matcher、timeout 或 protocol migration
- schema 1 receipt migration
- 项目级安装或项目文件修改
- 包管理器级自卸载
