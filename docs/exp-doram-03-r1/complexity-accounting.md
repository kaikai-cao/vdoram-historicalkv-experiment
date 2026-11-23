# complexity-accounting.md — 任务 G：复杂度核算

> 2026-11-23 · 起点 `b88f3db` · 符号化核算，不跑 benchmark。
> 目标：检查“ORAM 访问 polylog”是否真的兑现为“每步端到端 sublinear in N”，并显式列出任何 O(N) 隐藏项。
> 标记：**VERIFIED** 原文/源码/既有实测证据 · **CONSTRUCTED** 本轮计算 · **INFERRED** 由参数推导 · **UNKNOWN** 无实测/外部数据。

---

## G0. 参数

| 符号 | 含义 | 本轮示例 |
| --- | --- | --- |
| `N` | 逻辑地址空间大小 | `2²⁰` |
| `Z` | bucket 容量 | 4 |
| `R` | 每层 stash 容量 | 179（解析界 2⁻¹²⁸） |
| `B` | block 位宽 | 按 1 个域元素符号计数 |
| `λ` | 安全参数 | 128 |
| `T` | VM 步数 | 变量 |
| `m` | 参与方数 | 任意（Keller–Scholl SPDZ） |
| `χ` | 递归 pos-map 每块 position 数 | 4 |
| `D` | 总层数（含主树） | 10 |
| `L_j` | 第 j 层树高 | `20,18,…,2`，`ΣL_j=110` |

**范围声明**：sublinear 指**每步**更新/证明成本相对 N；总存储仍是 `O(N·Z + T)`，总执行仍随 T 增长。不要把“每步 polylog”写成“全程 polylog”。

---

## G1. 八类成本（每步，除非另注）

| # | 项目 | 符号化成本 | 示例（N=2²⁰, Z=4, R=179, χ=4） | 标记 |
| --- | --- | --- | --- | --- |
| 1 | MPC computation | `Σ_j [O(Z_j L_j + R_j + χ) + O(R_j²)（若 witness 唯一性在同电路）]` | `Σ(8L_j+179+179²)=323,080` 次乘法级操作（按 proof 侧计） | CONSTRUCTED |
| 2 | MPC communication | 与乘法数同阶（Beaver 三元组）；轮数依赖后端批处理，Keller–Scholl 给出 polylog overhead 存在性 | 无实测；不能给具体轮数 | VERIFIED(存在性) / UNKNOWN(具体数) |
| 3 | R1CS constraints | `C_hash + C_ORAM`，见 G2 | **≈2,798,280 个乘法约束/步** | CONSTRUCTED |
| 4 | witness size | `Σ_j O(Z_j L_j + R_j + L_j + χ)` 个域元素/份额 | 路径 `(L+1)Z`=21..3，stash 179，每层 auth `2L`；无整状态 | CONSTRUCTED |
| 5 | proof generation | 随 R1CS 规模近线性；collaborative 版另加多方通信 | 无实测，不给时间 | UNKNOWN |
| 6 | public verification | 单 proof 验证 + `O(D)` 公开根/step 输入；链上 T 步共 `O(T·D)` | D=10；Groth16 类配对验证为常数级 proof size | CONSTRUCTED / INFERRED |
| 7 | state commitment update | `Σ_j [(L_j+1)H(4Z_j) + L_j H(2) + H(4R_j)]` | 220 次 Merkle 父 hash + 120 次 bucket hash + 10 次 stash hash | CONSTRUCTED |
| 8 | HistoricalLog update | 每步 1 次 `H(5)`；终态仍需排序/一致性证明 | 每步 1300 乘法约束；最终排序 `O(T log²T)`（沿用 VERIFIED artifact 管线） | VERIFIED + CONSTRUCTED |

---

## G2. 约束公式（复算用）

```
H(k) = 260k                         // VDORAM MiMC 默认：65 rounds × 4 mult(x^7)
C_hash = Σ_j [ 2L_j·H(2) + (L_j+1)·H(4Z_j) + H(4R_j) ] + 1040χ + 1300
       = Σ_j [ 1040L_j + 1040Z_j(L_j+1) + 1040R_j ] + 1040χ + 1300

C_ORAM = Σ_j [ 2Z_jL_j + R_j + R_j² + O(χ) ]   // 读/evict + stash find + 唯一性 + 递归选择

示例:
C_hash = 2·110·520 + 120·4160 + 10·(1040·179)
       = 114,400 + 499,200 + 1,861,600 = 2,475,200
C_ORAM = 880 + 1,790 + 320,410 = 323,080
Total  = 2,798,280乘法约束/步
```

递归 PositionMap 的成本已含在上式的 `j=1..d`：`Σ_{j≥1} L_j ≈ (log₂N)²/(2log₂χ)`，不是 O(N)。

---

## G3. 基线对比

| 项目 | VDORAM HistoricalKV（E0 基线） | 本构造（Merkle + 递归 Path ORAM） |
| --- | --- | --- |
| 单步逻辑查询 | 扫 i 行历史：`O(i)` | `O(polylog N)` 路径 + 递归层 |
| T 步查询总量 | `O(T²)`（EXP-DORAM-01-R1 已确认 workload 一致后） | `O(T·polylog N)` |
| 最终排序/一致性 | `O(T log²T)` Bitonic + Prove | **仍需** `O(T log²T)`（HistoricalKV 语义保留） |
| 每步承诺更新 | 每行 trace hash；append-only | `Σ_j[(L_j+1)H(4Z_j)+L_jH(2)+H(4R_j)]` |
| 每步 R1CS | `i` 次 FieldEquals + LowBit + SelectCompose | ≈2.8M 乘法约束（示例参数） |
| 状态存储 | `O(T)` 历史 | `O(N·Z + R·D + T)` |
| witness | `O(i)` 历史行 | `O(Σ_j(ZL_j+R_j+L_j))` |
| 参与方 | 任意 m、dishonest majority | 同左（Keller–Scholl + VDORAM 证明层） |
| 公开验证 | 每 proof + 逐行 hash | 每 proof + 根/step/hist 串联 |

**重要**：EXP-DORAM-01-R1 的 `9.4–51.8×` 只是 E1 双结构相对 E0 的**参考数据结构**查询加速，不是 ORAM 数据，也不能外推为本构造的性能。

---

## G4. 显式 O(N) 项检查（验收重点 1）

| 潜在 O(N) 来源 | 本构造是否出现 | 处理 |
| --- | --- | --- |
| 单层 position map 线性秘密索引 `Σ_{j=0}^{N−1} Eq·pos[j]` | **若采用则出现 O(N)/步** | 排除：改为递归 Path ORAM，每层秘密索引经 oblivious array（A2） |
| 全树 Merkle 一致性重算 | 若实现要求“证明整棵树没被改”则 O(N·Z)/步 | 排除：R1CS C1.2 用旧 auth path + sibling 相等，只覆盖被触碰路径 |
| 整状态 `H(Encode(S_i))` 逐元素哈希 | 若采用则 O(N·Z)/步 | 排除：改为分层 Merkle root + stash root |
| 递归 PositionMap 全量承诺 | 若每层都全量承诺，仍 O(N·Z) | 排除：每层同样只增量更新一条路径 |
| HistoricalKV 最终排序 | **出现，但 O(T log²T)，不是 O(N)** | 保留；ORAM 只替代在线查询，不替代历史一致性证明 |
| 总存储空间 O(N·Z) | 是，但非每步成本 | 明确声明 |

**结论**：本轮构造中**没有每步 O(N) 项**；唯一保留的全量式工作是终态排序 `O(T log²T)`，属于 T 维而非 N 维，不影响“每步 sublinear in N”的判定，但影响端到端实用价值。

---

## G5. 与 O(T²) 的边界

```
ORAM 总工作 ≈ T · P(N, λ) + O(T log²T)      // P 为 G2 的多项式，≈polylog N
基线总工作 ≈ O(T²) + O(T log²T)
```

- 当 N 固定、T 足够大时，`T·polylog N` 渐近优于 `T²`；但示例常数 `P≈2.8M` 乘法约束意味着交叉点可能非常大，**本轮不给“实用更快”的结论**（UNKNOWN，无实测）。
- 当 N 随 T 增长（如 N≈T），ORAM 仍是 `T·polylog T`，渐近优于 `T²`；但证明/通信常数必须实测才知道是否划算。
- 若任何实现重新引入 O(N)/步承诺或索引，则总工作退回 `O(T·N·Z + T log²T)`，在 N~T 时与基线同阶或更差，GO 条件失效。

---

## G6. 未计入 / 未知项

- 协作 SNARK 的具体证明时间、proof size、verifier 配对次数（后端未固定，UNKNOWN）。
- MiMC 抗碰撞安全裕量与可能的参数升级导致的轮数变化（UNKNOWN）。
- 网络层通信轮数、批处理效率、预处理生成成本（UNKNOWN）。
- 恶意 prover 选择性 abort 对总工作的影响（见 `privacy-analysis.md`，UNKNOWN）。
