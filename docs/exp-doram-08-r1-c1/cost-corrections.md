# EXP-DORAM-08-R1-C1：成本闭式与交叉条件勘误

> 性质：纯成本模型勘误。基线 `584ec252cb1ff4a20997b507ee1c506aa66b61b3`（EXP-DORAM-08-R1，`CONDITIONAL_PASS`）保留为历史基线，不静默改写。
> 固定上游：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`。
> 本轮不重做源码审计、不重新论证 FieldSub/FieldNeg、不重新论证 E1 唯一槽位、不实现 MPC。
> 所有成本均为符号推导（秘密乘法计数），不是 MPC 实测、不是 R1CS 约束数、不是网络字节数。

---

## 1. 勘误一：E1-A 交叉阈值把 `fetch_a(1)` 当成线性系数

### 1.1 R1 原代码（错误）

`src/exp_doram_08_r1/costs.py`，`cross_threshold_n()`：

```python
fetch_coef = p.fetch_a(1) if variant == "A" else p.fetch_b(1)
# fetch_X(n) = fetch_coef*n + const; const cancels at exact-cross derivation
...
denom = (T - 1) * fetch_coef + w0 * p.c_upd_separate + wpos * upd_per_pos
K = p.c_eq + p.c_sel + 3
numer = K * T * (T - 1) // 2 - p.lowbit_and * (T - 1)
return numer / denom
```

### 1.2 错误原因

`fetch_a(n) = 393n − 2` 含常数项 `−2`。因此 `fetch_a(1) = 391`，**不是** n 的线性系数 `393`。R1 把 `391` 当作系数，同时分子保留 E0 的 `−2(T−1)` 却没有减去 E1-A 自身的 `−2(T−1)`（本应相消）。两个偏差叠加，使 E1-A 阈值系统性偏大：

- 分母系数 `391 < 393` → 阈值被放大约 `393/391 ≈ 1.0051`；
- 分子多减 `2(T−1)` → 阈值被缩小少许；
- 净效果为随 T 增大的正偏差（见 1.5）。

E1-B 因 `fetch_b(n) = 390n` 无常数项，`fetch_b(1) = 390` 恰为线性系数，分子保留 `−2(T−1)` 正确（E1-B 无常数项可与之相消），故 **E1-B 原实现与阈值结果均正确，无需撤回**。

### 1.3 修正后代码（显式拆分线性系数与常数项）

```python
K = p.c_eq + p.c_sel + p.lowbit_not + p.lowbit_and   # 393
b = p.lowbit_and                                     # 2
a0 = K * T * (T - 1) // 2 - b * (T - 1)              # C_E0(T)
if variant == "A":
    fx, cx = K, -b          # fetch_A(n) = 393n - 2
elif variant == "B":
    fx, cx = p.c_eq + p.c_sel, 0   # fetch_B(n) = 390n
U = w0 * p.c_upd_separate + wpos * upd_per_pos
numer = a0 - cx * (T - 1)
denom = fx * (T - 1) + U
return numer / denom
```

### 1.4 修正后公式

| 场景 | 条件 | 精确阈值 |
| --- | --- | --- |
| E1-A 只读 | `(T−1)(393n−2) < 393T(T−1)/2 − 2(T−1)` | `n < T/2` |
| E1-B 只读 | `390n(T−1) < 393T(T−1)/2 − 2(T−1)` | `n < (393T−4)/780` |
| 读写混合 | 见 `crossover-analysis.md` 第 4 节 | `n < [A0 − cx(T−1)] / [fx(T−1)+U]` |

`T > 1` 时 E1-A 的 `−2(T−1)` 与 E0 的 `−2(T−1)` 完全抵消，得到干净的 `n < T/2`。这与 R1 文档中已写下的符号结论一致——**错误只在代码实现和 CSV 的 `threshold_n_continuous` 列，不在 R1 文档的符号推导**。

### 1.5 影响范围与需撤回的旧数字

受影响：`src/exp_doram_08_r1/costs.py::cross_threshold_n`、`results/exp_doram_08_r1/sensitivity_raw.csv` 的 `threshold_n_continuous` 列（仅 E1-A 行）、由该列聚合的任何叙述。

**撤回** R1 `sensitivity_raw.csv` 中 `(c_eq=389, c_upd=2, store_ratio=0.0, update_mode=shared)` 下 E1-A 的四个阈值；C1 重算值如下（E1-B 列保留，未变）：

| T | 旧 E1-A（撤回） | C1 E1-A（正确） | E1-B（不变） |
| --- | --- | --- | --- |
| 64 | 32.1586 | **32.0000** | 32.2410 |
| 256 | 128.6496 | **128.0000** | 128.9795 |
| 1024 | 514.6138 | **512.0000** | 515.9333 |
| 4096 | 2058.4706 | **2048.0000** | 2063.7487 |

旧偏差随 T 约按 `+0.51%·T/2` 增长，最大 `+10.47`（T=4096）。在离散采样网格 `n∈{16,64,256,1024}`、`T∈{64,256,1024,4096}` 上，`winner` 列**未发生变化**（阈值偏差不足以跨越网格点），故 R1 基于胜负计数的敏感性结论保留；但任何引用上述四个具体阈值数字的表述必须改为 C1 值。

---

## 2. 勘误二：E1 历史追加闭式与逐步模型不一致

### 2.1 R1 原代码（错误）

```python
# e1a_total_closed / e1b_total_closed (R1):
return (T - 1) * fetch + upd0 + updpos + (T - 1) * p.append_mults   # <-- 错

# 但逐步模型每一步都加 append：
def e1a_step(step, n, is_store, p, share_eq=True):
    ...
    return total + p.append_mults        # step 0..T-1 共 T 次
```

即 `e1a_total_by_sum(T) − e1a_total_closed(T) = append_mults`，`e1b` 同理。`e0_total_closed` 用 `T * append_mults`，是三者中正确的那个。R1 的 `test_three_models_common_append` 还把错误的 `(T−1)*7` 写成了断言，等于固化了不一致。

### 2.2 语义依据（为什么是 T 次）

固定 commit 的 `ZkProgramExecutor.cs`：

- L116：`for (globalStepCounter = 0; ; globalStepCounter++)`，循环从 **step 0** 开始；
- L393-405：每个 step 的 "Save memory trace" 块无条件调用 `AddMemoryTrace(incomingTraceRow)`；
- L205-206：step 0 的特判只影响 `memVal = zeroShare`（不构造 Fetch 电路），**不跳过** trace 行追加；
- step 0 的 trace 行由公开 `global_step_counterField` 与 `out_trace_*` 组成（L396-403）。

因此历史追加事件在每个 step 都发生一次，共 `T` 次。修正方向是**把闭式改为 `T * append_mults` 以匹配逐步模型**，而不是反过来删掉 step 0 的追加（那需要改逐步模型、成本函数与三处语义，且违背源码）。

### 2.3 修正后代码与公式

```python
# e1a_total_closed / e1b_total_closed (R1-C1):
if T <= 0:
    return 0
...
return (T - 1) * fetch + upd0 + updpos + T * p.append_mults
```

并将早退条件从 `if T <= 0 or n <= 0: return 0` 改为 `if T <= 0: return 0`：当 `n<=0`（模型域外）时让 `fetch=0, upd=0`、追加仍为 `T·append_mults`，与逐步函数行为一致。

统一追加成本：

```
C_append(T) = T * append_mults        (E0 / E1-A / E1-B 三者相同)
```

### 2.4 影响范围与需撤回项

- 撤回 `e1a_total_closed` / `e1b_total_closed` 中 `(T−1)*append_mults` 的写法；
- 撤回 `tests/test_exp_doram_08_r1.py::test_three_models_common_append` 中 E1 增量 `(T−1)*7` 的断言，改为 `T*7` 并对逐步/闭式双检；
- **数值影响**：默认 `CostParams.append_mults = 0`（Fetch 电路不含历史追加），故 R1 及 C1 所有 CSV 的 `e0_cost`/`e1_cost`/`winner`/`cost_ratio` **完全不变**。该错误是模型自洽性问题，不是已报告成本数字的错算；一旦 `append_mults ≠ 0`，R1 的 E1 闭式会少算一个 `append_mults`。

---

## 3. 不受影响的部分（明确保留）

1. R1-1 / R1-2 / R1-3 三项源码勘误结论（`c_upd_shared=2`、`c_upd_separate=391`、`E1-A=393n−2`、`E1-B=390n`、step 0 STORE 强制 separate）——本轮未重做源码审计，未改动这些参数与构造。
2. E0 / E1-A / E1-B 的逐步模型 `e0_step` / `e1a_step` / `e1b_step`（除追加项与闭式对齐外无变化）。
3. 线性运算、当前串行执行器 barrier、三元组与在线域元素模型（`e0_linear` 等）未改动。
4. R1 文档 `source-corrections.md`、`construction-comparison.md`、`cost-model.md`、`sensitivity-analysis.md` 原文一字未改；本文件与 `crossover-analysis.md` 只说明"修正了什么"、不覆盖历史。
5. R1 的敏感性胜负结论：`(c_eq=389, c_upd=2)` 源码权重下 E1 在 10/16 个（`T/n≥4`）网格 cell 更便宜；压力权重 `c_eq/c_sel=1, c_upd/c_sel=100` 下 90% STORE 仅 3/16——因 `winner` 未变，结论保留。
6. R1 最终决策 `CONDITIONAL_PASS` 的实质理由（有界域、权重依赖、eq 复用未证、后端缺 SPDZ MAC/auth）不变；C1 决策见 `decision.md`。

## 4. 修改文件清单（仅授权路径）

| 文件 | 变更 |
| --- | --- |
| `src/exp_doram_08_r1/costs.py` | 修 `cross_threshold_n`；修 E1-A/E1-B 闭式追加项与早退条件 |
| `src/exp_doram_08_r1/sensitivity.py` | 三份 CSV 增加 `model_version=R1-C1` 列（可追溯性） |
| `tests/test_exp_doram_08_r1.py` | 修错误断言；新增精确交叉、append 边界、逐步/闭式一致性测试 |
| `results/exp_doram_08_r1/*.csv` | 重新生成（行数不变；E1-A 阈值列修正；新增版本列） |
| `docs/exp-doram-08-r1-c1/` | 本轮新增四份文档 |

未改：`docs/exp-doram-08-r1/`（R1 历史原文）、`docs/exp-doram-08/`、任何历史 CSV、上游 VDORAM、C#/Rust 执行路径。
