# ADR 记录禁 ultra 的机制层理据

Status: ready-for-agent

帖子拆解了 ultra 的实现：它不是独立思考档，而是「max 档 juice（帖称 960，
与 max 相同）+ 一段多代理编排提示词」的脚手架开关（首帖 + 楼主 24 楼补充）。
child 传 ultra 因此是范畴错误——等于让子代理再开一层编排，正是帖子描述的
「子代理套娃派生 Sol、额度耗尽、任务完不成」的失败模式。

这是本项目 `validate_child_effort` 专门禁 ultra 的最好理据
（src/codex_subagent_router/policy.py:52,71-74），但目前代码与文档都没记录
why——deny 文案被测试锁定（不必改），风险是未来有人把 ultra 当普通高档
重新放开。

待办：按 docs/agents/domain.md 的按需创建约定，在 docs/adr/ 落一条 ADR：

1. 决策：child reasoning effort 禁 ultra，deny-only。
2. 理据：ultra = 编排放大器而非 effort 档；child 传它语义错误且诱发套娃编排。
3. 来源标注：juice 数值与实现细节为 linux.do/t/topic/2578075 转述，
   未经官方文档证实，标注不确定性；机制描述与本项目探针观察到的
   spawn 行为不矛盾。
