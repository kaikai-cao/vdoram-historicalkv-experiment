# ABA-02-C1：三处文档勘误说明

本轮为**纯文档勘误**：只修正 ABA-02 评审发现的三处记录问题，不重新开展审计、不修改研究结论、不触及任何源码/测试/CSV/数据文件、不启动 R1CS 或原型。上游固定版本仍为 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。

## 问题一：BubbleSort 的 dummy Fetch 语义

**原问题**：`docs/aba-02/cost_model_applicability.md` 的 BubbleSort 行写“程序每条 Load/Store 都是真实访存，无 dummy”，容易被误读为“BubbleSort 的非内存指令不执行 Fetch”。

**证据核对（只读）**：固定 commit `ZkProgramExecutor.cs` L112（每个 `globalStepCounter` 主循环）、L129（Instruction Fetch）、L192（Fetch memory value）、L201（`globalStepCounter == 0` 特殊分支）、L225（memory address stored in reg0）。语义是：step 0 不执行内存 Fetch，其后每个 VM step 执行一次 Fetch，非内存指令同样执行 dummy Fetch。

**修正方式**：

- 在模型假设后新增“Fetch 口径说明（重要）”：显式 Load/Store 为真实访存、非内存步仍执行 dummy Fetch；Fetch 按 VM step 计，不等于显式 Load/Store 指令数；模型继续沿用 EXP-DORAM-08 既定口径；显式 Load/Store 的历史 trace 地址与 dummy Fetch 地址语义需区分。
- 表格“dummy Fetch”列改为“dummy Fetch / Fetch 口径”，逐行改为准确表述（BubbleSort、ReverseInput、SlidingWindow、无访存程序、未注册候选）。
- 第 4 节结论段落的“无 dummy”同步更正。
- 明确声明本说明不修改 EXP-DORAM-08 的任何公式、CSV、参数或实验结果（该阶段已冻结）。

## 问题二：实验四程序的执行证据等级

**原问题**：`docs/aba-02/workload_inventory.md` 把实验四 8 个程序统一标为 `VERIFIED_EXECUTED`，依据仅为生成器列表、实例导出入口和通用 `Execute()` 运行入口存在；固定 commit 中没有可核验的历史成功运行结果。

**证据核对（只读）**：`CollaborativeZkVmExperiment/Program.cs` L491–L500 为实验四包装生成器列表，L503–L510 为实例导出，L545–L649 / L651–L756 为运行器调用 `Execute()`。入口存在只证明“可运行路径存在”，不等于历史执行成功；包装生成器仅覆写 CodeName、复用示例 opcodes 与示例输入（`ExperimentFourZkProgramGeneratorBase.cs` L6–L18）。

**修正方式**（保留四类等级，不新增等级）：

- 统一四类等级含义，并明确“入口存在 ≠ 历史执行成功”，同时“未核验历史运行结果 ≠ 程序无法运行”。
- **保留 `VERIFIED_EXECUTED`**：ReverseInput、BubbleSort、GreaterThan、DivideByTwo——四者均有单方测试的明确 `Execute()` 调用（`ZkProgramExamplesTest.cs` L57–L67 / L70–L79 / L93–L143 / L82–L90），DivideByTwo 仍未主注册。BubbleSort 的等级来自测试执行，不是实验四入口。
- **实验四条目收紧**：SlidingWindow / Fibonacci / RangeQuery 在主注册表中，标 `VERIFIED_REGISTERED`（备注实验四包装生成器/运行入口存在，历史执行结果未核验）；BinarySearch / SetIntersection / LCIS 不在主注册表，保留 `SOURCE_ONLY` 并加同样备注。
- **Euclidean** 保持 `VERIFIED_REGISTERED`，未为提升等级扩大搜索范围。
- 同步收紧综合证据等级表与 `docs/aba-02/validation.md` 第 3 节的对应描述。

**必须保留的事实均保留**：主注册表仍只有 7 个程序（L6–L15）；实验四仍有 8 个包装生成器；包装生成器复用示例 opcodes 与示例输入；BubbleSort 仍是注册且有测试执行证据的真实工作负载候选。未把“未核验历史运行结果”写成“程序无法运行”。

## 问题三：Git 推送记录与实际执行不符

**原问题**：`docs/aba-02/validation.md` 写“短超时重试第 4 次成功，未用 API 回退”，与实际执行报告不符。

**修正方式**：按实际执行报告重写第 5 节——常规 `git push` 连续遇到 SSL EOF 与代理 502、多轮有限重试（含 HTTP/1.1 交替）均未成功；随后按仓库既有安全流程采用 GitHub API 回退：从 git 凭证管理器内存读取 token（未落盘），逐层上传 blob/tree/commit 对象并核验 SHA 与本地一致，远端 ref 仅作 fast-forward 更新（`force=false`，无强推、无历史重写、无额外分支或 PR）；最后 `git fetch origin` 确认 `HEAD` 与 `origin/main` 一致、工作区干净。删除“第 4 次成功”“未使用 API 回退”等错误描述，并写入真实最终 commit `0d862c57a74534f4d225019b127a6edc3da61164`。

## 本轮不改变的内容

- ABA-02 原决策 `GO_WITH_ADDED_INPUT_CONSTRAINTS` 保持不变；`decision.md`、`address_domain_audit.md`、`interface_design.md`、`source_inventory.md` 零改动。
- 未验证任何新增电路约束（Nmax、`1≤n≤Nmax`、`addr<n`、`k≤n`）。
- 未启动 R1CS 绑定、真实执行 trace 绑定、原型、HistoricalKV、SlidingWindow/BinarySearch/SetIntersection 新证书、MPC 微基准或新一轮文献调研。
- EXP-DORAM-08 成本模型（公式/CSV/参数/结果）与 EXP-DORAM-06 的 `NO_GO_CURRENT_ARCHITECTURE` 均不变。
