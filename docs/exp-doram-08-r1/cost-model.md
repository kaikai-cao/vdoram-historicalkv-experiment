# EXP-DORAM-08-R1 — 修正后的精确成本模型

固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
源码依据：`docs/exp-doram-08-r1/source-corrections.md`；构造依据：`construction-comparison.md`。

## 0. 符号定义

| 符号 | 含义 |
| --- | --- |
| `T` | 执行步数（step 0 … T−1） |
| `n` | 固定地址域大小（槽位数） |
| `W` | STORE 步数集合 `S ⊆ {0,…,T−1}`，`W=|S|` |
| `F` | 实际 Fetch 次数 = `T−1`（step>0 每步一次） |
| `c_eq` | 每行/每槽地址比较的秘密乘法数（保守 389；优化变体 388） |
| `c_sel` | 每行 SelectCompose 的秘密乘法数（1） |
| `c_upd_shared` | 复用本步 eq 的每槽更新乘法数（**2**，R1-1 修正） |
| `c_upd_separate` | 独立重算 eq 的每槽更新乘法数（`c_eq + 2`） |
| `lowbit(k)` | `3k − 2`（E1-A 专用；E1-B 无） |

所有量为**秘密乘法（BeaverMulti 调用）计数**，不是 R1CS 约束、不是时间、不是实测 MPC 延迟。R1CS 约束数仍 **UNKNOWN**。

---

## 1. E0-FullScan（沿用 R0，已核实）

每步 `s`（step 0-based）可见历史行数 = s，Fetch 乘法数：

```
fetch_E0(s) = 393·s − 2      (s ≥ 1)
fetch_E0(0) = 0               (step 0 特判，ZkProgramExecutor L205-206)
```

精确求和 + 闭式：

```
C_E0(T) = Σ_{s=1}^{T−1} (393s − 2)
        = 393·T(T−1)/2 − 2(T−1)
```

线性加法：`A_E0(T) = Σ_{s=1}^{T−1}(4s−1) = 2T(T−1) − (T−1) = (T−1)(2T−1)`。
历史追加：E0/E1 每步各追加同一 5 列 trace 行到 Prove 侧，**成本相同、可抵消**，单独记为 `append_mults`（Fetch 电路不含追加，此处按 0 计；Prove 侧另计且相等）。

---

## 2. E1-A（保守，含 LowBit）

### 2.1 Fetch（step s>0）

```
fetch_A = n·c_eq + (3n − 2) + n·c_sel = 389n + 3n − 2 + n = 393n − 2
```
（step 0 不 Fetch → 无此项）

### 2.2 STORE 更新（step s，若 s ∈ S）

```
update_A(s) =
    n · c_upd_separate       若 s == 0                       (无 eq 可复用，强制 separate)
    n · c_upd_shared         若 s > 0 且 share_eq=True        (复用本步读路径 eq)
    n · c_upd_separate       若 s > 0 且 share_eq=False       (独立重算 eq)
```
其中 `c_upd_shared = 2`，`c_upd_separate = c_eq + 2 = 391`（保守 c_eq=389）。

### 2.3 精确求和

记 `S = store_steps`，`S⁺ = S \ {0}`，`W = |S|`，`W⁺ = |S⁺|`，`δ₀ = 1` 若 `0 ∈ S` 否则 0：

```
C_E1A(T,n,S) = (T−1)·(393n − 2)
             + δ₀·n·(c_eq + 2)
             + W⁺·n·(2 if share_eq else c_eq+2)
             + (T−1)·append_mults
```

线性加法（Fetch + 更新）：

```
A_fetch_A = (T−1)·[2n (eq) + n (LowBit NOT) + (n−1) (SelectCompose)] = (T−1)(4n−1)
A_update  = W·2n   (每槽两次 FieldAdd：value−old_j 与 old_j+prod)
```

---

## 3. E1-B（唯一槽位，无 LowBit）

### 3.1 Fetch（step s>0）

```
fetch_B = n·c_eq + n·c_sel = 389n + n = 390n
```

### 3.2 STORE 更新

与 E1-A **完全相同**（复用同一批 raw eq_j；LowBit 只影响读选择，不影响 raw eq）。

### 3.3 精确求和

```
C_E1B(T,n,S) = (T−1)·(390n)
             + δ₀·n·(c_eq + 2)
             + W⁺·n·(2 if share_eq else c_eq+2)
             + (T−1)·append_mults
```

线性加法：`A_fetch_B = (T−1)·[2n + (n−1)] = (T−1)(3n−1)`；`A_update = W·2n`。

### 3.4 E1-A vs E1-B 差

```
C_E1A − C_E1B = (T−1)·(3n − 2)     (仅 Fetch 差，STORE/追加相同)
```

---

## 4. 三种模型共同项与 step 0 语义

| 事件 | E0 | E1-A | E1-B |
| --- | --- | --- | --- |
| step 0 LOAD | memVal=0，无 Fetch，无更新 | 同 | 同 |
| step 0 STORE | 追加历史 1 行；无 Fetch | 追加 1 行；**无 Fetch，更新按 separate**（`n(c_eq+2)`） | 同 E1-A |
| step s>0 LOAD | Fetch(s)=393s−2 | Fetch=393n−2 | Fetch=390n |
| step s>0 STORE | Fetch(s) + 追加 | Fetch + 更新(shared/separate) + 追加 | 同，Fetch 更省 |
| 历史追加 | 每步 1 行 5 列（Prove 侧） | 相同 | 相同 |

step 0 STORE 强制 separate 的依据：`ZkProgramExecutor.cs` L205-206 无 Fetch → 无 eq（R1-3 / source-corrections.md）。

---

## 5. 线性运算成本（R1 要求不遗漏）

| 组件 | 每单位线性加法 | 来源 |
| --- | --- | --- |
| `FieldEquals`（每 eq） | 2（FieldSub 的 FieldAdd + BoolNot 的 FieldAdd） | R0 source-evidence §4 |
| `LowBit`（每 k） | k（k 个 BoolNot 各含 1 FieldAdd） | R0 §4 |
| `SelectCompose`（每 k） | k−1（累加） | gadget 源码 VERIFIED |
| 条件更新（每槽） | 2（value−old_j 的 FieldAdd + old_j+prod 的 FieldAdd） | 本轮 R1-1 |

E0 总计 `A_E0 = (T−1)(2T−1)`；E1-A `A = (T−1)(4n−1) + 2nW`；E1-B `A = (T−1)(3n−1) + 2nW`。

---

## 6. 通信与预处理（严格边界）

沿用 EXP-DORAM-08，**不外推**：

- 当前串行执行器（L160 TODO 未并行）：每次 `BeaverMulti` → 1 个 `ExposeFieldValues` barrier → **barrier 数 = 秘密乘法数**；
- 每次秘密乘法消费 1 个 `FieldBeaverTripleShare{X,Y,XY}` → **3 域元素预处理/乘法**；
- 每次 `BeaverMulti` 在线暴露 `[dA,dB]` → **2 域元素/方/乘法**（字节数 UNKNOWN，未核实编码长度）；
- 输入分发 O(1) 轮、最终输出暴露 O(1) 轮（数量依电路，本轮不展开）。

**禁止**：把当前串行 barrier 数当作批处理 MPC 的轮数；把域元素数当作网络字节数；把 R1CS 约束数当作秘密乘法数。

参数化：

```
rounds   = mults (当前串行, rounds_per_mult=1)
preproc  = 3 · mults 域元素
online   = 2 · mults 域元素/方
```

---

## 7. 参数化交叉条件

### 7.1 只读（W=0）

```
E1-B < E0  ⟺  (T−1)·390n < 393·T(T−1)/2 − 2(T−1)
         ⟺  390n < 393T/2 − 2
         ⟺  n < (393T − 4) / 780 ≈ 0.50385·T
```
E1-A：`n < (393T − 4)/786 ≈ 0.50000·T`。两者只读交叉均约 `n < T/2`（即 `T/n > 2`）。

### 7.2 读写混合（一般式，保守 c_eq=389）

令 `K_A = 393`, `K_B = 390`（每 Fetch 系数），`δ = δ₀`：

```
C_E1X = (T−1)·K_X·n + δ·n·(c_eq+2) + W⁺·n·u + (T−1)·a
C_E0  = 393·T(T−1)/2 − 2(T−1) + (T−1)·a
```
其中 `u = 2 (shared) 或 c_eq+2 (separate)`，`a=append_mults`（抵消）。

`C_E1X < C_E0` 解出 n 的连续上界：

```
n < [393·T(T−1)/2 − 2(T−1)] / [(T−1)·K_X + δ·(c_eq+2) + W⁺·u]
```
`T=1` 时两边皆 0（无 Fetch），交叉无意义；`T=0` 同。

**关键差异（R1 修正带来的）**：R0 用 `u=1`；R1 用 `u=2`（shared）或 `u=391`（separate），且 step 0 STORE 强制 separate。因此高 STORE 比例下 E1 的更新项显著变大，交叉 n 上界下降。

### 7.3 极端情形

- **STORE=0%**：退化为 §7.1，E1-B 在 `n < ~0.504T` 胜；
- **STORE=100% 且 share_eq=True**：`u=2`，更新项小，E1 仍可能胜（每槽仅 2 次乘法）；
- **STORE=100% 且 share_eq=False**：`u=391`，每 STORE 每槽付 391 次乘法 → E1 在高 STORE 下**可能反劣**；
- **step 0 STORE**：单个 step 0 STORE 增加 `n·391` 次乘法（无论 share_eq），对 T 很小时影响相对显著；
- **n=1**：E1-B Fetch=390/Fetch，E0 Fetch(s)=393s−2；T 大时 E1 优势明显；
- **n≈T/2**：接近交叉边界，需按 §7.2 精确判定，不用经验阈值；
- **n≫T**：E1 每步扫 n 槽远多于 E0 扫 s≤T 行 → E1 必败。

**以上均为参数化表达式，不是经验阈值**。EXP-DORAM-07-R1 的 `T≳4n` 是已测充分条件，本轮不从经验反推理论交叉点。

---

## 8. 与 R0 的差异汇总

| 项 | R0 | R1 |
| --- | --- | --- |
| `c_upd_shared` | 1 | **2** |
| `c_upd_separate` | `c_eq+1` | **`c_eq+2`** |
| step 0 STORE | 错误复用 eq（付 1/槽） | **强制 separate（`c_eq+2`/槽）** |
| E1 读取 | 单一 `393n−2` | **E1-A `393n−2` / E1-B `390n`** 双构造 |
| 成本函数入参 | `W:int` + `share_eq` | **`store_steps: set[int]`** + `share_eq` |
| 线性成本 | 只算 Fetch | **补更新 2/槽** + 双构造分别计 |
| c_eq 细节 | 单一 389 | 保守 389 + 公开操作数优化 388（单列，非实测） |
