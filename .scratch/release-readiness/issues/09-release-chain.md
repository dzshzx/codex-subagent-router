# 可追溯发布链

Status: resolved

## Answer

2026-07-13 全链路打通并完成首次公开发布：
- 公开仓库 github.com/dzshzx/codex-subagent-router（MIT、topics、badges、CHANGELOG）
- CI：Python 3.11 + 3.14 全门禁，绿
- publish.yml：tag v* → 全门禁 + build + wheel/sdist 冒烟 → trusted publishing 发 PyPI
- pypi.org pending trusted publisher 已配置（publish.yml / environment pypi）
- v0.1.2 tag → workflow 成功 → https://pypi.org/project/codex-subagent-router/0.1.2/
- 端到端验证：公网 PyPI 全新 venv 安装，plan 只读输出正确，hook adapter 正确 deny ultra child
- GitHub Release v0.1.2 已创建

TestPyPI dry-run workflow 已删除（无对应账号，留着只会失败）。
