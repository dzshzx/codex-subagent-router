# validator 绑定 V2，普通用户默认是稳定 V1

Status: resolved

P0 结构性问题。validator 强制 task_name/fork_turns（V2），默认部署只有
稳定 V1（multi_agent stable true / multi_agent_v2 under development false）。

## Answer

commit fd3992c：按 tool_input 形状分流的 capability seam——task_name 或
fork_turns 出现走 V2 契约；否则按稳定 V1 契约（显式 agent_type/model/
reasoning_effort，message/items 二选一，fork_context 必须 false/省略）。
两路共享唯一策略源。上游依据：docs/research/codex-0.144.3-multiagent-spawn-contract.md。
注意：0.144.3 实测 hook tool_name 与源码推断存在出入（见 issue 04），
allowlist 同时覆盖 spawn_agent 与 collaborationspawn_agent 等变体。

## Comments

2026-07-13 installed-binary 探针：发行 0.144.3 二进制默认即 V2 形状契约
（tag 源码的 V1 契约未在二进制中观察到）。seam 保留——它同时覆盖发行二进制
现实与 tag 源码契约；V1 形状被放行后由 Codex 解析器自行拒绝，无 child 产生，
fail 方向安全。
