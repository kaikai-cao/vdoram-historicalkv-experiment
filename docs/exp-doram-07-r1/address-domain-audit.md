# EXP-DORAM-07-R1 — 固定地址域假设审计

> 目标：核查「影子表依赖固定有限地址域 `[0,n-1]`」这一假设在固定上游源码与现有 workload 范围内的证据等级。
> 证据分级：**VERIFIED** 源码/实验直接证明；**CONSTRUCTED** 我们自行定义的实验假设；
> **INFERRED** 由源码结构推导但无直接保证；**UNKNOWN** 现有证据不能确认。
> 不为让方案成立而自行添加地址范围假设。

## 0. 结论（先写结论）

> **固定 n 槽位影子表目前只适用于地址域有界的工作负载模型，不能据此宣称可直接替代原始 VDORAM 的任意域地址语义。**

- 地址字段是 **BLS12-377 标量域元素（253-bit）**，源码**未见**对内存地址的显式 `[0,n-1]` 范围约束（VERIFIED 无约束；范围上界 UNKNOWN）。
- 上游 `ZkProgramExecutor` 把 `in_mem_addr` 设为 `thisRegisters[0]`（通用寄存器，任意域元素），
  **没有**任何「地址必须 < 某常量」的电路约束（VERIFIED）。
- 示例程序 BubbleSort 通过 `LessThan(R0, R1)` 与公开数组长度 R1 **在程序逻辑层**把访问索引限制在 `[0, n_input-1]`
  （INFERRED：程序构造保证，非电路层强制）。
- 本实验的 5 类 workload 把地址显式限制在 `[0,n-1]`（CONSTRUCTED：我们定义的假设，不等于目标系统事实）。
- 因此影子表适用性必须**严格限定为有界地址域工作负载模型**；无界或超域地址下 `n` 槽位表无法表示，需外部范围证明或更大域。

## 1. 逐项核查（任务 8 的 8 个问题）

### 8.1 地址字段的具体类型与模数 — VERIFIED

- `ArithConfig.cs @ pinned`：`FieldSize = 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`，
  注释 `// BLS12-377`，`BitSize = 253`。
- `FieldFactory.cs @ pinned`：`New(BigInteger value) => new(value, this.FieldSize)`；`NegOne = New(FieldSize - 1)`。
  地址为域元素，取值空间 ≈ 2^253，不是小整数集合。
- `ZkProgramExecutor.cs`（快照 L229-230）：`in_mem_addr = thisRegisters[0]`，寄存器是 `MpcValue`（秘密共享域元素）。

### 8.2 上游是否显式约束地址范围 — VERIFIED（无此类约束）

- 全仓库 fixed commit 的 `ZkVmExecutorCircuitBoardGenerator.cs`（快照 1027 行）中，
  对 `in_mem_addr`/`out_mem_addr` 只做 `SelectComposeOtherwiseGadget(2)` 的 STORE/LOAD/NegOne 选择
  （L959-1000），**没有** `LessThan(addr, bound)` 或 range-check gadget 作用于内存地址。
- `constNumberWires`（L28-82）只预置 `0,1,2, 0..RegCount-1, opcode 值, 二进制幂` 等常量；
  寄存器选择 `SelectComposeGadget(RegCount)` 比较的是 opcode 参数与这些常量（L270-333），
  即**约束的是寄存器下标 `arg0/arg1/arg2 ∈ [0,RegCount-1]`**，不是内存地址值。
- 结论：内存地址是否落在某个小范围，电路层不强制；由程序语义间接决定（见 8.3/8.4）。

### 8.3 VM 真实生成的内存地址来自何处 — VERIFIED

- `ZkProgramExecutor.cs` L229-230：`in_mem_addr = thisRegisters[0]`，即 **reg0**，由程序 opcode 赋值。
- `BubbleSortProgramGenerator.cs`（快照 L22-83）：`Set R0,0` 后用 `Add R0,R0,R15` 递增，
  `LessThan R2,R0,R1` + `JumpIfZero` 控制循环；`Store/Load arg0` 指向该 R0。
  即地址来自**程序内循环计数器**，受程序逻辑约束。
- `ZkProgramOpcode.cs`（快照）：`Arg0/Arg1/Arg2` 均为 `Field`，`FromString` 用 `int.Parse` 后 `FieldFactory.New`，
  宿主侧参数是整数但**无范围校验**（VERIFIED：构造函数只判 required，不判大小）。

### 8.4 程序或参数是否限制最大内存规模 — INFERRED（程序层有，电路层无通用保证）

- BubbleSort：`publicInput = array length`（L23 `PublicInput R1`），`globalStepsNoMoreThan = opcodes.Count * n_input^2`（L83）。
  最大索引由 `LessThan(R0, R1)` 有界，R1 来自公开输入 → **程序层**访问 `[0, n_input-1]`（INFERRED）。
- 但这是**该示例程序**的构造；`ZkProgramInstance @ pinned` 的 `GlobalStepsNoMoreThan` 与 `PublicInputs`
  是宿主字段，未见「地址空间上限 n」这一通用参数。目标系统若运行其它程序，地址来源可能不同（UNKNOWN）。

### 8.5 是否存在地址空间扩展或动态分配 — UNKNOWN（未见机制，但不能证明不存在）

- 本轮核查的源码中未见 heap/allocator/dynamic address space 相关结构；地址为寄存器值。
- 不能从「未见」推出「不存在」：其它程序或其它实验目录可能用不同地址策略。判定 UNKNOWN。

### 8.6 现有 workload 能否证明所有有效地址均属于 [0,n-1] — CONSTRUCTED

- R1 的 `generate_workload(n,T,...)` 显式用 `rng.randrange(n)` 取地址 ∈ `[0,n-1]`；
  NOOP 的 `fetch_address = (step*k+n) % n` 也在域内。这是**我们定义的实验假设**，
  目的是让 n 槽位表有明确语义，**不构成对目标系统的证明**。
- 边界测试（test_b_unwritten_address / invalid-address）确认：域外查询在三模型都返回默认 0，
  但这只是模型约定，不表示目标系统也如此。

### 8.7 dummy Fetch 地址与实际有效地址如何区分 — VERIFIED

- `in_mem_addr = reg0`（L230），dummy Fetch（STORE/NOOP 步）也用 reg0 普通地址扫描全历史。
- trace 行的 `mem_addr`：非内存 op 由 `SelectComposeOtherwiseGadget(2)` 取 `constNumberNegOneWire = FieldSize-1`（L946, L992, L1000），
  即 NegOne 哨兵，与 `[0,n-1]` 内的有效地址在域元素层面天然不同（除非某有效地址恰等于 FieldSize-1，见 8.8）。
- 模型层：`DUMMY_ADDR = 2^32-1` 作为 NegOne 的 Python 代理（见 models.py）；与 `[0,n-1]`（n≤1024）不冲突。

### 8.8 地址映射到有限数组是否需要额外约束 — VERIFIED（需要，且不免费）

- 把任意域元素地址 `a` 映射到固定 `n` 槽位数组，必须保证 `a ∈ [0,n-1]`，否则数组无法索引。
  这一范围约束在上游电路中**不存在**（8.2）。因此 E1 影子表要落地必须**额外增加**：
  1. 一个地址范围约束（`a < n` 的电路/证明），或
  2. 由程序层保证并将该保证作为外部信任假设（类似 D3-02 的 EXTERNAL_TRUST 布局签名思路）。
- 若 `a = NegOne = FieldSize-1`（非内存 op 的 trace 地址），n 槽位表无法表示，必须单独处理为「非内存行」。
- 结论：固定域假设不是免费的，它是 E1 成立的前提条件之一，证据等级 CONSTRUCTED（我们的 workload）/
  INFERRED（示例程序），**非 VERIFIED**。

## 2. 证据汇总表

| 命题 | 等级 |
|---|---|
| 地址是 BLS12-377 域元素（253-bit），空间远大于 n | VERIFIED |
| 上游电路无地址范围约束 | VERIFIED |
| Fetch 地址 = reg0，dummy Fetch 同样全历史扫描 | VERIFIED |
| 非内存 op 的 trace 地址 = NegOne 哨兵 | VERIFIED |
| 示例程序 BubbleSort 在程序层把索引限制在 [0, n_input-1] | INFERRED |
| R1 workload 把地址显式限制在 [0,n-1] | CONSTRUCTED |
| 目标系统所有有效地址均有界 | UNKNOWN |
| 影子表需额外范围约束或外部信任假设 | VERIFIED（逻辑必然） |

## 3. 对研究问题的限定

本轮核心问题「在原始 Fetch 全历史扫描语义下，固定地址域当前状态表是否仍有算法成本优势」，
必须加上限定：**仅在地址域有界（a ∈ [0,n-1] 由程序或外部约束保证）且与 n 已知的工作负载模型下**讨论。
超出该限定，E1 不适用，不能与原始 VDORAM 的任意域地址语义直接比较。
