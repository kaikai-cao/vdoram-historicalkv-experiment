# EXP-DORAM-08-R1 — E1-A / E1-B 构造比较与代数正确性

固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`

## 0. 两种读取构造

记槽位 `j ∈ {0,…,n−1}`，槽值 `v_j`（秘密 share），查询地址 `a`（秘密 share）。

| 项目 | E1-A（保守） | E1-B（唯一槽位） |
| --- | --- | --- |
| 地址比较 | n 次 `FieldEquals(a, j)` | n 次 `FieldEquals(a, j)` |
| LowBit | **有**：`LowBit(n)` 把 raw eq 压成 one-hot | **无**：直接用 raw eq |
| SelectCompose | 有：`Σ sel_j · v_j` | 有：`Σ eq_j · v_j` |
| 唯一槽位前提 | 无额外唯一性前提（LowBit 兜底） | **有界域**：`a ∈ [0,n−1]` 时最多一个 eq_j=1 |
| 未命中返回 0 | LowBit 全 0 → SelectCompose 全 0 → 0 | 需代数证明（见 §2） |
| 每次 Fetch 秘密乘法（保守 c_eq=389） | `393n − 2` | `390n` |
| 每次 Fetch 秘密乘法（公开操作数优化 c_eq=388） | `392n − 2` | `389n` |
| 证据等级 | 构造 DERIVED（gadget VERIFIED） | 构造 DERIVED + **有界域为 CONSTRUCTED 假设** |

两者共同的硬边界：地址域 `[0,n−1]` 有界是**我们构造 E1 时引入的假设**（CONSTRUCTED），不是 VDORAM 上游保证。EXP-DORAM-07-R1 已核：目标系统全域有界 = **UNKNOWN**。

---

## 1. E1-A 正确性（有 LowBit）

`raw_j = FieldEquals(a, j) ∈ {0,1}`（域元素）。`sel = LowBit(raw_0,…,raw_{n−1})` 产生 one-hot：恰在最后一个 raw=1 的位置为 1（对应 E0 逆序选最新），其余为 0；若全 raw=0 则全 sel=0。

`out = SelectCompose(sel, v) = Σ sel_j v_j`：

- 若有匹配：`out = v_{latest matching j}`；
- 若无匹配：`out = 0`（有限域 sum of 0·v_j）。

**无需唯一性前提**：即使多个 raw_j=1（例如同一地址出现在多槽，尽管 E1 构造应避免），LowBit 仍选出一个。**代价**：多付 `LowBit(n)=3n−2` 次秘密乘法。

---

## 2. E1-B 正确性（无 LowBit）— 需证明的性质

### 性质 P1（域内唯一命中）

前提：`v_j` 所在槽位 j 的“地址标签”就是公开常量 j（影子表构造：槽 j 存地址 j 的当前值）。则：

```
eq_j = [a == j]
若 a ∈ [0,n−1] 且 a = k：eq_k = 1，且 ∀j≠k, eq_j = 0   （因 j 两两不同，a 为单值）
```

即 eq 向量已经是 one-hot，**无需 LowBit 再压缩**。

### 性质 P2（域外全部不命中）

若 `a ∉ {0,…,n−1}`（含 dummy/NegOne 等域外值），则 `∀j, a ≠ j`，故 `eq_j = 0` 对所有 j 成立。

### 性质 P3（SelectCompose 输出 = 默认值 0）

`out = SelectCompose(eq, v) = Σ_{j=0}^{n−1} eq_j · v_j`：

- 域内命中 k：`out = 1·v_k + Σ_{j≠k} 0·v_j = v_k`（正确返回槽 k 的值）；
- 域外/未命中：所有 eq_j=0 → `out = Σ 0·v_j = 0`（正确返回原始 Fetch 默认值）。

### 形式化反例检查（为什么 P1 依赖“槽地址=公开下标”）

若槽位存的是**秘密地址标签** `addr_j`（而非公开下标 j），则 `eq_j = [a == addr_j]`，多个槽可能同时命中（若表内有重复地址），P1 不成立 → E1-B 错误。因此在 E1-B 中必须固定“槽 j ≡ 地址 j”的构造，并把唯一性作为构造不变量（影子表每地址恰一槽，由 EXP-DORAM-07-R1 的 `ShadowState[a] == latest_value(a)` 保证）。

### 边界：`a` 为秘密时比较仍走秘密路径

`eq_j = FieldEquals(a, j)` 中 `a` 是秘密 share，`j` 是公开常量。差值 `a − j` 含秘密 → `FieldNorm` 仍走秘密求逆（EXP-DORAM-08 §5 已核），故每个 eq_j 仍需 `c_eq` 次秘密乘法（保守 389 / 优化 388，见 source-corrections.md R1-1）。**公开下标只省掉 FieldNeg 的 1 次（若 j 放在 right），不省掉秘密求逆。**

---

## 3. Sum-of-products 视角下的成本差

E1-A 比 E1-B 多付的正是 `LowBit(n)`：

```
fetch_A(n) − fetch_B(n) = (3n − 2)   [两构造的 eq 次数与 SelectCompose 次数相同]
```

代入保守 c_eq=389：`fetch_A = 393n−2`，`fetch_B = 390n`，差 `3n−2`。对 n=1024，差 3070 次秘密乘法/Fetch。

**这个差额是否值得，取决于 LowBit 是否是 E1 的必要安全/正确性组件**：

- 若影子表不变量成立（每地址恰一槽，地址域有界）→ eq 天然 one-hot → LowBit 冗余 → E1-B 更优；
- 若无法保证不变量（重复地址、域外地址、恶意 witness）→ E1-A 的 LowBit 提供兜底唯一性，但代价是每 Fetch 多 `3n−2`。

本轮选择：**两种都建模**，敏感性分别报告，不预设 E1-B 一定胜出。

---

## 4. 与 STORE 更新路径的耦合

STORE 更新 `new_j = old_j + eq_j·(value−old_j)` 复用**同一批 eq_j**（读路径已算）：

- **step 0**：无 Fetch → 无 eq → 强制 `c_upd_separate`（R1-3）；
- **step > 0, share_eq=True**：复用读路径 eq → 每槽 `c_upd_shared=2`；
- **step > 0, share_eq=False**：独立重算 → 每槽 `c_upd_separate=c_eq+2`。

E1-A 与 E1-B 的 eq_j 向量**数值相同**（都是 `[a==j]`），差别只在 E1-A 额外算了 LowBit 的 sel 向量。STORE 复用的是 raw eq_j（两者都有），因此**两者的 STORE 更新成本相同**，差异仅在 Fetch。

---

## 5. 未被本轮覆盖的更省路线

对秘密 `a` 做一次 bit decomposition，再与公开 j 逐位比较，理论上可摊薄 n 路比较成本（O(n·log n) 或更低）。该路线：

- **不在固定上游源码中**；
- 其安全性、Beaver 成本、位宽边界均无一手证据 → **UNKNOWN**；

本轮**不计入任何优势**，E1-A/B 都按“每槽一次 FieldEquals”建模。
