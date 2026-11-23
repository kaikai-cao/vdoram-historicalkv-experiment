# ABA-01 阶段 A：Bubble Sort 固定源码语义与证据

**上游**：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`（只读获取，未修改）。
**行号口径**：下列“L”均为该 commit 中文件原始行号（通过 GitHub blob 抓取，未加任何头部）。本地实验快照 `docs/source-snapshot/*.cs` 含 4 行抓取头，行号偏移 +4，不能直接用其行号引用。
**原则**：只记录源码可证事实；注释中的意图（如“if R0 < R1, goto”）不视为已验证约束，必须与电路生成代码交叉核对。

---

## 1. 程序指令序列（PC = 指令下标）

来源：`CompatCircuit/CollaborativeZkVm/ZkPrograms/Examples/BubbleSortProgramGenerator.cs` L16–L74。共 42 条，PC 0–42（Halt 为 PC 42）。

| PC | 指令 | 源码行 | 说明（源码注释） |
| --- | --- | --- | --- |
| 0 | `Set 15,1` | L18 | R15 = 1 |
| 1 | `PublicInput 1` | L19 | R1 = 公开输入（数组长度 n） |
| 2 | `Set 0,0` | L20 | R0 = 0 |
| 3 | `PrivateInput 2` | L21 | R2 = 下一个私有输入 |
| 4 | **`Store 2`** | L22 | **mem[R0] = R2** |
| 5 | `Add 0,0,15` | L23 | R0 = R0 + 1 |
| 6 | `LessThan 2,0,1` | L24 | R2 = bool(R0 < R1) |
| 7 | `Not 2,2` | L25 | R2 = NOT R2 |
| 8 | `JumpIfZero 2,3` | L26 | 若 R2==0 跳回 3（即 R0<R1 时继续） |
| 9 | `Move 8,1` | L29 | R8 = R1 |
| 10 | `Set 2,0` | L32 | R2 = 0（外层头） |
| 11 | `Set 6,0` | L33 | R6 = 0（交换计数） |
| 12 | `Add 3,2,15` | L35 | R3 = R2 + 1（内层头） |
| 13 | `LessThan 4,3,1` | L36 | R4 = bool(R3 < R1) |
| 14 | `JumpIfZero 4,29` | L37 | R3 >= R1 时跳到 29 |
| 15 | `Move 0,2` | L38 | R0 = R2 |
| 16 | **`Load 4`** | L39 | **R4 = mem[R0] = mem[R2]** |
| 17 | `Move 0,3` | L40 | R0 = R3 |
| 18 | **`Load 5`** | L41 | **R5 = mem[R0] = mem[R3]** |
| 19 | `LessThan 7,5,4` | L42 | R7 = bool(R5 < R4) |
| 20 | `JumpIfZero 7,26` | L43 | R5 >= R4 时跳到 26（不交换） |
| 21 | `Move 0,2` | L46 | R0 = R2（交换分支） |
| 22 | **`Store 5`** | L47 | **mem[R0] = R5 → mem[R2]** |
| 23 | `Move 0,3` | L48 | R0 = R3（交换分支） |
| 24 | **`Store 4`** | L49 | **mem[R0] = R4 → mem[R3]** |
| 25 | `Add 6,6,15` | L50 | R6 = R6 + 1（交换计数递增） |
| 26 | `Move 2,3` | L54 | R2 = R3（合并点，两分支都执行） |
| 27 | `Set 0,0` | L55 | R0 = 0 |
| 28 | `JumpIfZero 0,12` | L56 | 无条件跳回 12（因 R0 刚置 0） |
| 29 | `Set 0,0` | L58 | R0 = 0 |
| 30 | `LessThan 0,0,6` | L59 | R0 = bool(0 < R6) |
| 31 | `JumpIfZero 0,35` | L60 | R6 == 0 时跳到 35 |
| 32 | `Sub 1,1,15` | L61 | **R1 = R1 − 1**（每有交换的一轮，有效上界收缩） |
| 33 | `Set 0,0` | L62 | R0 = 0 |
| 34 | `JumpIfZero 0,10` | L63 | 无条件跳回 10 |
| 35 | `Set 0,0` | L66 | R0 = 0（输出循环） |
| 36 | **`Load 2`** | L67 | **R2 = mem[R0]** |
| 37 | `PublicOutput 2` | L68 | 公开输出 R2 |
| 38 | `Add 0,0,15` | L69 | R0 = R0 + 1 |
| 39 | `LessThan 2,0,8` | L70 | R2 = bool(R0 < R8) |
| 40 | `Not 2,2` | L71 | R2 = NOT R2 |
| 41 | `JumpIfZero 2,36` | L72 | R0 < R8 时跳回 36 |
| 42 | `Halt` | L73 | 停机 |

## 2. Load/Store 清单与执行前 R0 来源

| PC | 操作 | R0 的直接来源 | 上游定义链 |
| --- | --- | --- | --- |
| 4 | Store | PC2 `Set 0,0` 或 PC5 `Add 0,0,15` 的回边值 | 输入初始化循环：第 k 次访问时 R0=k，由 PC6–PC8 的 `R0<R1` 守卫回边维持 |
| 16 | Load | PC15 `Move 0,2`（R0=R2） | R2 由 PC10 `Set 2,0` 初始化，每轮 PC26 `Move 2,3` 更新为 R3 |
| 18 | Load | PC17 `Move 0,3`（R0=R3） | R3 由 PC12 `Add 3,2,15`，且 PC13–14 守卫 `R3<R1` |
| 22 | Store | PC21 `Move 0,2`（R0=R2） | 与 PC16 同一 R2，仅交换分支可达（PC19–20） |
| 24 | Store | PC23 `Move 0,3`（R0=R3） | 与 PC18 同一 R3，仅交换分支可达 |
| 36 | Load | PC35 `Set 0,0` 或 PC38 `Add 0,0,15` 的回边值 | 输出循环：第 k 次访问时 R0=k，由 PC39–PC41 的 `R0<R8` 守卫回边维持 |

**关键事实**：6 条内存指令中，没有一条把 `arg0`（被写/读的数据寄存器）当地址；地址始终取自 R0（见 §4 电路证据）。

**关键事实**：R1 不是原始终点。`BubbleSortProgramGenerator.cs` L61（PC32）在有交换的外层轮次执行 `R1 = R1 − 1`；原始 n 保存在 R8（PC9，L29）。因此排序循环的地址上界是**当前 R1**，输出循环的地址上界是**R8=n**。

## 3. 循环结构、入口/出口/回边

| 循环 | 头部 | 出口守卫 | 回边 | 计数器 | 上界 |
| --- | --- | --- | --- | --- | --- |
| 输入初始化（B1） | PC3 | PC6 `LessThan 2,0,1` + PC7 `Not` + PC8 `JumpIfZero 2,3` | 8→3 | R0（PC2 置 0，PC5 +1） | R1=n |
| 排序外层 | PC10 | PC30 `LessThan 0,0,6` + PC31 `JumpIfZero 0,35` | 34→10 | R1（PC32 −1） | R6>0 才继续 |
| 排序内层（B2） | PC12 | PC13 `LessThan 4,3,1` + PC14 `JumpIfZero 4,29` | 28→12 | R3=R2+1（PC26 推进 R2） | 当前 R1 |
| 输出（B3） | PC36 | PC39 `LessThan 2,0,8` + PC40 `Not` + PC41 `JumpIfZero 2,36` | 41→36 | R0（PC35 置 0，PC38 +1） | R8=n |

## 4. VM 指令真实语义（源码证据）

### 4.1 Load/Store 地址确实取 R0

- `ZkVmCircuits/ZkVmOpType.cs` L43–L52：`Store` 文档“memory address is stored in Reg0 (not to be confused with Reg{arg0})”；`Load` 同理；并注明 `NegOne` 地址保留。
- `ZkVmCircuits/ZkVmExecutorCircuitBoardGenerator.cs` L224–L227：注释掉的私有输入 `in_mem_addr` 被替换为 `Wire inMemAddrWire = inRegisterWires[0];`——地址线**就是 R0**，不是独立输入。
- 同文件 L499–L506（Store）：`out_mem_val = isStore * reg{arg0}`；L508–L515（Load）：`virtualOutHotRegAtArg0Possibilities.Add(opType, inMemValWire)`——注意 L509 注释“Set reg0 from memory”与代码不符，实际写目标是 `arg0`，不是 R0。
- 同文件 L925–L961：`out_mem_addr = isStore ? reg0 : NegOne`（对非 Store 填保留值）；L986–L1007：内存 trace 地址对 Store 取 `outMemAddrWire`（=R0），对 Load 取 `inMemAddrWire`（=R0），非内存操作取 `NegOne`。
- 结论：两条 Load/Store 的地址与 trace 地址都由电路约束到**执行时的 R0**，不是可由证明者自由指定的辅助值。

### 4.2 JumpIfZero

- `ZkVmOpType.cs` L39–L42：若 `Reg{arg0}` 为零则 PC=arg1，否则 PC+1。
- `ZkVmExecutorCircuitBoardGenerator.cs` L466–L497：`FieldNormGadget` 得到 `is_reg_at_arg0_non_zero`，`BoolNotGadget` 得到 zero 标志，`SelectComposeGadget(2)` 在 arg1 与默认 PC+1 间选择。
- `FieldNormGadget.cs`（固定 commit）：`x * InverseOrZero(x)`，故 x=0→0，x≠0→1；`Field.cs` L58–L60 定义 `InverseOrZero = Pow(p−2)`。

### 4.3 LessThan

- `ZkVmOpType.cs` L93–L96：`Reg{arg0} = 1 if Reg{arg1} < Reg{arg2}`。
- `ZkVmExecutorCircuitBoardGenerator.cs` L660–L695：对 `reg{arg1}`、`reg{arg2}` 各做一次 `BitDecompositionGadget`，随后 `BitsLessThanGadget(ArithConfig.BitSize)`（L681–L682 断言两者位数均为 BitSize），结果写入 arg0。
- `ArithConfig.cs` L10：p = `0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`（BLS12-377 标量域）；L13：BitSize = 253。
- `BitDecompositionGadget.cs` L6–L22：输出恰好 253 位；`BitsLessThanGadget.cs` L25–L51：从 MSB 到 LSB 取首个不同位，用 `LowBitGadget` + `SelectComposeGadget` 得到比较位。
- `CompatCircuitConverter.cs`（`ToMpcCircuitAndR1csCircuit`）：`AddBitDecompositionProof` 用预编译 `BitDecompositionProof.Circuit` 把位分解公开输出约束为 0；R1CS 中 `BitDecomposition`/`Inversion` 操作本身不直接生成约束，而由插入的证明电路与 `publicZeroOutputWires` 约束承担。（该文件通过 raw 源获取，未逐门审计预编译电路内部。）

### 4.4 Add / Sub / Not

- `ZkVmExecutorCircuitBoardGenerator.cs` L534–L546：Add 用 `FieldAddGadget`；L548–L560：Sub 用 `FieldSubGadget`。
- `Field.cs` L35–L43：`+`、`−` 均为 mod p 运算（`(a.Value ± b.Value) % p`，减法先加 p）。
- `ZkVmOpType.cs` L89–L92：Not 把输入当布尔值使用，**“will not check for this”**——即 NOT 本身不强制输入为 0/1。本程序中 Not 的输入均为 LessThan 输出（PC7、PC40），其布尔性依赖比较 gadget 输出结构。

## 5. 输入 n 的实际读取方式与现有范围约束

- 读取：`ZkProgramExecutor.cs` L54 建立公开输入枚举器；L255–L262 仅在 `PublicInput` 指令处 `AddPublic("in_public_input", publicInputEnumerator.Current)`；PC1 的 `PublicInput 1` 把该值写入 R1。
- 取值域：`FieldFactory.cs` L31 `New(BigInteger)` → `Field` 构造器 `Field.cs` L14–L21 只检查 `0 ≤ value < p`，**没有** `n ≥ 1`、没有 `n ≤ Nmax`、没有 `n < p−1` 的额外约束。
- 测试侧：`CollaborativeZkVmTest/ZkProgramExamplesTest.cs` L70–L78 用 `array.Count`（示例为 4）作为公开输入，L29/L78 的 `GlobalStepsNoMoreThan = opcodes.Count * array.Count * array.Count` 只是执行步数预算，不是地址范围约束。
- 结论：**当前源码不存在 n 的范围约束**（既无 `n≤Nmax`，也无 `n≥1`）。任何地址域证明必须把 `1 ≤ n ≤ Nmax < p` 作为外部明确输入约束，不能声称它已由现有电路保证。

## 6. 边界语义的源码事实（不作正确性假设）

- PC4 的 Store 位于输入循环**循环体中、守卫之前**：进入循环先写 `mem[R0]`，PC6 才检查 `R0 < R1`。因此 `n = 0` 时程序仍会执行一次 `PrivateInput` 和一次 `Store mem[0]`，随后 PC6 比较 `1 < 0` 为假而退出。即 `n=0` 时存在地址 0，但 `[0, n−1] = ∅`——程序语义与“地址均在 [0,n−1]”的命题不相容。
- 同理 PC36 的 Load 位于输出循环体首，PC39 才检查 `R0 < R8`；`n=0` 时仍会 `Load mem[0]` 并公开输出一个值。
- PC32 的 `Sub 1,1,15` 是 mod p 减法；是否有下溢只能由“交换只发生在 `R3<R1` 且 `R3≥1`、且 R1 递减受 R6>0 守卫”的静态推导判定，源码本身**没有**对 R1 下溢的显式约束。

> 证据边界：本节是程序级 / 源码级审计。字段位分解、布尔性、无回绕等是否已在 R1CS 中完整约束，见 `field_soundness.md`；本阶段不声称端到端密码学证明。
