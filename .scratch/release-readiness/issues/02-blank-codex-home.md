# 空白 --codex-home 解析为当前目录

Status: resolved

P0。CLI Path("").absolute() 变成 CWD；README 使用未定义 $CODEX_HOME。

## Answer

commit 5ac0238：argparse type 在原始字符串上拒绝空白值（exit 2）；README
显式定义 CODEX_HOME 并说明拒绝行为。
