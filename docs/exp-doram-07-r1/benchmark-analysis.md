# EXP-DORAM-07-R1 — 性能实验分析

> 数据：`results/exp_doram_07_r1/benchmark_raw.csv`（1200 行 = 80 cell × 5 rep × 3 impl）、
> `benchmark_summary.csv`（240 行 = 80 cell × 3 impl）。
> 参数：n∈{16,64,256,1024} × T∈{64,256,1024,4096} × 5 workload × 5 rep，同 seed 同序列。
> 汇总口径：中位数（Q1/Q3 见 CSV）。分析脚本：`src/exp_doram_07_r1/analyze.py`。
> 三模型 export/returns/invariant 全部通过（1200/1200 行标志 = 1）。
> **所有时间与计数均为参考模型指标，不是 MPC 门数/轮数/成本**（见 cost-model.md）。

## 0. 三组对比总览

### A. E0-EarlyExit vs E0-FullScan（提前退出带来的明文实现差异）

- 总扫描量比 `E0-FullScan / E0-EarlyExit`：min 1.02，median 2.89，max 121.29（uniform 子集 max 102.2 在 n=16,T=4096）。
- 提前退出在**热点/高密度命中**时收益极大（例 n=16,T=4096 uniform：EE 164,138 vs FS 16,773,120，约 102×）；
  在命中靠后的 workload（如 sparse_write）收益较小。
- Python 时间差异方向一致：例 n=16,T=256 uniform EE execute 0.00212s vs FS 0.00628s；
  n=256,T=4096 uniform EE 0.23842s vs FS 1.54616s。
- **解释**：EarlyExit 是明文 shortcut（逆序命中即返回），不是原始电路的语义（原始电路无提前退出，
  fetch-semantics.md §1-2）。此对比只量化「田野式中提前退出相对忠实全扫描能省多少」，
  **不能**用来声称原始 VDORAM 有这些收益。

### B. E0-FullScan vs E1（全历史扫描 vs 固定状态表扫描）

- E1 相对 E0-FullScan 的**总扫描量比** `scan = history_rows_scanned+history_equality_checks`（E0）对
  `shadow_slots_scanned+shadow_equality_checks`（E1）：
  - **E1 < E0-FullScan 在 50/80 cells**（全部 T/n ≥ 4 的 cell）。
  - E1 ≥ E0-FullScan 在 30/80 cells（全部 T/n ≤ 1 的 cell）。
  - 比值跨度：n=16,T=4096 sparse_write 最低 0.009（E1 扫描量仅 FullScan 的 0.9%）；
    n=1024,T=64 dense_write 最高 55.87（E1 比 FullScan 高 56×）。
- Python Execute 比值（E1/FullScan）：min 0.023, max 21.51, median 0.664；`cells<1 = 50/80`。
- 扫描方向与时间方向**逐 cell 一致**（80/80）。

### C. Execute vs End-to-end（Export 是否改变结论）

- Export 中位数占 Execute 中位数的比例最大 0.023（E1, n=16,T=1024 single_hotspot），
  E0-FullScan 最大 0.013。Export 成本相对 Execute 可忽略。
- Execute 比值与 End-to-end 比值几乎相同（median 均 0.664；例 n=16,T=64 uniform 0.856 vs 0.856）。
- **结论**：Export 不改变任何 cell 的胜负；用 Execute 或 End-to-end 得到相同判断。

## 1. 八个分析要求的直接回答

**Q1. E1 相对 E0-FullScan 的总扫描量是否下降？**
是，但**有明确条件**：在 50/80 cell（全部 T/n ≥ 4）下降；在 30/80 cell（T/n ≤ 1）反而上升。
不是无条件下降。

**Q2. 下降是否来自真实的算法结构差异？**
是。结构差异（不是参数微调）：
- E0-FullScan 单步代价随**历史长度**增长：总 `history_rows_scanned = T(T-1)/2`（与地址分布无关），
  T=4096 时 16,773,120 行；
- E1 单步代价只随**固定域 n** 增长：总 `shadow_slots_scanned = n·(fetch 数 + STORE 数)`，与历史长度无关。
- 因此当 T 相对 n 足够大，FullScan 的 O(T²) 历史扫描超过 E1 的 O(n·T) 固定表扫描。这是结构性的交叉，
  不是 workload 偏置。但须注意两类「扫描单元」权重在真实电路中未必相等（Q8）。

**Q3. dense_write 是否抵消 Query 的收益？**
**部分抵消但未翻转（在 T/n≥4 区域）**：
- dense_write 中 E1 的 `update_time / (fetch_time+update_time)` ≈ 0.42–0.48（约 43%），
  即全表 Update 成本接近一半；
- 总扫描比在 T/n=4 时 dense_write 0.868–0.937（仍 <1，但比 sparse_write 的 0.548 明显收窄）；
- 在 T/n≤1 时 dense_write 是最差的 cell（n=1024,T=64 比值 55.87）。
- 结论：dense_write **削弱**优势但不单独翻转已达 T/n≥4 的 cell；翻转由 T/n 主导。

**Q4. n/T 比例变化如何影响结果？**
胜负边界干净地落在 T/n 的 1 与 4 之间（矩阵中无 2、3）：
- T/n = 0.062：0 胜 / 5 负；T/n = 0.25：0/10；T/n = 1：0/15；
- T/n = 4：20 胜 / 0 负；T/n = 16：15/0；T/n = 64：10/0；T/n = 256：5/0。
- 规律：**T ≳ 4n 稳定获益，T ≲ n 必败**。n 增大在固定 T 下等同 T/n 减小，因此大 n 小 T 最不利。

**Q5. E0-EarlyExit 与 E0-FullScan 的差距有多大？**
FS/EE 总扫描比 median 2.89，max 121.29。命中越靠新（热点/密集写）差距越大：
n=16,T=4096 uniform 约 102×，n=1024,T=4096 uniform 约 4×（受 n/T 影响）。
这说明旧 E0 EarlyExit 数据会显著**低估**忠实全扫描的成本，不能作为原始电路基线。

**Q6. 原 EXP-DORAM-07 的 `T ≳ 16n` 经验阈值是否仍成立？**
**不再成立，须修正**。原阈值基于 E0-EarlyExit 基线；换成 E0-FullScan 后，
E1 的扫描优势从 T/n ≥ 4 就开始（T/n=4 的 20 个 cell 全部 E1 扫描更低，Execute 比值 0.023–0.94），
而 T/n=1 全部失败。因此本轮的经验结论应写为：
> 在忠实全历史 Fetch 基线下，影子表的总扫描优势约在 `T ≳ 4n` 开始稳定；
> `T ≲ n` 必败。原 `T ≳ 16n` 是 EarlyExit 基线下过度保守的阈值。
注意 4n/16n 均为**本参数矩阵的经验观察**，不是电路级保证；且 E1 单扫描单元权重与 E0 不同（Q8）。

**Q7. Python 时间和抽象操作计数是否一致？**
一致（方向层面）：80/80 cell 中，E1 相对 FullScan 的扫描比 <1 ⇔ Execute 比 <1。
FullScan 的 execute_median 在固定 n 下随 T 单调递增（uniform 四组均 True，T=64≈0.0007s → T=4096≈1.3–1.55s），
符合 T(T-1)/2 的计数预期。但**比值幅度不一致**（扫描比最低 0.009 vs 时间比最低 0.023），
因为 Python 有固定开销、缓存与分支成本，不能把比值等同。

**Q8. 哪些指标只能用于算法比较，不能外推 MPC 成本？**
全部本轮指标都属此类，特别是：
- `history_rows_scanned` / `history_equality_checks`：只表示电路纳入的行数与相等判断次数，
  不等于乘法门数或通信轮数（FieldNorm/LowBit/SelectCompose 的真实门数未纳入一手证据，判定 UNKNOWN）；
- `shadow_slots_scanned` / `shadow_equality_checks`：固定表扫描次数，不能换算成 E1 电路规模；
- 所有 `*_time_s`：Python 墙钟，含解释器开销；
- 扫描比与 Execute 比：只描述参考模型的算法结构差异。
任何向 MPC 成本/隐私/可验证性的外推都需后续独立阶段，本轮不做。

## 2. 数据可复现性

- 生成：`PYTHONPATH="src" python -m src.exp_doram_07_r1.benchmark`（约 4.5 分钟，80 cell × 3 impl × 5 rep）。
- 分析：`PYTHONPATH="src" python -m src.exp_doram_07_r1.analyze`。
- workload 由 `(seed|n|T|workload)` 字符串种子确定；同参数同序列。
- 每次 rep 内三模型用同一 `trace` 对象；正确性硬校验在每 cell 最后一次 rep 上执行，失败即抛错。
- 原始 CSV 保留每 rep 的 n/T/workload/seed/rep、三类时间、Execute/Export/End-to-end、全部计数与正确性标志；
  汇总保留中位数/Q1/Q3 与 E1 相对 FullScan 的三类比值。

## 3. 结论边界

本轮只证明：**在明文参考模型、固定地址域假设下，忠实全历史 Fetch 基线中影子表有结构性的扫描优势，
但优势取决于 T/n 与写入比例。** 不证明：MPC/R1CS 成本下降、真实运行时间收益、可验证性或隐私性质。
地址域适用性见 address-domain-audit.md。
