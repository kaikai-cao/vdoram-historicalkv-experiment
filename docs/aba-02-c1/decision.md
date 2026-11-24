# ABA-02-C1 最终决策

## `PASS_DOCUMENT_CORRECTIONS`

三处评审发现的记录问题均已按任务边界修正，且未引入新的未经验证事实：

1. BubbleSort 的 dummy Fetch 语义已更正：显式 Load/Store 为真实访存，非内存步仍按 VDORAM 原始语义执行 dummy Fetch，Fetch 按 VM step 计而非显式访存指令数；EXP-DORAM-08 冻结口径未改。
2. 实验四程序的执行证据等级已收紧：仅有运行入口者不再标 `VERIFIED_EXECUTED`，改按主注册与否标 `VERIFIED_REGISTERED` / `SOURCE_ONLY`，并备注历史执行结果未核验；有明确测试调用的四个程序保留 `VERIFIED_EXECUTED`；四类等级不变。
3. Git 推送记录已按实际执行报告更正，并与 ABA-02-C1-R1 核实的历史一致：在此前的历史操作中，常规 Git push 连续失败；随后通过 GitHub API 回退上传对象并逐级核验 SHA，远端 ref 仅 fast-forward 更新，GitHub API 查询权威确认远端 `refs/heads/main` 已更新至 `fa5344c…`；其后的 `git fetch origin` 因代理 502 失败、未成功完成 fetch；本地陈旧的 `origin/main` 引用随后被手动同步到该 API 已确认的 SHA。因此，远端 ref 已获 API 查询确认，不等于 fetch 成功。以上均为 R1 之前的历史事实，本轮未执行任何 API 回退或远端 ref 操作。

自检结果：`git diff --check` 干净；仅三份既有文档被修改、三份 C1 文档新增；源码/测试/CSV/数据/ABA-01/EXP-DORAM/上游快照零改动；证据等级含义一致；研究结论文件零改动。本轮无代码改动，未运行全仓库测试（按任务要求）。

## 冻结声明

- ABA-02 原决策 **`GO_WITH_ADDED_INPUT_CONSTRAINTS`** 保持不变；本轮不改变研究方向或结论。
- 本轮**没有**验证任何新增电路约束（Nmax、`1≤n≤Nmax`、`addr<n`、`k≤n`），这些仍是新增构造而非上游已有能力。
- 本轮**没有**启动 R1CS 绑定、真实执行 trace 绑定或任何原型，也没有扩展 SlidingWindow / BinarySearch / SetIntersection 的静态证书。
- EXP-DORAM-06 的 **`NO_GO_CURRENT_ARCHITECTURE`** 不变；不得把 EXP-DORAM-08 的 Python 参考模型/Fetch 相计数称为真实 MPC 性能优势。

ABA-02 工作负载适用性审计至此冻结。
