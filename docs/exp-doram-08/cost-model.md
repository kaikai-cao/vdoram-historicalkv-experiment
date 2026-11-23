# EXP-DORAM-08 — 可审计符号成本模型

所有数字来自 `source-evidence.md`。本文件只做**逐步求和**，不使用渐近符号代替表达式；所有成本参数均为源码推导或显式假设，**无实测 MPC 时间**。

## 0. 记号与参数状态

| 参数 | 含义 | 值 / 状态 |
| --- | --- | --- |
| T | 执行步数 | 输入 |
| n | 固定地址域大小 | 输入 |
| Q | 结果被使用的 Fetch（LOAD）数 | 输入 |
| W | STORE 数 | 输入 |
| D | dummy Fetch 数（STORE/NOOP 的 Fetch） | `D = F − Q` |
| F | 实际 Fetch 数 | `F = T − 1`（step 0 特判无 Fetch） |
| `A = popcount(p−2)`, `B = bitlen(p−2)` | 秘密求逆的平方乘次数 | `A=133, B=253`，**VERIFIED** |
| `m_inv = A + B` | 一次秘密求逆的 Beaver 乘法 | **386**，DERIVED |
| `c_eq` | 一次地址相等（`FieldEquals`）的秘密乘法 | **389**，DERIVED |
| `c_lb(k) = 3k−2` | `LowBit` over k 位的秘密乘法 | DERIVED |
| `c_sel = 1` | 一次 `select_compose` FieldMul | VERIFIED |
| `c_upd_shared = 1`/槽 | STORE 条件更新（复用同轮 eq） | **ASSUMED**（无源码证据） |
| `c_upd_sep = 390`/槽 | STORE 条件更新（独立重算 eq） | DERIVED |
| `c_append` | 每追加一行的 Fetch 相密码乘法 | **0**（FETCH 电路不处理 append） |
| `c_prove_row` | 每行 Prove/MiMC 的 R1CS 约束 | **UNKNOWN**（未取得编译映射） |
| `r_pm = 1` | 每秘密乘法对应的在线 barrier 轮 | VERIFIED（当前串行执行器） |

**单位区分（本轮硬约束）**：
- “秘密乘法” = `BeaverMulti` 调用次数 = `393k−2` 这类整数。
- “R1CS 约束” = 证明侧 `MemoryTraceProve` 路径的量，**与 Fetch 乘法数无关**，本轮 UNKNOWN。
- “在线轮数” = 当前实现中等于秘密乘法数（串行 + 每乘法一次 `ExposeFieldValues` barrier），但**若有批处理则乘法数不变、轮数下降**；不得把两者当同一概念写进结论。

## 1. E0-FullScan：每条历史行的 gadget 分解

Fetch 在 step s>0 看到 `t = s` 行（step 0 追加第 0 行；可见历史 = 已完成步数）。每行：

```
FieldEquals(addr_row, addr_query)
  ├─ FieldSub: FieldNeg(−1×x) 1 mult + FieldAdd 1 linear
  ├─ FieldNorm: FieldInverse 386 mult + FieldMul(x,x⁻¹) 1 mult
  └─ BoolNot(1−norm): FieldNeg 1 mult + FieldAdd 1 linear
  => 389 mult + 2 linear add / 行
```
全电路追加：
```
LowBit(t rows)          : 3t − 2 mult + t linear add
SelectCompose(t, 1 col) : t mult + (t−1) linear add
```
所以
```
m_fetch(t) = 389t + (3t−2) + t = 393t − 2      (t ≥ 1)
a_fetch(t) = 4t − 1                              (t ≥ 1)
m_fetch(0) = 0
```

**逐步累计（精确求和式）**：
```
C_E0_mult(T) = Σ_{s=1}^{T−1} m_fetch(s) + T·c_append
             = Σ_{s=1}^{T−1} (393s − 2) + 0
             = 393 · T(T−1)/2 − 2(T−1)
```
行数校验：R1 模型 `history_rows_scanned = T(T−1)/2`，与此式一阶项一致。
`C_E0_linear(T) = Σ_{s=1}^{T−1}(4s−1) = 2T(T−1) − (T−1)`
`C_E0_rounds(T) = C_E0_mult(T) + r_setup + r_output`（`r_setup, r_output` = O(1)，具体值 UNKNOWN，不填数字）
`C_E0_preproc_field_elems(T) = 3 · C_E0_mult(T)`（每三元组 X,Y,XY）
`C_E0_online_field_elems(T) = 2 · C_E0_mult(T)`（每 BeaverMulti 暴露 dA,dB；不含 input/output）

## 2. E1-ShadowState：每槽位读写分解

用同一套 gadget、n 个槽位；槽位下标 j 是**公开常量**，但 `shadow[j]` 与查询 `addr` 均为秘密 share：

```
read eq(j,addr) : FieldEquals → 389 mult/槽（公开 j 不带来执行器优惠）
read select     : LowBit(n)=3n−2 + SelectCompose(n)=n
  => m_read(n)  = 393n − 2        （与 m_fetch(n) 完全同价）
write eq        : 复用同轮 eq（share_eq）→ 0 额外 eq 乘法
                  独立重算 eq（sep_eq）  → 389n
write apply     : new[j] = old[j] + eq_j·(v − old[j]) → 1 mult/槽
  => m_upd(n)   = n               (share_eq)
                 = 390n           (sep_eq)
```

**逐步累计**：step s=0 无 Fetch；s≥1 每次 fetch 扫 n 槽；每个 STORE 额外 n 槽更新。

```
C_E1_mult(T,n,W) = Σ_{s=1}^{T−1} m_read(n) + W·m_upd(n) + T·c_append
                 = (T−1)(393n − 2) + W·( n | 390n ) + 0
```
`C_E1_linear = (T−1)(4n−1) + W·2n`（2n: `v−old` 与 `old+prod` 各 n 次线性）
`C_E1_rounds = C_E1_mult + r_setup + r_output`；预处理 = `3·C_E1_mult`；在线 = `2·C_E1_mult`。

**PROVE 侧（共同项，不构成优势）**：两模型追加相同的 5 列 trace 行；`MemoryTraceProve` 每行一次 MiMC(7) 及相邻行的相等/比较/布尔门。该成本 `T·c_prove_row` **E0=E1**，且 `c_prove_row` 为 UNKNOWN。因此**不能**声称 E1 降低了 R1CS 约束总量。

## 3. Fetch / LOAD / STORE / NOOP 逐步成本表

step s 的活动（s≥1）：

| op | Fetch | 选择 | 状态写 | E0 mult(s) | E1 mult(s) |
| --- | --- | --- | --- | --- | --- |
| LOAD | 有（结果使用） | 有 | 无 | `393s−2` | `393n−2` |
| STORE | 有（dummy，结果不用） | 有 | 有 | `393s−2` | `393n−2 + (n｜390n)` |
| NOOP | 有（dummy，结果不用） | 有 | 无 | `393s−2` | `393n−2` |
| step 0（任意 op） | 无 | 无 | STORE 时 E1 有 | 0 | `0 (+ n｜390n)` |

注意：dummy Fetch **不是免费的**——原电路对所有 op 都执行 Fetch，所以 STORE/NOOP 也付 `393t−2` 或 `393n−2`。这是 Q5 “全 NOOP/dummy” 分析的关键。

## 4. 交叉条件推导（从表达式推出，不用 R1 经验阈值）

共同项（append、Prove、setup）在比较中消去。令 `S = T(T−1)/2`（E0 总扫描行数）。

**(a) 只读 / 无 STORE（W=0）**
`(T−1)(393n−2) < 393S − 2(T−1)`
`⟹ 393n(T−1) < 393S ⟹ n < T/2 ⟹ T/n > 2`

**(b) 读写混合 + 复用 eq（share_eq）**
`n[393(T−1) + W] < 393S`
`⟹ n < 393·T(T−1) / (2[393(T−1)+W])`

**(c) 高 STORE 比例 + 独立 eq（sep_eq，保守）**
`n[393(T−1) + 390W] < 393S`
`W = T−1` 时 `n < 393T / (2·783) ≈ T/3.985 ⟹ T/n ≳ 4`

**(d) 全 dummy（Q=0，W=0）**：与 (a) 同，dummy 不改变表达式，只改变 Fetch 结果是否被使用。

**(e) n 很小 / n 接近 T / T ≫ n**：
`n ≪ T` → E1 常量优势，`C_E1/C_E0 ≈ 2n/T`；
`n ≈ T` → 比值 `≈ 2·(T−1)/T → 2`，E1 反而约 2× 贵（因 E0 早期扫描行数远小于 T）；
`n > T/2` → 任何读写比例下 E1 都更贵（(a) 是上界）。

**与 R1 经验阈值的关系**：R1 测到的格子只有 `T/n ∈ {1/16,1/4,1,4,16,64,256}`，`1` 必败、`4` 必胜，故写成 `T≳4n`（经验、已测试充分条件）。理论边界：share_eq 为 `T/n>2`；sep_eq 且全 STORE 为 `T/n≳4`。**R1 的 4 不是理论值，也不能反推为理论值**。

## 5. 不确定参数清单（不得填实测数字）

| 项 | 状态 | 原因 |
| --- | --- | --- |
| `c_prove_row` / R1CS 约束数 | UNKNOWN | 未取得 `MpcCircuit → R1CS` 映射源码；Prove 侧未实测 |
| `r_setup`, `r_output` | UNKNOWN | 依赖共享存储/网络实现；本轮不测 |
| 在线字节数 | UNKNOWN | 域元素编码字节数依赖 `Field` 实现，未逐项核对 |
| `share_eq` 是否可复用 | ASSUMED | 需电路层实现证据，当前无 |
| “所有乘法等成本” | ASSUMED（基线） | 真实微基准中常数乘/秘密乘/求逆权重可不同；本项目当前执行器中均走 Beaver，故基线取等权，只作**符号比较** |
| Rust `inv_pair` 路径 | UNKNOWN（不适用） | 证明侧 crate，不在 Fetch 执行路径 |
| E1 位分解摊薄比较 | UNKNOWN（不计入） | 无源码证据，属新构造 |
