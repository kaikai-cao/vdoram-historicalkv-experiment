# path-read-write-analysis.md — Path Read/Write 组件审计

> 基线：VDORAM artifact @ `10c90d35464620a35ddb1e2c29d2e8725acedd52` · 论文 NDSS'26 eprint 2025/039
> 标注：VERIFIED / INFERRED / UNKNOWN / BLOCKED
> 源码在 `source-evidence/` 与 `../source-snapshot/`；论文在 `paper/EXCERPTS.md`。

## 0. 结论（先给判定）

**MPC 层具备实现"固定形状路径读写"所需的大部分底层原语，但不具备"秘密索引数组访问"这一关键原语，且整条路径访问链缺少跨 step 状态通道。** 底层原语可用 ≠ 完整 Path ORAM 可实现。

判定：**底层原语 VERIFIED（部分）/ 秘密索引 BLOCKED / 完整路径读写 UNKNOWN+BLOCKED**。

## 1. 现有 MPC 原语清单（VERIFIED）

MPC 电路原生操作类型只有 4 种（`CompatCircuitOperationType.cs`；下文 gadget 全部基于它们）：

| 原生操作 | 通信轮数（论文 p10 §IV-E） |
| --- | --- |
| Addition | 0 |
| Multiplication | 1（广播一个 reveal 值） |
| Inversion-or-zero | `l + 4`（l = ⌈log₂p⌉） |
| BitDecomposition | `19l + 2` |

Gadget 层（`source-evidence/CompatCircuit__CompatCircuitProgramming__Gadgets/`，均 VERIFIED）：

| 能力 | gadget | 实现要点 |
| --- | --- | --- |
| 相等/零测试 | FieldEqualsGadget / inversion-or-zero | 减法 + `1 − a·inv` |
| 大小比较 | FieldLessThanGadget L12-44、BitsLessThanGadget | 全位分解 + 布尔比较 |
| 布尔逻辑 | BoolAnd/Or/Not/XorGadget | — |
| 条件选择 | SelectComposeGadget L16-44、SelectComposeOtherwiseGadget L16-67 | `Σ cᵢvᵢ`，编译期固定候选数 |
| 最低置位选择 | LowBitGadget、LowBitWithCarryGadget | Fetch 取"最新匹配" |
| 低比特生成 | BitDecompositionGadget | — |
| hash/加密 | MimcHashGadget、MimcEncryptGadget | 逐行承诺（MiMC） |

论文 p8 §IV-B 明确写了这一设计取舍（VERIFIED）：*"where an efficient MPC comparison [64] is insufficient for ZKP statement construction, we substitute it with a sequence of boolean operations on decomposed bits"*——这正是 `FieldLessThanGadget` 的实现。

## 2. bucket 字段能否秘密共享（VERIFIED / INFERRED）

| 字段 | 能否秘密共享 | 证据 |
| --- | --- | --- |
| key / addr | 能。域元素作为秘密份额 | 论文 p5：加法秘密共享 `[a]`；源码 `MpcValue.IsSecretShare` 贯穿 |
| value | 能。同上 | 源码 Fetch 输入 `in_trace_{row}_{col}` 为 `AddPrivate`（L225） |
| leaf（位置标签） | 能（域元素/位串） | INFERRED（无现成结构，但加法共享可表示） |
| valid bit | 能（布尔份额） | `BoolXor/AndGadget`、`EdaBitsKai`（daBit/edaBit）支持混合域 |
| 重随机化随机数 | 需要 domain separation 的随机份额；`MpcExecutor` 消费 preprocessed EdaBits/DaBits/Beaver（Factory L18-21） | VERIFIED（原语存在）/ INFERRED（用于 ORAM 重加密需新协议） |

**结论**：字段级秘密共享 VERIFIED 可行（有原语）；bucket 级数据结构本身不存在（INFERRED 需新建）。

## 3. 秘密索引数组访问（BLOCKED，关键缺口）

Path ORAM 的核心操作是"按秘密 leaf 读内存树节点"——即**秘密索引的数组访问 `[node]`**。本仓库情况：

- `SelectComposeGadget`（L16-44）：输入 `condition_i`、`value_i` 各 `SelectionCount` 个（`SelectionCount` 在构造时固定），输出 `Σ condition_i·value_i`。这是"从编译期枚举的候选中按秘密条件线性组合"，**不是** secret-index lookup。若用它实现 N 项数组的秘密索引，需要把全部 N 项都作为线值输入 → O(N) 每步，退化为线性扫描。
- 源码树全量搜索：`oram / index / swap / obliv / permute / shuffle` 路径命中 0 个 ORAM 相关文件（只命中无关的 BitDecomposition 与 marlin indexer，VERIFIED）。
- 条件交换（conditional swap） gadget 不存在；oblivious sort 用的是**电路级 Bitonic 网络**（`MemoryTraceSortCircuitBoardGenerator.cs` + `MemoryTraceSortInnerLoopCircuitBoardGenerator.cs`），比较器固定，可以对**已知长度数组**做全排列，但不能替代按秘密地址的单点访问。

**判定**：缺少"secret-index array read/write"原语。这是 Path Read/Write 相对当前框架的**结构性缺口**，不是"调参可解"。（若接受 O(N) 全扫描实现秘密索引，则等价于回到 VDORAM 已有线性扫描，无 ORAM 收益。）

## 4. dummy ORAM 操作（INFERRED，需设计）

- 论文 p6 Fig.2 与 p10 §IV-D：每步都执行 memory fetch，非内存操作也用 `addr = p−1` 做 dummy fetch；"the number of memory accesses equals the total number of instruction cycles"（p10，VERIFIED）。
- 若换成 Path ORAM，为满足同样隐私声明，非内存步也必须执行**与真实访问不可区分的 dummy 路径读写**（随机 leaf + 假 value + stash 空操作），否则周期数与访问模式相关性泄露。
- 本仓库无 dummy path 操作（无路径结构），该要求属 INFERRED（从隐私声明推导的新设计约束）。
- **地址语义分离保持**：Fetch 输入 `reg0`（`ZkProgramExecutor.cs` L230）与历史 trace `out_trace_mem_addr`（`ZkVmExecutorCircuitBoardGenerator.cs` L990-1000，NOOP=NegOne）是两个字段；R1 已在 trace 层分离（`generator_r1.py`），路径读写必须沿用分离语义——dummy 的 path 输入是 reg0 的普通地址，历史行仍是 NegOne（VERIFIED 语义 + INFERRED 接入）。

## 5. 通信轮数与成本估计（INFERRED / UNKNOWN）

用论文的 gadget 成本（p10）对**单次路径访问**做符号化估计（详细推导见 `complexity-model.md`）：

- 读路径 L 层 × 每层 Z 个 bucket 行，每行字段做相等/选择：每行 O(l) 位分解 → 每行约 `O(l)` 轮乘法（l=⌈log₂p⌉）。
- 一次 Path Read 的轮数量级：`O(L · Z · l)`（每 bucket 行做一次秘密 tag 比较 + 选择）；若 stash 为 S，另加 `O(S · l)`。
- 通信量：每轮广播 reveal 值，规模随比较位数增长；具体字节数需实测，**UNKNOWN**。
- **对比基准**：论文实测当前线性扫描 memory fetch 是 `O(T²)` 轮（p10 §IV-E，VERIFIED）；Path ORAM 单步 `O(L·Z·l)`，T 步累计 `O(T·L·Z·l)`。结构上有 `T·L·Z·l ≪ T²` 的空间（当 T 大），但常数与递归 position map 成本未知——不能据此宣称"有优势"（见 `complexity-model.md`）。

## 6. 五项必答清单

| 必答项 | 结论 | 标注 |
| --- | --- | --- |
| MPC 是否支持路径读写操作 | 底层比较/选择/位分解具备；秘密索引缺失 | VERIFIED（原语）/ BLOCKED（索引） |
| bucket key/value/leaf/valid 秘密共享 | 字段级可行 | VERIFIED/INFERRED |
| 可复用原语 | equality、less-than、select、lowbit、bitdecomp、MiMC；无 swap/secret-index | VERIFIED |
| 是否需要秘密索引数组访问 | 需要；现有框架无此原语 | VERIFIED（缺失）/ BLOCKED |
| 通信轮数量级 | 单步 O(L·Z·l)；T 步 O(T·L·Z·l)（符号，常数 UNKNOWN） | INFERRED |
| 固定数量/长度路径访问 | 电路形状可固定（L、Z 编译期常量） | INFERRED |
| 非内存 dummy ORAM | 需新增设计（随机 leaf + 假值），否则泄露访问模式 | INFERRED |
| 地址语义分离 | Fetch reg0 vs trace NegOne 已在 R1 分离，路径读写须沿用 | VERIFIED（语义）/ INFERRED（接入） |

## 7. 证据索引

- `source-evidence/CompatCircuit__CompatCircuitProgramming__Gadgets/*`（10 个 gadget，逐文件带 BLOB SHA）。
- `source-evidence/...MpcExecutorFactory.cs` L18-21（Beaver/EdaBits/DaBits 预处理消费）、L45-67（session 更替）。
- `source-snapshot/ZkProgramExecutor.cs` L205-236（每步 Fetch）、L230（reg0）、L302（in_mem_val）。
- `source-snapshot/ZkVmExecutorCircuitBoardGenerator.cs` L990-1000（trace addr 选择）。
- `../source-snapshot/MemoryTraceSortCircuitBoardGenerator.cs`、`...InnerLoop...`（Bitonic 全排列，非秘密索引）。
- `paper/EXCERPTS.md` p8 §IV-B（比较原语取舍）、p10 §IV-E（轮数 O(T²)、gadget 成本）、p6 Fig.2（dummy fetch）、p10（隐私声明）。
