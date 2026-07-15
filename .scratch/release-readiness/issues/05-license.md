# 公共发布缺少许可证

Status: resolved

## Answer

用户选定 MIT。LICENSE 文件 + pyproject `license = "MIT"` /
`license-files = ["LICENSE"]`（PEP 639，build 后端升 setuptools>=77）。
wheel METADATA 含 License-Expression: MIT，LICENSE 进 wheel 与 sdist，
已实测验证。PEP 639 下不再使用 license classifier。
