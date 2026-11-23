# ABA-01 阶段 C：有限域无回绕与整数解释健全性

**核心问题**：VM 的 Add/Sub 是 mod p 运算；LessThan 虽输出布尔，但比较的是**域元素的规范位表示**。必须证明整数解释在这些运算上成立，才能把 B1–B3 的不变量当作地址界。

---

## 1. 模数与位宽（源码事实）

- `CompatCircuit/CompatCircuitCore/GlobalConfig/ArithConfig.cs` L10：
  `p = 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`（BLS12-377 标量域）。
- 同文件 L13：`BitSize = bitlength(p−1) = 253`。
- `Arithmetic/Field.cs` L14–L21：`Field(value,p)` 仅允许 `0 ≤ value < p`；L35–L43：`+`、`−` 均为 mod p。

因此每个寄存器值在规范解释下总是 `[0,p−1]` 的整数；但 `p−1` 在整数意义上代表“−1”，`LessThan` 不会把它当负数。

## 2. LessThan 的真实语义

- `ZkVmExecutorCircuitBoardGenerator.cs` L660–L695：对两个操作数各做 253 位 `BitDecompositionGadget`，再执行 `BitsLessThanGadget(253)`。
- `BitsLessThanGadget.cs` L25–L51：MSB→LSB 找第一个不同位，输出该位上 `right` 的值（即 `left < right` 的规范整数比较）。
- `CompatCircuitConverter.cs`（`AddBitDecompositionProof` / `ToMpcCircuitAndR1csCircuit`）：位分解经预编译 `BitDecompositionProof.Circuit` 插入证明，其公开输出被约束为 0；R1CS 中 `BitDecomposition` 操作不直接生成约束，而由该证明电路的乘法/加法约束与零输出约束承担。
- 结论：LessThan 比较的是 `[0,p−1]` 上的**规范整数**，不是有符号整数，也不是任意精度整数。整数解释成立的前提是所有参与比较的值都足够小（本程序要求 `n ≤ Nmax ≪ p`），或至少按规范解释处理。本推导统一采用规范解释，并要求 `Nmax < p`。

## 3. 逐项无回绕 / 无下溢分析

| 项 | 指令 | 源码位置 | 需要的整数界 | 是否已有电路保证 | 结论 |
| --- | --- | --- | --- | --- | --- |
| n 输入范围 | `PublicInput 1` | 生成器 L19；执行器 L255–L262 | `1 ≤ n ≤ Nmax`，`Nmax < p` | **否**：`Field` 只校验 `0≤v<p`（Field.cs L14–L21） | 必须新增外部约束；无约束时无法证明 |
| R0+1（输入循环） | `Add 0,0,15` PC5 | 生成器 L23；电路 L534–L546 | 执行时 `R0 ≤ n−1`，故 `R0+1 ≤ n < p` | 部分：Add 的 mod p 语义由电路保证；上界由上一段不变量静态导出 | 在 `n<p` 下无回绕；`n≥1` 下 Store 地址不越界 |
| R0+1（输出循环） | `Add 0,0,15` PC38 | 生成器 L69 | `R0 ≤ n−1`，`R0+1 ≤ n < p` | 同上 | 无回绕 |
| R3=R2+1 | `Add 3,2,15` PC12 | 生成器 L35 | `R2 ≤ R1−2 ≤ n−2`，`R3 ≤ n−1 < p` | 同上（上界来自 PC13 守卫的静态推导） | 无回绕 |
| R1−1 | `Sub 1,1,15` PC32 | 生成器 L61；电路 L548–L560 | `R1 ≥ 2` 当 R6>0（交换必在 `R3<R1` 且 `R3≥1` 时发生） | 部分：Sub 的 mod p 语义由电路保证；`R1≥2` 为静态推导 | 无下溢；由 I2/I3 支撑 |
| R6+1 | `Add 6,6,15` PC25 | 生成器 L50 | `R6 < p`（最坏 `R6 ≤ n(n−1)/2`） | 否：无显式计数器上界约束 | 需保守假设 `Nmax² < p`；否则 mod p 回绕可使 `R6=0` 误判“无交换” |
| 比较结果布尔 | LessThan / Not / JumpIfZero | 电路 L660–L695、L644–L657、L466–L497 | 输出 ∈ {0,1} | 部分：LessThan 结构上由 BoolXor/LowBit/SelectCompose 组合产生 0/1；`Not` 文档明言**不检查**输入布尔（ZkVmOpType.cs L89–L92） | 本程序 Not 的输入均为 LessThan 输出，故可用；但未逐门审计预编译位分解电路内部 |
| Load/Store 地址 | `inRegisterWires[0]` | 电路 L224–L227、L925–L1007 | `R0 < p`（自动满足）与 `R0 < n`（静态推导） | **地址取自 R0 由电路保证**；`R0 < n` 未约束 | 程序级可证；执行电路未绑定 |

## 4. 四类条件的明确区分

### 4.1 已由现有 VDORAM / 上游电路保证

1. 所有寄存器值规范化为 `[0,p−1]`（`Field.cs` L14–L21）。
2. Load/Store 的地址线与内存 trace 地址取**执行时 R0**，不是自由辅助输入（`ZkVmExecutorCircuitBoardGenerator.cs` L224–L227、L925–L1007）。
3. Add/Sub 的 mod p 算术语义（`Field.cs` L35–L43；电路 L534–L560）。
4. LessThan 使用 253 位分解 + `BitsLessThanGadget`，JumpIfZero 使用 FieldNorm + BoolNot + SelectCompose（电路 L466–L497、L660–L695）。
5. 位分解经 `AddBitDecompositionProof` 插入零输出证明（Converter 的 `ToMpcCircuitAndR1csCircuit` 路径）；**未逐门审计预编译电路内部**。

### 4.2 需要新增约束（当前不存在）

1. `1 ≤ n ≤ Nmax`（公开输入范围）——当前无任何约束。
2. `Nmax < p`（以及保守的 `Nmax² < p`，保证 R6 计数不回绕）。
3. 若要做端到端密码学证明，还需把“地址 ∈ [0,n−1]”作为执行关系的显式约束或由上述约束在电路内推导——当前 R1CS 没有这一步。

### 4.3 仅由静态分析推导（非电路约束）

1. B1/B2/B3 的不变量及全部 6 个访存点的地址界。
2. `R1 ≥ 1`、PC32 无下溢；`R0+1 ≤ n`、`R3 ≤ n−1` 无回绕。
3. `R8 = n` 全程不变、`R15 = 1` 全程不变（全程序写点唯一性）。
4. 交换与不交换两条路径复用同一 R2/R3 地址。

### 4.4 目前无法证明 / 需警惕

1. `n = 0` 时程序仍访问地址 0：与 `[0,n−1]=∅` 矛盾，属程序语义问题（见 `invariants.md` B4）。
2. 预编译 `BitDecompositionProof.Circuit` 内部是否完整强制“各位为 0/1 且按二进制重构输入”——本次仅确认其被插入并零输出约束，未逐门验证。
3. `Not` 的输入布尔性依赖约定而非约束；本程序恰好只接 LessThan 输出，但这一“恰好”是静态分析结论。
4. R6 的 mod p 回绕（`n` 极大时）无电路约束，需要 `Nmax² < p` 外部假设。
5. 所有静态推导尚未接入 R1CS 执行关系；证书不绑定真实执行（见 `decision.md`）。

## 5. 最小补充约束建议（未实现，不得表述为已存在）

- 在公开输入处增加范围证明：`n ∈ [1, Nmax]` 的 253 位分解与比较约束（可用现有 LessThan gadget 实现，但需新增约束连线）。
- 增加 `Nmax < p`、`Nmax² < p` 的公开常量校验。
- 在每条 Load/Store 处增加 `addr = R0` 且 `0 ≤ R0 < n`（或 `< Nmax`）的执行关系约束；若希望绑定真实执行，需把该约束加入 `ZkVmExecutorCircuitBoardGenerator.cs` 的 per-step 电路——**本轮不做**。

> 结论边界：本节说明“在明确输入约束与规范整数解释下，程序级整数推导是自洽的”；**不**说明当前电路已强制这些前提，更不说明已完成端到端 R1CS 绑定。
