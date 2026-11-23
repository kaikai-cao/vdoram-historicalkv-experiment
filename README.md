# vdoram-historicalkv-experiment

EXP-DORAM-01：HistoricalKV 双结构替代方案可行性验证的独立实验工程。

- 上游基线：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`（NDSS'26 VDORAM artifact）
- 本轮不修改 VDORAM 上游、不实现 Path ORAM、不启动 Halo2、不声称普通模拟器有密码学安全性。
- 结论与证据见 [`docs/experiment-report.md`](docs/experiment-report.md) 与 [`docs/source-audit.md`](docs/source-audit.md)。
- 上游源码快照见 [`docs/source-snapshot/`](docs/source-snapshot/)（17 个文件，头部含 PATH/BLOB SHA）。

## 三实现定位

| 实现 | 做法 | 本轮定位 |
| --- | --- | --- |
| E0 | VDORAM 原始 HistoricalKV 线性扫描（语义等价参考模型） | 真实基线 |
| E1 | CurrentStateStore + Append-only HistoricalLog | 功能参考模型（**非 ORAM**） |
| E2 | MPC Path ORAM + append-only log | 后续目标；本轮仅源码级接口审计 |

## 目录

```
├── README.md
├── docs/
│   ├── EXP-DORAM-01-plan.md      # 任务设计包原文（scope 冻结）
│   ├── source-audit.md           # 上游源码核查 + E2 接口审计
│   ├── experiment-report.md      # 性能/正确性/差异与结论
│   └── source-snapshot/          # 固定 commit 的源码证据（17 文件）
├── src/
│   ├── oracle.py                 # 独立真值
│   ├── baseline/e0_linear_scan.py
│   ├── dual_store/e1_dual_store.py
│   ├── trace/generator.py
│   └── benchmark/benchmark.py
├── tests/test_correctness.py     # 12 项正确性测试
├── data/traces/                  # 16 个固定种子轨迹（JSONL）
├── data/results/                 # 原始 CSV + 汇总 + 测试输出
└── scripts/fetch_snapshot.py     # 经 GitHub API 取源码快照
```

## 复现（Windows / Python 3.13）

```bash
PYTHONPATH="." python -m src.trace.generator           # 生成轨迹
PYTHONPATH="." python -m unittest tests.test_correctness -v   # 12 项测试
PYTHONPATH="." python -m src.benchmark.benchmark       # E0/E1 benchmark
```

## 关键结论（摘要）

- E1 双结构在功能上保持 HistoricalKV 语义，5 列历史记录 + 逐行承诺完整保留（12/12 测试通过，16 轨迹与独立 oracle 一致）。
- 纯查询耗时 E0/E1 加速比 4×–23×，随 T 增长扩大；但 E1 总执行时间反而更高（额外承诺计算），不可把「哈希表快于线性扫描」当价值结论。
- 源码级存在可行 ORAM 接入路径（`in_mem_val` 命名线 + MPC session 链），但具体 Path ORAM 构造与 MPC 成本为 UNKNOWN。
- 决策：交研究负责人验收，再决定是否进入真实 MPC Path ORAM 原型。

标注体系：VERIFIED / INFERRED / BLOCKED / UNKNOWN，详见报告。
