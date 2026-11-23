# EXP-DORAM-07-R1 — 成本模型与计时边界

> 三模型：E0-EarlyExit（只读适配器，原文明实现）、E0-FullScan（忠实全历史扫描）、E1-ShadowState（固定 n 槽位全域扫描）。
> 本文件定义计数器与时间的口径，防止把三类成本混为一谈。所有代码在 `src/exp_doram_07_r1/`。

## 1. 三类成本必须分开（任务 5.3）

| 类别 | 含义 | 可否外推 MPC 成本 |
|---|---|---|
| (a) 算法扫描次数 | 抽象参考模型的操作计数（`*_scanned`、`*_equality_checks` 等） | **否**。只是 Python 层机械计数 |
| (b) Python 实际运行时间 | `perf_counter` 墙钟，`*_time_s` / `execute_time_s` / `end_to_end_s` | **否**。含解释器开销、缓存、分支预测，与隐私计算无关 |
| (c) 未来 MPC 原语调用次数 | 乘法门、布尔 AND、通信轮数 | 本轮**不测量、不估计**。fetch-semantics.md §3 明确列为 UNKNOWN |

全历史比较只说明原始电路对历史记录的**扫描范围**（每行一个 FieldEquals + 每行一个 SelectCompose 乘法）。
不能仅凭 `history_rows_scanned` 推导 R1CS 乘法门数或通信轮数；也不能从 `shadow_slots_scanned` 推出 E1 的电路规模。
本轮结论仅限 (a) 算法结构层与 (b) 参考实现时间层，(c) 留给未来的 MPC 成本模型阶段（若决策允许）。

## 2. 扫描计数指标（任务 5.1，逐个模型）

| 计数器 | E0-EarlyExit（原实现） | E0-FullScan | E1-ShadowState |
|---|---|---|---|
| `history_rows_scanned` | 逆序扫描到命中为止的行数 | **每次 Fetch = 当时可见全部历史行数** | 0（不扫历史） |
| `history_equality_checks` | = 命中位置的行数 | = 当时可见全部历史行数 | 0 |
| `shadow_slots_scanned` | 0 | 0 | 每次 Fetch/Update = n |
| `shadow_equality_checks` | 0 | 0 | 每次 Fetch/Update = n |
| `selection_operations` | 命中时 1 | 有匹配时 1（低比特 one-hot 选一个输出） | 地址在域内时 1 |
| `update_operations` | 0 | 0 | 域内 STORE 时 1 |
| `history_append_operations` | 每步 1 | 每步 1 | 每步 1 |
| `fetch_count` | 每个 step>0 各 1 | 每个 step>0 各 1 | 每个 step>0 各 1 |
| `query_count` | LOAD 步数 | LOAD 步数 | LOAD 步数 |
| `update_count` | STORE 步数 | STORE 步数 | STORE 步数 |

关键区分：E0-FullScan 的 `history_rows_scanned` 反映原始电路的**全历史扫描范围**；
E1 的 `shadow_slots_scanned` 反映固定表全域扫描范围。二者是不同结构的算法计数，
比较时以「总扫描量」(history+shadow 的相关项之和) 为准，但须记住它们的单步代价权重未必相同（见 §5）。

## 3. 时间指标与计时边界（任务 5.2）

- `fetch_time_s`：所有 Fetch 的扫描耗时累计。E0-EarlyExit 由原实现的 `query_time_s` 映射而来（原实现不区分 fetch/query 计时）。
- `query_time_s`：LOAD 步的 Fetch 耗时子集（`query()` 调 `fetch()`）。对 E0-EarlyExit 是 fetch 时间的镜像（口径差异已标注）。
- `update_time_s`：状态更新耗时（E1 的 `_state_update`；E0 为空操作≈0）。
- `append_time_s`：历史行追加 + 行承诺计算耗时（三模型相同逻辑）。
- `export_time_s`：`export()` 的耗时，**独立于 Execute 计时**。
- `execute_time_s`：**Execute = 所有 Fetch、Query、Update、History append 的执行耗时**，
  即 `run()` 中对整条 trace 逐步 `execute_step` 的墙钟；计时边界从 `run()` 内 `t0` 到循环结束，**不含**
  模型初始化、workload 生成、Export。
- `end_to_end_s`：**End-to-end = Execute + Export** = `execute_time_s + export_time_s`。

三模型使用同一 workload 记录（同 seed、同 n/T、同事件），各自独立计时；
`gc.collect()` 在计时前调用，避免 GC 暂停落入执行计时。计时用 `time.perf_counter`，不用 tracemalloc。

## 4. 时间字段在 CSV 中的落位

`benchmark_raw.csv` 每行（每次重复）包含三模型各自的 `fetch_s / update_s / append_s / export_s /
execute_s / end_to_end_s`，以及扫描/操作计数和正确性标志。
`benchmark_summary.csv` 报告每个 (impl, n, T, workload) 的中位数、Q1、Q3 及 E1 相对 E0-FullScan 的比值。

## 5. 对「总扫描量下降」的正确解读

任务 7.4 要求判断 E1 相对 E0-FullScan 的总扫描量是否下降、是否来自真实算法结构差异。
本模型口径下：

- E0-FullScan 总 `history_rows_scanned` ≈ T(T-1)/2（每步扫当时全部历史，与地址分布无关）。
- E1 总 `shadow_slots_scanned` ≈ n·(Fetch 数 + STORE 数)（与历史长度无关，只与 n 和写比例有关）。

因此优势来自结构差异：E0-FullScan 的单步代价随**历史长度**增长，E1 的单步代价只随**固定域 n** 增长。
但二者的「一次扫描单元」权重在真实 MPC 电路中未必相等（E0 每行含 FieldEquals+SelectCompose 乘法；
E1 每槽含一次相等判断与一次 select/write），故本轮只报告**扫描次数**层面的比较，
并在 benchmark-analysis.md 明确：不把次数比直接当作电路门数比。

## 6. 不得混淆的边界

1. 不把 Python 时间换算成真实 MPC 时间/成本。
2. 不把 `history_rows_scanned` 当作 R1CS 约束数或通信轮数。
3. Export 时间单列，用 End-to-end 判断其是否改变结论。
4. E0-EarlyExit 的计时口径与原实现一致（fetch/query 不分），只用于比较 A（提前退出收益），
   不用于和 FullScan/E1 做严格时间对比时的口径混用——比较 A 时以扫描计数为主、时间为辅。
