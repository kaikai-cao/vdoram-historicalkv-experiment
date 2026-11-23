# source-audit.md — VDORAM 原始代码与关键接口核查

> EXP-DORAM-01 · 基线 commit `10c90d35464620a35ddb1e2c29d2e8725acedd52`（`BDS-SDU/vdoram-artifacts`，NDSS'26 VDORAM artifact）
> 审计日期：2026-11-23 · 所有源码快照见 `docs/source-snapshot/`（每文件头部记录 PATH / BLOB SHA）
> 标注体系：**VERIFIED**（源码/测试/实测直接支持）· **INFERRED**（基于已核查证据推导）· **BLOCKED**（环境/依赖阻断）· **UNKNOWN**（尚未验证）

---

## 0. 基线与证据来源

| 项 | 值 | 状态 |
| --- | --- | --- |
| 上游仓库 | `BDS-SDU/vdoram-artifacts`（NDSS'26 "VDORAM: Towards a Random Access Machine with Both Public Verifiability and Distributed Obliviousness"） | VERIFIED |
| 基线 commit | `10c90d35464620a35ddb1e2c29d2e8725acedd52`，message `build: Make rust 1.93.0-nightly happy`，author Huayi Qi 2026-04-28 | VERIFIED（GitHub API commit 端点返回） |
| commit tree | `a93493550938ce2abe8ddf9db95937f40f772281`，递归条目 1497，`.cs` 文件 255，未截断 | VERIFIED |
| 取源方式 | 逐个 blob（base64）经 `api.github.com/.../git/blobs/{sha}` 下载，避开本机到 GitHub 大 pack 流被截断的问题 | VERIFIED（17/17 文件成功，见 `scripts/fetch_snapshot.py`） |
| 本地环境 | Windows 11 家庭版 Insider Preview 26320 / Intel i7-14700 (20C/28T) / RAM 31.69 GB / **无 .NET SDK** / git 2.55.0 / Python 3.13.14 | VERIFIED |

**重要边界（VERIFIED）**：本机未安装 .NET SDK，`dotnet` 不在 PATH，`C:\Program Files\dotnet\dotnet.exe` 不存在。因此本轮**无法编译或运行 VDORAM 原始 C# 工程**；E0 依据源码逻辑建立可独立运行的 Python 参考模型，E2 结论为纯源码级审计，不涉及实际 MPC / Halo2 执行。

---

## 1. 关键源码逻辑核查

### 1.1 E0 基线：HistoricalKV 线性扫描 = MemoryTraceFetch

文件：`CompatCircuit/CollaborativeZkVm/ZkVmCircuits/MemoryTraceFetchCircuitBoardGenerator.cs`（blob `8232e2b83dd2…`）

逐条证据（行号对应快照文件）：

1. **列定义（快照 L13-14）**：`ColumnNames = ["mem_addr", "global_step_counter", "is_mem_op", "is_mem_write", "mem_val"]`；`ColumnNamesToBeFetched = ["mem_val"]`。历史记录即一张 5 列 memory trace 表。
2. **全历史行作为私有输入（L23-34）**：对每个 `col × row` 建 `Wire.NewPrivateInputWire("in_trace_{row}_{col}")`，`row ∈ [0, traceCount)`。
3. **查询地址单独输入（L45-47）**：`inMemAddrWire = Wire.NewPrivateInputWire("in_mem_addr")`。
4. **逐行地址相等比较（L49-63）**：`for (row = traceCount-1; row >= 0; row--)`，每行施加 `FieldEqualsGadget([inTraceMemAddrWires[row], inMemAddrWire])`，输出 `row_selection_{row}_raw`（匹配=1，否则=0）。注意此列表**逆序**累积。
5. **选最新匹配（L65-74）**：`LowBitGadget(rowSelectionRawWires)` 取最低置位 → 由于逆序累积，最低位对应**最大 row index**，即时间上**最新**一条匹配；输出再 `Reverse()` 恢复升序。
   - 未匹配情形：全部 raw bit 为 0 → LowBit 输出全 0 → SelectCompose 选出 0。即 **Read(未写地址) = 0**（这与任务要求一致，且是源码直接行为，VERIFIED）。
6. **组合输出（L78-89）**：`SelectComposeGadget(traceCount)` 用选择位从 `mem_val` 列取值，输出 `out_trace_mem_val`（私有输出）。

**工作量化（VERIFIED）**：单次 Fetch 查询 = `traceCount` 次 `FieldEqualsGadget` + 1 次 `LowBitGadget(traceCount)` + 1 次 `SelectComposeGadget(traceCount)`。这是 E0「扫描全部历史记录、地址匹配、选最新、未匹配返零」的精确电路对应。任务包 §四 EXP-01-A 要求复现的选择逻辑 = 本文件的 LowBit-of-reversed-equals 逻辑。

### 1.2 历史一致性与证明输入：MemoryTraceProve

文件：`CompatCircuit/CollaborativeZkVm/ZkVmCircuits/MemoryTraceProveCircuitBoardGenerator.cs`（blob `7269ee8eb1fc…`）

1. **每行承诺（L64-83）**：`out_{i}_hash_mem_trace = H(magic, global_step_counter, is_mem_op, is_mem_write, mem_addr, mem_val, enc_key)`，全部为 **public output**。即每行 trace 都进入公开证明输入/承诺。
2. **上次访问判定（L85-110）**：`last_access_i = NOT FieldEquals(mem_addr[row], mem_addr[row+1])`；`not_last_access_i = FieldEquals(...)`。
3. **顺序约束（L121-166）**：
   - `is_step_increased = global_step_counter[row] < global_step_counter[row+1]`
   - `is_addr_increased = mem_addr[row] < mem_addr[row+1]`
   - 约束：`last_access ⇒ addr 递增`（跨地址必须排序）；`not_last_access ⇒ step 递增`（同地址按时间排序）。这就是**排序 + 时间戳语义**的电路编码。
4. **值完整性（L171-197）**：若 `is_mem_write[row] == 0` 且 `not_last_access`，则强制 `mem_val[row] == mem_val[row-1]`（非写操作不得改变值，等价于 Load 不改变内存）。
5. **汇总（L209-216）**：`out_is_satisfied = AND(all is_satisfied_i)`，public output。

**结论（VERIFIED）**：原始「HistoricalKV 一致性」不只看最终字典，而是由 Prove 电路强制：(a) 行级 hash 承诺进入公开输出；(b) 排序顺序（地址主键 + 时间戳次键）；(c) 非写行的值沿时间链不变。E1 的双结构必须保留能重构这 5 列 trace 的全部字段，否则无法进入原证明流程。

### 1.3 排序流程：ZkProgramExecutor 的 Memory Trace 管线

文件：`CompatCircuit/CollaborativeZkVm/ZkPrograms/ZkProgramExecutor.cs`（blob `24ddf044e895…`）

| 阶段 | 证据（行号） | 内容 |
| --- | --- | --- |
| trace 累积 | L84-111 | `memoryTrace`（row→col→MpcValue）与 `hashMemoryTraceCount`；注释明言 `globalStepCounter` 有序 |
| Fetch 调用 | L196-238 | 每步 `new MemoryTraceFetchCircuitBoardGenerator(globalStepCounter)`；`AddPrivate` 全部历史行；`in_mem_addr = thisRegisters[0]`；输出 `memVal = GetOutput("out_trace_mem_val")`；step 0 特判 `memVal = zeroShare` |
| **in_mem_val 绑定** | L300-304 | `AddPrivate("in_mem_val", memVal)` 传入 ZkVmCircuit —— **任务要求的绑定点成立（VERIFIED）** |
| VM 私有输出 | L341-346 | `privOutMemVal = GetOutput("out_mem_val")` 存入 `privOutMemValFields`（MPC 方私有保存） |
| trace 追加 | L393-406 | 每步把 `out_trace_{colName}` 收集为一行；`global_step_counter` 用公开值；`AddMemoryTrace(incomingTraceRow)` |
| hash 计数 | L408-412, L571-587 | 每步 `AddHashMemoryTrace(outHashMemTrace)`； Prove 后逐 hash 比对 count，防丢行/重排行 |
| 排序 | L443-522 | pad 到 2 的幂（填 NegOne）；逐 `MemoryTraceSortInnerLoopCircuitBoardGenerator.GetAllLoopIndexKJ` 轮次用独立 MPC session 排序；再去 padding |
| Prove | L524-593 | 对排序后 trace 跑 `MemoryTraceProveCircuitBoardGenerator`，检查 `out_is_satisfied == 1` 且 hash 计数一致 |
| witness 保存 | L45-48, L191, L415, L590 | `RaiseR1csCircuitWithValuesGenerated` 为 IF / ZkVm / Prove 电路各保存 `R1csCircuitWithValues`（含值份额）供后续证明 |

**结论（VERIFIED）**：Fetch 输出值通过单一命名线 `in_mem_val` 进入 VM 电路，可被 ORAM 返回值替换而**无需改动 VM 电路接口**（概念上：ORAM read 只需产出同名的秘密共享 `memVal`）。但排序与 Prove 依赖整张 trace，这部分不在本轮替换范围。

### 1.4 排序电路与 VM 电路字段语义

- `ZkVmExecutorCircuitBoardGenerator.cs`（blob `65042dcd438b…`）：
  - L224-231：`in_mem_val` 为私有输入；`inMemAddrWire = inRegisterWires[0]`（**地址固定在 reg0**）。
  - L512-519：`Load` 把 `inMemValWire` 写入 reg{arg0}（通常 reg0）。
  - L503-510：`Store` 不改寄存器，`out_mem_val = reg{arg0}`（L933-940），`out_mem_addr = reg0`（L957-965）。
  - L972-1011：`out_trace_is_mem_op = (Load∨Store)`；`out_trace_is_mem_write = Store`；非内存操作时 `mem_addr = NegOne, mem_val = 0`；Load 时 `out_trace_mem_val = inMemValWire`。**这解释了 dummy access 规则**：非内存指令以 `addr=NegOne, val=0` 入 trace，不泄露操作类型到 trace 内容之外。
  - L1013-1022：`out_hash_mem_trace` 承诺。
- `MemoryTraceSortCircuitBoardGenerator.cs` / `MemoryTraceSortInnerLoopCircuitBoardGenerator.cs`：已在快照中取得，本轮审计只确认其存在与被 L472-506 调用（VERIFIED），不深入比较网络细节（属 E2 后续实现）。

### 1.5 E2 接口审计：MpcExecutor / Factory / IMpcExecutor

文件：`MpcExecutor.cs`（`30b7eeb09a99…`）、`MpcExecutorFactory.cs`（`07165e08d153…`）、`IMpcExecutor.cs`（`7a043675bbfc…`）

| 核查项（任务 §四 EXP-01-C） | 源码证据 | 判定 |
| --- | --- | --- |
| C1 `MpcExecutor` 能否表示 ORAM 读写电路 | `MpcExecutor.ComputeOperations` L152-398 支持 `BitDecomposition / Addition / Multiplication / Inversion`；秘密共享比较经 `LowBit`(L900-916)、`BitsAdd`(L864)、`BeaverMulti`(L736)、`EdaBits`/`DaBit` 原语组合实现 `FieldEqualsGadget`/`FieldLessThanGadget`（L56/L124 等在电路层调用） | **VERIFIED**：底层算术 + 秘密比较 + 位分解原语齐备，足以表达任意算术化 ORAM 地址选择/比较逻辑。但具体 Path ORAM 电路是否存在、正确性未验证 → 该具体电路为 **UNKNOWN** |
| C2 秘密共享状态下地址选择 | Fetch 电路 `AddPrivate("in_mem_addr", thisRegisters[0])`（ZkProgramExecutor L230），`thisRegisters` 全程为 `MpcValue`（秘密份额，L73/376）；`FieldEqualsGadget`/`LowBit`/`SelectCompose` 在 MPC 会话中跑（L209-234） | **VERIFIED**：地址以秘密份额输入，选择逻辑在 MPC 内完成，选择位不出明文 |
| C3 每次状态更新后保留 witness | L191/L415/L590 每电路保存 `R1csCircuitWithValues`；`CircuitExecuteResult.ValueBoard` 保留全部线值（MpcExecutor L506/652） | **VERIFIED**：每个 MPC session 的线值+witness 均落盘回调；ORAM session 若沿用 `CircuitBoardMpcExecutorWrapper` 可同等保存（INFERRED，需实际接线验证） |
| C4 ORAM 返回值绑定 `in_mem_val` | ZkProgramExecutor L234 `memVal = GetOutput("out_trace_mem_val")` → L302 `AddPrivate("in_mem_val", memVal)`；VM 电路 L225 `inMemValWire` → L518 Load 写入 reg0 | **VERIFIED**：命名线契约清晰，ORAM read 输出替换为同名 `memVal` 即可绑定 |
| C5 ORAM 状态更新与 HistoricalLog 追加绑定协同证明 | trace 追加 L393-406 + hash 计数 L408-412 + Prove L524-593；`IMpcExecutorFactory.NextExecutor()`（L45-67）提供**顺序、单一活跃**的 MPC session，前一 session 完成后才建下一个（L46-48 断言） | **INFERRED**：可通过「ORAM read/write session → VM session → append trace」的 session 链，把 ORAM 输出的旧值/新值作为 `out_trace_*` 输入 Prove。但 ORAM 自身访问轨迹（position map / stash / tree）**是否/如何进入公开 trace** 未在 artifact 中定义 → **UNKNOWN** |

**Factory 语义补充（VERIFIED）**：`MpcExecutorFactory.NextExecutor()` 在新建 session 前 `UnregisterSession()` 上一个，且断言上一 executor 必须 `Completed`；beaver/edaBit/daBit 枚举器跨 session 共享。含义：ORAM 的跨 step 持久状态（如 position map、stash）**不会自动跨 session 保存**，必须以秘密份额形式作为私有输入显式传给下一 session（与 `thisRegisters` / `inEncKey` 的传递模式同构，ZkProgramExecutor L288-298）。这是接入路径的**可行动结论**（INFERRED，有 L288-298 的类比证据支撑）。

---

## 2. E2 接口兼容性总判定

> 任务要求：明确哪些已验证、哪些只是推测。

| 结论 | 标注 | 依据 |
| --- | --- | --- |
| VDORAM 使用通用算术化 MPC（加/乘/逆/位分解 + 秘密比较），能表达 ORAM 的地址选择与数据移动算术逻辑 | **VERIFIED** | MpcExecutor L152-398, L736-916；Fetch 电路 L52-89 |
| ORAM read 返回值可通过 `in_mem_val` 命名线注入 VM，无需改 VM 电路 | **VERIFIED** | ZkProgramExecutor L234 & L302；ZkVmExecutor L225/L518 |
| 历史 trace 的每行 hash 承诺 + 排序 + 值完整性检查构成公开证明输入，E1/E2 必须保留 5 列 trace | **VERIFIED** | Prove 电路 L64-83/L121-197；ZkProgramExecutor L393-412/L571-587 |
| 每个 MPC session 的 witness（`R1csCircuitWithValues`）可落盘，ORAM session 可复用该机制 | **INFERRED** | L45-48/L191/L415/L590 + CircuitExecuteResult.ValueBoard |
| 跨 step 的 ORAM 持久状态需以秘密份额显式传入下一 session（同 registers 模式） | **INFERRED** | Factory L45-67 + ZkProgramExecutor L288-298 |
| 存在可行的 ORAM 接入路径（session 链：ORAM → VM → append trace → Prove） | **INFERRED** | 上述 C1-C5 综合 |
| 具体 Path ORAM 电路的通信量/轮数/约束数/证明时间 | **UNKNOWN** | 本轮不实现 E2、不启动 Halo2、无 .NET SDK |
| ORAM 内部访问轨迹能否/是否需要进入公开 trace 与 Prove 电路（obliviousness 与 public verifiability 的接口） | **UNKNOWN** | artifact 未定义；这是路线核心开放问题 |
| 当前 MPC 框架的实际安全参数、参与方数、预处理规模 | **UNKNOWN / BLOCKED** | 无 .NET SDK 无法运行 artifact；源码审计不涉及运行参数 |

**E2 净结论**：源码级存在**可行的接入路径**（VERIFIED 的命名线契约 + INFERRED 的 session 链），但「可接入」不等于「已实现」或「有性能优势」；具体构造、成本与公开可验证性接口仍为 UNKNOWN。按任务包 §八决策规则，此状态对应「E2 可接入（源码级路径），成本未知」，**不直接认定 NO-GO，也不进入论文级实验**。

---

## 3. 审计范围外（明确不声称）

- 不声称普通 Python E1 模型具备任何密码学安全性 / 访问模式隐藏能力。
- 不声称 E0 的 Python 参考模型与 C# 电路逐 gadget 等价；只声称与**选择语义**（全历史扫描 + 最新匹配 + 未匹配返零）一致（见 experiment-report 的方法学）。
- 不启动 Halo2，不虚构 MPC 通信量 / 轮数 / 约束数 / 证明时间。
- 不修改 VDORAM 上游，不创建 PR。
