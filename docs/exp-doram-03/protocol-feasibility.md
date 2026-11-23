# protocol-feasibility.md — EXP-DORAM-03：ORAM 状态转换的协议级可构造性验证

> 日期：2026-11-23 · 起点 commit `9c92279` · 基线 VDORAM artifact `10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 定位：**纯纸面协议构造 + 复杂度/泄露面分析**。不实现 Path ORAM、不改上游、不跑 benchmark、不重做 EXP-DORAM-01/R1、**不重新审计回调与 verifier**（沿用 `docs/exp-doram-02-r1/verifier-chain-check.md` 结论）。
> 标记口径：**VERIFIED** 源码/论文直接证据 · **CONSTRUCTED** 已给出完整可检查的协议构造 · **INFERRED** 有依据未证明 · **UNKNOWN** 无法判断 · **BLOCKED** 明确障碍。
> 文献证据：`source-evidence/literature-notes.md`（带 URL/访问日期）；论文原文：`../exp-doram-02/paper/EXCERPTS.md`。

---

## 0. 判定摘要（先给结论）

**最终判定：HOLD。** 不是 GO_TO_MINIMAL_PROTOTYPE，也不是 NO_GO。

- **不 NO_GO**：任务包 §9 的 NO_GO 需要"目标威胁模型下明确不可绕过的矛盾"。本轮的**关键反证**是 Keller–Scholl 2014（VERIFIED，文献 L2）：Path ORAM 可在 **SPDZ（dishonest majority、t = m−1、任意 m 方）** 中以 polylog overhead 用 secret index 实现。这**直接推翻**了 EXP-DORAM-02 中"ORAM 必然限 2–3 方"的隐含前提——任意方 MPC-ORAM 是存在的。因此"参与方数量冲突"不能再作为整体 NO_GO 依据，只能针对**直接移植现有 3-party DORAM**。
- **不 GO**：两个方案的**端到端**构造都有一处无法从现有证据跨过的核心缺口——**覆盖完整 ORAM 状态（Tree + PositionMap + Stash）的承诺，其每步更新与 verifier 强制串联能否做到 sublinear in N，同时本身是 collaborative zkSNARK 可证的 R1CS 关系**。朴素承诺每步 O(N·Z) 约束会与 ORAM 访问的 polylog 优势相互抵消；且本仓库此前已核实 verifier 侧无跨电路串联（`verifier-chain-check.md` §3–4）。
- **唯一最关键阻断问题**（见 §9）：能否构造一组承诺 `C_i`，使 `C_{i+1}` 对完整 ORAM 状态的**每步更新、R1CS 内验证、以及 verifier 的 `C_{i+1}^{out}=C_i^{in}` 强制串联三者同时为 o(N)（sublinear）**，且不牺牲"地址/叶子/操作类型对 <t 合谋方隐藏"？——这是"ORAM 访问 polylog"能否兑现为"整条状态机优于 O(T²) 且不弱于 VDORAM 隐私/正确性"的**必要条件**，现有证据尚未解决（UNKNOWN/BLOCKED on current artifact）。

**两个必须守住的区分（本轮反复强调）：**
1. **SNARK 证明状态转换正确 ≠ MPC 执行隐藏了访问模式。** 前者是 correctness（全体 prover 合谋下仍可由 verifier 拒绝非法转换）；后者是 privacy（仅 <t 合谋下成立）。必须分别构造，**不能用一个替代另一个**（§2）。
2. **承诺链绑定连续性 ≠ 证明转换合法性。** `C_i→C_{i+1}` 的串联只保证"下一步用的是上一步承诺的状态"，不保证 `S_{i+1}` 是合法 ORAM 转换的结果；后者必须由转换电路自身的 R1CS 约束表达（§5.3，沿用 R1 已收紧结论）。

---

## 1. 目标与固定前提

### 1.1 五问（逐条，不合并）

| # | 问题 | 本轮结论 | 标记 |
| --- | --- | --- | --- |
| Q1 | 访问地址和路径对满足隐私阈值的参与方集合隐藏？ | 方案 A/B 在"≥t 诚实"下可构造（依赖 Keller–Scholl active-secure secret index）；**全体合谋下 privacy 不适用**（VDORAM 威胁模型本身如此） | CONSTRUCTED + INFERRED |
| Q2 | 每步状态转换可表达为 R1CS？ | 可表达——ORAM 八步全是算术/比较/选择，C→R1CS 无类型障碍；但承诺覆盖全状态的约束规模是核心成本 | CONSTRUCTED（转化可行）/ UNKNOWN（规模可接受） |
| Q3 | 每步公开承诺可被 verifier 强制串联？ | **构造上给出规则**（§5.5 四条）；但**本 artifact 未实现**，外部证明仓库 UNKNOWN | CONSTRUCTED（规则）/ BLOCKED（当前 artifact） |
| Q4 | 保留任意参与方目标？ | **方案 B 用 Keller–Scholl SPDZ 保住任意方**；方案 A 若用 3-party DORAM 则违约（明确标注）；Path ORAM 的"参与方限制"是**实现选择**不是本质 | CONSTRUCTED + VERIFIED(文献) |
| Q5 | ORAM 开销有机会优于 O(T²) 累计扫描？ | 有机会但**未被证明**：访问复杂度可 polylog，但每步全状态承诺 O(N) 可能抵消；在 N≪T 时 O(TN) 优于 O(T²)，N~T 时相当或更差 | INFERRED / UNKNOWN |

### 1.2 固定前提（全部沿用，不擅自改变）

| 前提 | 内容 | 来源/标记 |
| --- | --- | --- |
| P1 基线 | VDORAM artifact `10c90d3` 的执行/证明模型 | VERIFIED |
| P2 Fetch 语义 | 每个非初始 step 执行一次逻辑 Fetch；step 0 用 zeroShare 不执行 | VERIFIED（`ZkProgramExecutor.cs` L205-236，EXP-DORAM-01-R1） |
| P3 地址语义分离 | `fetch_address = thisRegisters[0]`（L230）；Store/Load 的 `trace_address` 为实际地址，非内存操作为 NegOne（L990-1000） | VERIFIED |
| P4 地址域 | 固定密集 `[0,n−1]`，**不扩展为动态 KV** | VERIFIED（论文 p8 Fig.5） |
| P5 历史语义 | append-only HistoricalLog + `FHistoricalKV.Export()` 保留全部 (addr,val,aux) 供公开证明 | VERIFIED（论文 p8-9） |
| P6 物理状态可变 | ORAM 读取/重排/驱逐可改变物理状态，即使逻辑内存不变 | 任务包约定 |
| P7 correctness | prover 可**全部合谋**，错误结果仍须被公开验证拒绝（0 honest） | VERIFIED（论文 p4） |
| P8 privacy | 仅 ≥t（如 t=1）诚实参与方下讨论；dishonest majority `t=m−1`、additive shares、mixed domain Fp+Z2ⁿ | VERIFIED（论文 p4-5） |
| P9 禁止等价 | 普通秘密分享 / 单纯 R1CS 正确性 ≠ ORAM 隐私 | 任务包约定 |

### 1.3 符号

`N` 逻辑容量（=`n`）· `Z` bucket 容量（block 数）· `L=⌈log₂N⌉` 树高 · `S` stash 容量 · `B` block 位宽 · `T` 执行步数 · `m` 参与方数 · `t` 隐私阈值 · `κ` 安全参数 · `C_i` 第 i 步 ORAM 状态承诺 · `[·]` 秘密共享值。

---

## 2. 正确性 / 隐私双轨设计（本轮核心纪律）

VDORAM 威胁模型（P7/P8）把两个属性**分离**，ORAM 状态机必须双轨构造：

```
轨道 A — PRIVACY（协议问题，MPC 层）
  目标：fetch_address、物理叶子、访问路径、操作类型 对 < t 合谋方隐藏
  机制：dishonest-majority MPC（SPDZ/compatible-circuit）中执行 ORAM 转换；
        secret index 访问 pos map / stash / tree；dummy 操作固定形状
  保证：t-zero-knowledge / distributed obliviousness（<t 合谋）
  失效：全体合谋 → privacy 不适用（论文原设定，不声称全体合谋仍隐私）
  证据：Keller–Scholl 2014 = 此轨道的存在性证明（VERIFIED，L2）

轨道 B — CORRECTNESS（证明问题，SNARK 层）
  目标：即使全体 prover 合谋，非法的 S_i→S_{i+1} 仍被 verifier 拒绝
  机制：每步转换表达为 R_i(C_i,C_{i+1},step_i; witness_i)，协作 SNARK 出证明；
        verifier 强制承诺串联 + step 连续 + 初始/最终锚点
  保证：knowledge soundness（全体合谋无法伪造有效证明）
  要求：转换"合法"必须由 R_i 的 R1CS 约束表达，不是只加一个独立承诺

★ 两轨不可互换：轨道 B 成立（转换可证）不蕴含轨道 A（访问隐藏）；
  轨道 A 成立（MPC 隐藏访问）不蕴含轨道 B（恶意 prover 不作弊）。
  这正是"SNARK 正确 ≠ MPC 隐私"的精确含义。
```

**与 VDORAM 现有设计的一致性（VERIFIED/INFERRED）**：论文 p4-5 描述的正是此双轨——MPC 计算 intermediate values 作 secret shares → collaborative zkSNARK 用这些 shares 作 witness（L5/L6）。本构造沿用该范式，新增的是"把 ORAM 状态转换纳入 witness 关系 + 承诺串联"。

---

## 3. 候选方案 A：秘密分享状态上的 Path ORAM

### 3.1 状态定义与完整编码（CONSTRUCTED）

```
S_i = (Tree_i, PositionMap_i, Stash_i, metadata_i)，全部为 additive shares [·]

Tree_i        : 完全二叉树，N 个叶子，深度 L；每个 bucket 恰 Z 个 block slot；
                每个 slot = ([addr], [val], [leaf], [valid])
                —— total = (2^{L+1}−1)·Z slots；固定形状，dummy slot 用 valid=0 填充
PositionMap_i : N 项数组 pos[0..N−1]，pos[a] = [leaf_a]（a∈[0,n−1]）
Stash_i       : 固定 R 个 slot，每 slot = ([addr],[val],[leaf],[valid])；
                R 取 Path ORAM 统计界对应值（Z=4: R≈89 达 2⁻⁸⁰；Z=5: R≈100 达 128-bit）
metadata_i    : [globalStepCounter]、历史日志指针/长度、以及（可选）状态承诺 salt
```

**正式编码**：`Encode(S_i)` = 按固定顺序把上述所有 field 元素拼成向量；`C_i = H(Encode(S_i))`，`H` 为域内 arithmetic-friendly hash（如 MiMC/Poseidon，VDORAM 已有 `MimcHashGadget`，VERIFIED 源码快照）。**承诺覆盖 Tree/PositionMap/Stash/metadata 全部字段**——满足任务包 §4.5。

### 3.2 每步状态转换伪代码（CONSTRUCTED，8 步，逐步标注 MPC 操作与泄露面）

```
ORAM_Access_A(S_i, [a], op, [v])  →  (S_{i+1}, [result]):
  输入: [a] = fetch_address（reg0 份额，每步都给，含 dummy Fetch）
        op ∈ {LOAD, STORE, NOOP} —— 在 B 方案中作为秘密 [op] 处理（见 §3.5）
  步骤:
  (1) POS-LOOKUP   [leaf] ← SecretIndex(PositionMap_i, [a])
                   // 秘密索引：朴素=对 N 项做 FieldEquals([a],j)·pos[j] 求和 → O(N) 乘法
                   //   或递归 ORAM（Keller–Scholl）→ polylog，但需递归状态也跨步承诺
                   // 泄露: 地址/叶子对 <t 合谋方 HIDDEN（secret index, active-secure）
  (2) REMAP        [leaf'] ← FreshRandomLeaf()   // MPC 内共同随机（预处理 random/Beaver）
                   PositionMap_{i+1}[[a]] ← [leaf']  // 秘密写入（同 O(N) 或递归）
                   // 泄露: 新叶子随机 → 独立于访问序列（Path ORAM 不变式）
  (3) READ-PATH    𝒫 ← buckets on path([leaf]);  把 𝒫 中所有 Z·(L+1) 个 slot 载入 stash
                   // 固定形状: 无论目标在何处都读整条路径 → 路径对观察者隐藏在"总读整条"
                   // MPC 操作: 每个 slot 字段是份额，条件载入用 select（乘法）
  (4) STASH-FIND   对 stash 每槽 j: [eq_j] ← Eq([addr_j],[a]) ∧ [valid_j];
                   [result] ← Σ_j [eq_j]·[val_j];  [found] ← Σ_j [eq_j]
                   // 全 stash 扫描 O(R) 次秘密比较/选择（R 是安全参数级常数，非 N）
                   // 泄露: 目标在 stash 中的位置 HIDDEN
  (5) APPLY-OP     if op=STORE: 在命中槽写 [v]（用 [eq_j] 条件更新）；
                   if op=LOAD/NOOP: result 即读出值（NOOP 的 result 丢弃但查询已执行）
                   // dummy Fetch: NOOP 仍执行 (1)-(4)，保证与真实访问不可区分
  (6) EVICT        自底向上，对每个 bucket 贪心选 stash 中 leaf 落在该路径的 block 填入，
                   剩余填 dummy；固定每 bucket Z 个槽的写入形状
                   // MPC 操作: O(Z·L) 次秘密比较（候选 leaf 是否落在当前 bucket 子树）+ select
  (7) PERSIST      Tree_{i+1} ← 写回路径后的树；Stash_{i+1} ← 剩余 stash（固定 R 槽）
                   // 物理状态改变，逻辑内存按 P6 不变式保持
  (8) COMMIT       C_{i+1} ← H(Encode(S_{i+1}));  输出 ([result], S_{i+1} shares, C_{i+1})
  返回 ([result], S_{i+1}, C_{i+1})
```

### 3.3 Position Map 秘密索引：两条路线（CONSTRUCTED / 关键成本分叉）

- **路线 A1（朴素）**：`SecretIndex` 用 N 项 `FieldEquals` + 乘加，**每步 O(N) 秘密选择**。→ **明确不宣称 O(log N)**；单步 O(N + ZL + R)，T 步 O(T·N + T·ZL)。在实验规模 N≤512 下 O(N) 常数小，但这是**全量扫描**，与要替代的线性扫描同阶（只差常数与"隐藏了什么"）。
- **路线 A2（递归）**：pos map 自身是一个更小的 Path ORAM（Stefanov 标准组件，L1 VERIFIED），递归 `⌈log_χ N⌉` 层 → 索引 polylog。**但每层递归的 pos/stash/tree 也是跨步状态**，必须一并纳入 `S_i` 与承诺 `C_i` → 承诺规模随递归层数增长。这是 §9 核心缺口的具体来源。
- **结论**：秘密索引"可行"（Keller–Scholl VERIFIED），但"polylog 索引"必然伴随"递归状态承诺"，**不能只算主 ORAM 路径而忽略递归 pos map**（呼应任务包 §6 要求）。

### 3.4 Stash 有界与溢出（CONSTRUCTED / 部分 BLOCKED）

- **容量依据（VERIFIED，L1）**：Path ORAM 统计界 `Pr[|S|>R] ≤ 14·(0.6002)^R`；Z=4 时 R=89 → `2⁻⁸⁰`，Z=5 时 R≈100 → 128-bit。**有可证明的概率界，不是"stash 足够大"**。
- **溢出处理**：固定 R 槽 + `[valid]` 标志；若实际超出 R（概率 ≤ negl），只能 **abort**。但"abort 事件"本身是**泄露**（暴露"这一步 stash 溢出"这一数据相关事件）——在 malicious prover 场景，prover 可**故意构造 overflow** 来制造选择性 abort。→ **BLOCKED（当前构造）**：要把 abort 变成不泄露，需 (a) 用足够大的 R 使概率对**所有 prover 策略**（含自适应）仍 negl，且 (b) 证明 prover 无法通过选择 witness 触发溢出而不被发现——这要求 R 内的 stash 内容本身受承诺约束且溢出条件在 R1CS 内可证。
- **固定执行形状**：无论真实 stash 占用多少，(4)(6) 都扫描/写回固定 R 与 Z·L 个槽 → 形状固定（✔ 对网络观察者隐藏占用）；占用本身是份额（✔ 对 <t 合谋隐藏）。

### 3.5 多方改造 + dummy Fetch（CONSTRUCTED）

- Path ORAM 原生是**客户端/服务器**（可信客户端持 pos+stash，L1）——**不能直接称为多方 MPC-ORAM**。改造：把 Tree 存为各方 additive shares（无单一服务器），pos/stash 也 secret-shared，八步全部由 MPC 执行。这正是 Keller–Scholl 的 oblivious array 构造（VERIFIED，L2）。
- **Load/Store 隐私**：`op` 若公开，则"操作类型"对 verifier 泄露。要隐藏，把 op 编码为 `[op]`（one-hot），(5) 用 `[is_store]·v + [is_load]·result` 统一计算——沿用 PFE-RAM 的"并行评估所有操作再秘密选择"思路（VERIFIED，L4），但 PFE-RAM 是 4 方 semi-honest，此处需换成任意方 active。
- **dummy Fetch（P2/P3）**：**每个非初始 step 都执行 (1)–(4)**，NOOP 的 `[a]` 用 reg0（普通地址，非 NegOne），result 丢弃但查询成本与访问已发生；历史行 `trace_address=NegOne`。→ 操作类型/是否真访问对 <t 合谋方 HIDDEN（都跑同一形状）。

### 3.6 方案 A 判定小结

| 子问题 | 判定 | 依据 |
| --- | --- | --- |
| 状态转换可构造 | **CONSTRUCTED** | §3.2 八步伪代码，全为 MPC 原语（比较/乘加/select/随机） |
| 任意方兼容 | **CONSTRUCTED（若用 Keller–Scholl）/ BLOCKED（若用 3-party DORAM）** | L2 vs L3 |
| 秘密索引可行 | **VERIFIED 存在 / UNKNOWN 成本** | L2 polylog 存在；递归状态承诺成本未解 |
| Stash 有界 | **VERIFIED 概率界 / BLOCKED 恶意溢出** | L1 统计界；prover 故意溢出未防 |
| 承诺覆盖全状态 | **CONSTRUCTED / UNKNOWN 更新成本** | §3.1 覆盖；每步 O(NZ) 约束 |
| 访问模式隐私 | **CONSTRUCTED（<t 合谋）/ 不适用（全体合谋）** | secret index + 固定形状 + 共同随机 |

---

## 4. 候选方案 B：通用 MPC-ORAM 子协议 + VDORAM 证明层

### 4.1 子协议抽象（CONSTRUCTED）

```
MPC_ORAM.Access([S_i], [addr], [op], [v]; ρ) → ([S_{i+1}], [result])
  ρ = MPC 内部随机带（叶子重采样等），由各方共同提供
子协议黑盒性质（需满足）:
  (i)  privacy: 给定 <t 方视图，addr/op/路径/leaf 计算上不可区分
  (ii) correctness(半诚实): 诚实执行时 S_{i+1} 满足 Path ORAM 不变式
  (iii) state-carrying: S_i shares 由外层执行器持有、跨 session 传递（沿用 R1 已核实机制）
```

候选实例化：
- **B1 = Keller–Scholl SPDZ Path ORAM**（L2）：任意 m 方、dishonest majority、active secure、polylog → **满足任意方目标**（关键）。
- **B2 = 3-party DORAM**（L3）或 **4-party PFE-RAM DORAM**（L4）：高效但**固定 3/4 方** → **明确标注与 VDORAM 任意方目标冲突**，仅作对照，不选。

### 4.2 输出状态绑定到 R1CS + transcript 问题（CONSTRUCTED，本方案关键）

研究负责人点名："若 transcript 不进入 SNARK，如何防 prover 提交与实际 MPC 输出不一致的 witness？"

**回答（沿用 VDORAM CompatCircuit 范式，VERIFIED 论文 p4-5）**：

```
协作 SNARK 的 witness 就是各方的 secret shares 本身：
  - MPC 计算 ORAM 转换 → 得到 [S_{i+1}], [result] 的 shares
  - 这些 shares 直接作为 collaborative SNARK 的 witness 分片 w_0..w_{m−1}
  - Prove 在 MPC 中"重算"转换电路的 R1CS 并出证明（witness 与计算同源）
  ⇒ "实际 MPC 执行的转换" 与 "证明验证的转换" 是同一次计算，
     transcript 无需单独进入 SNARK —— 一致性由 witness=计算输出 天然保证。
  ⇒ 恶意 prover 若改用不一致的 S_{i+1}，其 shares 不再满足 R_i 的转换约束，
     knowledge soundness 拒绝（前提是 R_i 完整编码了转换，见 §5.3）。
```

**限制（VERIFIED，来自 R1 核查，未重审）**：当前 artifact 的回调只把 R1CS+witness **落盘为 JSON**，协作证明是外部 Rust client **逐电路手动运行**，verifier 无跨电路串联（`verifier-chain-check.md` §1-4）。→ B 方案在**设计层 CONSTRUCTED**，在**当前工程层 BLOCKED**（需新增证明链与 verifier 串联，非本轮范围）。

### 4.3 参与方 / 隐私阈值（VERIFIED 文献 + 约束）

- B1（Keller–Scholl）：t = m−1（dishonest majority），privacy 需 ≥t 诚实——与 VDORAM P8 **完全一致**（VERIFIED，L2+L5）。
- B2/B3（3/4-party DORAM、PFE-RAM）：固定方数、多为 honest majority 或 semi-honest → **与 P8 冲突**，标注为"直接移植违约"（VERIFIED，L3/L4）。
- 全体 prover 合谋：privacy 不适用（P7）；correctness 由 SNARK soundness 保证（轨道 B）。

### 4.4 方案 B 判定小结

| 子问题 | 判定 | 依据 |
| --- | --- | --- |
| 状态转换可构造 | **CONSTRUCTED** | §4.1 黑盒 + §5 R1CS |
| witness 与实际 MPC 一致 | **CONSTRUCTED（设计）/ BLOCKED（当前 artifact 只落盘）** | §4.2 + R1 核查 |
| 任意方兼容 | **CONSTRUCTED（B1 Keller–Scholl）** | L2 VERIFIED |
| transcript 入证明 | **不需要**（witness=shares 同源，§4.2） | VDORAM CompatCircuit 范式 VERIFIED |
| 参与方限制 | **B2/B3 NO_GO narrower；B1 无限制** | L2 vs L3/L4 |

---

## 5. 统一证明接口设计（任务包 §4）

### 5.1 候选关系（对 A/B 同构，CONSTRUCTED）

```
R_i( C_i, C_{i+1}, step_i ; witness_i ) = 1

  C_i, C_{i+1} : 公开输入 — 本步输入/输出 ORAM 状态承诺
  step_i       : 公开输入 — 全局步数（连续递增，由 verifier 强制）
  witness_i    : 私有 — (S_i, S_{i+1}, [a], [op], [v], ρ, Tree/posmap/stash 中间值,
                        HistoricalLog 新行)

R_i 成立 ⟺ 下列 6 族约束全部满足:
  (α) 承诺正确:   C_i = H(Encode(S_i))  ∧  C_{i+1} = H(Encode(S_{i+1}))
  (β) 转换合法:   S_{i+1} = ORAM_Access_A(S_i,[a],[op],[v];ρ)  — §3.2 八步的 R1CS 展开
  (γ) 逻辑语义:   result 在 op=LOAD 时等于最新写入值；未写地址=0；Store 覆盖（P5 一致）
  (δ) VM 绑定:    result → AddPrivate("in_mem_val", result)（复用 L302 钩子，VERIFIED）
  (ε) 历史绑定:   append 一行 (trace_address, result, aux=(step_i,[op]))；
                  trace_address = (op∈{LOAD,STORE}) ? [a] : NegOne（P3，VERIFIED 语义）
  (ζ) 步数:       step_{i+1} = step_i + 1（供 verifier 串联校验）
```

### 5.2 承诺覆盖性（任务包 §4.5，CONSTRUCTED / UNKNOWN 成本）

`Encode(S_i)` **显式包含** Tree 全部 bucket slot、PositionMap 全部 N 项、Stash 全部 R 槽、metadata——无遗漏（满足 §4.5"承诺确实覆盖 Tree/PositionMap/Stash"）。**代价**：若用逐元素 hash，每步承诺更新与 (α) 验证为 `O(N·Z + N + R)` 约束。这是 §9 核心缺口——见 §8 复杂度。

### 5.3 承诺 ≠ 转换证明（VERIFIED 约束事实，本轮保持不变）

- `C_{i+1}=H(S_{i+1})` 只绑定"承诺对应某个状态"，**不能单独证明** `S_{i+1}` 是合法转换结果。
- 合法性由 **(β) ORAM_Access_A 的 R1CS 展开**保证——即 prover 必须用满足八步约束的 witness 才能通过。
- 若 (β) 缺失（只留承诺链），恶意 prover 可用任意 `S_{i+1}` 配对应承诺通过 → knowledge soundness 被绕过。**因此 (β) 不可省**。
- 沿用 R1 已收紧结论（未重审）：执行器宿主 hash 检查 ≠ verifier 强制约束；本 artifact 未提供后者（BLOCKED on current artifact）。

### 5.4 HistoricalLog 与逻辑地址（CONSTRUCTED，VERIFIED 语义）

- ORAM 改变**物理位置/叶子/重排**，但 HistoricalLog 仍按**逻辑语义** append：`trace_address` 用 reg0 派生的逻辑地址（Store/Load）或 NegOne（NOOP），**不是 ORAM 物理叶子**。→ 保持 R1 已分离的 `fetch_address`/`trace_address` 语义。
- `FHistoricalKV.Export()`（论文 p8，VERIFIED）仍需保留全部历史供公开证明——ORAM 替代的是**在线查询成本**，不替代**历史记录**（与 EXP-01 双结构结论一致）。

### 5.5 verifier 强制串联规则（任务包 §4.6，CONSTRUCTED 规则 / BLOCKED 实现）

```
verifier 持有公开序列: (C_0, step_0), (C_1, step_1), ..., (C_T, step_T) 与 proof π_1..π_T
强制检查（缺一不可）:
  V1 相邻串联:  对 i=1..T:  C_i^{input of R_i} == C_{i-1}^{output of R_{i-1}}
                 // 即"上一步输出承诺 = 下一步输入承诺"，防状态替换/跳接
  V2 步数连续:  对 i=1..T:  step_i == step_{i-1} + 1   // 防跳步
  V3 初始锚点:  C_0 == H(Encode(S_empty))              // 空内存/全 dummy 树的规定承诺
  V4 最终锚点:  C_T == H(Encode(S_final))  （若执行结束状态公开；否则用公开输出声明绑定）
  V5 每步证明:  Verify(pp, (C_i,C_{i+1},step_i), π_i) == 1  // arkworks verify_proof 级
```

**现状诚实声明（VERIFIED，来自 R1 未重审）**：本 artifact 的 C# 执行器有宿主层 hash 一致性检查（L322-328/L367-371），但 **回调只落盘**、**协作证明外部逐电路手动**、**verifier 无跨电路公开 IO 串联/步数/锚点检查**（`verifier-chain-check.md` §3-4）。→ V1–V4 是**本轮新增的设计要求**，当前工程**未提供**，属 BLOCKED（需新增 verifier 层，非本轮实现范围）。外部 `collaborative-zksnark-mod`（codeup.aliyun.com）验证端是否已有 —— UNKNOWN（不在固定 commit 证据内）。

### 5.6 A/B 共用接口小结

A 与 B 在**证明接口层同构**（都是 `R_i` + V1–V5），差异只在 (β) 内部：A 用 §3.2 显式八步电路；B 把子协议 `MPC_ORAM.Access` 的 R1CS 展开嵌入 (β)。两者都必须解决 §9 的承诺 sublinear 缺口。

---

## 6. 隐私与泄露面分析（任务包 §5）

### 6.1 观察者定义

- **O1 单个诚实参与方**：持 1/m share，<t 合谋。
- **O2 达到阈值的合谋集合**：|C|<t 方合谋（privacy 仍成立的上限）。
- **O3 全体 prover**：|C|=m，可合谋破坏 correctness（privacy 不适用）。
- **O4 公开 verifier**：只见公开输出 + proof，不持任何秘密。

### 6.2 泄露矩阵（CONSTRUCTED 分析；标注基于"构造满足 §3-5 且承诺不泄露内容"的前提）

| 信息项 | O1 单诚实方 | O2 <t 合谋 | O3 全体 prover | O4 公开 verifier | 依据 |
| --- | --- | --- | --- | --- | --- |
| 逻辑地址 `fetch_address` | HIDDEN | HIDDEN | LEAKED（输入持有者本就知晓/可合谋恢复） | HIDDEN（仅在 witness/承诺内） | L2 active secret index；P7 |
| 物理叶子 `leaf/leaf'` | HIDDEN | HIDDEN | LEAKED | HIDDEN | §3.2(2) 共同随机 + 承诺隐藏 |
| 访问路径 `P(leaf)` | HIDDEN | HIDDEN | LEAKED | HIDDEN | §3.2(3) 固定读整条路径 |
| 操作类型 Load/Store/NOOP | HIDDEN（若 [op] 秘密） | HIDDEN | LEAKED | CONDITIONALLY HIDDEN（公开输出若含 op 则泄露） | §3.5 [op] one-hot；P7 |
| dummy Fetch（NOOP 也查询） | HIDDEN（形状同真实） | HIDDEN | LEAKED | HIDDEN（步数固定 T） | P2/P3；§3.5 |
| PositionMap 更新 | HIDDEN | HIDDEN | LEAKED | HIDDEN | §3.2(2) 秘密写入 |
| Stash 占用/溢出 | HIDDEN | HIDDEN | LEAKED | CONDITIONALLY HIDDEN（abort 会泄露，§3.4） | §3.4 |
| MPC 通信轮次/消息长度 | CONDITIONALLY HIDDEN（形状固定则 HIDDEN；溢出/abort 泄露） | 同左 | LEAKED | 不适用 | §3.4/§3.5 固定形状 |
| 公开承诺 C_i | 公开（隐藏内容） | 公开 | 公开 | 公开（单向隐藏 S_i） | §5.2 H() |
| 公开 step_i | LEAKED | LEAKED | LEAKED | LEAKED（设计使然） | §5.5 V2 |
| proof 数量 | LEAKED（=T） | LEAKED | LEAKED | LEAKED | 每步一证明 |

**关键诚实点（不得省略）**：
1. **全体 prover（O3）几乎全 LEAKED 是威胁模型的预期，不是缺陷**——VDORAM P7 明确 correctness 下 0 honest、privacy 下才要求 ≥t 诚实；**不得声称全体合谋时仍有隐私**（呼应 P9）。
2. `CONDITIONALLY HIDDEN` 的两项（操作类型对 verifier、stash abort）是**真实剩余泄露面**：前者取决于公开输出是否含 op（程序输出设计问题）；后者是 §3.4 的 BLOCKED 溢出问题——**这是隐私轨道的未闭合点**。
3. 承诺 `C_i` 对 verifier 隐藏状态内容，依赖 `H` 的单向性 + witness 保密（协作 SNARK t-zero-knowledge）——若 H 选择不当（如可直接反解的小域 hash）则泄露，属 UNKNOWN（需实现时定参）。
4. "通信轮次/消息长度固定"依赖严格固定 ORAM 形状（R/Z/L 全 pad）；任何 data-dependent 提前退出都会泄露——§3.4 溢出是典型反例。

---

## 7. 与已有工作的差异（任务包 §7，四问逐答）

证据见 `source-evidence/literature-notes.md`（带 URL）。

| 问题 | 回答 | 标记 |
| --- | --- | --- |
| ① 哪些方案已提供状态转换机制？ | Path ORAM'13（tree+pos+stash）、Keller–Scholl'14（MPC oblivious array）、各 DORAM/PFE-RAM（分层/DPF）——都有 | VERIFIED |
| ② 哪些只解决访问隐私、无公开协作 SNARK？ | **Keller–Scholl、3-party DORAM、PFE-RAM 全部**——这正是必须新增证明层（§5）的原因 | VERIFIED |
| ③ 哪些只支持少数参与方？ | 3-party DORAM（3 方 honest majority，L3）、PFE-RAM（4 方 semi-honest，L4）是**硬限制**；**关键反例：Keller–Scholl SPDZ 是任意方**（L2）→ 破除"ORAM 必然限方" | VERIFIED |
| ④ 哪些未隐藏 PositionMap/Stash/维护操作？ | Path ORAM 原生把 pos+stash 放**可信客户端**——多方直接暴露即泄露；Keller–Scholl/DORAM 用 MPC 隐藏索引但无公开证明（VERIFIED/INFERRED） | VERIFIED + INFERRED |

**本构造究竟增加了什么（不是拼接两个组件）**：

```
已有组件各自缺一半：
  Keller–Scholl'14 = 任意方 MPC-ORAM 状态转换 + 访问隐私，但【无公开可验证、无跨步承诺】
  VDORAM'26       = 任意方公开协作证明 + 分布式遗忘，但【在线查询 O(T²) 线性扫描】
本构造新增的第三件东西（两者都没有）：
  (a) 每步 S_i→S_{i+1} 作为 R1CS 关系 R_i（把 ORAM 转换变成可公开验证的语句）
  (b) verifier 强制串联的状态承诺链 V1–V4（防替换/跳步/回滚，R1 已确认本 artifact 缺失）
  (c) ORAM 逻辑结果与 in_mem_val(L302) + HistoricalLog(P3/P5) 的语义绑定
⇒ 新增的是"公开可验证的跨步 ORAM 状态机证明层"，不是把 Path ORAM 插进 VDORAM。
```

---

## 8. 复杂度分析（任务包 §6，符号化，不编造常数）

### 8.1 对比表

| 项目 | VDORAM HistoricalKV（现状） | 方案 A（朴素 pos / 递归 pos） | 方案 B（Keller–Scholl 子协议） |
| --- | --- | --- | --- |
| 单步逻辑访问 | 随历史增长，O(i)（第 i 步扫 i 行） | 朴素 `O(N + ZL + R)`；递归 `O(polylog N · Z)` | `O(polylog N)`（L2 VERIFIED） |
| T 步累计访问 | `O(T²)` 查询扫描（论文 p10 / R1 实测） | 朴素 `O(T·N + T·ZL)`；递归 `O(T·polylog N·Z)` | `O(T·polylog N)` |
| 状态持久化 | 历史日志 O(T) | Tree O(N·Z) + pos O(N) + stash O(R)（每步全量承诺则更新 O(NZ)） | 同 A（子协议状态需同样承诺） |
| 每步 MPC 通信 | 现有 Fetch/Trace 机制 | 朴素 pos O(N) 轮内乘加；递归 polylog；READ-PATH/写回 O(ZL) | polylog（Keller–Scholl 实测 2 方 100 万元素 <100ms，仅 MPC 不含证明） |
| 每步 R1CS 规模 | 现有 Fetch/Trace 电路 | (β)+(α)：朴素承诺 O(NZ+R) 约束；实际电路因 pos 秘密索引放大 | 子协议 R1CS 展开 + 承诺 O(NZ) |
| witness 大小 | 历史行 | S_i+S_{i+1}+路径+stash = O(NZ) | 同 A |
| 证明生成 | 每电路协作证明 | 随 R1CS 规模；承诺全量更新 => 每步 O(NZ) | 同 A |
| 承诺更新 | 历史 hash 链（每步 append） | O(NZ)（朴素）/ UNKNOWN（增量或 Merkle-friendly，需设计） | 同 A |
| 存储空间 | O(T) 历史 | O(N·Z) 永久 + O(R) stash + O(T) 历史 | 同 A |

### 8.2 六类成本必须分开（任务包 §6 要求）

1. **MPC 计算复杂度**：朴素 pos 索引 O(N) 次域乘加/步；路径读 O(ZL)；stash O(R)；evict O(ZL)。递归 pos 把 O(N) 换为 polylog 层递归（每层 O(Z·L)）。
2. **MPC 通信复杂度**：与计算同阶（每乘加一个 Beaver 三元组一轮）；Keller–Scholl 证明 polylog 可达（VERIFIED，L2），但**不含协作证明开销**。
3. **R1CS 约束数量**：(β) ORAM 转换展开 + (α) 承诺。朴素逐元素 hash 下 (α) = O(NZ) —— **这是全量成本，不随 ORAM 访问是否 polylog 而减少**。
4. **witness 大小**：每步 O(NZ)（S_i、S_{i+1} 及中间树/路径/stash）。
5. **证明生成开销**：随 R1CS 规模线性/近线性；承诺全量更新直接放大每步证明。
6. **状态承诺更新开销**：O(NZ)（朴素）——**§9 核心缺口**。

### 8.3 明确标出 O(N) 步骤（不虚报 O(log N)）

- **朴素 pos map 索引是 O(N) 秘密选择** —— 明确写出，**不宣称整体 O(log N)**。
- **朴素全状态承诺是 O(NZ)** —— 即使 ORAM 访问 polylog，承诺仍全量，整体不 sublinear。
- 递归 pos map（路线 A2）虽把索引降到 polylog，但**递归状态承诺**把 O(NZ) 分摊到多层，**总承诺更新未按 O(log N) 减少**——UNKNOWN 是否有增量承诺技巧（如只承诺变化路径 + Merkle proof），本轮未构造出可验证方案。
- **与 O(T²) 的关系**：只有当 N 固定且与 T 无关、且承诺做到 sublinear 时，ORAM 的 O(T·polylog N) 才渐近优于 O(T²)；朴素全量承诺 O(T·NZ) 在 N~T 时**可能与 O(T²) 同阶甚至更差**——这正是"优势机会存在但未证明"。

---

## 9. 不可解决点、关键假设与最终判定

### 9.1 不可 / 未解决点

| # | 点 | 状态 | 是否阻断 GO |
| --- | --- | --- | --- |
| N1 | 全状态承诺每步 O(NZ)：ORAM polylog 访问被承诺全量更新抵消 | **UNKNOWN**（是否有 sublinear 增量承诺） | **是——核心** |
| N2 | verifier 跨电路串联 V1–V4 当前 artifact 未提供 | **BLOCKED**（本仓库未发现；外部 UNKNOWN） | 是（工程层，非协议层） |
| N3 | 恶意 prover 故意触发 stash overflow 造成选择性 abort | **BLOCKED**（§3.4） | 部分（隐私轨道泄露面） |
| N4 | 递归 pos map 的递归状态也需承诺/证明，成本未闭合 | **UNKNOWN** | 与 N1 同源 |
| N5 | 全体 prover 合谋下 privacy 不适用 | VERIFIED（威胁模型设定） | 否（预期，非缺陷） |
| N6 | 直接移植 3/4-party DORAM 违约任意方目标 | VERIFIED（L3/L4） | 否（避开即可：用 B1） |

### 9.2 关键假设（若成立则路线可 GO）

- **K1**：存在 arithmetic-friendly 承诺 `H`，其对 ORAM 状态的**每步更新、R1CS 内验证、verifier 串联**均为 sublinear in N（例如基于变化路径 + Merkle/向量承诺的增量方案）——**当前未构造出**。
- **K2**：协作 SNARK 后端支持把 Keller–Scholl 的任意方 active-secure MPC-ORAM 转换电路纳入 collaborative witness 关系，且 t-zero-knowledge 覆盖 ORAM witness（地址/叶子）——INFERRED（ CompatCircuit 范式 VERIFIED，但 ORAM 电路实证未做）。
- **K3**：stash overflow 概率对所有（含自适应恶意）prover 策略仍 negl，或溢出可在 R1CS 内证明未发生——BLOCKED（§3.4）。
- **K4**：verifier 侧可新增 V1–V4 串联（当前 artifact 缺失）——工程假设，非协议矛盾。

### 9.3 最终判定（任务包 §9 三选一）

**HOLD。**

**GO_TO_MINIMAL_PROTOTYPE 未满足**：任务包 GO 要求"主要成本没有明显退化为每步 O(N) 全量扫描"。当前构造中**朴素 pos 索引与全状态承诺均为 O(N)**（§8.3），递归方案的成本闭合（N1/N4）与 verifier 串联（N2）都未解决——**不能 GO**。

**NO_GO 未满足**：任务包 NO_GO 要求"目标威胁模型下明确不可绕过的矛盾"。Keller–Scholl（L2，VERIFIED）证明任意方 dishonest-majority MPC-ORAM 存在，**推翻了"参与方数量必然冲突"**；状态转换可表达为 R1CS（§3.2/§5，CONSTRUCTED）；访问隐私可构造（§6，<t 合谋）。**没有发现不可绕过的协议矛盾**——不能 NO_GO。

**唯一最关键阻断问题（必须且只需先解决这一个）**：

> **能否构造一组 ORAM 状态承诺 `C_i`，使得 (a) 每步更新、(b) R1CS 内验证 `(β)(α)`、(c) verifier 的 `C_{i+1}^{out}=C_i^{in}` 强制串联，三者同时为 o(N)（sublinear in N），同时见证的 witness 仍对 <t 合谋方隐藏地址/叶子/操作类型？**
>
> 这是"ORAM 访问 polylog 优势"能否兑现为"整条状态机端到端优于 O(T²)、且不弱于 VDORAM 隐私/正确性"的**必要条件**。若答案为否（承诺必然全量），则 ORAM 路线即使可构造也无性能意义 → 那时才升级为 NO_GO；若答案为是，则进入最小原型设计（先纸面细化该承诺 + 递归 pos map 成本闭合，再写代码）。

**下一步建议（本轮不执行）**：围绕上述唯一问题做**一次**有边界的承诺方案设计（增量/Merkle/向量承诺在 ORAM 状态上的适配 + verifier 串联规则落到具体电路），不做完整 ORAM 实现、不跑 benchmark。该问题有肯定答案前，不启动任何最小原型。

---

## 10. 本轮明确边界（纪律复述）

- 未实现 Path ORAM、未写任何 ORAM 电路代码、未跑 benchmark、未做 E0/E1。
- 未重新审计回调与 verifier——全部沿用 `exp-doram-02-r1/verifier-chain-check.md` 的已核实结论并标注"未重审"。
- 未把 R1CS 电路正确性当成访问模式隐私（§2 双轨分离）。
- 未把单个 proof 有效性当成完整轨迹有效性（§5.5 V1–V5 明确要求串联）。
- 未为得到 GO 降低参与方/威胁模型（§4.3 用 Keller–Scholl 任意方而非 3/4-party；隐私仅 <t 合谋）。
- 文献为定向核查（`source-evidence/literature-notes.md`），非泛泛综述；每条带 URL 与标记。

本轮到此停止，交付文档与证据，等待研究负责人集中核查与判定，不自动启动原型。
