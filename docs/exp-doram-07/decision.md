# decision.md — EXP-DORAM-07 最终决策

> 基线：起始 `c545ddcb9a14853811e2333b132a75f1592f8566`；上游 `10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 决策时间：2026-11-23

---

## 0. 唯一最终决策：**CONDITIONAL_PASS**

按任务 §10 三选一规则：

- **PASS_TO_NEXT_STAGE 不成立**：虽然正确性全部通过，但“在 n/T 较小的多个代表性场景中总成本有稳定改善”这一条**不满足**。收益并非稳定：n=1024 时 T=64/256 的 10 个 cell 全部 E1 更慢，n=256,T=64 也只有 2/5 获益。不全矩阵稳定。
- **NO_GO 不成立**：未出现任何“无法保持原始语义 / Export 不一致 / 不变量失败 / 代表性负载无改善 / 优势仅来自 Python 细节 / 地址域假设不符”的触发条件。语义、Export、不变量在 800 次运行 + 100 组差分中全部通过；在 `T ≫ n` 场景有明确且随 T 单调增强的收益，且趋势由算法结构（O(T²) 早停历史扫描 vs O(n) 固定扫描）支持，不是单纯的 Python 实现细节。
- **CONDITIONAL_PASS 成立**：正确性通过；Query 有明显改善（最高 9.5×）；但**总成本收益依赖 n/T 比例与写入比例**，完全符合 CONDITIONAL_PASS 的定义。

**后续只允许**：确定适用工作负载（`T ≳ 16n` 且非密集写入更优），不扩大密码学构造，不进入 MPC 电路实现。

---

## 1. 验收标准逐条结果（任务 §9）

| # | 标准 | 结果 |
| --- | --- | --- |
| 1 | 固定起始 commit 正确 | ✅ 分支 main，HEAD=`c545ddc...`，工作区 clean，上游 commit 可达 |
| 2 | 上游语义核查完成 | ✅ `semantic-audit.md`，10 项逐条核查，未发现影子表语义障碍 |
| 3 | E0/E1 操作序列完全一致 | ✅ 同一 workload seed，双字段 fetch/trace 地址一致 |
| 4 | 所有语义测试通过 | ✅ 12 项语义测试全过 |
| 5 | ≥100 组固定种子差分测试通过 | ✅ 100 组，每组逐步比对 Query/不变量/Export |
| 6 | Export 逐字段完全一致 | ✅ 800 次运行 `export_ok=1`，逐字段比对 |
| 7 | 每步影子表与历史最新值一致 | ✅ 100 组差分 + 全矩阵每步 `invariant_ok=1` |
| 8 | 至少一组代表性性能矩阵 | ✅ 全矩阵 4×4×5=80 cell，未缩减 |
| 9 | 原始/汇总 CSV 可复现 | ✅ 800×24 与 160×29，固定 seed，确定性输出 |
| 10 | 区分抽象操作成本与真实 MPC 成本 | ✅ `benchmark-methodology.md` §2.5/2.6 与 `design.md` 明确标注 |
| 11 | 未修改上游源码及旧实验文件 | ✅ 仅新增 `src/exp_doram_07/`、`tests/test_exp_doram_07.py`、`docs/exp-doram-07/`、`results/exp_doram_07/` |
| 12 | 新增文件只在指定目录 | ✅ 同上 |

完整测试：`python -m unittest discover -s tests -v` → `Ran 43 tests ... OK`（本轮 24 项 + 既有 19 项，无导入冲突）；`python -m unittest discover -s tests -p "test_exp_doram_07.py" -v` → `Ran 24 tests ... OK`。实际输出见本报告 §4。

---

## 2. 语义核查结论（摘要）

- 上游无 `HistoricalKV` 类，真实对应是 memory trace 5 列 + Fetch/Prove 电路（`semantic-audit.md` §0）。
- Query 读**最新**历史匹配值、未写返 0、step 0 走 zeroShare 不构造 Fetch、每非初始步恒一次 Fetch、`fetch_address≠trace_address`（NOOP）、每步一条历史行、Export 保留被覆盖旧值——均由源码直接确认（SRC）。
- **固定地址域 `[0,n-1]` 是本轮模型假设，不是上游源码事实**（源码地址为域元素，无 n 限制）；模型对越界地址按“未写=0”处理。地址域假设问题在任务 NO_GO 列表中，但因结论是条件性且与假设一致，不触发 NO_GO，仅在边界声明中记录。

---

## 3. 性能原始数据与汇总（摘要）

- 原始：`results/exp_doram_07/benchmark_raw.csv`（800 行 × 24 字段）。
- 汇总：`results/exp_doram_07/benchmark_summary.csv`（160 行 × 29 字段，含中位数/Q1/Q3）。
- 全矩阵 80 cell × 5 工作负载 × 5 重复；三个一致性标志全为 1。
- Query 最高加速 9.49×（n=256,T=4096,uniform）；总成本最高加速 4.56×（n=1024,T=4096,sparse_write）。
- 全矩阵 63/80 cell 总成本 E1 更快；失败集中在 `T ≲ n` 区域。

### 主要成本交叉点

| 地址域 n | E1 开始稳定获益的 T | 证据 |
| --- | --- | --- |
| 16 | T≥256（5/5） | T=64 仅 4/5 |
| 64 | T≥256（5/5） | T=64 仅 3/5 |
| 256 | T≥1024（5/5） | T=64 仅 2/5，T=256 为 4/5 |
| 1024 | T≥1024（5/5） | T=64/256 均 0/5 |

经验交叉：`T ≳ 16n` 时 E1 在全部工作负载占优；`T ≲ n` 时 E1 必败。写入比例也影响幅度：dense_write（75% 写）因 E1 每次写要 O(n) 全扫，优势显著小于 uniform/sparse_write（例：n=256,T=4096，dense_write 2.60× vs single_hot 4.59×）。

---

## 4. 完整测试结果

`python -m unittest discover -s tests -p "test_exp_doram_07.py" -v`：`Ran 24 tests ... OK`（12 语义 + 2 计数器 + 9 边界 + 1 组 100 序列差分）。
`python -m src.exp_doram_07.benchmark`：80 个 cell 全部 `export/returns/invariant OK`，800 原始行 + 160 汇总行落盘。
全仓库 `python -m unittest discover -s tests -v`：本轮测试与既有 `test_correctness.py` / `test_fetch_r1.py` 并存，无导入冲突。

---

## 5. 最终决策及理由

**CONDITIONAL_PASS**。

理由：

1. **正确性与语义保持是硬的**：上游语义逐条核查；E0/E1 逐字段 Export 一致；每步不变量成立；100 组差分 + 800 次 benchmark 全部通过。NO_GO 的语义/Export/不变量触发项全部排除。
2. **收益真实存在但有明确边界**：在 `T ≫ n`（本轮 `T ≳ 16n`）时，总成本随 T 单调增大地改善（n=1024,T=4096 达 3.51×），Query 改善更显著（最高 9.49×）；这是 O(T²) 历史早停扫描与 O(n) 固定扫描的结构性差异，不是随机噪声。
3. **但不能给 PASS_TO_NEXT_STAGE**：n=1024,T=64/256 的全部 cell E1 更慢，n=256,T=64 也几乎无优势。收益依赖 n/T 与写入比例，不满足“多个代表性场景稳定改善”。若据此直接进入 MPC 原语成本评估，会在小 T 大 n 区误导投入。
4. **不是 NO_GO**：代表性负载（`T ≫ n`）确有端到端收益，且抽象计数与复杂度模型一致；地址域 `[0,n-1]` 虽为模型假设，但与任务给定的“固定地址域”前提一致，不构成对目标系统的证伪。

**后续限定**：先确定适用工作负载（`T ≳ 16n`，避免 dense_write 主导），再评估 MPC 层相等/选择原语成本；不得直接宣称论文创新，不得把 Python 数字外推为 MPC 成本。

---

## 6. 未完成项目（最多三个，任务 §11 要求）

1. **MPC 层验证未做**：E1 的相等判断与选择尚未算术化为秘密共享原语，未计乘法门/通信轮数；`design.md` Q5/Q7/Q8 标为 D2。
2. **影子表未纳入 R1CS/公开证明**：不变量目前只是 Python 断言；纳入证明需新增的约束族仅列在 `design.md` Q4，未构造（D3）。
3. **地址域假设的实证**：`n` 固定且地址限于 `[0,n-1]` 是模型假设，未在目标 VDORAM 工作负载上验证其符合性；超出域按“未写=0”处理是模型约定。

---

## 7. 边界声明（明确不声称）

- 不声称 E1 具备 obliviousness、恶意安全或公开可验证性；固定长度全域扫描 ≠ 完整 obliviousness。
- 不声称 Python 毫秒数或抽象计数器等于 MPC 成本；二者不可换算。
- 不声称上游存在 `HistoricalKV` 类；5 列 trace 与 Fetch/Prove 电路才是真实源码实体。
- 未修改上游源码、未接入 ORAM、未改 C#/Rust witness 契约、未碰 EXP-DORAM-01..06；本轮完成后停止，不启动 EXP-DORAM-08。
