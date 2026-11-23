# semantic-audit.md — EXP-DORAM-07 原始 HistoricalKV 语义核查

> 上游：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`（NDSS'26 VDORAM artifact）
> 实验起点：`kaikai-cao/vdoram-historicalkv-experiment` @ `c545ddcb9a14853811e2333b132a75f1592f8566`
> 核查日期：2026-11-23 · 标注：**SRC**（上游源码直接确认）· **MODEL**（本轮参考模型假设）· **UNKNOWN**（源码无法确认）
> 取源方式：`api.github.com/.../git/blobs` 逐文件按固定 commit 下载，逐行核对；本机无 .NET SDK，不运行上游 C#。

---

## 0. 先澄清一个命名问题

上游 artifact 中**没有**名为 `HistoricalKV` 的类。任务包中的 “HistoricalKV 的 Add / Query / Export” 是对论文/任务语义的概括，其对应的真实源码实体是：

| 任务概念 | 上游源码实体 | 状态 |
| --- | --- | --- |
| 历史日志（append-only） | `memoryTrace`：`List<Dictionary<string, MpcValue>>`，每行 5 列（`mem_addr, global_step_counter, is_mem_op, is_mem_write, mem_val`） | SRC |
| Query / 读最新值 | `MemoryTraceFetchCircuitBoardGenerator`：逆序逐行 `FieldEqualsGadget` + `LowBitGadget` + `SelectComposeGadget` | SRC |
| Add / 写一条历史 | `ZkProgramExecutor` 每步 `AddMemoryTrace(incomingTraceRow)` | SRC |
| Export / 历史证明接口 | `MemoryTraceProveCircuitBoardGenerator` + `AddHashMemoryTrace` 计数比对 | SRC |

因此本轮“保持原始语义”的判据是：**保持这 5 列 trace 的逐行内容、顺序、承诺字段与 Fetch 选择语义不变**。影子表只作为 Query/Update 的加速结构，不改变 trace 本身。

---

## 1. 逐项核查（任务 §3）

### 1.1 五列定义与被 Fetch 的列 — SRC

`MemoryTraceFetchCircuitBoardGenerator.cs` L13-14：

```csharp
ColumnNames = ["mem_addr", "global_step_counter", "is_mem_op", "is_mem_write", "mem_val"];
ColumnNamesToBeFetched = ["mem_val"];
```

- 历史行固定 5 列；Fetch 只取 `mem_val` 一列。
- 每行以私有输入线 `in_trace_{row}_{col}` 进入电路（L23-34），全历史行都是 witness。
- 查询地址是独立私有输入线 `in_mem_addr`（L45-47）。

### 1.2 Query 是否读取最新历史值 — SRC（是）

`MemoryTraceFetchCircuitBoardGenerator.cs` L49-89：

```csharp
for (int row = traceCount - 1; row >= 0; row--)          // L52 逆序
    FieldEqualsGadget(mem_addr[row], in_mem_addr)         // L56
    -> row_selection_{row}_raw                            // L59
LowBitGadget(rowSelectionRawWires)                        // L68 取最低置位
rowSelectionLowBitWires.Reverse();                        // L74 恢复升序
SelectComposeGadget(... mem_val ...) -> out_trace_mem_val // L83
```

逆序累积使“最低置位”对应**最大原始行号**，即时间上**最新**的一条匹配。结论：**Query 读最新历史值**，由电路结构直接确认（SRC）。

### 1.3 未写入地址 / 空历史的默认值 — SRC（返回 0）

- 全部 `FieldEquals` 为 0 → `LowBit` 全 0 → `SelectCompose` 选出 0（L65-89）。**未写地址 Query = 0**，源码直接行为（SRC）。
- `traceCount = 0` 时电路构造抛 `ArgumentOutOfRangeException`（L12）。因此**空历史不构造 Fetch 电路**；这与 step 0 走 `zeroShare` 分支（§1.5）在语义上一致：都没有真实的历史扫描。
- 本轮参考模型对“空历史 / 未写地址”统一返回 0（MODEL，与 SRC 行为对齐）。

### 1.4 初始地址空间 — 部分 SRC + MODEL

- SRC：`mem_addr` 是有限域元素（`Fr(BLS12-377)`），源码**未**出现“固定地址域 `[0,n-1]`”的约束；地址上界来自程序/寄存器取值，不在 Fetch / Prove 电路中限制。
- 非内存操作使用哨兵 `NegOne`（`ZkVmExecutorCircuitBoardGenerator.cs` L992：`SelectComposeOtherwiseGadget(..., constNumberNegOneWire)`）。本轮参考模型取 `DUMMY_ADDR = 2^32-1` 表示该哨兵（MODEL，沿用 EXP-DORAM-01 既有约定）。
- MODEL：**固定地址域 `[0,n-1]` 是本轮影子表方案的显式假设，不是上游源码事实**。影子表只在 `[0,n-1]` 上建立；任何超出该域的 `fetch_address` 按“未写地址 = 0”处理，不改变上游错误/默认值语义。该假设是否符合目标系统在 `decision.md` 中单独讨论。

### 1.5 每一步 Fetch 的触发条件与 step 0 — SRC

`ZkProgramExecutor.cs` L192-234：

```csharp
if (globalStepCounter == 0) {
    memVal = zeroShare;                                  // L201-203，不构造 Fetch 电路
} else {
    new MemoryTraceFetchCircuitBoardGenerator(globalStepCounter) // L205，traceCount = 当前历史行数
    ... AddPrivate(in_trace_*, memoryTrace[row][col])    // L218-223
    AddPrivate("in_mem_addr", thisRegisters[0]);          // L226，地址固定在 reg0
    await Compute();
    memVal = GetOutput("out_trace_mem_val");              // L230
}
```

- **step 0：`memVal = zeroShare`，不构造/运行 Fetch 电路**（SRC）。
- **每个 step > 0：无条件构造并运行 Fetch 电路**，与操作类型（LOAD / STORE / NOOP）无关（SRC）。这一点是 EXP-DORAM-01-R1 修正的核心，本轮继续沿用。
- 注意 Fetch 电路的 `traceCount = globalStepCounter`，即只覆盖**当前已有**历史行，不含本步即将追加的行（SRC，L199 断言 `globalStepCounter == privOutMemValFields.Count`、L217 断言 `== memoryTrace.Count`）。

### 1.6 非内存指令 dummy Fetch 的行为 — SRC

`ZkVmExecutorCircuitBoardGenerator.cs` L967-1007：

```csharp
out_trace_is_mem_op     = BoolOr(isLoad, isStore)                       // L971
out_trace_is_mem_write  = isStore                                       // L979
out_trace_mem_addr      = SelectComposeOtherwise(isStore, isLoad,
                              outMemAddr, inMemAddr, NegOne)            // L991-992
out_trace_mem_val       = SelectComposeOtherwise(isStore, isLoad,
                              outMemVal, inMemVal, constNumberWires[0]) // L1001-1002
```

- 非内存操作：`is_mem_op=0, is_mem_write=0, mem_addr=NegOne, mem_val=0`，**仍追加一行历史**（dummy event，不删除）。
- 但**该步的 Fetch 电路仍以 `thisRegisters[0]`（普通地址）运行**（§1.5），只是返回的 `memVal` 对 NOOP 不被消费（VM 电路的 `out_trace_mem_val` 对非内存操作选 `constNumberWires[0]`）。这正是 `fetch_address != trace_address` 的来源。

### 1.7 `fetch_address` 与 `trace_address` 的区别 — SRC

| 概念 | 源码位置 | 含义 |
| --- | --- | --- |
| `fetch_address` | `ZkProgramExecutor.cs` L226 `AddPrivate("in_mem_addr", thisRegisters[0])` | Fetch 电路输入，恒为 reg0；step>0 每步都有；对 NOOP 也是普通地址 |
| `trace_address` | `ZkVmExecutorCircuitBoardGenerator.cs` L991-992 `out_trace_mem_addr` | 写入历史行的地址；LOAD/STORE = 实际地址，NOOP = `NegOne` |

- LOAD/STORE 时两者相等；NOOP 时不同。这是两个独立概念，**不得合并**（SRC）。
- 本轮模型沿用 EXP-DORAM-01-R1 的 `fetch_address` / `trace_address` 双字段事件格式（MODEL，与 SRC 对齐）。

### 1.8 Add 是否总是对应一条历史记录 — SRC（是，每步一条）

`ZkProgramExecutor.cs` L389-408：

```csharp
foreach (string colName in memoryTraceColumnNames) {
    if (colName == "global_step_counter")
        incomingTraceRow.Add(colName, MpcShareFromPublicValue(globalStepCounterField));
    else
        incomingTraceRow.Add(colName, GetOutput($"out_trace_{colName}"));
}
AddMemoryTrace(incomingTraceRow);                        // L401
AddHashMemoryTrace(GetOutput("out_hash_mem_trace"));     // L406-407
```

- 每个执行步（含 NOOP）恰好追加一行，逐行承诺同步累积。
- 本轮模型：每次 `add()` 恰好追加一条不可变历史行并计算一次行承诺（MODEL，与 SRC 对齐）。

### 1.9 最终 Export 是否保留被覆盖的旧值 — SRC（是）

`MemoryTraceProveCircuitBoardGenerator.cs` L60-79 对**全部** trace 行逐行承诺：

```csharp
out_{i}_hash_mem_trace = H(magic, step, is_mem_op, is_mem_write, addr, val, enc_key)
```

L84-203 在**排序后**整表上强制顺序与值完整性（跨地址按 `addr` 递增、同地址按 `step` 递增；非写行值沿时间链不变）。`ZkProgramExecutor.cs` L571-587 用 `AddHashMemoryTrace` 的执行期计数与 Prove 期重算计数比对，防丢行/重排。

- 结论：Export = 完整历史日志，**被覆盖的旧值仍作为历史行存在并进入承诺**，不是只保留最终字典（SRC）。影子表不得删/合并/覆盖历史行，本轮模型严格遵守（MODEL）。

### 1.10 值完整性语义 — SRC

- `MemoryTraceProveCircuitBoardGenerator.cs` L167-193：`is_integrity_check_ignored = is_mem_write OR last_access`；若非写且非该地址最后一行，则要求 `mem_val[row] == mem_val[row-1]`。
- 含义：Load 行携带的是**当时读到的值**，且在同地址的时间链上，两次写之间所有 Load 的值必须相同。这与“Query 读最新写入值”一致（SRC）。
- 本轮参考模型的 `latest_value(HistoryLog, a)` 定义：取该地址最后一条 `is_mem_write=1` 行的 `mem_val`；无写则返回 0（MODEL，与 §1.2/§1.3/本条对齐）。

---

## 2. 影子表模型能否保持原始语义

| 检查项 | 判定 | 依据 |
| --- | --- | --- |
| 5 列 trace 逐行内容一致 | 可保持 | E1 与 E0 共用同一行构造规则，只实现不同读取路径 |
| step 0 特判 | 可保持 | 两者都在 step 0 直接给 0、不触发任何扫描 |
| step>0 每步一次 Fetch | 可保持 | 两者都在每个非初始步调用一次读原语 |
| NOOP 仍追加 dummy 行 | 可保持 | 追加规则与操作类型无关 |
| `fetch_address != trace_address` | 可保持 | 双字段事件格式沿用 R1 |
| Query 读最新值 | 可保持 | E1 影子表由每次 Update 同步维护；不变量每步校验 |
| 未写地址返回 0 | 可保持 | 影子表初值全 0 |
| Export 保留被覆盖旧值 | 可保持 | HistoryLog 与 E0 独立且同规则追加，互不删改 |
| 固定地址域 `[0,n-1]` | **仅模型假设** | 源码未限制地址域；超出域按未写=0 处理 |

**结论：未发现影子表模型无法保持原始语义的障碍，继续执行实现。** 唯一需在决策中明确的是“固定地址域”为模型假设（§1.4）。

---

## 3. 明确不声称

- 不声称 E1 的影子表已具备 obliviousness、恶意安全或公开可验证性。
- 不声称 Reference Python 计时等价于 MPC 门数、通信轮数或证明约束数。
- 不声称上游存在名为 `HistoricalKV` 的类；§0 已给出真实源码映射。
- 不修改上游源码、不改 Rust/C# witness 契约、不改 EXP-DORAM-01..06 任何文件。
