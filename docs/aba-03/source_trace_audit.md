# ABA-03 / Phase A：VM 地址与执行 trace 源码审计

> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`；本地实验仓起点 `06535962fdecd62534bc0bea1bccfc50b05ebce6`。
>
> **行号口径**：`D:/tmp/aba01/src/*.cs` 为无头原始 blob，行号即原始行号。`MemoryTraceProveCircuitBoardGenerator.cs` 只存在于实验仓 `docs/source-snapshot/`，其头部有 4 行抓取信息（`SOURCE`/`PATH`/`BLOB SHA`/空行）；本文所有该文件的行号均按 **原始行号 = 快照行号 − 4** 换算并注明。
>
> 证据标签：`VERIFIED_SOURCE` = 直接读到的源码事实；`CONSTRUCTED` = 实验侧自行构造并验证的静态产物；`INFERRED` = 由源码事实推出的设计结论；`UNKNOWN` = 无证据；`BLOCKED` = 本轮手段无法核验。

## 0. 证据边界

- 快照头记录的 commit 与任务固定 commit 一致；本地 `D:/tmp/aba01/` 无 `.git`，本轮**不能独立重验 commit 归属** → `BLOCKED`（沿用既有冻结记录）。
- `MemoryTraceFetchCircuitBoardGenerator.cs`、`ZkVmExecutorCircuitBoardGenerator.cs` 的无头文件与快照头 BLOB SHA 一致；Prove 文件去掉 4 行头后与快照头 BLOB SHA 一致 → `VERIFIED_SOURCE`。
- 本轮只读，未重新下载上游、未修改任何既有文件、未运行代码测试。

## A1. VM 指令执行与地址生成

| 审计项 | 源码事实（原始行号） | 标签 |
| --- | --- | --- |
| 指令表示 | `ZkProgramOpcode.cs:7-11` `record ZkProgramOpcode { OpType, Arg0, Arg1, Arg2 }`；`:24` `ToString()` 拼成 `op arg0 arg1 arg2`；`ZkVmOpType.cs:2` `enum ... : byte` | `VERIFIED_SOURCE` |
| opcode 表来源 | `InstructionFetchCircuitBoardGenerator.cs:126-156`：整张表 `opcode_table_{i}_{op,arg0,arg1,arg2}` 均为 **PublicInput**；执行器 `ZkProgramExecutor.cs:147-157` 逐行 `AddPublic` 填入 `program.Opcodes` | `VERIFIED_SOURCE` |
| PC 选择与取指 | `InstructionFetchCircuitBoardGenerator.cs:158-169`：`FieldEquals(constNumberWires[i], thisProgramCounterSafe)` 产生行选择位；`:171-213` 用 `SelectComposeGadget` 选出 arg0/1/2 与 op；越界行由 `:201-202` 的 `outOfRangeWire = NegOne` 兜底 | `VERIFIED_SOURCE` |
| opcode 进入执行电路 | `ZkVmExecutorCircuitBoardGenerator.cs:231-241`：`in_opcode_table_op/arg0/arg1/arg2` 是 **PrivateInputWire**；`:273-347` 与常量逐项比较，产生 `isTableOpEquals*` 与 `isArg*EqualsConstNumber*` | `VERIFIED_SOURCE` |
| 逐行 opcode 哈希 | `InstructionFetchCircuitBoardGenerator.cs:215-235` 输出 `out_hash_opcode_table_row`；`ZkVmExecutorCircuitBoardGenerator.cs:243-263` 重算同一哈希，`:247-248` 注释写明 “manually verified by verifiers”；域分隔魔数 `MagicNumber.cs:24` | `VERIFIED_SOURCE` |
| 地址操作数 | `ZkVmExecutorCircuitBoardGenerator.cs:224-227`：原私有 `in_mem_addr` 被注释，实际 `Wire inMemAddrWire = inRegisterWires[0]`；`ZkVmOpType.cs:44-51` 注释明确“地址在 Reg0，Arg0 是数据寄存器”；执行器 `ZkProgramExecutor.cs:225-226` `AddPrivate("in_mem_addr", thisRegisters[0])` | `VERIFIED_SOURCE` |
| `thisRegisters[0]` 更新 | `ZkVmExecutorCircuitBoardGenerator.cs:793-874` 组装 `out_reg_i`：`:799-814` 按 `op AND arg0==i` 选热寄存器候选，`:858-859` 默认保持 `in_reg_i`；Load 写回在 `:508-515`（`inMemValWire`），Store 不改寄存器 `:499-506`；执行器 `:369-373` 把 `out_reg_0..15` 写回 | `VERIFIED_SOURCE`（机制）；Load 注释写 “Set reg0” 但代码按 `arg0` 写，属通用热寄存器写 → `INFERRED` |
| Load 数据入口 | `ZkVmExecutorCircuitBoardGenerator.cs:220-222` `in_mem_val` 私有输入；执行器 `ZkProgramExecutor.cs:296-298` 把 `memVal` 送入；`memVal` 来自 `:230` 的 `out_trace_mem_val`（step 0 为 `:202` 的 `zeroShare`） | `VERIFIED_SOURCE` |
| Store 数据出口 | `ZkVmExecutorCircuitBoardGenerator.cs:929-937` `out_mem_val = isStore × inRegAtArg0`，私有输出；执行器 `:337-342` 收集 | `VERIFIED_SOURCE` |
| 非内存步 dummy Fetch 地址 | `ZkVmExecutorCircuitBoardGenerator.cs:941-943` 默认地址 `NegOne`（`FieldFactory.NegOne = p−1`）；`:945-961` `out_mem_addr = Store ? reg0 : NegOne`；`:968-981` `is_mem_op = Load OR Store`、`is_mem_write = Store`；`:989-1007` trace 地址 `Store/Load ? reg0 : NegOne`，trace 值 `Store/Load ? val : 0` | `VERIFIED_SOURCE` |
| step 0 无 Fetch | `ZkProgramExecutor.cs:201-203` `if (globalStepCounter == 0) memVal = zeroShare; else` 才构造 MemoryFetch；电路侧 `ZkVmExecutorCircuitBoardGenerator.cs:101-123` 计 `is_global_step_counter_non_zero`，`:133-145`、`:172-193`、`:147-169`、`:195-217` 把 pc/reg 与哈希在 step 0 归零；`MemoryTraceFetchCircuitBoardGenerator.cs:8` 要求 `traceCount > 0` | `VERIFIED_SOURCE`（归零/跳转），step 0 的 `inMemAddrWire=0` 为 `INFERRED` |
| 逐步 pc/opcode/addr 绑定 | pc 为私有输入（`ZkVmExecutorCircuitBoardGenerator.cs:134-136`），opcode 行为私有输入（`:231-241`），地址来自私有 reg0（`:177,227`）；约束只保证 witness 与**本轮公开哈希表/哈希链**自洽，执行器在 `:302-332` 做外部哈希比较。没有单一电路内的 `(pc_i, opcode_i, addr_i)` 直接公开绑定 | `VERIFIED_SOURCE`（存在性）+ `INFERRED`（结论） |

## A2. Fetch 与 MemoryTrace

| 审计项 | 源码事实 | 标签 |
| --- | --- | --- |
| Fetch 地址输入 | `MemoryTraceFetchCircuitBoardGenerator.cs:41-42` `in_mem_addr` 为 `Wire.NewPrivateInputWire`；trace 各列 `:17,24` 同为私有输入；`:52` 逐行 `FieldEquals(in_trace_row_mem_addr, in_mem_addr)`；`:74-85` 输出 `out_trace_mem_val` 为私有输出 | `VERIFIED_SOURCE` |
| Fetch 地址与 `out_trace_mem_addr` | Fetch 侧地址 = `thisRegisters[0]`（`ZkProgramExecutor.cs:226`）；Executor 侧 `:989-997` 的 `out_trace_mem_addr` 在 Load 分支取 `inMemAddrWire`（=`inRegisterWires[0]`，`:227`），Store 分支取 `outMemAddrWire`（`:953-961` 亦取 reg0）。二者**构造上同源**，但分属不同电路，源码中没有一条 in-circuit 等式 `in_mem_addr == out_trace_mem_addr` | `VERIFIED_SOURCE`（同源）+ `INFERRED`（无显式等式） |
| trace 列 | `MemoryTraceFetchCircuitBoardGenerator.cs:9` `ColumnNames = ["mem_addr","global_step_counter","is_mem_op","is_mem_write","mem_val"]`；`:10` 只取 `mem_val` | `VERIFIED_SOURCE` |
| Prove 消费 trace | Prove 快照 `L12 → 原始 L8` 复用同一列集；`L47/53 → 原始 L43/49` 把 trace 作为私有输入；`L65-82 → 原始 L61-78` 为每行公开输出 `out_{row}_hash_mem_trace = H(magic=9, step, is_mem_op, is_mem_write, addr, val, enc_key)`；`L84-162 → 原始 L80-158` 检查排序顺序（末次访问按地址升序、其余按 step 升序）；`L171-197 → 原始 L167-193` 检查同址非写时值不变；`L209-216 → 原始 L205-212` 公开 `out_is_satisfied` | `VERIFIED_SOURCE` |
| trace 字段来源 | `address/value`：`ZkVmExecutorCircuitBoardGenerator.cs:995/1005` 私有输出 → `ZkProgramExecutor.cs:397` 写入 trace；`step`：不是电路输出，由 `:393-395` 以公开值 `MpcShareFromPublicValue(globalStepCounterField)` 注入；`operation`：只有 `is_mem_op/is_mem_write` 布尔列（`:968-981`），**没有原始 opcode 列** | `VERIFIED_SOURCE` |
| 是否绑定 PC/opcode/操作数 | Prove 电路输入只有 trace 列与 `in_enc_key`，**不接收 pc/opcode/操作数**，只检查 trace 内部一致性与哈希；`MemoryTraceProve...cs:168-169 → 原始 164-165` 明确写“非内存操作地址 NegOne、值 0，因此可忽略 is_mem_op” | `VERIFIED_SOURCE` |
| 跨电路哈希核对 | `ZkProgramExecutor.cs:404-408`、`:567-583` 对 `out_hash_mem_trace` 与 Prove 的行哈希做**多重集计数比对**；这是在 MPC 执行器代码中的外部检查，不是电路内约束；`enc_key` 哈希同样在 `:176-181`、`:302-308` 外部核对 | `VERIFIED_SOURCE`（代码）+ `INFERRED`（安全边界） |
| trace 公开可见性 | pc/reg/addr/trace 列都是秘密分享私有输入（`:226`、`:292-294`、`:488`），外部只见哈希摘要（`:406`、`ZkVmExecutorCircuitBoardGenerator.cs:1017`） | `VERIFIED_SOURCE` |

## A3. 程序执行与静态证书

| 审计项 | 源码事实 | 标签 |
| --- | --- | --- |
| BubbleSort 输入与初始化 | `BubbleSortProgramGenerator.cs:18` `Set R15,1`；`:19` `PublicInput R1`（n）；`:20` `Set R0,0`；`:29` `Move R8,R1`；`:32` `Set R2,0`；`:33` `Set R6,0`；`:76` 示例 `n=5`。源码**无** `n≥1`/`n≤Nmax`/`n<p−1` 约束；`:79` 的 `globalStepsNoMoreThan` 只是执行器阈值（`ZkProgramExecutor.cs:114-116`） | `VERIFIED_SOURCE`（存在/缺失）+ `INFERRED`（无界结论） |
| 指令与访存点 | `BubbleSortProgramGenerator.cs:18-73` 共 **43 条**，PC 0–42，Halt 在 PC42；Load/Store 在 PC **4/16/18/22/24/36**，地址全部取 R0；`arg0` 是数据寄存器 | `VERIFIED_SOURCE` |
| 控制流 | 输入循环 PC3→8（`:21-26`）；排序内层 PC12→28（`:35-56`）；外层 PC30/31/34（`:59-63`）；输出循环 PC35→41（`:66-72`） | `VERIFIED_SOURCE` |
| 静态证书来源 | 实验侧 `src/aba_01/cfg.py:4-6` 明确是从上述 L16–74 转录；`analyzer.py` 推导 `address_register=0`、`address_def_pc`、`guard_pc`、`proof_rule`、`interval=[0,n−1]`；`certificate.py` 独立重放规则检查。PC 值与上游一致，但整套结构化事实是实验侧 **CONSTRUCTED** | PC 值 `VERIFIED_SOURCE`；机制 `CONSTRUCTED` |
| 证书绑定项 | `cfg.py:46-56` 对 `code_name+source_commit+source_path+instrs` 做 canonical JSON 后 sha256；`certificate.py:255-261` 重算；含 `instruction_count=43`；**不含**具体 `n`，**不含** `program_id`，**不读取** C# 实例文件或 R1CS | `VERIFIED_SOURCE` |
| 与执行字节码一致性 | 本 pinned commit 内，Python 转录的 43 条与 C# 逐条一致；但生成路径完全离线（`certificate.py:54-85` 只接受 Python `Program`）。C# 执行从 `{CodeName}.instance.{party}.json` 反序列化（`...Experiment...Program.cs:474-475,580-581,700-701`），`ZkProgramExecutor.cs:58,147-157` 直接取 `program.Opcodes`，从不读证书 | `VERIFIED_SOURCE`（一致性 + 解耦） |
| 运行时强制验证 | 在 `D:/tmp/aba01/src/` 全量搜索 `certificate/aba-01/nmax/analyzer` 无命中；`ZkProgramExecutor.cs:170-181,302-332,551-565,567-583` 的检查都是同一次执行内部哈希自洽与 `out_is_satisfied`，期望值来自前序执行输出而非证书；只有 `r1cs.SelfVerify()`（`...Program.cs:258`） | `VERIFIED_SOURCE`（缺失）+ `INFERRED`（结论） |
| 可复用的程序身份机制 | 有逐行 opcode 哈希、pc/寄存器链哈希、enc_key 哈希、magic 域分隔（`MagicNumber.cs:9-30`），但**没有整程序 hash / ROM commitment**；哈希 preimage 含 `global_step_counter` 且每次执行用随机 `enc_key`（`ZkProgramExecutor.cs:61`），不能稳定充当 program ID | `VERIFIED_SOURCE`（缺失）+ `INFERRED` |
| n 是否公开 | 是：`ZkProgramExecutor.cs:256-262` 在 `PublicInput` 处 `AddPublic`；取指电路把 `PublicInput` 列为 revealed op（`:14`、`:237-269`）；opcode 表整表公开。但公开 ≠ 有界 | `VERIFIED_SOURCE` |

## A4. 三段结论汇总

1. **地址界限正确性**：静态推导 `[0,n−1]` 只在外部假设 `1≤n≤Nmax` 下成立；上游执行电路没有任何 n 范围或地址范围约束 → `CONSTRUCTED` + `INFERRED`。
2. **执行绑定正确性**：`trace_addr` 与 Fetch 地址在构造上都来自同一 `reg0`（`ZkVmExecutorCircuitBoardGenerator.cs:227` vs `ZkProgramExecutor.cs:226`），但跨电路一致性依赖执行器外部哈希核对，且 verifier 只见哈希；没有电路内直接绑定 → `INFERRED`，强绑定 `BLOCKED`（接口未定义）。
3. **电路强制性**：当前既无 `n≤Nmax`、也无 `addr<n` 的 bit-decomposition/comparator 约束；静态证书完全在电路外 → `VERIFIED_SOURCE`（缺失证据）。
