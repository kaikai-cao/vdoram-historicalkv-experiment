# position-map-analysis.md — Position Map 组件审计

> 基线：VDORAM artifact @ `10c90d35464620a35ddb1e2c29d2e8725acedd52` · 论文 NDSS'26 eprint 2025/039
> 标注：VERIFIED（源码/论文原文直接支持）· INFERRED（据证据推导）· UNKNOWN · BLOCKED
> 源码证据位于 `source-evidence/`（头部含 PATH + BLOB SHA）；论文原文见 `paper/EXCERPTS.md`（PDF 页码）。

## 0. 本组件的结论（先给判定）

**Position Map 在本仓库现有技术路径下不是一个可替换/可审计的独立组件，而是 VDORAM 刻意不采用的结构。**

- 论文明确：VDORAM 的 `FHistoricalKV` 地址域固定为 `addr ∈ [0, n−1]`，且实际实现用**单个线性扫描的 oblivious array**，不是 Path ORAM，因而**不存在 position map 这一状态组件**（论文 p8-9，VERIFIED）。
- 论文明确：现有高效 DORAM 只支持 2-3 方，与 VDORAM「任意数量 provers」目标冲突，这是它选择线性扫描的**直接原因**（p9，VERIFIED）。
- 因此"给当前 VDORAM 引入 Position Map"等价于**引入一套它刻意排除的 DORAM 数据结构**，必须连同参与方模型一起重新论证——这不是一个局部插件替换。

判定：**BLOCKED（在当前 VDORAM 实现路径内）/ INFERRED（若另起 n 方 ORAM 则结构可行但成本与威胁模型未证）**。

## 1. 地址域（VERIFIED）

| 问题 | 结论 | 证据 |
| --- | --- | --- |
| 固定 `[0,n-1]` 还是动态 key？ | **固定区间** `addr ∈ [0,n−1]` | 论文 p8 Fig.5：`Parameters. Memory size n that restricts the address addr ∈ [0, n − 1]` |
| 实际容量 | 论文另一处称 read-write memory with full address space，容量 `p`（域大小），即" virtually unlimited" | 论文 p10 §IV-E：*"capacity of p"*；与 Fig.5 的 `n` 是同一模型两种表述（有限域地址可视为至多 p 个槽） |
| 非内存操作地址 | `addr = p−1`（域最大值 = NegOne sentinel） | 论文 p8 §IV-C 与 p6 Fig.2；源码 `ZkVmExecutorCircuitBoardGenerator.cs` L990-1000 SelectComposeOtherwiseGadget |
| 未写地址读取 | 返回 0 | 论文 p10 §IV-D step 6：*"if t = 0, provers publicly sets [val] ← 0"*；R1 oracle/模型一致 |

**判断**：地址是**密集固定域上的索引**，不是任意动态稀疏 key。标准固定容量 Path ORAM 的地址模型与之相容——**这一道门槛实际上可过**（与负责人的初步担忧不同，需要修正预期）。真正的问题不在地址域形态，而在参与方模型与状态绑定（见 decision.md）。

## 2. Position Map 的必需性与递归问题（INFERRED / UNKNOWN）

若改用 Path ORAM 结构：

- Position Map 是 `addr → leaf` 的映射，规模 = 逻辑块数 N，每条目 `⌈log₂N⌉` 位。
- 标准优化是把它放入递归 ORAM（recursive position map）以避免客户端 O(N) 存储。
- 在本仓库现有 client 模型下：
  - **没有**任何 position-map 数据结构、secret array indexing 或递归 ORAM 的实例（源码树全量搜索：路径含 `oram/position/leaf/bucket/stash/index/swap/permute/shuffle` 的文件 0 个命中，仅命中无关的 `BitDecomposition`/`ArrayHelper`/`marlin indexer`，VERIFIED，见 §0）。
  - MPC 电路的原生操作仅 4 种：Addition / Multiplication / Inversion / BitDecomposition（`CompatCircuitOperationType.cs`；`source-evidence/` 中 gadget 均基于这四种组合，VERIFIED）。
  - 秘密索引访问（secret-index array read/write）**没有现成 gadget**；`SelectComposeGadget` 是 `Σ condition_i · value_i` 的线性组合，要求所有候选值在编译期已是具体线集合——这对 N 地址的 position map 意味着 O(N) 线性扫描，不是 O(log N) 的 ORAM 路径。

**递归问题（关键）**：如果 position map 自身放在递归 ORAM 里，则每层递归都需要独立的跨 step 状态（position map 的 position map...），把本已阻断的"跨 step 状态绑定"（见 `state-binding-analysis.md`）再复制多层。**不能只算主 ORAM 的路径成本而忽略递归层**——这一点在 `complexity-model.md` 中单列。

## 3. 存储结构与秘密共享需求（INFERRED）

| 项 | 结论 | 标注 |
| --- | --- | --- |
| 映射结构 | 标准方案用数组 `pos[addr] = leaf`；本仓库无此结构 | VERIFIED（缺失）/ INFERRED（可行性） |
| 是否必须秘密共享 | 是。论文 `distributed obliviousness` 要求 provers 不知任何 addr 的附加信息，包括"某未知地址被访问了几次"（p8-9）。position map 若明文持有，leaf 值直接泄漏访问位置趋势 | INFERRED（从 p8-9 原文要求推导） |
| 容量假设 | N = 逻辑块数；叶子数 = 2^L，L=⌈log₂N⌉；bucket size B、stash S 均为 UNKNOWN（论文与源码均不提供 Path ORAM 参数） | UNKNOWN |
| 单次逻辑操作 | `read(addr)`: 查 pos[addr]→leaf→读路径→更新 pos[addr] 为随机新 leaf→回写；`write` 同理。跨 VM step 需要把 new pos 保留到下一步 | INFERRED |
| 初始/首次写 | 标准 Path ORAM 需初始化所有块为 dummy 并随机分配 leaf；本文 `addr=p−1` 哨兵只用于 NOOP，与 Path ORAM 初始化语义不同，需设计映射 | INFERRED |

## 4. 跨 VM step 持久化（BLOCKED，核心）

- 本仓库跨 step 传递的状态只有（源码 L70-74 初始化、L358-376 更新）：
  - `thisProgramCounter`（秘密份额）、`thisRegisters`（秘密份额列表）
  - `hashThisProgramCounter`、`hashThisRegisters`（公开 hash）
  - `memoryTrace` 与 `hashMemoryTraceCount`（历史表与计数）
- **没有**任何机制把一组"position map 份额"或"树节点份额"作为 VM 状态的一部分传入下一步。
- 更根本的是：`MpcExecutorFactory.NextExecutor()`（`source-evidence/...MpcExecutorFactory.cs` L45-67）在每次创建新 executor 前 `this._prevMpcShareStorage?.UnregisterSession()`（L50），`MpcSharedStorage` 在 `Dispose()` 中清空所有 share 向量（`...MpcSharedStorage.cs` L47-55）。**session 是短命的，份额不跨 session 自动保留**。
- 若要持久化 ORAM 状态，必须显式仿照 registers 的做法：把整个 position map 作为输入份额注入下一个 session 的电路，并在输出侧产生新份额——这要求：(a) 电路输入规模随 N 变化；(b) 份额作为"输出"被 VM 主循环持有；(c) 与 SNARK witness/公开承诺对齐。三点在现有源码均**无先例、无实现**。

判定：**BLOCKED**（当前架构无跨 step 状态通道）/ **INFERRED**（理论上可仿 registers 模式扩充，但属新增协议工作，非审计范围内已证事实）。

## 5. 固定数组 Path ORAM ≠ 动态 key oblivious map（VERIFIED 区分）

- 负责人的关注点"固定大小数组 Path ORAM 不等于动态任意 key 的 oblivious map"——在**本例地址域条件下可收敛**：VDORAM 地址是 `[0,n−1]` 固定密集域（p8 Fig.5），因此固定容量数组模型足够，**不需要**一般化的动态 KV oblivious map。
- 但需注意：`Query` 要求"未写地址返回 0"，Path ORAM 中所有槽初始为 dummy 可满足；`Export()` 要求导出**全部历史含被覆盖值**（p8 Fig.5），这不是标准 Path ORAM 的原语——必须额外维护 append-only 历史表。这正是 VDORAM 的双结构（ORAM + HistoricalKV）问题，与 E1 结论一致。
- **结论修正**：动态 key 不是本项目的第一阻断；第一阻断是"任意参与方 + 跨 step 状态绑定 + 公开证明"三者叠加。

## 6. 六项必答清单

| 必答项 | 结论 | 标注 |
| --- | --- | --- |
| 地址域 | 固定 `[0,n−1]`（另有 `p−1` 作 NOOP 哨兵）；密集索引，非动态 key | VERIFIED |
| Position Map 容量假设 | N 条 `addr→leaf`；递归层参数全 UNKNOWN；本仓库不存在该结构 | VERIFIED（不存在）/ UNKNOWN（参数） |
| 单次访问逻辑操作 | 查 leaf/更新 leaf/路径读写（标准 Path ORAM，INFERRED）；本仓库无对应电路 | INFERRED |
| 更新后状态形式 | 秘密共享的 pos 数组 + 树节点 + stash；需跨 step 输入 | INFERRED / BLOCKED（持久化） |
| 递归 vs 非递归 | 非递归需每方 O(N) 秘密存储（不现实）；递归放不下现有跨 step 通道 | INFERRED / BLOCKED |
| 不能解决的问题 | 当前框架无法跨 session 保存 ORAM 状态；无秘密索引原语；DORAM 与任意参与方目标冲突（论文 p9） | VERIFIED |

## 7. 证据索引

- `paper/EXCERPTS.md` p8：Fig.5 `FHistoricalKV` 参数/功能/`Export()`；§IV-C 地址 `p−1` 哨兵；2-party Circuit ORAM / 3-party RAM 举例。
- `paper/EXCERPTS.md` p9：*"existing efficient DORAM schemes support an insubstantial number of parties ... arbitrary number of provers ... one linearly-scanned oblivious array"*；Bitonic sort/padding；复杂度 O(T²)。
- `paper/EXCERPTS.md` p10：§IV-E 容量 p；"if t = 0 ... [val] ← 0"；MPC 轮数。
- `source-evidence/`：`MpcExecutorFactory.cs` L45-67（session 更替/注销）、`MpcSharedStorage.cs` L47-55（Dispose 清空）、`ZkProgramExecutor.cs`（原 `source-snapshot/`）L70-74/L358-376（跨 step 状态）、`SelectComposeGadget.cs` L28-44（线性组合选择）。
- 源码树全量搜索结果（本轮 `data/_tree2.json.tmp`，1497 条目）：无 ORAM/position/leaf/bucket/stash/secret-index 文件。
