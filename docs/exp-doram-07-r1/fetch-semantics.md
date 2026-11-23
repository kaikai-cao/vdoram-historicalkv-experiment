# EXP-DORAM-07-R1 — 原始 Fetch 全历史扫描语义核查

> 上游固定 commit：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 本地证据：大部分源码来自 EXP-DORAM-07 已固定的 `docs/source-snapshot/`（每个文件头部含 `SOURCE/PATH/BLOB SHA`）；
> 三个 gadget 与 `ArithConfig.cs`/`ZkProgramInstance.cs` 不在原快照中，本轮按同一固定 commit 用 raw.githubusercontent.com 现场抓取，
> 逐字引用于本文附录 A/B，未写入旧快照目录（本轮禁止修改 EXP-DORAM-07 原有文件）。
> 本文只做语义核查；`history_rows_scanned` 是抽象参考模型计数，不等于 MPC 乘法门数或通信轮数（见 cost-model.md）。

## 0. 结论摘要（先给结论）

1. **A（电路结构层）：成立。** 原始 `MemoryTraceFetchCircuitBoardGenerator` 对 `traceCount = current_step` 条历史行
   **逐行**生成一次地址相等判断；不做数据相关的提前退出。step s>0 时 Fetch 电路的输入历史行数恰为 s（ZkProgramExecutor L221 断言保证）。
2. **B（底层执行优化层）：不能从 A 推出「每行等价数量的昂贵 MPC 乘法」。**
   相等判断由 `FieldEqualsGadget`（Sub + Norm + Not）构成，最新值选择由 `LowBitWithCarryGadget`（布尔 Not/And）+
   `SelectComposeGadget`（每行一次 `FieldMulGadget`，再累加）构成。哪些门在底层被常数折叠/复用属于
   `.Optimize()` 与 `CircuitBoardConverter` 的实现细节，本轮未拿到该部分源码，**判定为 UNKNOWN**。
   因此 E0-FullScan 的 `history_rows_scanned = s` 只是「电路纳入的行数」的忠实参考，不是乘法门数声明。
3. dummy Fetch 与 step 0：step 0 **不构造/不执行 Fetch 电路**（memVal=zeroShare，L205-207）；
   step>0 时 **每个 op（LOAD/STORE/NOOP）都执行一次 Fetch**（L208-236），Fetch 地址恒为 `reg0`（L229-230），
   Fetch 结果只有 LOAD 真正消费（L302 送入执行电路，NOOP/STORE 仍照常算但不使用）。这就是 R1 要区分的「dummy Fetch」。
4. Fetch 地址 ≠ trace 地址：`in_mem_addr = reg0`（ Fetch 用）；写入 trace 行的 `mem_addr` 由
   `SelectComposeOtherwiseGadget(2)` 在 STORE/LOAD 时取 out_mem_addr/inMemAddr，其余取 `NegOne`（L990-1000）。
   非内存 op 的 trace 行地址为 NegOne，但 **Fetch 仍用 reg0 普通地址扫描全历史**。

---

## 1. 历史行迭代范围与逐行相等判断

证据1 — `MemoryTraceFetchCircuitBoardGenerator.cs`（本地快照 L11-14, L46-63）：

```
L11  public class MemoryTraceFetchCircuitBoardGenerator(int traceCount) : ICircuitBoardGenerator {
L12      TraceCount = traceCount > 0 ? traceCount : throw ...;
L13      ColumnNames = ["mem_addr","global_step_counter","is_mem_op","is_mem_write","mem_val"];
L14      ColumnNamesToBeFetched = ["mem_val"];
...
L46      Wire inMemAddrWire = Wire.NewPrivateInputWire("in_mem_addr");
...
L52      for (int row = traceCount - 1; row >= 0; row--) {
L56          GadgetInstance ins = new FieldEqualsGadget().ApplyGadget(
L56              [inTraceMemAddrWires[row], inMemAddrWire], $"row_selection_{row}_raw()");
L59          rowSelectionRawWire.Name = $"row_selection_{row}_raw";
L62          rowSelectionRawWires.Add(rowSelectionRawWire);
L63      }
```

- 循环从 `traceCount-1` 到 `0`，**无条件**遍历每一行；每行调用一次 `FieldEqualsGadget` 比较该行 `mem_addr` 与 `in_mem_addr`。
- `rowSelectionRawWires` 按逆序（最新行在前）累积；L65-71 再交给 `LowBitGadget`。
- 没有任何 `if (is_mem_op)` 门控、没有 `break`/early-exit，**A 成立**。

证据2 — 历史长度在调用点的精确值，`ZkProgramExecutor.cs`（本地快照 L203-236）：

```
L203  Trace.Assert(globalStepCounter == privOutMemValFields.Count);
L205  if (globalStepCounter == 0) { memVal = zeroShare; }
L208  else {
L209      CircuitBoard ... = new MemoryTraceFetchCircuitBoardGenerator(globalStepCounter).GetCircuitBoard().Optimize();
L221      Trace.Assert(globalStepCounter == memoryTrace.Count);
L222-227  for col ... for row in [0, memoryTrace.Count): AddPrivate($"in_trace_{row}_{colName}", ...)
L230      AddPrivate("in_mem_addr", thisRegisters[0]);
L232      await Compute();
L234      memVal = GetOutput("out_trace_mem_val");
```

- 断言 L203 + L221 共同保证：step s 时 `memoryTrace.Count == s`，Fetch 电路 `traceCount == s`。
  即 **每步 Fetch 可见且必须扫描的历史 = 该步之前全部真实 trace 行**（含 NOOP 行；不含尚未生成的当步行；
  不含仅在 halt 后 sort 阶段填充的 NegOne padding 行——L455-467 发生在 Fetch 全部结束之后）。
- `.Optimize()` 在 L209 与 L61/477/534 一致出现，是电路图优化，不是「跳过历史行」的语义优化；
  是否折叠相等门为 UNKNOWN（见 §3）。

## 2. 最新匹配值的选择方式（LowBitGadget + SelectComposeGadget）

证据3 — `MemoryTraceFetchCircuitBoardGenerator.cs` L65-89：

```
L68  new LowBitGadget(rowSelectionRawWires.Count).ApplyGadget(rowSelectionRawWires, "lowbit()")
L74  rowSelectionLowBitWires.Reverse();        // 恢复升序，与 in_trace 行序一致
L83  new SelectComposeGadget(traceCount).ApplyGadget(
L83      [.. rowSelectionLowBitWires, .. inTraceValueWires[col]], $"out_trace_mem_val()")
```

- 输入 `rowSelectionRawWires` 为逆序（最新行 index 0）。`LowBitWithCarryGadget` 的定义（附录 A）为：
  `output[0]=input[0]`，`output[i]=input[i] ∧ ¬input[0] ∧ ... ∧ ¬input[i-1]`，
  即在**逆序序列中第一个为 1 的位**置 1，其余 0 → 对应**时间上最新的匹配行**是 one-hot。
- `SelectComposeGadget(traceCount)`（附录 A）对每行计算 `selected_i = lowbit_i × value_i` 并求和；
  由于 lowbit 是 one-hot，输出 = 最新匹配行的 `mem_val`；无匹配时全 0 → 输出 0（原始默认值）。
- 这与 E0-FullScan 的「正向扫描覆盖候选值 / 逆序扫描但不提前退出」在**返回值语义上等价**，
  但在**扫描范围上不等价于 early-exit**：one-hot 的选择依赖所有 raw 位，所有行都参与了计算。

## 3. 约束生成 vs 昂贵 MPC 乘法（区分 A 与 B）

按一手 gadget 源码逐层展开（附录 A/B 逐字引用）：

| 层次 | gadget | 对每行/每步做的事 | 本轮判定 |
|---|---|---|---|
| 相等判断 | `FieldEqualsGadget` | `FieldSub` → `FieldNorm` → `BoolNot` | 每行都生成该约束链（VERIFIED）；Norm 的具体门数与是否含昂贵乘法 = UNKNOWN（未取 FieldNormGadget 源码） |
| 最新位 | `LowBitGadget` → `LowBitWithCarryGadget` | 每行 1 个 `BoolNot`，i≥1 每行 2 个 `BoolAnd` | 布尔门逐行生成（VERIFIED）；布尔 AND 在 MPC 下是否每次都是乘法轮 = UNKNOWN（依赖 secret-sharing 后端） |
| 值选择 | `SelectComposeGadget` | 每行 1 个 `FieldMulGadget`，再逐行累加 | **每行一次域乘法被显式生成**（VERIFIED，源码 L83 + gadget 内循环）；累加为 FieldAdd |
| 图优化 | `.Optimize()` / `CircuitBoardConverter` | L209 调用，源码不在快照 | 是否把常量行/重复乘法折叠 = UNKNOWN |

**因此**：`history_rows_scanned = s` 与 `history_equality_checks = s` 忠实刻画「原始电路把 s 行都纳入了约束与相等比较」，
支持「E0-FullScan 是正确的算法语义基线」；但**不能**据此声称「原始 Fetch 每步需要 s 次昂贵 MPC 乘法 / s 轮通信」，
也不能把 E1 的 `shadow_slots_scanned = n` 换算成 n 次乘法门。这是本轮与未来 MPC 成本模型之间的明确边界。

## 4. dummy Fetch、step 0、Fetch/trace 地址

- **step 0**：L205-207 `memVal = zeroShare`，**没有** `new MemoryTraceFetchCircuitBoardGenerator`，不 AddPrivate，不 Compute。
  R1 参考模型必须让 step 0 零扫描（与 EXP-DORAM-07 `models.py` L185-186 一致，R1 沿用）。
- **dummy Fetch**（结果不被 LOAD 消费的 Fetch）：L208-236 不区分 op；STORE/NOOP 步同样构造并运行 Fetch 电路、
  扫描全部 s 行；L302 把 memVal 作为 `in_mem_val` 送入执行电路，但只有 LOAD 的输出会改变寄存器。
  → R1 中「NOOP/STORE 也要计一次 fetch、也要扫全历史」，不得漏计（tests §dummy Fetch）。
- **Fetch 地址**：L229-230 注释 `memory address is stored in reg0`，`in_mem_addr = thisRegisters[0]`（秘密共享值）。
- **trace 地址**：`ZkVmExecutorCircuitBoardGenerator.cs` L945-1000：
  - `defaultMemAddrWire = NegOne`（L946）；
  - `out_mem_addr = STORE ? reg0 : NegOne`（L959-963，SelectComposeGadget(2)）；
  - `out_trace_mem_addr = SelectComposeOtherwiseGadget(2)([isStore,isLoad,out_mem_addr,in_mem_addr,NegOne])`（L995-1000），
    即 STORE/LOAD 取地址、其余取 NegOne（L990-992 注释）。
  - trace 行在 L393-405 由执行电路 `out_trace_*` 产出并 `AddMemoryTrace`，**在 Fetch 之后追加**，构成下一步可见历史。
- 结论：**fetch_address 与 trace_address 是两个不同来源**；NOOP 的 trace_address=NegOne 但 fetch_address=reg0 普通地址，
  二者不可混用（与本仓 EXP-DORAM-01-R1 的拆分一致）。

## 5. 证据分级

| 命题 | 等级 | 依据 |
|---|---|---|
| step s>0 的 Fetch 电路 traceCount = s 且逐行生成相等判断 | VERIFIED | 快照 Fetch L52-63；Executor L203/L209/L221 |
| 最新匹配行由 LowBit one-hot 选出、无匹配返回 0 | VERIFIED | Fetch L65-89；附录 A gadget 源码 |
| step 0 不执行 Fetch；dummy Fetch 仍全扫描 | VERIFIED | Executor L205-236, L302 |
| Fetch 地址=reg0；trace 地址非内存 op 为 NegOne | VERIFIED | Executor L229-230；Board L945-1000 |
| SelectCompose 每行显式生成一次 FieldMul | VERIFIED | 附录 A `SelectComposeGadget.ApplyGadget` 循环 |
| 相等判断的 FieldNorm 具体乘法门数 / 布尔 AND 的 MPC 轮数 | UNKNOWN | gadget 依赖未纳入本轮一手证据 |
| `.Optimize()` 是否折叠常量/重复门 | UNKNOWN | 该实现源码未纳入本轮一手证据 |
| 地址域存在有限上界 [0,n-1] | 见 address-domain-audit.md | 源码仅为 253-bit 域元素 |

## 附录 A — gadget 逐字引用（raw @ pinned commit）

### LowBitGadget.cs
```csharp
public class LowBitGadget(int bitCount) : IGadget {
    public int BitCount { get; } = bitCount;
    public List GetInputWireNames() => Enumerable.Range(0, this.BitCount).Select(i => $"input_{i}").ToList();
    public List GetOutputWireNames() => Enumerable.Range(0, this.BitCount).Select(i => $"output_{i}").ToList();
    public GadgetInstance ApplyGadget(IReadOnlyList inputWires, string namePrefix) {
        if (inputWires.Count != this.BitCount) throw new ArgumentException("Unexpected element count", nameof(inputWires));
        GadgetIncompleteCircuitBoard circuitBoard = new();
        List outputWires = [];
        { GadgetInstance ins = new LowBitWithCarryGadget(inputWires.Count).ApplyGadget(inputWires, $"{namePrefix}_[low_bit_with_carry]");
          ins.Save(circuitBoard); outputWires.AddRange(ins.OutputWires.SkipLast(1)); }
        Trace.Assert(outputWires.Count == this.BitCount);
        return GadgetIncompleteCircuitBoardHelper.NewGadgetInstanceFromGadgetIncompleteCircuitBoard(outputWires, circuitBoard);
    }
}
```

### LowBitWithCarryGadget.cs（核心循环）
```csharp
outputWires.Add(inputWires[0]);
Wire previousAreFalse = notInputWires[0];
for (int i = 1; i < inputWires.Count; i++) {
    // output[i] = previousAreFalse AND input[i]
    ... new BoolAndGadget().ApplyGadget([previousAreFalse, inputWires[i]], ...);
    // previousAreFalse = previousAreFalse AND NOT input[i]
    ... new BoolAndGadget().ApplyGadget([previousAreFalse, notInputWires[i]], ...);
}
outputWires.Add(previousAreFalse); // carry
```
（前面另有逐位 `BoolNotGadget` 生成 `notInputWires`。）

### SelectComposeGadget.cs（核心循环）
```csharp
Wire? finalSelectionValue = null;
for (int i = 0; i < this.SelectionCount; i++) {
    Wire selectionWire = inputWires[i];
    Wire valueWire = inputWires[i + this.SelectionCount];
    GadgetInstance ins1 = new FieldMulGadget().ApplyGadget([selectionWire, valueWire], ...);
    ins1.Save(circuitBoard);
    if (finalSelectionValue is null) finalSelectionValue = ins1.OutputWires[0];
    else { ... new FieldAddGadget().ApplyGadget([finalSelectionValue, ins1.OutputWires[0]], ...); ... }
}
```

### FieldEqualsGadget.cs
```csharp
GadgetInstance ins1 = new FieldSubGadget().ApplyGadget(inputWires, ...);   // difference
GadgetInstance ins2 = new FieldNormGadget().ApplyGadget([difference], ...); // normBit
GadgetInstance ins3 = new BoolNotGadget().ApplyGadget([normBit], ...);      // resultBit
```

## 附录 B — 域与程序证据（供 address-domain-audit.md 引用）

- `ArithConfig.cs @ pinned`：`FieldSize = 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`，
  注释 `// BLS12-377`，`BitSize = 253`。地址为域元素，**域本身无 [0,n-1] 上界**。
- `BubbleSortProgramGenerator.cs`（本地快照 L22-30, L70-83）：地址来自程序内循环寄存器 R0（从 0 递增，受
  `LessThan(R0,R1)` 与 `array length` 公开输入 R1 约束）；`globalStepsNoMoreThan = opcodes.Count * n_input^2`。
  这说明**示例程序层面**地址在 `[0, n_input-1]`，但这是程序构造（CONSTRUCTED/INFERRED），不是电路层的范围约束。
- `ZkProgramInstance.cs @ pinned`：`GlobalStepsNoMoreThan`、`PublicInputs`、`PrivateInputShares` 均为宿主字段，
  未见对地址域的显式 `Range` 校验。
