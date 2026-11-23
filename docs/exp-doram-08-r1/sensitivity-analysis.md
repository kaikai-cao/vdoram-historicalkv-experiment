# EXP-DORAM-08-R1 — 参数敏感性分析（重算）

固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`

数据：`results/exp_doram_08_r1/{symbolic_costs,sensitivity_raw,sensitivity_summary}.csv`。
所有数值为**符号秘密乘法计数**，`parameter_status` 标注 DERIVED（源码推导）或 ASSUMED（假设权重），**不是实测 MPC benchmark**。

## 0. 扫描维度

- `n ∈ {16,64,256,1024}`，`T ∈ {64,256,1024,4096}` → 16 个 (T,n) cell
- STORE 比例 `∈ {0%,10%,50%,90%,100%}`；STORE 位置策略 `∈ {uniform, step0, no_step0}`
- 更新模式 `∈ {shared, separate}`；变体 `∈ {E1-A, E1-B}`
- 权重比 `c_eq/c_sel ∈ {389, 1}`、`c_upd/c_sel ∈ {2, 100}`：
  - `(389, 2)` = **DERIVED**（固定 commit 源码链 + R1-1 修正）
  - 其余三组 = **ASSUMED** 压力测试（比较便宜、更新昂贵），用于探边界
- 产物：`symbolic_costs.csv` 960 行、`sensitivity_raw.csv` 1280 行、`sensitivity_summary.csv` 80 行。

---

## 1. 源码推导基线（c_eq=389, c_upd=2，DERIVED）

`E1-B`（无 LowBit，最省构造）以 shared 更新模式：

| STORE 比例 | E1 胜场 | 中位 cost_ratio | T/n≥4 胜场 |
| --- | --- | --- | --- |
| 0% | 10/16 | 0.496 | 10/10 |
| 50% | 10/16 | 0.499 | 10/10 |
| 100% | 10/16 | 0.500 | 10/10 |

`E1-B` 以 **separate** 更新模式（不假设 eq 复用）：

| STORE 比例 | E1 胜场 | 中位 cost_ratio | 说明 |
| --- | --- | --- | --- |
| 0% | 10/16 | 0.496 | 与 shared 同（无 STORE） |
| 50% | 10/16 | 0.746 | 更新成本上升但不翻盘 |
| 90% | 10/16 | 0.945 | 接近持平 |
| 100% | **9/16** | 0.995 | **边界 cell 翻转**（见 §4） |

`E1-A`（含 LowBit）在上述所有点相对 E1-B 多付 `(T−1)(3n−2)`，胜负格局与 E1-B 一致但在边界更早失利。

**基线结论**：在源码推导权重下，E1 的胜场精确等于 `T/n ≥ 4` 的 10 个 cell（与 EXP-DORAM-07-R1 的已测充分条件一致），`T/n ≤ 1` 的 cell 全部反劣。`E1-B` 由于省掉 LowBit，cost_ratio 系统性低于 `E1-A`。

---

## 2. 有利 E1 的参数区域（DERIVED + 一致）

1. **只读或低 STORE**（W≈0）：交叉约 `n < 0.504·T`（E1-B）/ `n < 0.500·T`（E1-A），即 `T/n > 2` 理论上 E1 更省乘法；已测网格中 `T/n≥4` 全部胜。
2. **shared 更新**（eq 可复用）：即便 STORE=100%，每槽仅 2 次乘法（`c_upd_shared=2`），E1 仍全胜（中位 ratio≈0.50）。这是 E1 最有利的情形。
3. **E1-B 无 LowBit**：每 Fetch 比 E1-A 省 `3n−2` 次乘法，n 越大优势越明显。

## 3. 不利 E1 的参数区域（含 ASSUMED 压力测试）

1. **T/n ≤ 1**：E1 每步扫 n 槽 ≥ E0 扫 s≤T 行，全部反劣；最坏 `n=1024,T=64` 达 64×（基线）乃至更高（压力）。
2. **separate + 高 STORE**：`c_upd_separate=391`（源码权重）在 STORE=100% 使边界 cell `n=16,T=64 (T/n=4.0)` 翻转（ratio=1.0017），因为 step 0 STORE 强制 separate 多付 `n·389`。
3. **ASSUMED 压力权重** `c_eq/c_sel=1, c_upd/c_sel=100`（比较极便宜、更新极贵）：

   | STORE 比例 | E1-B 胜场 | 中位 ratio | 最坏 ratio |
   | --- | --- | --- | --- |
   | 0% | 13/16 | 0.200 | 12.96 |
   | 10% | 6/16 | 1.210 | 75.30 |
   | 50% | 3/16 | 5.27 | 345.45 |
   | 90% | 3/16 | 9.32 | 615.59 |
   | 100% | 3/16 | 10.34 | 677.93 |

   结论：一旦更新远贵于比较，E1 优势迅速消失（3/16 胜，中位反劣 5–10×）。这印证 EXP-DORAM-08 的发现：**E1 优势依赖 c_eq ≫ c_upd 的权重结构**。

---

## 4. step 0 STORE 对总成本的影响（R1-3）

用 `store_step_strategy` 做同数量 STORE 的干净隔离（E1-B, shared, n=64, T=256, ratio=50%）：

| 策略 | STORE steps | update_cost | e1_cost |
| --- | --- | --- | --- |
| `no_step0`（步 1..k） | 128 个，均 step>0 | 25024+... | 6381184 |
| `uniform`（步 0..k−1，含 step0） | 128 个，含 step0 | 多 24896 | 6406080 |

差值精确为 `n·(c_upd_separate − c_upd_shared) = n·(391−2) = n·389`：n=64 → 24896，n=16 → 6224。**每个 step 0 STORE 因无法复用 eq 而多付 n·389 次秘密乘法**。对大 T 影响可忽略；对小 T（如 T=64）足以翻转边界 cell（见 §3.2）。

`symbolic_costs.csv` 中 `step0` 策略（仅 step 0 一次 STORE）显示单次 step0 STORE 的绝对成本 = `n·391`。

---

## 5. E1-A 与 E1-B 的差距

`C_E1A − C_E1B = (T−1)(3n−2)`（仅 Fetch，STORE 与追加相同，见 construction-comparison.md §3）。

| n | T | 差额（次秘密乘法/Fetch 全程） |
| --- | --- | --- |
| 16 | 256 | 255 × 46 = 11730 |
| 64 | 1024 | 1023 × 190 = 194370 |
| 1024 | 4096 | 4095 × 3070 = 12,571,650 |

n 越大，LowBit 的 `3n−2` 越显著。**若影子表不变量成立（每地址恰一槽、域有界），E1-B 严格优于 E1-A**；若不成立，E1-A 的 LowBit 是必要兜底。两者都建模，决策见 decision.md。

---

## 6. 非源码参数清单（全部 ASSUMED）

| 参数 | 源码值 | 压力值 | 状态 |
| --- | --- | --- | --- |
| `c_eq/c_sel` | 389 | 1 | 389=DERIVED；1=ASSUMED |
| `c_upd/c_sel` | 2 | 100 | 2=DERIVED（R1-1）；100=ASSUMED |
| `c_eq_e1` 公开操作数优化 | 389（保守） | 388 | 388=DERIVED 变体，非实测 |
| eq 能否跨读/写复用 | 建模 shared/separate 两种 | — | ASSUMED（E1 非上游电路） |
| 地址域有界 `[0,n−1]` | CONSTRUCTED | — | UNKNOWN（目标系统） |

**不得**把 `c_eq/c_sel=1` 或 `c_upd/c_sel=100` 的压力结果写成实测，也不得把当前串行 barrier 数外推为批处理 MPC 轮数。
