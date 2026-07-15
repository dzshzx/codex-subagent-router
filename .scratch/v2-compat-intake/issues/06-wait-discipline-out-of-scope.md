# 派发后行为纪律（立即 wait / close_agent / 单轮不复用）不纳入 hook 注入 guidance

Status: wontfix

帖子的行为准则：并发派发后主代理立即 `wait_agent` 并停手、结果返回即
`close_agent`、每个子代理单轮不复用不追派、累计 10 分钟未返回视为异常介入、
wait_timeout 是等待区间而非子代理生存期（引 openai/codex#18394）。

判断：这些是编排行为纪律，属用户级 AGENTS.md 的职责，不属于本项目
hook 注入的路由 guidance——超出「model / effort / role / context 路由策略」
的范围契约（docs/initial-scope.md）。start_context 的 root guidance 保持
只含路由选择规则（src/codex_subagent_router/start_context.py:15-42）。

记录本票是为防止同一情报被重复 intake。若未来项目范围扩到编排行为指导，
帖子的这套纪律（含 #18394 的 timeout 语义）是现成的输入。
