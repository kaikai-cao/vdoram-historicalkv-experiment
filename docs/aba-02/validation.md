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
- 实验四注册 8 个（含未主注册的 BinarySearch/SetIntersection/LCIS）：`Experiment/Program.cs` L491–L500；运行入口 L545–L649、L651–L756；生成器只复用示例输入（L79 等）。运行入口存在不等于历史执行结果已核验，这些程序未凭入口升级为 `VERIFIED_EXECUTED`；收紧后的等级见 `workload_inventory.md`（主注册者 `VERIFIED_REGISTERED`，未主注册者保留 `SOURCE_ONLY`）。
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

- 审计文档提交：`ec1cb3f92eaf370182ea30c817fcd8c55f261738`（`docs(aba-02): audit real VDORAM workloads for bounded address domains`，7 文件、410 insertions）。
- 最终 commit：`0d862c57a74534f4d225019b127a6edc3da61164`（`docs(aba-02): record audit commit and push details`，本文件哈希回填提交）；`git rev-parse HEAD` = `git rev-parse origin/main` = `0d862c5...`，`git status --short --branch` 为 `## main...origin/main`（工作区干净）。
- 推送过程（以实际执行报告为准）：常规 `git push` 连续遇到 SSL EOF 与代理 502，多轮有限重试（含 HTTP/1.1 交替尝试）均未成功；随后按仓库既有安全流程采用 **GitHub API 回退**——从 git 凭证管理器内存读取 token（未落盘），逐层上传缺失的 blob/tree/commit 对象，核验每个对象 SHA 与本地完全一致，再通过 **GitHub API 权威查询**确认远端 `refs/heads/main` 已更新至 `0d862c5...`（此前 API 已将远端 ref 仅作 **fast-forward** 更新，`force=false`，无强推、无历史重写、无额外分支或 PR）。
- 关于远端同步的确认方式：**权威证据是上述 GitHub API 查询，不是 `git fetch`**。此后 `git fetch origin` 仍因代理 502 失败，未成功；因此不能声称“fetch 确认远端更新成功”。最终是把本地陈旧的 `origin/main` 引用同步到 API 已确认的远端 SHA `0d862c5...`，从而使本地 `HEAD` 与 `origin/main` 一致、工作区干净。远端 ref 的权威确认 ≠ `git fetch` 成功，二者不可混写。
