# 安装事务静默覆盖并发用户修改

Status: resolved

P0。atomic_write 替换前不校验目标；异常恢复无条件回写快照；rollback
validate 与 apply 之间有窗口。竞态探针实证外部编辑丢失且 status 仍报 installed。

## Answer

commit 257dd67：单次字节快照派生 plan 与提交预期；guarded compare-and-commit
在 rename 前重验快照；失败按已写入进度撤销，外部编辑保留时保留 journal 并
fail closed。新增真实外部编辑器子进程测试（任意交错下外部编辑必须存活）。
残留：POSIX rename 语义下 read-compare-rename 的微秒级窗口不可消除，已在
代码注释与文档说明。
