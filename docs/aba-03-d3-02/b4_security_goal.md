# ABA-03-D3-02 / Phase 1：B4 事件完整性安全目标冻结

> 实验仓起点：`e93e882ab01dca5c44768f0be8a1a81a246c4318`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读设计与反例分析；不实现电路、不重抓上游源码、不解除任何 HOLD、不运行测试、不顺手处理 P1-A / VK / P2。
>
> 标签：`VERIFIED_SOURCE` = 固定 commit 源码事实；`CONSTRUCTED` = 本轮候选构造；`INFERRED` = 由源码事实或既有证据推导；`UNKNOWN` = 缺证据；`BLOCKED` = 当前接口无法支撑结论。
>
> 行号口径：沿用 `../aba-03/source_trace_audit.md` 与 `../aba-03-d1/p2_binding_semantics.md` 的冻结口径——`ZkProgramExecutor.cs` / `ZkVmExecutorCircuitBoardGenerator.cs` / `InstructionFetchCircuitBoardGenerator.cs` / `MemoryTraceFetchCircuitBoardGenerator.cs` 行号为固定 commit 原始行号；`MemoryTraceProveCircuitBoardGenerator.cs` 原始行号 = 快照行号 − 4。本轮**只引用**，不重抓源码。

---

## 0. 一句话结论

B4 要回答的不是“事件数量对不对”，而是：**验证者如何确认被提交并证明的 Fetch 事件序列，恰好等于那一次 VM 执行实际产生的全部 Fetch 事件（不多、不少、不重、不重排、类型与 step 均对应），而不是证明者从真实轨迹中挑选、遗漏、复制或重新标记后的子序列。**本文冻结这一目标、相关概念与四类证据边界；候选关系、攻击矩阵与构造比较分别见 `event_sequence_relation.md`、`completeness_attack_matrix.md`、`candidate_constructions.md`。

---

## 1. B4 安全目标的精确定义

### 1.1 理想参照物

定义一次固定执行 `E` 的**理想 Fetch 事件序列**：

```
E* = [e*_1, e*_2, ..., e*_{T-1}]
e*_i = (step_i, type_i, addr_i, row_i)
```

其中 `i` 从 1 到 `T−1`（step 0 不在序列内）；`type_i ∈ {real, dummy}` 由该步 opcode 决定；`addr_i` 为 real 的 `reg0` 或 dummy 的 `p−1`；`row_i` 为该步的 VM trace 行。

定义证明者实际提交并被 verifier 接受的**已证明事件序列**：

```
P = [p_1, p_2, ..., p_N]
p_j = (step_j, type_j, addr_j, row_j, proof_j)
```

### 1.2 安全目标（B4）

verifier 接受 `P` 当且仅当 `P` 与 `E*` 在**内容、数量、顺序、类型、step、trace row、终止边界**上逐项一致：

```
B4_GOAL :  Accept(P)  ⇒  P ≡ E*      （事件序列的逐项等价）
```

其中 `P ≡ E*` 至少要求：

1. `N = N_all = T−1`（数量）；
2. 存在保序双射 `π : [1,T−1] → [1,N]`，使 `p_{π(i)}` 与 `e*_i` 在 step、type、addr(语义)、row 上一致（顺序 + 内容 + 唯一）；
3. `T` 是本次真实执行的实际终止步，`P` 覆盖到该步而非更短前缀（终止）。

**关键判别要求（本轮验收核心）**：一个把某个 `e*_j` 换成另一个 `e*_k` 副本的序列 `P`，与 `E*` **数量相同**（均为 `T−1`）但**内容不同**。任何只检查 `count(P)=T−1` 的关系都无法区分二者；B4 关系必须能区分“数量相同但内容不同”的序列。此点贯穿 `event_sequence_relation.md` 与 `completeness_attack_matrix.md`。

### 1.3 什么不是 B4（避免目标漂移）

- **不是**单步地址相等（B1）：`fetch=reg0=trace_addr` 只覆盖单步，不覆盖整条序列（`p2_binding_semantics.md` §3 B4）。
- **不是**承诺同一性（C2）：两电路对同一 `com` 只保证该步地址同一性，不保证无遗漏/无重排（`context_and_replay.md` §4）。
- **不是**程序身份（P1-A）或 VK 锚定：二者是 verifier 侧前置，与事件序列完整性正交（`verifier_independence.md` §4）。
- **不是**跨执行防重放（context/replay）：那是另一个独立问题（`context_and_replay.md` §3）。
- **不是**已实现性质：本轮所有关系均为候选分析，成功形式化也不等于现有实现满足 B4。

---

## 2. 概念冻结（沿用既有语义，本轮不改）

### 2.1 计数语义（`../aba-03-d3-01/unified_statement.md` §2.1/§4、`event_completeness.md` §1，C1 已勘误）

```
T               = VM 总步数，包含 step 0
N_all           = T − 1              # 总 Fetch 事件数（step0 无 Fetch）
N_real          = M                  # 真实 Load/Store 事件数
N_dummy         = T − 1 − M          # dummy Fetch 事件数（不是总数）
N_all           = N_real + N_dummy
```

`T−1−M` 是 **dummy 数，不是总数**。step 0 有 trace row，但无 Fetch、无承诺事件，不进入 Fetch 事件序列。

### 2.2 三类事件语义（`p2_binding_semantics.md` §0/§1/§3，冻结）

| 类别 | Fetch lookup 地址 | memory trace 地址 | 是否入事件序列 |
| --- | --- | --- | --- |
| 真实 Load/Store（`is_mem_op=1`） | `reg0` | `reg0` | 是（real 事件） |
| Dummy Fetch（`is_mem_op=0`，step≥1） | `reg0` | `p−1` | 是（dummy 事件） |
| step 0 | 不执行 Fetch | 有 trace row（`p−1`） | **否** |

- 真实 Fetch：`fetch_lookup_addr = reg0`，`trace_addr = reg0`（`= reg0` 与范围检查为候选约束 `CONSTRUCTED`；地址源同源为 `VERIFIED_SOURCE`）。
- Dummy Fetch：`fetch_lookup_addr = reg0`，`trace_addr = p−1`；**不得**把 lookup 地址约束为 `p−1`，**不得**因此公开或承诺 dummy 的 `reg0`。
- step 0：不构造 Fetch（`ZkProgramExecutor.cs:201-203`），仍 append 一行 trace（`:389-402`），该行 `is_mem_op=0`、地址 `p−1`、值 0（`INFERRED`，ABA-03-C1 冻结）。

### 2.3 九个关键概念与当前可见性

| 概念 | 固定 commit 中的证据 | 当前可见性 / 标签 |
| --- | --- | --- |
| VM 总步数 `T` | `global_step_counter` 宿主公开注入 trace（`ZkProgramExecutor.cs:393-395`）；`globalStepsNoMoreThan` 是执行器阈值（`:114-116`），非电路约束 | 宿主值可见；真实终止步 `UNKNOWN` |
| step 0 | 不构造 Fetch（`:201-203`）；仍 append trace（`:389-402`） | 源码事实 `VERIFIED_SOURCE` |
| step≥1 Fetch 行为 | else 分支每步构造 Fetch，输入 `thisRegisters[0]`（`:205-228`，`:226`） | `VERIFIED_SOURCE`；每步“恰好一次”进 proof 为 `CONSTRUCTED` |
| real Fetch | `is_mem_op=Load OR Store` 由 opcode 派生（`ZkVmExecutor...cs:968-976`） | 派生 `VERIFIED_SOURCE`，私有输出；公开绑定 `CONSTRUCTED` |
| dummy Fetch | 非内存步 lookup 仍为 reg0（`:226`），trace 地址 `p−1`（`:941-943,989-997`） | `VERIFIED_SOURCE` |
| VM trace row | 由执行器 append（`ZkProgramExecutor.cs:389-402`）；Prove 电路检查排序与同址值不变（原始 L80-158 / L167-193） | 内部一致性 `VERIFIED_SOURCE`；step↔row 绑定 `UNKNOWN` |
| Fetch lookup 地址 | `MemoryTraceFetch...cs:41-43` 私有输入，`:52` 逐行 `FieldEquals` 作查找键，`:75-85` 只输出 `mem_val` | 私有 `VERIFIED_SOURCE`；Fetch 不输出/强制 trace_addr |
| memory trace 地址 | `out_trace_mem_addr` 电路派生（`ZkVmExecutor...cs:989-997`），私有输出 | `VERIFIED_SOURCE`；verifier 不可见明文 |
| Fetch 事件承诺/证明记录 | 固定 commit 无事件序列承诺概念；Prove 电路不接收 pc/opcode（原始 L164-165），忽略 `is_mem_op` | `CONSTRUCTED` / 缺失 |

---

## 3. 四类证据边界（本轮统一口径）

| 类别 | 含义 | 本轮中的典型项 |
| --- | --- | --- |
| 已由固定上游源码支持 | 源码事实，不等于 verifier 可验证绑定 | step0 无 Fetch、每 step≥1 构造一次 Fetch、opcode 派生 `is_mem_op`、dummy trace 地址 `p−1`、Prove 内部排序/同址值检查、跨电路宿主哈希 `throw` |
| D3-01 已提出的候选关系 | 上一阶段写出但未经实现验证 | `N_all/T−1` 计数、event_type 公开绑定、step↔trace row 映射、B4 count/order/halt 约束 |
| 本轮新提出的构造 | 本文与 `event_sequence_relation.md` / `candidate_constructions.md` 中的候选草案 | step-index 注入性 + 保序双射判据、事件累积承诺、VM/Fetch 电路内直接绑定、递归组合 |
| 尚未证明的性质 | 缺源码或实验支持 | 真实终止步 `T` 的可信锚定、step index 的电路内可信产生、事件内容与 step 的绑定、event_type 证明层区分、任何方案的具体成本 |

---

## 4. 本轮不声称的事

- 不声称 B4 已在固定上游实现：所有完整性/顺序/终止关系均为 `CONSTRUCTED` 或 `UNKNOWN`。
- 不声称 `count(P)=T−1` 足以证明完整性：数量相等无法区分省略 + 复制（§1.2）。
- 不声称宿主哈希 `throw` / 多重集比对（`ZkProgramExecutor.cs:404-408,567-583`）是 proof soundness 或 verifier 检查（`source_trace_audit.md` A2/E12）。
- 不声称本轮提出的哈希链或 step-index 方案已解决 B4：它们只是候选构造，缺可信锚点与实现证据。
- 不改变 P1-A / VK / P2 的既有结论，不改变总决策 `HOLD_INSUFFICIENT_EVIDENCE`。

本轮目标止于：**把 B4 冻结成一个明确的验证关系问题，并给出能区分“数量相同、内容不同”序列的判据**；是否可实现、是否安全，另轮评估。
