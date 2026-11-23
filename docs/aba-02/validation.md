# ABA-02 验证记录

## 1. 基线与范围

- 分支：`main`；起始 HEAD = `203fcae2a8f593e36461741734b6784a4f2c410d` = `origin/main`；`git status --short --branch` 干净；`git diff --check` 无输出。
- ABA-01 与 ABA-01-C1 交付文件均存在（`docs/aba-01/` 6 份、`docs/aba-01-c1/` 3 份）。
- 固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`，只读；经 GitHub API 以内存 token 只读抓取 35 个相关 `.cs`（token 未落盘），本地快照 `D:/tmp/aba01/src/`。
- 最终 `git status --short` 仅 `?? docs/aba-02/`；`git diff --stat` 为空；`git status --short -- src/ tests/ results/ data/ docs/aba-01/ docs/aba-01-c1/` 为空（既有源码/测试/CSV/文档零改动）。

## 2. 新增文件（7 份，全部在允许范围）

| 文件 | 内容 |
| --- | --- |
| `docs/aba-02/source_inventory.md` | 固定 commit 的 11 个生成器、注册表、执行/测试入口、Field/地址线语义，带路径+行号 |
| `docs/aba-02/workload_inventory.md` | 源码存在/注册/执行三清单与证据等级，任务列表差异说明 |
| `docs/aba-02/address_domain_audit.md` | 逐程序地址域审计、静态/动态访存区分、有限域分析、Bubble Sort 特殊复核 |
| `docs/aba-02/interface_design.md` | `(program_id,Nmax,n,constraints)` 接口、七项责任划分、各层能力边界（设计不实现） |
| `docs/aba-02/cost_model_applicability.md` | 与 EXP-DORAM-08 假设的适用性映射与分类 |
| `docs/aba-02/validation.md` | 本文件 |
| `docs/aba-02/decision.md` | 最终决策与 VERIFIED/CONSTRUCTED/INFERRED/UNKNOWN 分层 |

## 3. 关键事实（带证据）

- 主注册仅 7 个程序：`ZkProgramExamples.cs` L6–L15。
- 有单方测试执行证据：ReverseInput（测试 L57–L67，n=4）、BubbleSort（L70–L79，n=4）、DivideByTwo（L82–L90，未注册）、GreaterThan（L93–L143）。
- 实验四注册 8 个（含未主注册的 BinarySearch/SetIntersection/LCIS）：`Experiment/Program.cs` L491–L500；运行入口 L545–L649、L651–L756；生成器只复用示例输入（L79 等）。
- BubbleSort 输入：`PublicInput 1`（L19），示例公共输入 `n=5`（L76），`globalStepsNoMoreThan=43×5×5`（L79）；`GlobalStepsNoMoreThan` 只在执行器 L114–L116 抛错，不进电路。
- 地址线：`ZkVmOpType.cs` L44–L50（Load/Store 用 Reg0，NegOne 保留）；`ZkVmExecutorCircuitBoardGenerator.cs` L126–L131（in_public_input 公共线）、L988（NegOne 返回 0）。
- 无 Nmax 参数、无 `1≤n≤Nmax` 约束、无地址上界电路——这在固定 commit 中未找到（已检索生成器和执行器）。

## 4. 验证命令结果

```text
git status --short                  -> ?? docs/aba-02/
git rev-parse HEAD                  -> 203fcae2a8f593e36461741734b6784a4f2c410d
git rev-parse origin/main           -> 203fcae2a8f593e36461741734b6784a4f2c410d
git diff --check                    -> 无输出（clean）
git diff --stat                     -> 空（仅新增未跟踪文档）
```

按任务要求：只有文档新增，未重复运行全仓库测试；既有测试文件未改、原始 CSV 未改、源代码未改、上游引用均指向固定 commit、关键判断均带文件路径和行号。

## 5. 提交记录

（提交推送后以 `git rev-parse HEAD` 为准；最终 HEAD = origin/main，工作区干净。）
