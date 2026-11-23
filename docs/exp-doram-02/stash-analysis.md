# stash-analysis.md — Stash 组件审计

> 基线：VDORAM artifact @ `10c90d35464620a35ddb1e2c29d2e8725acedd52` · 论文 NDSS'26 eprint 2025/039
> 标注：VERIFIED / INFERRED / UNKNOWN / BLOCKED
> 源码证据在 `source-evidence/`；论文原文在 `paper/EXCERPTS.md`。

## 0. 结论（先给判定）

**当前 VDORAM 实现中没有 Stash——因为根本没有 Path ORAM 树/路径访问。** Stash 是 Path ORAM 特有的临时缓存，随树结构一并缺失。

若引入 Path ORAM，Stash 的实现面临**三重障碍**：

1. **无跨 step 持久通道**：stash 内容必须在 step 之间保留（见 `position-map-analysis.md` §4、`state-binding-analysis.md`），当前 session 用完即销毁（VERIFIED）。
2. **固定执行形状可做，但秘密索引容量受限**：秘密比较/选择原语存在，但 `SelectComposeGadget` 是线性组合，stash 扫描是 O(S) 的线性遍历，S 必须编译期固定（VERIFIED + INFERRED）。
3. **overflow 概率界与参数全 UNKNOWN**：论文与源码均未给出 Path ORAM 参数（B、Z、L、S）或 overflow 界；不能写"stash 足够大"。

判定：**BLOCKED（当前架构）/ UNKNOWN（引入 Path ORAM 后的容量与 overflow 界）**。

## 1. Path Read 后数据进入 Stash 的机制（INFERRED，本仓库无实现）

标准 Path ORAM：读根到叶路径上每个 bucket 的全部 Z 个块 → 解压到 stash → 找到目标块 → 重加密/重随机化 → 沿路径尽量写回 → 剩余留 stash。

本仓库对应情况：
- 无 bucket、无路径、无 stash 数据结构（源码树全量搜索路径含 `path/stash/bucket/leaf/oram` 的 .cs 文件：0 命中，VERIFIED）。
- Fetch 电路（`MemoryTraceFetchCircuitBoardGenerator.cs`，原 `source-snapshot/`）做的是对**全部历史行**的 `FieldEquals(mem_addr)` + 逆序 LowBit 选最新，是 O(T) 线性扫描，不是路径访问。
- 因此"Path Read 后 bucket 进入 stash"这一流程**在本仓库无对应代码路径**，只能标 INFERRED（标准协议推演）。

## 2. Stash 是否固定容量（VERIFIED 缺失 / UNKNOWN 取值）

- 现有实现的"历史表"容量是 `T`（运行步数），padding 到 2 的幂（论文 p9；源码 `ZkProgramExecutor.cs` L455-466），这是 append-only 数组，**不是 stash**。
- 若引入 Path ORAM，stash 容量 S 必须**编译期固定**（MPC 电路形状固定，与 VDORAM "固定执行形状"要求一致：每步执行相同电路，无论是否内存操作——论文 p6/p10，VERIFIED）。
- S 的取值依据（标准 Path ORAM 界，如 `S = O(log N)` 且 overflow 概率随安全参数指数小）在本论文/源码中**均未给出**，标 UNKNOWN。**禁止**写"stash 足够大"。

## 3. Stash 查找的秘密比较与条件选择（VERIFIED 原语存在）

可用原语（均为 4 原生操作 `Add/Mul/Inv/BitDecomp` 上的 gadget）：

| 原语 | 文件（BLOB SHA 见文件头） | 能力 |
| --- | --- | --- |
| 秘密相等 | `FieldEqualsGadget.cs` | 域元素相等 → 0/1 秘密位（减法 + inversion-or-zero） |
| 秘密小于 | `FieldLessThanGadget.cs` L12-44 | 全位分解 + `BitsLessThanGadget`；比纯 MPC 比较贵但可作 ZK witness（论文 p8，VERIFIED） |
| 位运算 | `BoolAnd/Or/Not/XorGadget.cs` | 布尔组合 |
| 条件选择 | `SelectComposeGadget.cs` L16-44 / `SelectComposeOtherwiseGadget.cs` L16-67 | `Σ condition_i · value_i`，互斥条件 |
| 低比特 | `LowBitGadget.cs` / `LowBitWithCarryGadget.cs` | 取最低置位的 1-bit，用于"最新匹配"选择 |

**关键限制**：`SelectComposeGadget` 的两个特征决定了 stash 操作形态：
- (a) 输入是**编译期长度的线列表**（`SelectionCount` 构造时固定，`GetInputWireNames` 按 range 生成）——不是运行时秘密索引。
- (b) 输出是**线性组合** `Σ cᵢvᵢ`——适合"从已枚举候选中按条件挑选"，不适合"按秘密下标随机访问数组元素"。

因此 stash 查找可以这样做：对 stash 中**所有 S 个槽**并行做 `FieldEquals(tag_i, target)` → `SelectCompose` 汇总匹配值。复杂度 O(S) 每步，S 编译期固定 → **固定执行形状成立**（INFERRED）。但没有 O(log S) 的秘密索引结构；若 S 较大，成本线性增长。

## 4. 插入/删除/重排的固定形状（INFERRED）

- 标准 Path ORAM 的 stash 重排是数据相关的（"能写回路径的就写回"），在 MPC 中必须改成：对 S 个槽逐个计算 `条件 = (leaf_i 在路径上)`，用 `SelectCompose` 统一更新，保持电路形状固定。
- 本仓库有全部所需布尔/相等/选择原语（§3，VERIFIED），因此**固定形状 stash 重排在原语层面是 INFERRED 可行**。
- 但：重排产生的**新 stash 必须作为秘密份额带入下一步**——这一步被跨 step 状态通道阻断（见 §1 与 `state-binding-analysis.md`），是本组件的实际 BLOCKED 点。

## 5. Overflow 处理（UNKNOWN / BLOCKED）

| 问题 | 结论 | 标注 |
| --- | --- | --- |
| overflow 如何处理 | 标准方案：随机 eviction / 更大的 S / 触发重建。本仓库均无 | UNKNOWN |
| 概率界 | 论文与源码均未给 Path ORAM 参数下的 stash overflow 概率界 | UNKNOWN |
| rebuild/扩容是否泄露 | 若 rebuild 由公开计数触发，可能泄露访问规模；需设计成固定周期或秘密触发，均无实现 | UNKNOWN / BLOCKED |
| 是否泄露访问模式或数据规模 | 若 stash 满时执行不同分支（rebuild），而分支条件可被 observe，会泄露——**禁止**假定不会 | BLOCKED（无设计） |

**明确结论**：没有 overflow 处理方案，也没有可引用的概率界参数。若有人声称"stash 设为常数即可"，这是没有依据的——必须给出 ORAM 参数（N、B、Z、L、S）与安全参数下的 overflow 概率，而这些在本证据集中全为 UNKNOWN。

## 6. 与 VDORAM 威胁模型的交互（INFERRED）

- 恶意 prover 合谋（正确性 0 honest，见论文 p4）时，若 stash 状态由 provers 自己秘密持有并传入下一步，他们可用不一致的 stash 份额"重放"旧状态——除非 SNARK 约束 stash 转换（见 `state-binding-analysis.md`）。
- 诚实阈值 `t`（隐私）只要求至少 t 个 prover 诚实；stash 份额作为加法秘密共享，少于全部 prover 合谋时隐私可保（与论文 dishonest-majority 模型一致，p5）。
- 但 stash **大小 / overflow 事件**若在公开 trace 中可观察（例如影响 trace 行数），会破坏 p10 "memory accesses 数量 = 指令周期数"的隐私声明——需固定形状保证，见 §4。

## 7. 必答清单

| 必答项 | 结论 | 标注 |
| --- | --- | --- |
| bucket → stash 机制 | 本仓库无路径/桶/stash，无对应代码 | VERIFIED（缺失） |
| 固定容量 | 必须编译期固定 S；取值 UNKNOWN；禁写"足够大" | VERIFIED（约束）/ UNKNOWN（值） |
| 秘密比较/选择 | 具备（equality/less-than/select 等 gadget） | VERIFIED |
| 插入/删除/重排固定形状 | 原语层 INFERRED 可行；但新 stash 无跨 step 通道 | INFERRED / BLOCKED |
| overflow 处理与界 | 无方案、无界、无参数；rebuild 泄露风险未排除 | UNKNOWN / BLOCKED |

## 8. 证据索引

- `source-evidence/CompatCircuit__CompatCircuitProgramming__Gadgets/`：FieldEqualsGadget、FieldLessThanGadget、BitsLessThanGadget、BoolAndGadget、LowBitGadget、SelectComposeGadget（L16-44）、SelectComposeOtherwiseGadget（L16-67）。
- `source-evidence/...MpcExecutorFactory.cs` L45-67、`...MpcSharedStorage.cs` L47-55：session 短命、份额不跨 session。
- `source-snapshot/ZkProgramExecutor.cs` L70-74/L358-376：跨 step 状态仅 pc/registers/hash/memoryTrace。
- `source-snapshot/ZkVmExecutorCircuitBoardGenerator.cs` L990-1000：`out_trace_mem_addr` 非内存 op 用 NegOne。
- `paper/EXCERPTS.md` p8-9：Fig.5 / §IV-C / 线性扫描选择理由 / dummy 地址 `p−1`；p10：隐私声明"memory accesses 数量 = 总周期数"、MPC 轮数 O(T²)。
