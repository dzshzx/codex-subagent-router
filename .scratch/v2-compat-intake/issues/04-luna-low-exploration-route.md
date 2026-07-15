# 评估 gpt-5.6-luna/low 作为探索型负载的 routine 低档

Status: ready-for-human

现状：routine 路由最低档为 terra/medium 与 sol/low，无 luna
（src/codex_subagent_router/policy.py:18-39）。既有路由证据
（docs/research/deepswe-v1.1-routing-evidence.md）只评过 luna/high
（被 sol/low 支配而排除，:68）与 luna/max（政策性排除，:77），
**未评估 luna/low**；且 DeepSWE 口径是端到端编码任务 Pass@1，
与「探索/检索型子任务」的负载分布不同。

帖子提供的是探索型负载下的实测背书：luna/low 探子两三分钟返回、额度极低，
楼主在该配置下完成数万行大库重构、体感消耗与 5.5 持平（118 楼）。

可行性已有本仓库证据：0.144.1 探针实测过 V2 spawn 显式指定
`model=gpt-5.6-luna`（含 luna/low）成功、`turn_context.model = gpt-5.6-luna`
（docs/research/codex-0.144.1-hook-evidence.md:263-285）。luna 在模型目录标
`multi_agent_version: "v1"` 不构成障碍——spawn 协议版本随主代理。

需要用户决策的点（ready-for-human 的原因）：

1. 加档是路由契约变更（测试锁定精确顺序与字面量），属 minor 级策略变更。
2. 探索型负载没有现成 DeepSWE 式基准，采信口径（外部实测背书 vs 自建评测）
   需要拍板；若采信，luna/low 应落在能力升序的哪个位置也需定
   （直觉上在 terra/medium 之前作为最低档）。
