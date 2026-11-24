# ABA-03 最终决策

## `HOLD`

本轮完成了固定上游 `BDS-SDU/vdoram-artifacts@10c90d35464620a35ddb1e2c29d2e8725acedd52` 的源码审计、约束规格、绑定方案比较和攻击反例设计。**不发出 `GO_TO_MINIMAL_CIRCUIT_PROTOTYPE`，也不判定 `NO_GO_CURRENT_APPROACH`。**

## 1. 为什么不是 GO

地址范围约束本身可以写清楚（`constraint_spec.md` B1/B2），但本轮最重要的验收点——**被约束的地址是否就是 VM 实际执行的地址**——目前只有设计路径，没有闭合的接口事实：

1. **程序身份锚点缺失**：上游只有逐行 `out_hash_opcode_table_row`（`InstructionFetchCircuitBoardGenerator.cs:215-235`）和含随机 `enc_key`/step 的状态哈希，没有整程序承诺；opcode 表虽是公开输入（`InstructionFetchCircuitBoardGenerator.cs:126-156`），但 verifier 没有固定期望值。因此“静态证书分析的程序 = 实际执行的程序”在电路中无法强制。
2. **地址同一性未显式闭合**：`fetch_addr = thisRegisters[0]`（`ZkProgramExecutor.cs:225-226`）与 `trace_mem_addr = inRegisterWires[0]`（`ZkVmExecutorCircuitBoardGenerator.cs:224-227,989-997`）在构造上同源，但分属不同电路；现有跨电路一致性只是执行器外部哈希核对（`:302-332,404-408,567-583`），verifier 只见哈希摘要，没有电路内 `fetch_addr = reg0 = trace_addr` 等式或共享承诺。
3. **静态证书完全在电路外**：证书绑定 Python 侧 `program_hash`、指令数和源字符串，不绑定具体 `n`，不读取 C# 实例，运行时无任何强制检查（`aba-01/certificate_format.md:5-7`；源码全量搜索无证书引用）。把证书 `PASS` 当作运行时保证属于 overclaim。
4. **无 gadget 级成本数据**：所有约束规模只能标 `UNKNOWN`，无法据实测判断是否满足现有证明预算。

以上都属于“方案有合理构造，但关键绑定关系尚未验证 / 需要进一步核对上游电路接口”，符合 `HOLD` 的定义。

## 2. 为什么不是 NO_GO

现有 VM 电路**已经**提供 pc→opcode 行选择（`InstructionFetchCircuitBoardGenerator.cs:158-213`）、Load/Store→reg0 地址派生（`ZkVmExecutorCircuitBoardGenerator.cs:224-227,941-997`）、寄存器状态转移（`:793-874`）和公开 trace 哈希（`:1009-1018`）。缺少的是外部锚点与同一性断言，不是必须推翻现有执行/证明架构。因此不判定 `NO_GO_CURRENT_APPROACH`。

## 3. 最小可行候选与未决项

- 最小可行候选：**C1 每步直接绑定**（`trace_binding_analysis.md`），它不依赖“静态 PC 列表 = 动态事件列表”，天然覆盖循环、分支与提前终止。
- 未决项见 `trace_binding_analysis.md` C4：整表 `program_hash` 公开锚点、跨电路地址共享承诺、三类负向 witness 的最小原型验证、静态证书是否升级为策略层。

## 4. 验收自检

- 固定 commit 源码证据可复核：路径 + 原始行号见 `source_trace_audit.md`；Prove 文件明确按快照行号 −4 换算。
- 源码事实、实验构造、设计推断分别以 `VERIFIED_SOURCE` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED` 标注。
- 静态程序分析与动态执行 trace 已分开：证书是离线 `CONSTRUCTED`，运行时绑定是待验证 `INFERRED`。
- 两种绑定方案（C1/C2）已给出并比较；没有把静态 PC 列表当动态事件列表。
- 十个攻击反例均已分析，且明确未实际执行。
- 约束规格明确字段/整数语义与 `2^L ≤ p` no-wrap 条件，并指出“低位截断别名”风险：`p` 为奇数，`p−1` 的低 L 位不可能全为 1，风险在于截断值可能很小却通过比较，因此必须约束完整字段等式。
- 成本未知项标 `UNKNOWN`，未虚构约束数。
- 只新增 `docs/aba-03/` 六份文档；未修改任何既有文件；未运行代码测试。

## 5. 冻结声明

- ABA-01、ABA-01-C1、ABA-02、ABA-02-C1/R1/R2 与 EXP-DORAM 系列全部保持冻结，本轮只读引用。
- ABA-02 决策 `GO_WITH_ADDED_INPUT_CONSTRAINTS` 不变；EXP-DORAM-06 `NO_GO_CURRENT_ARCHITECTURE` 不变。
- 本轮**没有**新增 Halo2/R1CS 电路、测试脚本、CSV、基准数据或修改 HistoricalKV/Fetch/MemoryTrace/排序电路。
- 本轮**没有**证明 R1CS 映射已实现、Halo2 电路已实现、协同证明后端可用或真实执行 trace 已绑定。

## 6. ABA-03-C1 勘误（不改变本决策）

本轮只修正两处文档事实/数学描述：

1. **step 0**：不执行 MemoryFetch（`ZkProgramExecutor.cs:201-203`），但仍无条件追加一行 MemoryTrace（`:389-402`、`:85-97`）；该行 `is_mem_op=0`，不是真实访存事件。MemoryTrace 行数不得当作动态访存事件数。
2. **`p−1` 低位别名**：`p` 为奇数，`p−1` 的低 L 位不可能全为 1；风险是低 L 位截断值可能很小却通过比较，故必须同时强制逐位 Boolean、完整字段等式 `addr=Σ2^j d_j (in F_p)`、整数位比较与 `2^L≤p`。

修正只涉及 `constraint_spec.md`、`trace_binding_analysis.md`、`attack_cases.md`、`validation.md`、`decision.md`；`source_trace_audit.md` 未发现相关错误，未修改。没有实现电路、没有运行测试、没有改变上述 `HOLD` 结论。

ABA-03 审计至此冻结；解除 HOLD 前不启动 ABA-04 或电路原型。
