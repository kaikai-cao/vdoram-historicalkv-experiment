# EXP-DORAM-01 任务设计包（scope 冻结）

> 本文件记录本轮实验的原始范围，作为验收基准；范围不得在执行中扩大。
> 执行者：本次会话 · 启动日期：2026-11-23 · 状态：已执行完毕，待验收。

## 实验目标

验证 Current-state ORAM + Append-only Historical Log 是否能改善 VDORAM 的 HistoricalKV 在线查询，同时保留原有公开证明所需的信息。

## 本轮范围

- 复现原始线性扫描基线（E0）
- 建立统一访问轨迹
- 实现一个功能正确的双结构参考模型（E1）
- 测量不同规模下的查询工作量
- 检查历史日志与原证明输入的兼容性
- 对 MPC Executor 和证明接口开展源码级 E2 兼容性审计

## 本轮不做（硬边界）

- 不改 VDORAM 上游代码
- 不实现完整的生产级 Path ORAM
- 不宣称普通模拟器具备密码学安全性
- 不启动 Halo2 电路
- 不提前写论文创新性结论

## 固定参数

| 项 | 值 |
| --- | --- |
| 上游 commit | `10c90d35464620a35ddb1e2c29d2e8725acedd52` |
| N（逻辑地址空间） | 64 / 128 / 256 / 512 |
| T（访问次数） | 128 / 256 / 512 / 1024 |
| 地址宽度 | 32 bit |
| 值宽度 | 32 bit |
| 初始状态 | 全零 |
| 随机种子 | 20261123 |
| 轨迹模式 | 未写地址读 / 同址重复读 / 同址多次写 / 先写后读 / 多址交替 / dummy access |

## 三实现定位

- E0 = 真实基线（VDORAM 原始线性扫描）
- E1 = 功能参考模型（CurrentStateStore + HistoricalLog；非 ORAM）
- E2 = 后续密码学实现目标（本轮不实现，仅接口审计）

## E2 接口审计检查点（要求源码级证据）

1. `MpcExecutor` 能否表示 ORAM 读写电路
2. 能否在秘密共享状态下执行地址选择
3. 每次状态更新后能否保留 witness
4. ORAM 返回值能否绑定 VM 的 `in_mem_val`
5. ORAM 状态更新与 HistoricalLog 追加能否进入协同证明流程

重点文件：`MpcExecutorFactory.cs`、`MpcExecutor.cs`、`ZkProgramExecutor.cs`、`MemoryTraceFetchCircuitBoardGenerator.cs`、`MemoryTraceProveCircuitBoardGenerator.cs`。

## 必测正确性（任务 §五 8 项 + 强化）

见 `tests/test_correctness.py`（本轮实现 12 项）。

## 必测性能指标（任务 §六）

Query 总耗时、单次 Query 平均耗时、查询工作量（E0 扫描行数 / E1 哈希查找数）、历史记录数量、内存占用、最终状态一致性；每组 ≥10 次，记录中位数/最小/最大。E0/E1 工作量指标不是同一种操作，不可直接等同比较。

## 交付物

1. `docs/source-audit.md`
2. `docs/experiment-report.md`
3. `data/results/` 原始 CSV
4. `data/traces/` 固定种子轨迹
5. 可重复运行 benchmark 脚本
6. 完整测试输出
7. E2 接口兼容性结论（VERIFIED/INFERRED/BLOCKED/UNKNOWN）

## 验收三问

- 双结构架构能否保持原始 HistoricalKV 的语义？
- 证明所需的历史记录能否完整保留？
- 当前 MPC/证明执行框架是否存在可行的 ORAM 接入路径？

## 决策规则（提前冻结）

| 实验结果 | 下一步 |
| --- | --- |
| E1 语义不一致 | 修复一次；仍失败则停止该架构 |
| E1 正确，但 E2 无法接入 MPC | 暂停这条路线，重新评估协议结构 |
| E2 可接入，但成本没有优势 | 比较其他 DORAM 构造，不直接认定 NO-GO |
| E2 可接入且有明显性能潜力 | 进入真实 MPC Path ORAM 原型 |
| E2 能保持隐私和公开证明完整性，且性能有优势 | 进入论文级实验设计 |

## 纪律

每个结论标记 VERIFIED / INFERRED / BLOCKED / UNKNOWN；不把 E1 性能当 ORAM 性能；不把功能正确性当隐私安全证明；完成后停止，不自行扩大范围，交研究负责人验收。
