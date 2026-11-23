# vdoram-historicalkv-experiment

EXP-DORAM-01（含 **R1 修正轮**）：HistoricalKV 双结构替代方案可行性验证的独立实验工程。

- 上游基线：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`（NDSS'26 VDORAM artifact）
- 本轮不修改 VDORAM 上游、不实现 Path ORAM、不启动 Halo2、不声称普通模拟器有密码学安全性。
- 结论与证据见 [`docs/experiment-report.md`](docs/experiment-report.md) 与 [`docs/source-audit.md`](docs/source-audit.md)。
- 上游源码快照见 [`docs/source-snapshot/`](docs/source-snapshot/)（17 个文件，头部含 PATH/BLOB SHA）。

> **R1 修正轮**：研究负责人验收发现旧轮 E0 只在 LOAD 时 Fetch、E1 每步查找，工作负载不一致，
> 旧 `4–23×` 结论已撤回。R1 统一为每步（step 0 除外）都 Fetch、地址序列一致，重测数据见报告 §6。
> 旧轮原始数据完整保留，未被覆盖。

## 后续阶段（协议/源码审计）

- **EXP-DORAM-02**（ORAM 状态组件兼容性审计）：8 份文档见 [`docs/exp-doram-02/`](docs/exp-doram-02/)，含论文带页码摘录与 25 个源码证据。
- **EXP-DORAM-02-R1**（State-Carrying Feasibility Check）：见 [`docs/exp-doram-02-r1/state-carrying-feasibility.md`](docs/exp-doram-02-r1/state-carrying-feasibility.md)。核查确认 registers 份额跨 session 由外层执行器持有、可推广到 ORAM 状态载体机制；**撤回**原"session 注销 → 份额销毁 → 状态无法跨步"推理。
- **当前决策**（[`decision-revision.md`](docs/exp-doram-02-r1/decision-revision.md)）：整体 **HOLD**；NO_GO 严格限定为"直接移植现有 2-3 方 DORAM 且不改 VDORAM 执行/证明契约"。原 [`decision.md`](docs/exp-doram-02/decision.md) 保留为历史记录。

## 三实现定位

| 实现 | 做法 | 本轮定位 |
| --- | --- | --- |
| E0 | VDORAM 原始 HistoricalKV 线性扫描（选择语义 + 执行节奏等价参考模型） | 真实基线 |
| E1 | CurrentStateStore + Append-only HistoricalLog | 功能参考模型（**非 ORAM**） |
| E2 | MPC Path ORAM + append-only log | 后续目标；本轮仅源码级接口审计 |

## 目录

```
├── README.md
├── docs/
│   ├── EXP-DORAM-01-plan.md      # 任务设计包原文（scope 冻结）
│   ├── source-audit.md           # 上游源码核查 + E2 接口审计
│   ├── experiment-report.md      # 性能/正确性/差异与结论（含 R1 修正）
│   └── source-snapshot/          # 固定 commit 的源码证据（17 文件）
├── src/
│   ├── oracle.py                 # 独立真值
│   ├── baseline/e0_linear_scan.py
│   ├── dual_store/e1_dual_store.py
│   ├── trace/
│   │   ├── generator.py          # 旧轮轨迹（单 address 字段，存档）
│   │   └── generator_r1.py       # R1 轨迹（fetch_address / trace_address 分离）
│   └── benchmark/
│       ├── benchmark.py          # 旧轮 benchmark（存档）
│       └── benchmark_r1.py       # R1 benchmark（统一 Fetch 工作负载，权威）
├── tests/
│   ├── test_correctness.py       # 原有 12 项正确性测试
│   └── test_fetch_r1.py          # R1 新增 7 项 Fetch 一致性测试
├── data/traces/                  # 旧轮 16 个轨迹（JSONL）
├── data/traces/r1/               # R1 16 个双地址轨迹（JSONL）
├── data/results/                 # 旧轮 + r1_* 原始 CSV / 汇总 / 测试输出
└── scripts/fetch_snapshot.py     # 经 GitHub API 取源码快照
```

## 复现（Windows / Python 3.13）

```bash
# 旧轮（存档）
PYTHONPATH="." python -m src.trace.generator
PYTHONPATH="." python -m unittest tests.test_correctness -v
PYTHONPATH="." python -m src.benchmark.benchmark

# R1 修正轮（权威）
PYTHONPATH="." python -m src.trace.generator_r1
PYTHONPATH="." python -m unittest tests.test_fetch_r1 -v
PYTHONPATH="." python -m src.benchmark.benchmark_r1
```

## 关键结论（R1 摘要）

- E1 双结构在统一 Fetch 工作负载下仍保持 HistoricalKV 语义，5 列历史记录 + 逐行承诺完整保留（旧 12 项 + R1 7 项全过，16 轨迹与 oracle 一致，Fetch 地址序列逐项相同）。
- 旧 `4–23×` 加速比因工作负载不一致已撤回。R1 重测：统一 T-1 次 Fetch 后，E1 查询总耗时仍显著低于 E0（9.4×–51.8×，随 T 增长）；但这只是参考数据结构的查询复杂度差异，**不是 VDORAM/ORAM 性能**。
- 总执行时间出现 R1 新现象：小 T 时 E1 略慢（承诺开销），T ≥ 512 时 E0 反超（每步全历史扫描 O(T²)），T=1024 时 E0 约为 E1 的 1.6–2.2×。
- 源码级 ORAM 接入只确认到 VM 输入钩子（`in_mem_val`）与 session 链；ORAM 内部状态跨 step 参与 MPC/证明为 UNKNOWN。
- 决策：交研究负责人验收；其建议下一步先做 ORAM 状态组件（stash/position map/路径读写）的 MPC/证明兼容性设计，再决定是否进入 Path ORAM 原型。

标注体系：VERIFIED / INFERRED / BLOCKED / UNKNOWN，详见报告。
