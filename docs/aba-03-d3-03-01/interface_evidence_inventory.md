# ABA-03-D3-03-01 / Phase 1：接口证据清单（R5–R8）

> 实验仓起点：`9788d5c1888ac28ee936892d36086cac32423115`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读源码证据审计。本轮允许只读打开固定 commit 下 `docs/source-snapshot/` 的源码快照核实接口与行号；未修改任何文件、未实现电路、未运行测试。plonk.rs / verifier.rs 的 Rust 侧接口沿用 `../aba-03-c2/verifier_interface_audit.md` 与 `../aba-03-d3-01/verifier_independence.md` 已固定的证据（本仓无其源码快照，不重抓）。
>
> 标签：`VERIFIED`（固定 commit 源码/接口直接支持）· `CONSTRUCTED`（本轮候选接口/约束）· `INFERRED`（由已验证事实推导）· `UNKNOWN`（缺证据）· `BLOCKED`（固定架构缺必要接口）。
>
> 行号口径：C# 快照 `docs/source-snapshot/CompatCircuit__*.cs` 头部有 4 行抓取信息（SOURCE/PATH/BLOB SHA/空行），但本文沿用既有 `source-audit.md` / `aba-03/source_trace_audit.md` 已冻结的**原始行号**口径（去掉 4 行头后 = 原始行号）；已逐一在当前快照中复读核对，行号一致。Prove 电路快照头部同为 4 行，原始行号 = 快照行号 − 4（沿用 `source_trace_audit.md` 口径）。

---

## 0. 四类数据来源的严格区分（本轮最重要的方法学边界）

B4 的核心问题是：step、事件类型、trace row、终止步数是否来自"同一次完整 VM 执行"，还是 prover 自我声明。为此必须把每个字段归入以下四类之一，不得混淆：

| 类别 | 定义 | 能否作为 verifier 可信来源 |
| --- | --- | --- |
| **VM 内部 witness** | 电路内由私有输入/状态派生的线值（reg0、pc、opcode 行、is_mem_op、out_trace_mem_addr） | 否，除非被约束进 public statement 或承诺 |
| **host 传入值** | C# 执行器 `AddPublic`/`AddPrivate` 注入的值（global_step_counter、opcode table、public/private input） | 否；`AddPublic` 只表示进入 proof public input，不表示由 verifier 固定 |
| **circuit public input / output** | 声明为 `NewPublicInputWire` / `IsPublicOutput` 的线 | public input 是 verifier 可见的 statement 一部分；public output 随证明公开，但其"正确性"取决于电路约束与输入来源 |
| **verifier 固定/可信取得** | 独立 verifier 预先固定或经可信通道取得（预期 opcode table、VK、预期 T） | 是；当前固定 commit **不存在**独立 verifier 主体 |

**关键结论（VERIFIED）**：当前 `plonk.rs:293-315` 在同一函数内 setup→prove→reveal→verify，vk 由 `test_rng()` 现场生成（`plonk.rs:302-304`），public inputs 全部来自 prover 的 JSON（`plonk.rs:97-110,143-161,203-247`）。因此"某字段是 circuit public input"**不等于**"verifier 已用可信期望值检查它"；"host 做了 `if (...) throw` 检查"**不等于**电路约束或 proof soundness。这是全篇的判断基线。

---

## 1. 七类组件接口逐项记录

### 组件 1：VM 执行电路（ZkVmExecutorCircuitBoardGenerator）

| 项 | 内容 | 标签 |
| --- | --- | --- |
| 源码路径 | `docs/source-snapshot/CompatCircuit__CollaborativeZkVm__ZkVmCircuits__ZkVmExecutorCircuitBoardGenerator.cs` | VERIFIED |
| step 相关输入 | `in_global_step_counter` 为 `Wire.NewPublicInputWire`（L106-107），由 host 每步注入；用于 step0 归零（L110-125、L142-217）与哈希 preimage（L155、L251、L880、L891） | VERIFIED |
| 执行语义输入 | `in_this_program_counter`（私有）、`in_opcode_table_op/arg0/arg1/arg2`（私有 L231-241 原始）、`in_this_reg_i`（私有）、`in_enc_key`（私有）、`in_mem_val`（私有 L220-222 原始） | VERIFIED |
| 地址 | `inMemAddrWire = inRegisterWires[0]`（L231 原始），即地址固定在 reg0，私有 | VERIFIED |
| 输出（私有） | `out_mem_val`、`out_mem_addr`、`out_program_counter`、`out_reg_0..15`、`out_mem_addr`、`out_trace_mem_addr/mem_val/is_mem_op/is_mem_write`（L929-1007 原始） | VERIFIED |
| 输出（public） | `out_hash_this_program_counter`、`out_hash_this_registers`、`out_hash_opcode_table_row`、`out_hash_next_program_counter`、`out_hash_next_registers`、`out_hash_mem_trace`、`out_halt`、`out_error`、`out_public_output`（L251、L880-923、L1013 原始） | VERIFIED |
| 生成者 | MPC 执行器 `CircuitBoardMpcExecutorWrapper`，每步一个独立 session（`ZkProgramExecutor.cs:142,250,142`） | VERIFIED |
| verifier 当前可检查 | 只见 public output 哈希与 public input（step counter / public input / opcode table）；pc/reg/opcode/addr 均为私有 witness，不可见 | VERIFIED |
| 与 R5–R8 关系 | R5（step 是 host public input 非电路状态）、R6（is_mem_op 私有派生）、R7（out_trace_mem_addr 私有派生）、R8（out_halt 是 public output） | VERIFIED |

### 组件 2：Fetch 电路（MemoryTraceFetchCircuitBoardGenerator）

| 项 | 内容 | 标签 |
| --- | --- | --- |
| 源码路径 | `docs/source-snapshot/CompatCircuit__CollaborativeZkVm__ZkVmCircuits__MemoryTraceFetchCircuitBoardGenerator.cs` | VERIFIED |
| 列定义 | `ColumnNames = ["mem_addr","global_step_counter","is_mem_op","is_mem_write","mem_val"]`（L13）；`ColumnNamesToBeFetched = ["mem_val"]`（L14） | VERIFIED |
| 输入（全部私有） | trace 各列 `in_trace_{row}_{col}` 为 `NewPrivateInputWire`（L24-28）；查询地址 `in_mem_addr` 为 `NewPrivateInputWire`（L45-46） | VERIFIED |
| 约束 | 逐行 `FieldEqualsGadget(in_trace_mem_addr_wires[row], in_mem_addr)` 产生选择位（L56）；LowBit 选最新匹配；无 step 约束、无 is_mem_op 输入/约束 | VERIFIED |
| 输出 | `out_trace_mem_val`（`SelectCompose`，私有，L79-86）；只取 `mem_val` 列 | VERIFIED |
| 生成者 | 每步≥1 在 `ZkProgramExecutor.cs:205-234` 构造；step0 跳过（`:205`） | VERIFIED |
| verifier 当前可检查 | 无 Fetch 专属 public input/output；地址与 trace 行都是私有 witness | VERIFIED |
| 与 R5–R8 关系 | R7（地址逐行比对在电路内，但 trace 行与当前 step 的对应无公开绑定）；R6（Fetch 不接收 is_mem_op，dummy/real 分支不在本电路） | VERIFIED |

### 组件 3：MemoryTrace row 生成位置及字段

| 项 | 内容 | 标签 |
| --- | --- | --- |
| 生成位置 | `ZkProgramExecutor.cs:393-405` 每步把 `out_trace_{colName}` 收集成一行并 `AddMemoryTrace`；step 列用 public `globalStepCounterField`（L397-398），其余列取电路私有输出（L401） | VERIFIED |
| 字段来源 | `trace_mem_addr`/`trace_mem_val` 来自 VM 电路私有输出（ZkVmExecutor L990-1007）；`is_mem_op=Load∨Store`、`is_mem_write=Store`（L972-984）；无原始 opcode 列 | VERIFIED |
| 有序性假设 | `ZkProgramExecutor.cs:87` 注释："we assume that globalStepCounter is ordered. As long as MPC parties honestly behave, this assumption holds." | VERIFIED |
| step↔row 对应 | row 在 host 侧按执行顺序 append（`:100`），step 列由 host 注入；**无电路内 step↔row 位置约束** | VERIFIED + INFERRED（结论） |
| verifier 当前可检查 | 不可见 trace 行内容；只见 Prove 电路公开的行哈希多重集 | VERIFIED |
| 与 R5–R8 关系 | R5（step 列 host 注入）、R7（row 来源私有 + host append）、R8（row 数由执行步数决定但无电路约束） | VERIFIED |

### 组件 4：is_mem_op / opcode / PC 执行语义信息来源

| 项 | 内容 | 标签 |
| --- | --- | --- |
| opcode 表 | `InstructionFetchCircuitBoardGenerator.cs:126-156` 整表为 `NewPublicInputWire`；执行器 `ZkProgramExecutor.cs:147-157` 逐行 `AddPublic` | VERIFIED（既有证据） |
| PC | `in_this_program_counter` 私有输入（ZkVmExecutor L134-136 原始）；逐行哈希 public output 链 | VERIFIED |
| is_mem_op 派生 | `out_trace_is_mem_op = BoolOr(op==Load, op==Store)`（L972-978），私有 output；`is_mem_write = Store`（L982-984） | VERIFIED |
| Prove 对 is_mem_op 的处理 | Prove 电路 L119 注释"不需要确保 is_mem_op/is_mem_write 在 [0,1]，哈希输出已保证"；L169 "we can safely ignore is_mem_op"；Prove 输入只有 trace 列 + enc_key，不接收 pc/opcode | VERIFIED |
| verifier 当前可检查 | opcode 表可作 public input 比对（P1-A）；is_mem_op 与 PC 是私有 witness，不可直接检查 | VERIFIED |
| 与 R5–R8 关系 | R6（类型来源私有派生、Prove 忽略）；R5（PC/opcode 私有，无法证明 step 来自真实执行） | VERIFIED |

### 组件 5：VM 执行步数、停止条件及产生位置

| 项 | 内容 | 标签 |
| --- | --- | --- |
| 步数计数 | `for (globalStepCounter = 0; ; globalStepCounter++)`（L116），C# host 循环变量 | VERIFIED |
| 步数上限 | `GlobalStepNoMoreThan`（L34/L118-120），执行器阈值，超出 `throw`；非电路约束 | VERIFIED |
| 停止条件 | `out_halt` 为 public output（ZkVmExecutor L902-906）；host 在 L419-421 `if (pubOutHalt == One) break;` | VERIFIED |
| 最终步数记录 | `ZkProgramExecuteResult.GlobalStepCounter = globalStepCounter`（L601），host 返回值 | VERIFIED |
| verifier 当前可检查 | halt 状态随 proof 公开但无 verifier 固定预期终止；最终 T 不进入 statement 作为可锚定值 | VERIFIED |
| 与 R5–R8 关系 | R8（终止锚定缺失：halt 是电路输出但 break 与最终 T 由 host 控制） | VERIFIED |

### 组件 6：电路 public input 的生成、排列与验证

| 项 | 内容 | 标签 |
| --- | --- | --- |
| public input 集合 | 每步 VM 电路：`in_global_step_counter`、`in_public_input`（n 等）、opcode table 四列（C# `ZkProgramExecutor.cs:149,157-160,265-268,287`；Rust `plonk.rs:143-161`） | VERIFIED（既有证据） |
| 排列 | Rust 侧 `named_public_values` 按 circuit 定义顺序排列进 `&public`（`plonk.rs:143-161,203-247`） | VERIFIED（既有证据） |
| 来源 | 全部来自 prover 的 JSON（`plonk.rs:97-110`）；无 prover 之外的期望值 | VERIFIED（既有证据） |
| 验证 | `verifier.rs:27-61 verify_proof(pvk, proof, public_inputs)` 只做长度 + pairing 等式 | VERIFIED（既有证据） |
| 与 R5–R8 关系 | R5（step 是 public input 但来源 prover）、R8（T 不在 public input 集合）、全局（public input 存在 ≠ verifier 检查） | VERIFIED |

### 组件 7：proof / VK / public input 的传递方式

| 项 | 内容 | 标签 |
| --- | --- | --- |
| setup | `plonk.rs:302-304` `test_rng()` 现场 `universal_setup` + `circuit_setup` 得 `(pk,vk)` | VERIFIED（既有证据） |
| prove | `plonk.rs:311` `MpcPlonk::prove`；`:312` `mpc_pf.reveal()` | VERIFIED（既有证据） |
| verify | `plonk.rs:314` `LocalPlonk::verify(&vk, &v_circ, pf, &public)`，同一函数内 | VERIFIED（既有证据） |
| VK 信任模型 | 外部 verifier 是否固定/可信取得 VK：`UNKNOWN`；是否接受 prover 自提 VK：`UNKNOWN`；条件性重选 setup 风险：`CONDITIONAL INFERENCE`（沿用 D1-C1 分级，本轮不改） | 既有结论 |
| 与 R5–R8 关系 | 全局：无独立 verifier，任何"verifier 检查"目前都是 prover 进程内自洽检查 | VERIFIED |

---

## 2. 证据清单小结：四类来源在 R5–R8 上的分布

| 字段 | VM witness | host 传入 | circuit public | verifier 固定 | 当前可信来源？ |
| --- | --- | --- | --- | --- | --- |
| step counter | — | ✓（`AddPublic`） | ✓（public input） | ✗ | 否（prover/host 提供） |
| is_mem_op / opcode | ✓（私有派生） | opcode 表 ✓ | opcode 表 ✓ | ✗ | 否（类型 witness 私有） |
| trace_mem_addr row | ✓（私有输出） | step 列 ✓ | ✗（只有行哈希） | ✗ | 否 |
| halt / T | ✓（halt public output） | break 控制 ✓ | halt ✓ / T ✗ | ✗ | 否 |

**本轮核心判断（VERIFIED + INFERRED）**：R5–R8 所需的四类信息（可信 step、事件类型、trace 行对应、真实终止步）在当前固定实现中**全部**停留在"VM 内部 witness / host 传入 / prover 提供的 public input"三类，没有任何一项由 verifier 固定或可信取得。这不等于"架构不可能"，但意味着当前的证明接口**尚未**让 verifier 摆脱对 prover/host 自我声明的依赖。逐项可实现性判断见 `r5_step_provenance.md`、`r6_r7_event_trace_binding.md`、`r8_termination_anchor.md`，总判定见 `decision.md`。
