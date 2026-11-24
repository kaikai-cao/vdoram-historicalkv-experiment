# ABA-02-C1-R1 最终决策

## `PASS_DOCUMENT_CORRECTION`

三份既有文档中的 Git 推送记录已按事实补正：远端 `refs/heads/main` 的权威确认来自 GitHub API 查询，`git fetch origin` 当时因代理 502 失败、未成功，本地 `origin/main` 引用是同步到 API 已确认的远端 SHA `fa5344c...`；明确区分“远端 ref 的权威确认 ≠ `git fetch` 成功”。本轮新增 R1 三份记录文档，说明修正内容与边界。

自检：`git diff --check` 干净；范围仅三份既有文档修改 + 三份 R1 文档新增；源码/测试/CSV/数据/研究结论文件零改动；未运行代码测试（无代码改动）。

## 边界与冻结声明

- 本轮**只修正历史记录**，不重新验证历史网络操作；不执行 push、API 回退、上传对象、fetch 或远端 ref 修改。
- ABA-02 原决策 **`GO_WITH_ADDED_INPUT_CONSTRAINTS`** 不变；EXP-DORAM-06 的 **`NO_GO_CURRENT_ARCHITECTURE`** 不变；未新增研究假设、实验、公式或成本模型。
- 遗留事项：`docs/aba-02-c1/decision.md` 第 9 行同类表述因不在授权范围未改，已在 R1 `fix.md` 记录，供后续决定。
- 本轮完成后立即停止，不启动下一阶段。
