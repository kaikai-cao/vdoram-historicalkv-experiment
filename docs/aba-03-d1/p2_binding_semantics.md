# ABA-03-D1 / Phase A+B：P2 按操作类型的地址绑定语义与目标安全关系

> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`；起点 commit `f393347477d96f7d804d80704272309db7ccf52a`（实验仓）。
>
> 性质：只读源码 + 设计评估。不实现电路、不改原始 VDORAM、不解除 ABA-03 `HOLD`、不运行测试。
>
> 标签：`VERIFIED_SOURCE` = 固定 commit 源码事实；`CONSTRUCTED` = 实验侧构造产物；`INFERRED` = 由源码事实推导；`UNKNOWN` = 无证据；`BLOCKED` = 本轮手段无法核验。
>
> 行号口径：`D:/tmp/aba01/src/*.cs` 为无头原始 blob，行号即原始行号。`MemoryTraceProveCircuitBoardGenerator.cs` 仅存于实验仓 `docs/source-snapshot/`，原始行号 = 快照行号 − 4。

---

## 0. 本轮最重要的语义修正（相对 ABA-03 原文）

ABA-03 的 `constraint_spec.md` B3 第 4 项、`trace_binding_analysis.md` C1 曾写 `fetch_addr_i = reg0_i = trace_addr_i`。本轮**收紧为带操作类型条件的等式**，不再对每一步无条件施加：

- **真实 Load/Store**（`is_mem_op_i = 1`）：`fetch_addr_i = reg0_i = trace_addr_i` 成立，可施加相等约束。
- **非内存操作的 dummy Fetch**（`is_mem_op_i = 0`，`step ≥ 1`）：`fetch_addr_i = reg0_i` 成立，但 `trace_addr_i = p−1`；**不得**要求 `fetch_addr_i = trace_addr_i`，二者在当前语义下本来就不相等。
- **step 0**：不构造 Fetch 电路，不存在 `in_mem_addr` 输入；不能虚构 Fetch 地址绑定。

这一修正由 ABA-03-C1 已冻结的 step 0 语义勘误与本轮重新核对的 `ZkVmExecutorCircuitBoardGenerator.cs:941-1007`、`MemoryTraceFetchCircuitBoardGenerator.cs:41-52`、`ZkProgramExecutor.cs:201-226` 共同支撑。

---

## 1. Phase A：按步骤分类的执行语义（逐项源码核对）

任务给出的四行表格是**待核对框架**。下表逐项给出源码依据与标签；其中「是否真实内存事件」与「VM trace 地址」两项须区分电路派生值与宿主记录值。

| 步骤类别 | MemoryFetch | Fetch 输入 | VM trace 地址 `trace_addr` | 是否真实内存事件 |
| --- | --- | --- | --- | --- |
| step 0 | 无（`ZkProgramExecutor.cs:201-203`） | 不适用（`:204-232` 的 else 分支才构造 Fetch 电路） | `:389-402` 仍无条件 append 一行；列值取 `out_trace_*`（step 0 电路内 pc/reg 归零 → `is_mem_op=0`、地址否则分支 `p−1`、值 0） | 否 |
| 后续 Load | 有（`:205-228`） | `thisRegisters[0]`（`:226`） | `inMemAddrWire = inRegisterWires[0]`（`ZkVmExecutor...cs:224-227,989-997`，Load 分支取 `inMemAddrWire`） | 是（`is_mem_op=1`，`:968-976`） |
| 后续 Store | 有（`:205-228`） | `thisRegisters[0]`（`:226`） | `outMemAddrWire`（`:953-961` 取 `inRegisterWires[0]`）；`out_trace_mem_addr` 的 Store 分支取 `outMemAddrWire`（`:989-997`） | 是（`is_mem_op=1`） |
| 后续非内存操作 | 有（dummy，`:205-228` 不区分 op） | `thisRegisters[0]`（`:226`，与 Load/Store 完全相同） | `out_trace_mem_addr` 的 otherwise 分支 `constNumberNegOneWire = p−1`（`:989-997`、`:941-943`） | 否（`is_mem_op=0`） |

### 逐项证据与标签

1. **step 0 不执行 MemoryFetch** — `ZkProgramExecutor.cs:201-203`：`if (globalStepCounter == 0) { memVal = zeroShare; } else { ... }`，Fetch 电路 `MemoryTraceFetchCircuitBoardGenerator(globalStepCounter)` 只在 else 分支 L205 构造。`VERIFIED_SOURCE`。
2. **step 0 仍追加 MemoryTrace 行** — `ZkProgramExecutor.cs:389-402` 位于步执行之后、无条件执行；逐列取 `GetOutput($"out_trace_{colName}")`（`:397`），仅 `global_step_counter` 用公开值 `MpcShareFromPublicValue` 注入（`:393-395`）；`AddMemoryTrace` 在 `:85-97` 直接 `memoryTrace.Add`。`VERIFIED_SOURCE`（append 事实）。该行 `is_mem_op=0`、`trace_addr=p−1`、`trace_mem_val=0` 由 step 0 电路内 pc/reg 归零（`ZkVmExecutor...cs:101-123,133-145,147-217`）与 trace 字段 otherwise 分支（`:989-1007`）推导 → `INFERRED`（与 ABA-03-C1 冻结结论一致，本轮未重新执行验证）。
3. **后续每步（含 dummy）都执行 Fetch，输入同为 reg0** — `ZkProgramExecutor.cs:205-228` 的 else 分支**不含任何 op 类型判断**，`:226` 无条件 `AddPrivate("in_mem_addr", thisRegisters[0])`。`VERIFIED_SOURCE`。
4. **Fetch 电路把 `in_mem_addr` 当查找键，不强制 trace_addr** — `MemoryTraceFetchCircuitBoardGenerator.cs:41-43` 声明私有输入 `in_mem_addr`；`:48-56` 对每行 `FieldEqualsGadget(in_trace_mem_addr_wires[row], in_mem_addr)` 生成行选择位；`:64` `LowBitGadget` 选出至多一行；`:75-85` 仅对 `ColumnNamesToBeFetched = ["mem_val"]`（`:10`）做 `SelectComposeGadget` 输出 `out_trace_mem_val`（私有输出，`:83`）。**Fetch 电路没有输出 trace_addr，也没有任何 `trace_addr = in_mem_addr` 的约束**——它只在既有 trace 中按地址查值。`VERIFIED_SOURCE`。
5. **VM 电路地址源与 trace 地址派生** — `ZkVmExecutorCircuitBoardGenerator.cs:224-227` 原 `in_mem_addr` 被注释，实际 `inMemAddrWire = inRegisterWires[0]`；`:941-943` 默认地址 `constNumberNegOneWire`；`:953-961` `out_mem_addr = Store ? reg0 : NegOne`；`:989-997` `out_trace_mem_addr = Store ? outMemAddrWire : (Load ? inMemAddrWire : NegOne)`；`:999-1007` `out_trace_mem_val` 同理，otherwise 为常量 0。`VERIFIED_SOURCE`。
6. **`is_mem_op`/`is_mem_write` 是电路内派生** — `ZkVmExecutor...cs:968-976` `BoolOrGadget(Load, Store)` → `out_trace_is_mem_op`（私有输出）；`:978-981` `out_trace_is_mem_write = Store`。它们由 opcode 表行选择位（`:273-347`）驱动，不是宿主任意填入的标志。`VERIFIED_SOURCE`（派生路径）。

### 关键推论：为什么不能对 dummy 步要求三者相等

Fetch 电路用 `reg0` 作为**查找键**去匹配 trace 中 `mem_addr == reg0` 的行；而 VM 电路为非内存步写出的 trace 行 `mem_addr = p−1`。因此 dummy 步的 `fetch_addr = reg0` 与同一步 `trace_addr = p−1` 在一般情况下是两个不同的元素。Fetch 输出的 `mem_val` 只在 Load 分支被 VM 电路消费（`ZkProgramExecutor.cs:296-298` 把 `memVal` 送入 `in_mem_val`；`ZkVmExecutor...cs:999-1007` 的 Load 分支取 `inMemValWire`），非内存步虽计算了该值但不用它更新寄存器或内存。`INFERRED`（由 3/4/5/6 推得；本轮未执行）。

**结论**：`fetch_addr = reg0 = trace_addr` 只在 `is_mem_op = 1` 的步成立；把它写成全局每步约束会与 dummy 语义冲突，并可能在未来原型中拒绝合法执行或制造伪越界。

---

## 2. 四个地址相关量的角色（避免术语混淆）

| 量 | 电路 | 角色 | 可见性 |
| --- | --- | --- | --- |
| `fetch_addr`（Fetch 电路 `in_mem_addr`） | MemoryFetch | 在既有 trace 中查找 `mem_val` 的**键** | 私有输入（`MemoryTraceFetch...cs:42`） |
| `reg0`（`thisRegisters[0]` / `inRegisterWires[0]`） | VM Executor | 地址寄存器，Fetch 键与真实访存地址的共同来源 | 私有输入（`ZkVmExecutor...cs:177,227`） |
| `out_mem_addr` | VM Executor | Store 时 = reg0，否则 = `p−1` 的私有输出 | 私有输出（`:960`） |
| `trace_addr`（`out_trace_mem_addr`） | VM Executor | trace 行的地址列：Load/Store = reg0，否则 = `p−1` | 私有输出（`:996`） |

注意：`out_mem_addr` 与 `out_trace_mem_addr` 在 Store 时都取 reg0，在 Load 时 `out_mem_addr` 取 `p−1`（因为只有 Store 写内存）而 `out_trace_mem_addr` 取 reg0（因为 Load 读该地址）。二者不是同一个量，不应混用。以上均为 `VERIFIED_SOURCE`。

---

## 3. Phase B：必须闭合的目标安全关系（不依赖具体方案）

### B1 真实访问地址一致性

对每个 `is_mem_op_i = 1` 的步 `i`：

```
is_mem_op_i = 1  ⇒  fetch_addr_i = reg0_i = trace_addr_i
                     且 0 ≤ trace_addr_i < n（完整域元素相等 + 整数范围）
```

- 相等必须是 **`F_p` 中完整元素相等**，不得仅比较低位截断值（ABA-03-C1 已勘误：`p` 为奇数，`p−1` 偶，低 L 位不可能全 1；风险是截断值 `(p−1) mod 2^L` 可能很小并通过小范围比较，须用逐位 Boolean + 完整字段等式 + 位比较防御）。
- 现状：`fetch_addr` 与 `trace_addr` 构造同源（都来自 reg0），但分属不同电路、均为私有值，无电路内等式 → 该关系**尚未闭合**。`INFERRED` + `VERIFIED_SOURCE`（缺失）。

### B2 Dummy Fetch 语义

对每个 `is_mem_op_i = 0` 且 `step ≥ 1` 的步：

```
is_mem_op_i = 0  ⇒  trace_addr_i = p−1  且  trace_mem_val_i = 0
                     fetch_addr_i = reg0_i（仍成立，但不参与真实访问）
                     禁止断言 fetch_addr_i = trace_addr_i
```

执行次数/来源/值处理核对（任务要求）：

- **次数**：每个 `step ≥ 1` 都执行一次 Fetch（`ZkProgramExecutor.cs:204-232`），dummy Fetch 数 = 非内存步数。若总执行步数为 `T`（含 step 0）、真实访问数为 `M`，则 dummy Fetch 数 = `T − 1 − M`（step 0 无 Fetch）。`INFERRED`。
- **来源**：`in_mem_addr = thisRegisters[0]`（`:226`），与真实访问相同。`VERIFIED_SOURCE`。
- **值处理**：`out_trace_mem_val` 被取回为 `memVal`（`:230`），仅在 Load 分支送入 VM 电路（`:296-298`）；非内存步不消费该值。`VERIFIED_SOURCE`。
- 现状：Prove 电路明确忽略 `is_mem_op`（原始 L164-165），trace 中同时存在真实行与 `p−1` 行；没有电路约束把「dummy 行地址必为 `p−1`」交给 verifier 检查。`VERIFIED_SOURCE` + `INFERRED`。

### B3 step 0 语义

- step 0 不构造 Fetch（`ZkProgramExecutor.cs:201-203`）→ 任何要求 step 0 提供 `fetch_addr` 或真实访问事件的接口都与源码冲突。
- step 0 仍 append 一行 trace（`:389-402`），该行 `is_mem_op = 0`（ABA-03-C1 冻结结论）→ 不得因 trace 行数增加而被计为真实访问。
- 目标关系：验证方必须能从证明中识别并排除 step 0，使其既不被伪造为一次真实 Fetch，也不被计入事件数。`INFERRED`。

### B4 完整性与顺序（单步相等 ≠ 执行轨迹完整）

即使 B1–B3 的逐步关系全部成立，也**不能自动推出**整条执行轨迹完整。verifier 还需能确认：

1. 每个应执行的 Fetch 都有对应证明（无遗漏）；
2. 不存在重复或重排的真实内存事件（顺序与唯一性）；
3. 每条绑定对应正确的 `step_i`、`pc_i` 与 `opcode_i`；
4. 分支、循环、提前终止与步数变化不造成绑定错位（事件 → 步的映射单调且无空洞）；
5. dummy Fetch 不会被误分类为真实访问，反之亦然。

现状评估：上游 Prove 电路不接收 pc/opcode（ABA-03 `source_trace_audit.md` A2），trace `step` 列由宿主以公开值注入（`:393-395`），跨电路一致性靠宿主哈希 `throw`（`:170-181,302-332,551-583`），这些都不构成 verifier 可检查的完整性约束。`VERIFIED_SOURCE`（缺失）+ `INFERRED`。

**结论**：B4 是独立于 B1 的 harder problem。任何只做「单步地址相等」的方案都不解决 B4；本轮把二者分开记录，避免把单步相等误当成轨迹完整性已闭合。

---

## 4. 边界声明

- 本轮只核对固定 commit 与既有冻结文档，未重新下载上游、未修改任何源码或既有文档、未运行测试。
- `is_mem_op` 为电路内派生（有约束）但私有输出（verifier 不可见明文）；宿主 trace 列值来自电路输出而非宿主任意标志——这与「宿主传入的可信标志」不同，后续文档据此区分。
- 本文所有「尚未闭合」「缺失」均限定于固定 commit 与本轮检索范围，不等于 VDORAM 论文层面不存在相应设计。
- 不声称任何绑定关系已被电路实现、已被验证或已具备安全性质。
