# ABA-03-D3-02 / Phase 2：Fetch 事件序列关系的形式化草案

> 实验仓起点：`e93e882ab01dca5c44768f0be8a1a81a246c4318`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读形式化草案；所有关系表达式均为 `CONSTRUCTED`，**不是现有实现**，也不是安全证明。不实现电路、不重抓源码、不运行测试。
>
> 标签：`VERIFIED_SOURCE` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`（口径见 `b4_security_goal.md`）。
>
> 证据来源（只引用）：`b4_security_goal.md`；`../aba-03-d3-01/unified_statement.md` §2、`event_completeness.md` §1/§3；`../aba-03-d1/p2_binding_semantics.md` §1/§3 B1–B4；`../aba-03/source_trace_audit.md` A1–A3；`../aba-03-d2/context_and_replay.md` §1/§3/§4。

---

## 0. 抽象关系链

```
VM execution  E
    │  (实际产生，含 step 0)
    ▼
Expected Fetch events  E* = [e*_1 .. e*_{T-1}]        # 由执行语义确定，非 prover 可选
    │  (电路约束 / 可信锚点：当前缺失)
    ▼
Committed / proved Fetch events  P = [p_1 .. p_N]      # prover 提交，verifier 可见
    │  (verifier 检查关系 R1..R8)
    ▼
Verifier acceptance  Accept(P)  ⇒  P ≡ E*              # B4_GOAL
```

B4 的全部难点集中在中间两条箭头：**E 如何可信地映射到 E\***，以及 **P 如何被约束为恰等于 E\***。当前固定上游在这两条箭头上都只有部分源码事实，没有 verifier 可检查的约束。

---

## 1. 符号

```
T            真实执行总步数（含 step0）；须由 verifier 固定或可信证明，当前 UNKNOWN
E*           理想事件序列 [e*_i], i=1..T−1
e*_i         (step_i, type_i, addr_i, row_i)
P            已证明事件序列 [p_j], j=1..N
p_j          (step_j, type_j, addr_j, row_ref_j, proof_j)
step_j       事件携带的 step 索引（须电路内产生/约束，而非 prover 自由填）
type_j       ∈ {real, dummy}
addr_j       real→reg0；dummy→p−1
row_ref_j    事件引用的 VM trace row
proof_j      该事件的证明对象
N_all=T−1, N_real=M, N_dummy=T−1−M
```

---

## 2. 八项关系逐项形式化

每项给出：数学关系草案（全部 `CONSTRUCTED`）、所依赖输入、由谁生成、verifier 能检查什么、固定上游现状。

### R1 — Existence（每个 step≥1 是否恰好产生一个 Fetch 事件）

- **关系草案**：
  ```
  ∀ i ∈ [1, T−1] :  ∃! event e_i 由 step i 的执行产生
  ```
- **依赖输入**：执行轨迹、每步 Fetch 构造。
- **由谁生成**：VM 执行器（`ZkProgramExecutor.cs:205-228`）。
- **verifier 能检查**：当前不能；需“每步恰好一次”进入可验证 statement。
- **固定上游现状**：每 step≥1 无条件构造一次 Fetch、输入 `thisRegisters[0]`（`:205-228`、`:226`）→ `VERIFIED_SOURCE`（存在）；但“恰好一次”未被证明进 proof → `CONSTRUCTED`。

### R2 — Completeness（是否存在未纳入证明的 Fetch）

- **关系草案**：
  ```
  {step_j | p_j ∈ P} = [1, T−1]        # 已证明事件的 step 集合恰为全体 step
  ```
  即 P 覆盖每一个应有 Fetch 的 step（无遗漏）。
- **依赖输入**：P 的 step 集合、`T`。
- **由谁生成**：step_j 必须由电路约束产生。
- **verifier 能检查**：仅当能比对 step 集合与 verifier 固定的 `[1,T−1]`；当前无此关系。
- **固定上游现状**：无事件序列概念；Prove 只查 trace 内部（`source_trace_audit.md` A2）→ `BLOCKED` / `UNKNOWN`。

### R3 — Uniqueness（同一步是否可能出现多个被接受的 Fetch）

- **关系草案**：
  ```
  j ≠ k  ⇒  step_j ≠ step_k           # step 索引注入性（无重复）
  ```
- **依赖输入**：每个 p_j 的 step_j。
- **由谁生成**：电路约束的 step 索引。
- **verifier 能检查**：能检查提交的 step 列表是否两两不同（若 step_j 为公开值）。
- **固定上游现状**：宿主公开注入 step（`:393-395`），但无“每个 step 只提交一次事件”的约束 → `CONSTRUCTED` / `UNKNOWN`。

### R4 — Ordering（事件顺序是否与 VM step 顺序一致）

- **关系草案**：
  ```
  P 按 step_j 严格递增排列；或存在保序双射 π 使 p_{π(i)} ↔ e*_i
  ```
- **依赖输入**：step 序列、执行顺序真实性。
- **由谁生成**：顺序须由电路/statement 约束，而非 prover 排列。
- **verifier 能检查**：能检查公开 step 列表单调；不能检查该顺序等于真实执行顺序。
- **固定上游现状**：Prove 电路对 trace 排序检查（原始 L80-158：`source_trace_audit.md` A2）仅为 trace 内部一致性，不覆盖事件序列 → `VERIFIED_SOURCE`（trace 内部）+ `UNKNOWN`（事件顺序）。

### R5 — Step binding（事件是否绑定到正确的 VM step）

- **关系草案**：
  ```
  step_j = step of the VM execution that produced e*_j's semantics
  ```
  即事件的 step 不是 prover 自由填写，而与产生该事件的 VM 执行步一致。
- **依赖输入**：VM 电路的 step / pc / opcode 派生值。
- **由谁生成**：需电路内产生并绑定；当前 step 为宿主公开注入（`:393-395`），pc/opcode 为私有输入（`:134-136`、`:231-241`）。
- **verifier 能检查**：当前只能见到公开注入的 step 值，不能验证其与执行语义绑定。
- **固定上游现状**：无单一电路内 `(pc_i, opcode_i, addr_i)` 公开绑定（`source_trace_audit.md` A1 末行、`A4.2`）→ `UNKNOWN`。

### R6 — Type binding（real/dummy 是否由可信执行语义决定）

- **关系草案**：
  ```
  type_j = real  ⇔  is_mem_op_j = 1  ⇔  opcode_j ∈ {Load, Store}
  type_j = dummy ⇔  is_mem_op_j = 0
  ```
- **依赖输入**：opcode 表行选择位 → `is_mem_op`。
- **由谁生成**：VM 电路内 BoolOr(Load, Store)（`ZkVmExecutor...cs:968-976`）。
- **verifier 能检查**：仅当 `is_mem_op` 被绑定到公开 statement/承诺；Prove 电路当前明确忽略 `is_mem_op`（原始 L164-165，`source_trace_audit.md` A2）。
- **固定上游现状**：派生路径 `VERIFIED_SOURCE`；证明层区分缺失 → `CONSTRUCTED` / `UNKNOWN`。

### R7 — Trace binding（事件 trace row 是否为对应 step 的 VM trace row）

- **关系草案**：
  ```
  row_ref_j ↔ row_{step_j}
  real :  FieldEquals(row_ref_j.mem_addr, reg0_j)
  dummy:  FieldEquals(row_ref_j.mem_addr, p−1)      # 只约束 trace 地址哨兵
  ```
  dummy 的 lookup 地址仍为 `reg0`，**不**约束为 `p−1`，**不**公开/承诺 dummy 的 `reg0`。
- **依赖输入**：trace row 列、step↔row 映射、sentinel。
- **由谁生成**：需新增 step↔row 电路映射 + sentinel 约束。
- **verifier 能检查**：当前不能；Fetch 电路只按地址查 `mem_val`（`MemoryTraceFetch...cs:48-56,75-85`），不输出/强制 `trace_addr`。
- **固定上游现状**：VM 侧 `out_trace_mem_addr` 派生（`:989-997`，`VERIFIED_SOURCE`）；step↔row 对应与 dummy row 绑定 → `CONSTRUCTED` / `UNKNOWN`（`event_completeness.md` E7）。

### R8 — Termination binding（是否覆盖实际执行到最后一步）

- **关系草案**：
  ```
  T = actual_halt_step(E)        # 非 prover 自选的较短前缀
  max(step_j) = T−1              # 事件序列覆盖到最后一步
  halt/异常中止 在 statement 中有可信表达
  ```
- **依赖输入**：执行终止条件、`T` 上限。
- **由谁生成**：`T` 须 verifier 固定或由电路证明终止。
- **verifier 能检查**：当前无 verifier 可检查的 halt 边界。
- **固定上游现状**：`globalStepsNoMoreThan` 是执行器阈值（`ZkProgramExecutor.cs:114-116`），非电路约束；`global_step_counter` 宿主公开注入（`:393-395`）→ `UNKNOWN` / `CONSTRUCTED`（`event_completeness.md` E11）。

---

## 3. 关系汇总表

| 关系 | 草案 | 依赖输入 | 生成者 | verifier 可检查 | 上游现状 / 标签 |
| --- | --- | --- | --- | --- | --- |
| R1 Existence | `∀i≥1 ∃!e_i` | 执行轨迹、Fetch 构造 | 执行器 | 否（需进 statement） | 每步构造 `VERIFIED_SOURCE`；“恰好一次” `CONSTRUCTED` |
| R2 Completeness | step 集合 = `[1,T−1]` | P.step 集合、T | 电路约束 step | 否（需比对全集） | `BLOCKED` / `UNKNOWN` |
| R3 Uniqueness | `j≠k ⇒ step_j≠step_k` | 每个 step_j | 电路约束 step | 能查公开列表两两不同 | `CONSTRUCTED` / `UNKNOWN` |
| R4 Ordering | step 严格递增 / 保序双射 | step 序列、执行顺序 | statement 约束 | 能查单调，不能查等于真实顺序 | trace 内部 `VERIFIED_SOURCE`；事件 `UNKNOWN` |
| R5 Step binding | step_j = 产生该事件的 VM 步 | pc/opcode/step 派生 | 电路内产生 | 否 | `UNKNOWN` |
| R6 Type binding | type ⇔ is_mem_op ⇔ opcode | opcode 行选择位 | VM 电路 `VERIFIED_SOURCE` | 否（Prove 忽略 is_mem_op） | `CONSTRUCTED` / `UNKNOWN` |
| R7 Trace binding | `row_ref_j ↔ row_{step_j}` + sentinel | trace 列、step↔row、p−1 | 新增映射电路 | 否 | `CONSTRUCTED` / `UNKNOWN` |
| R8 Termination | `T = halt(E)`、`max step_j = T−1` | 终止条件、T | verifier 固定 / 电路证明 | 否 | `UNKNOWN` / `CONSTRUCTED` |

---

## 4. 为什么 `count(P)=T−1` 不够（形式化说明，含充分条件中的 R4）

设真实序列 `E*` 与提交序列 `P` 均含 `T−1` 个元素。构造反例：

```
E* = [e*_1, e*_2, e*_3, ..., e*_{T-1}]
P  = [e*_1, e*_2, e*_2, ..., e*_{T-1}]     # 省略 e*_3，复制 e*_2
```

则：

- `count(P) = T−1 = count(E*)`（`N_all` 通过）；
- real/dummy 计数也可能同时满足：若 `e*_2`、`e*_3` 同为 real，则 `N_real`、`N_dummy` 也通过；
- 但 `P ≠ E*`：`step=3` 的事件内容变成了 `e*_2` 的副本。

因此：

```
count(P)=N_all ∧ count(real)=N_real ∧ count(dummy)=N_dummy
    ⇏  P ≡ E*
```

三类计数相等（D3-01 E1a–E1d）只是**必要非充分**条件。

**第二个反例（重排，独立于上面的省略+复制）**：即使每个事件的内容都正确，只改变排列顺序也会破坏序列等价。设 `T=4`：

```
E* = [e1(step=1), e2(step=2), e3(step=3)]
P  = [e1(step=1), e3(step=3), e2(step=2)]
```

三个事件的 step、type、trace row 均正确，`T` 也可信：

- R2：`{step_j} = {1,2,3}` 覆盖成立；
- R3：`step_j` 两两不同，注入成立；
- R5/R6/R7：每个事件的 step、类型、trace row 都绑定到正确语义；
- R8：`max(step_j)=3=T−1`，终止边界成立。

但 `P[2]=e3`、`E*[2]=e2`，故 `P ≠ E*`（按序逐项比较）。这证明：**集合覆盖与注入性只能推出“每个 step 恰好出现一次”，不能推出“事件按 step 顺序排列”。** 必须把以下两类性质严格区分：

```
集合覆盖（R2+R3+可信 T）：每个 step 都出现恰好一次  —— 与排列顺序无关
序列顺序（R4）：            事件按可信 step 顺序递增排列 —— 逐项等价所必需
```

要把上述两个反例都排除，需要同时满足：

1. **R3 注入性** + **R2 覆盖性** + verifier 固定/可信锚定的 `T`：若每个 `step_j ∈ [1,T−1]`、两两不同、且数量为 `T−1`，则由鸽巢原理 `{step_j}=[1,T−1]`（每个 step 恰一次），副本因 step 冲突被拒，遗漏因 step 缺席被拒。此步只确定“集合”，不处理排列。
2. **R4 顺序性**（**充分条件必要项，非补充项**）：提交序列须按可信 step 顺序排列（或存在保序双射 `p_{π(i)} ↔ e*_i`），把上面第二个反例（集合正确但 step 2/3 交换）排除。R4 依赖 R5 的可信 step，不能只检查 prover 自报 step 字段的单调性。
3. **R5/R6/R7 内容绑定**：即使 step 集合与排列都正确，还需每个 `p_j` 的内容（type、addr、row）绑定到该 step 的真实语义，否则可把正确 step 上的 real 改标为 dummy（Type forgery）或引用错误 trace row（Trace substitution）。
4. **R8 终止绑定**：`T` 本身须是真实终止步，否则 prover 声明更短 `T′` 并只提交前缀即可自洽（Prefix truncation）。

**结论**：能区分“数量相同但内容不同”**且顺序一致**的序列（即满足完整 B4 目标 `P ≡ E*`）的最小充分关系集合是：

```
R2 ∧ R3 ∧ R4 ∧ R5 ∧ R6 ∧ R7 ∧ R8     （前提：T 由 verifier 固定或可信证明锚定）
```

其中 R2+R3+可信 `T` 给出“每个 step 恰好一次”、R4 给出“按 step 顺序排列”、R5/R6/R7 给出“内容与对应 step 绑定”、R8 给出“覆盖真实终止步”。**R4 是充分条件的必要组成部分，不能再降格为“顺序的补充表达”。** R1（每步 Fetch 存在性）可在上述条件下由“step 集合覆盖 = `[1,T−1]` + 每步恰一 Fetch 的执行语义”蕴含，但该蕴含依赖 R5 的可信 step 与执行语义前提；若这些前提不成立，R1 仍需独立显式约束，不得无解释地忽略。

当前这些关系全部为 `CONSTRUCTED` / `UNKNOWN` / `BLOCKED`，没有任何一项在固定上游被 verifier 检查。形式化草案成立，但不等同于可实现或已实现。
