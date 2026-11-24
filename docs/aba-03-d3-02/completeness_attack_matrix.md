# ABA-03-D3-02 / Phase 3：B4 事件完整性攻击矩阵（反例分析）

> 实验仓起点：`e93e882ab01dca5c44768f0be8a1a81a246c4318`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读反例分析。**以下均为候选关系下的可能性分析，不是已复现的攻击，不是已证明的漏洞。**“是否存在通过验证的可能”一栏只在明确写出前提时才给出判断；缺证据处一律 `UNKNOWN`。
>
> 标签：`VERIFIED_SOURCE` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 证据来源：`b4_security_goal.md` §1、`event_sequence_relation.md` §2；`../aba-03-d1/p2_binding_semantics.md` §3 B4；`../aba-03-d2/context_and_replay.md` §3/§4；`../aba-03/source_trace_audit.md` A2。

---

## 0. 分析方法与前提

- **理想序列** `E*=[e*_1..e*_{T-1}]`，提交序列 `P=[p_1..p_N]`（`b4_security_goal.md` §1）。
- **当前候选关系**指 D3-01 的 `N_all=T−1`、`N_real=M`、`N_dummy=T−1−M`、加和式，以及 `event_sequence_relation.md` 的 R1–R8 草案；其中**计数关系为 `CONSTRUCTED`，R1–R8 均未在固定上游实现**。
- **“当前能否通过”**分两层回答：
  1. **仅按计数关系**（D3-01 已写出的候选）是否能通过；
  2. **按完整候选关系 R1–R8**（若全部实现且 `T` 可信锚定）是否能通过。
- 任何“通过”判断都不等于在真实部署中已发生；当前无独立 verifier、固定 VK 或事件序列 statement（`verifier_independence.md` §1），真实验证路径尚不存在，`BLOCKED` 是主基调。

---

## 1. 九类攻击逐项分析

### A1. Omission（省略一个真实或 dummy Fetch）

- **攻击者修改什么**：从 P 中删除 `e*_j`，并补一个其他元素使 `N` 仍等于 `T−1`（见 A2 复制），或直接提交 `N=T−2`。
- **当前候选关系检查什么**：仅检查 `count(P)`；若补了元素则计数通过。
- **通过可能**：
  - 若直接少提交（`N<T−1`）：计数关系 `count(P)=N_all` 拒绝（`CONSTRUCTED` 检查）；但固定上游无该计数约束 → 实际 `BLOCKED`。
  - 若省略 + 复制凑数：计数全部通过；只有在 `R2 覆盖性`（step 集合 = `[1,T−1]`）成立时，`step_j` 缺席才可检出 → 当前 `BLOCKED`/`UNKNOWN`。
- **缺什么证据**：verifier 可检查的 step 集合覆盖关系（R2）、可信的 `T`、`T` 与 step 集合的公开 statement 绑定。

### A2. Duplication（复制另一个 step 的 Fetch 事件）

- **攻击者修改什么**：把 `e*_k` 复制到本应是 `e*_j` 的位置（k≠j），内容相同但 step 标签视实现而定。
- **当前候选关系检查什么**：计数、real/dummy 分类计数（若 `e*_j`、`e*_k` 同类型则也通过）。
- **通过可能**：
  - 仅计数：通过（这是“数量相同但内容不同”的典型，`b4_security_goal.md` §1.2 反例）。
  - 完整 R1–R8：若复制品携带原 step `k`，则 `step_k` 出现两次 → R3 注入性拒绝；若复制品被改成 step `j`，则需 R5/R7 内容绑定检出（内容属于 step k 却标 step j）→ 依赖 R5/R7，`UNKNOWN`。
- **缺什么证据**：step 索引由电路约束产生（R5）、step↔row 与内容绑定（R7）、事件内容与 step 的一致性证明。

### A3. Reordering（调换两个 Fetch 事件顺序）

- **攻击者修改什么**：提交 `[..., e*_k, ..., e*_j, ...]` 而真实为 `[..., e*_j, ..., e*_k, ...]`（j<k）。
- **当前候选关系检查什么**：计数与分类计数均通过；无顺序检查。
- **通过可能**：
  - 仅计数：通过。
  - 完整 R1–R8：R4 要求 step 单调 → 若事件携带 step 且 verifier 检查单调，则拒绝；但“单调”只保证顺序一致于 step 值，若 step 值本身可伪造则仍需 R5 → 依赖 R4+R5，`UNKNOWN`。
- **缺什么证据**：step 真实顺序的电路证明（R4/R5）；注意 Prove 电路的 trace 排序检查（原始 L80-158）只覆盖 trace 内部，不覆盖事件序列（`source_trace_audit.md` A2）。

### A4. Step substitution（将事件绑定到错误 step）

- **攻击者修改什么**：把某个合法事件 `e*_j` 的 step 字段改成另一个值 `j′`。
- **当前候选关系检查什么**：若 step 为公开注入值（`:393-395`），计数与分类不检查 step 语义。
- **通过可能**：
  - 仅计数：通过。
  - 完整 R1–R8：只要 step 字段由 prover 自由写，R3/R4/R5 全部可被绕过（可重排 step 使其成为 `[1,T−1]` 的双射）；必须 step 由电路约束产生 → 当前 `UNKNOWN`。
- **缺什么证据**：step 索引的电路内可信产生（R5），而非宿主公开注入（`ZkProgramExecutor.cs:393-395`）；step 与 pc/opcode/addr 的同电路绑定（`source_trace_audit.md` A1 末行）。

### A5. Type forgery（real 改 dummy 或反之）

- **攻击者修改什么**：把真实 Load/Store 的 `type` 声明为 dummy，或把 dummy 声明为 real。
- **当前候选关系检查什么**：`N_real`、`N_dummy` 计数；若同时交换一对 real/dummy，则两类计数均不变。
- **通过可能**：
  - 仅计数：通过（一增一减，`N_real`/`N_dummy` 不变）。
  - 完整 R1–R8：R6 要求 `type ⇔ is_mem_op ⇔ opcode`；若 `is_mem_op` 绑定到公开 statement，且由 opcode 派生（`ZkVmExecutor...cs:968-976`），则可检出 → 但 Prove 电路当前明确忽略 `is_mem_op`（原始 L164-165）→ `UNKNOWN`。
- **缺什么证据**：`is_mem_op` 的证明层公开绑定（R6）；`context_and_replay.md` §1 已指出 event_type 若由 prover 声明即可伪造。

### A6. Trace substitution（使用另一个 step 的 trace row）

- **攻击者修改什么**：事件引用 `row_{k}` 而声称属于 step j（k≠j）。
- **当前候选关系检查什么**：计数与分类不检查 row 引用。
- **通过可能**：
  - 仅计数：通过。
  - 完整 R1–R8：R7 要求 `row_ref_j ↔ row_{step_j}` 且地址按 real/dummy 分支约束；当前 Fetch 电路只按 `mem_addr` 查 `mem_val`（`MemoryTraceFetch...cs:48-56,75-85`），不输出/强制 trace_addr，step↔row 未证 → `UNKNOWN`/`BLOCKED`。
- **缺什么证据**：step↔row 电路映射 + real/dummy 地址约束（`event_completeness.md` E7）；dummy 只约束 `FieldEquals(row.mem_addr, p−1)`，不约束 lookup。

### A7. Prefix truncation（只证明执行前缀）

- **攻击者修改什么**：真实执行到 `T`，但只提交 `[e*_1..e*_{T′-1}]`（`T′<T`），并声明 `T=T′`。
- **当前候选关系检查什么**：计数 `count(P)=T′−1=T−1`（按其声明的 `T′`）自洽；若 `T` 由 prover 声明则通过。
- **通过可能**：
  - 仅计数（prover 自报 T）：通过。
  - 完整 R1–R8：R8 要求 `T=actual_halt_step(E)` 且由 verifier 固定/电路证明；当前 `globalStepsNoMoreThan` 是执行器阈值（`:114-116`），`global_step_counter` 宿主注入（`:393-395`），无 verifier 可检查 halt 边界 → `UNKNOWN`。
- **缺什么证据**：真实终止步的可信锚定（R8）；verifier 固定的 halt 条件或执行终止证明（`event_completeness.md` E11）。这是 count 关系**根本无法覆盖**的一类（计数只对声明的 T 自洽）。

### A8. Extra event（插入不存在的 Fetch）

- **攻击者修改什么**：插入一个不对应任何真实 step 的事件 `p`（伪造 step 或复用已有内容）。
- **当前候选关系检查什么**：计数；若不删除其他元素则 `N>T−1` 被计数拒绝。
- **通过可能**：
  - 只插入：`count(P)=T` 破坏 `N_all` → 计数关系拒绝（`CONSTRUCTED`）；固定上游无该约束 → 实际 `BLOCKED`。
  - 插入 + 省略凑数：退化为 A1+A2 组合，计数通过，需 R2/R3/R5 检出 → `UNKNOWN`。
- **缺什么证据**：同 A1/A2——step 集合覆盖与注入性、内容与 step 绑定。

### A9. Sentinel confusion（利用 p−1 与真实地址的语义差异）

- **攻击者修改什么**：利用 dummy `trace_addr=p−1` 与 real `reg0` 的差异做文章，例如：(a) 把 real 的 trace 地址伪造成 `p−1` 以冒充 dummy；(b) 让某 real 地址恰等于 `(p−1) mod 2^L` 的低位截断，绕过小范围比较；(c) 把 dummy 的 lookup `reg0` 误当 `p−1` 处理。
- **当前候选关系检查什么**：R6（type binding）、R7（dummy 只约束 trace row `p−1`）、以及 real 的地址范围检查 `0≤addr<n`。
- **通过可能**：
  - 若 real 范围检查用低位截断：ABA-03-C1 已勘误——`p` 奇数、`p−1` 偶，低 L 位不可能全 1；风险是截断值 `(p−1) mod 2^L` 可能很小却通过小范围比较 → 必须用完整域元素相等 + 逐位 Boolean + 位比较（`p2_binding_semantics.md` B1）。若实现只用截断，存在绕过可能 → `CONSTRUCTED`（防御已定义，实现缺失）。
  - 若 dummy 的 lookup 被错误约束为 `p−1`：与冻结语义冲突（`p2_binding_semantics.md` §0），本轮明确禁止；正确做法是 dummy lookup 仍为 `reg0`、只承诺/约束 trace 地址 `p−1`，不公开/承诺 `reg0`。
  - `p−1` 作为 `F_p` 元素与真实地址域 `[0,n−1]` 的关系：需 `n≤p−1` 边界（当前无，`source_trace_audit.md` A3）→ `UNKNOWN`。
- **缺什么证据**：real 地址完整字段范围约束（`n≤Nmax`、`n<p−1`、`0≤addr<n`）、event_type 证明层绑定、dummy 正确语义的电路约束。

---

## 2. 攻击矩阵汇总

| 攻击 | 仅计数关系能否通过 | 完整 R1–R8（若实现且 T 可信）能否通过 | 决定性关系 | 判定 |
| --- | --- | --- | --- | --- |
| A1 Omission（省略+凑数） | 通过 | 拒绝（step 缺席） | R2 覆盖 | 缺证据 `UNKNOWN`/`BLOCKED` |
| A2 Duplication | 通过 | step 冲突→R3 拒绝；改 step 需 R5/R7 | R3+R5+R7 | 缺证据 `UNKNOWN` |
| A3 Reordering | 通过 | R4 单调 + R5 | R4+R5 | 缺证据 `UNKNOWN` |
| A4 Step substitution | 通过 | 仅 step 可伪造时绕过；需电路约束 step | R5 | 缺证据 `UNKNOWN` |
| A5 Type forgery | 通过（成对换） | R6（is_mem_op 绑定） | R6 | 缺证据 `UNKNOWN` |
| A6 Trace substitution | 通过 | R7（step↔row + sentinel） | R7 | 缺证据 `UNKNOWN`/`BLOCKED` |
| A7 Prefix truncation | 通过（prover 自报 T） | R8（真实终止步 verifier 固定） | R8 | 缺证据 `UNKNOWN` |
| A8 Extra event（插入+凑数） | 通过 | R2/R3/R5 | R2+R3+R5 | 缺证据 `UNKNOWN` |
| A9 Sentinel confusion | 视实现 | real 完整范围 + R6/R7 | 范围约束+R6/R7 | 防御已定义，实现缺失 |

---

## 3. 攻击矩阵结论

1. **九类攻击在“仅计数关系”下全部可能通过**（直接少/多提交的子情形会被计数拒绝，但省略+复制、成对换类型、自报 T 等变体计数均通过）。这再次证明 `count(P)=T−1` 与三类计数相等都**不是**完整性证明。
2. **在完整 R1–R8 假设下**，理论上每类攻击都有对应的“决定性关系”（R2 覆盖、R3 注入、**R4 顺序**、R5 step 绑定、R6 类型、R7 trace、R8 终止）。要排除**全部九类攻击**（即满足完整 B4 `P ≡ E*` 的逐项顺序等价），充分关系集合必须是 `R2 ∧ R3 ∧ R4 ∧ R5 ∧ R6 ∧ R7 ∧ R8`（前提 `T` 可信锚定）——其中 R4 不可省：R2+R3 只保证“每个 step 恰一次”，把 step 2 与 step 3 的事件交换位置仍可通过 R2/R3/R5/R6/R7/R8（见 `event_sequence_relation.md` §4 第二反例），只有 R4 能检出这种重排。但这些关系当前**全部未在固定上游实现**，因此本矩阵给出的是**候选防御映射，不是已验证的抵御能力**。
3. **A7 Prefix truncation 是计数关系的结构性盲区**：计数只对 prover 声明的 `T` 自洽，必须另行锚定真实终止步。任何不处理 R8 的方案都不能声称 B4。
4. **“数量相同但内容不同”的核心判别**（A1/A2/A5）依赖 `R2+R3+R5+R6+R7` 联合，而非任一单项——这是针对省略/复制/类型伪造的**局部**判别集合。它不含 A3 重排：step 值全部正确但顺序交换时，该局部集合仍通过；完整序列等价（含顺序）必须在它之上再加入 `R4`，即 `R2+R3+R4+R5+R6+R7+R8`。`event_sequence_relation.md` §4 给出鸽巢原理下的集合覆盖论证与两个反例（省略+复制、纯重排）。
5. **所有判断均按可能性分析给出**，没有一项写成“已复现攻击”或“已证明安全”；固定 commit 无独立 verifier 与事件序列 statement，真实攻击面尚无法测量 → 整体 `BLOCKED`。
