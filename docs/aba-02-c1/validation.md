# ABA-02-C1 验证记录

## 1. 基线与范围

- 分支：`main`；起始 HEAD = `0d862c57a74534f4d225019b127a6edc3da61164` = `origin/main`；`git status --short --branch` 干净；`git diff --check` 无输出。
- ABA-02 七份文档均存在（`docs/aba-02/`）；`docs/aba-02-c1/` 起始时不存在。
- 固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`，本轮仅只读核对既有本地快照中的 Fetch 语义、实验四入口与注册行号，**未重新下载源码、未重新执行 ABA-02 审计**。

## 2. 修改与新增文件（共 6 个，全部在允许范围）

修改的既有文档（3 个）：

| 文件 | 修正内容 |
| --- | --- |
| `docs/aba-02/cost_model_applicability.md` | 新增 Fetch 口径说明，修正 BubbleSort/ReverseInput/SlidingWindow/无访存/未注册行的 dummy Fetch 描述，同步第 4 节结论 |
| `docs/aba-02/workload_inventory.md` | 统一四类证据等级含义与分级规则，收紧实验四条目与综合表等级，保留 BubbleSort 测试执行等级 |
| `docs/aba-02/validation.md` | 同步实验四等级说明；按实际执行报告重写 Git 推送记录与最终 commit |

新增的 C1 文档（3 个）：`docs/aba-02-c1/fix.md`、`docs/aba-02-c1/validation.md`（本文件）、`docs/aba-02-c1/decision.md`。

未修改：`decision.md`、`address_domain_audit.md`、`interface_design.md`、`source_inventory.md`（ABA-02 研究结论文件零改动）；所有源码、测试、CSV、数据文件、ABA-01/ABA-01-C1、EXP-DORAM 文档、上游快照均未改动。

## 3. 三处修正核验

1. **dummy Fetch 语义**：已明确“step 0 无 Fetch、其后每 VM step 一次 Fetch、非内存步仍执行 dummy Fetch、Fetch 按 VM step 计而非显式 Load/Store 数”，并声明不修改 EXP-DORAM-08 冻结公式/CSV/参数/结果。
2. **实验四证据等级**：仍为四类等级；`VERIFIED_EXECUTED` 仅用于 ReverseInput / BubbleSort / GreaterThan / DivideByTwo（均有明确测试 `Execute()` 调用）；SlidingWindow / Fibonacci / RangeQuery / Euclidean 为 `VERIFIED_REGISTERED`；BinarySearch / SetIntersection / LCIS 保留 `SOURCE_ONLY` 并备注“实验四包装生成器/运行入口存在，历史执行结果未核验”。主注册 7 个、实验四 8 个包装生成器、BubbleSort 注册且有测试执行证据等事实均保留。
3. **Git 推送记录**：已删除“第 4 次成功 / 未用 API 回退”错误描述，改为常规 push 连续 SSL EOF/代理 502 → API 回退上传 blob/tree/commit 并核验 SHA → 远端 ref fast-forward（force=false）→ fetch 确认 local=remote、工作区干净；token 内存读取未落盘。

## 4. 检查结果（命令与实际输出）

```text
git diff --check                    -> 无输出（clean）
git diff --stat                     -> 3 files changed, 51 insertions(+), 26 deletions(-)
git status --short                  -> 仅 M docs/aba-02/{cost_model_applicability,validation,workload_inventory}.md
git diff --name-only                -> 上述三份文档
git status --short -- src/ tests/ results/ data/ docs/aba-01/ docs/aba-01-c1/ docs/aba-02/{其余四份} -> 空（零改动）
```

未运行全仓库测试：本轮无代码改动，仅文档勘误（按任务要求不需要运行代码测试）。

## 5. 证据等级一致性核验

四类等级含义在 `workload_inventory.md` 中统一定义，两处表格与 `validation.md` 第 3 节表述一致；`VERIFIED_EXECUTED` 的判定依据均为明确测试执行调用，而非实验四入口存在。BubbleSort 仍明确是“注册且有测试执行证据”的真实工作负载候选，未因本轮勘误改变其地位。

## 6. 最终 commit 与远端同步状态

- 本轮提交：`docs(aba-02-c1): correct three ABA-02 documentation records`（单一提交，6 个授权文件）。
- 最终 commit 即本文件所属提交，以 `git rev-parse HEAD` 为准；提交并推送后 `git rev-parse HEAD` = `git rev-parse origin/main`，`git status --short --branch` 为 `## main...origin/main`（工作区干净）。若常规 push 失败，按仓库既有安全流程有限重试或 API 回退（内存 token、对象 SHA 核验、仅 fast-forward、不强推、无额外分支），并在实际执行报告中如实记录。
