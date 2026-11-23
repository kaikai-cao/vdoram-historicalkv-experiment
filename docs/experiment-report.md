# experiment-report.md — EXP-DORAM-01 实验结果

> 执行日期：2026-11-23 · 基线 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 标注：**VERIFIED**（源码/测试/实测直接支持）· **INFERRED**（据已核查证据推导）· **BLOCKED**（环境/依赖阻断）· **UNKNOWN**（未验证）
> 原始数据：`data/results/benchmark_raw.csv`（320 行）、`benchmark_summary.csv`（32 组）、`correctness-output.txt`、`oracle.json`
> 轨迹：`data/traces/`（16 个固定种子 JSONL）

---

## 0. 一句话结论

**双结构（CurrentStateStore + Append-only HistoricalLog）在功能上完全保持 VDORAM HistoricalKV 语义，并完整保留公开证明所需的 5 列历史记录与逐行承诺；源码级存在可接入现有 MPC/证明框架的 ORAM 路径（命名线契约 + session 链），但本轮未实现 Path ORAM、未测密码学成本。** 按任务包 §八决策规则，当前状态 = 「E1 语义一致 + E2 源码级可接入、成本 UNKNOWN」→ 既不 NO-GO，也不进入论文级实验；是否投入真实 Path ORAM 原型交研究负责人决策。

---

## 1. 环境与基线（VERIFIED）

| 项 | 值 |
| --- | --- |
| OS | Windows 11 家庭版 Insider Preview 26320 (64-bit) |
| CPU | Intel Core i7-14700，20 核 / 28 线程 |
| RAM | 31.69 GB |
| .NET SDK | **未安装**（`dotnet` 不在 PATH，`C:\Program Files\dotnet\dotnet.exe` 不存在） |
| Python | 3.13.14（本轮全部实现/测量用 Python 3） |
| git | 2.55.0.windows.3 |
| 上游 artifact | `BDS-SDU/vdoram-artifacts` commit `10c90d3…`，经 GitHub API 逐 blob 取源（本机大 pack 流被截断） |

**BLOCKED 项**：本机无 .NET SDK，无法编译运行 VDORAM 原始 C# 工程。E0 依据 C# 源码（Fetch/Prove 电路生成器）建立可独立运行的**语义等价参考模型**，非逐 gadget 复刻；E2 为纯源码审计，未执行任何 MPC 或 Halo2。

---

## 2. 统一访问轨迹（VERIFIED）

- 固定种子 `20261123`；N ∈ {64,128,256,512}，T ∈ {128,256,512,1024}，共 16 个文件，每文件 T 行。
- 地址/值宽度 32 bit；全零初始状态；`LOAD.value = null`（期望结果不作为输入喂给被测实现）。
- 6 类模式按轮转覆盖：从未写地址读、同址重复读、同址多次写、先写后读、多址交替、非内存 NOOP（统一 dummy access：addr = 2³²−1 = NegOne，val = 0）。
- 写操作被限制在地址空间低半区，从未写地址的读被限制在高半区，使「读未写地址」结构性保证而非概率保证（源码审计确认：真实 VDORAM 用 NegOne 地址表示非内存操作，见 source-audit §1.4）。

---

## 3. E0 参考模型复现（VERIFIED）

- 依据 `MemoryTraceFetchCircuitBoardGenerator.cs`：全历史行 `FieldEquals(mem_addr)` → 逆序 LowBit 选**最新**匹配 → SelectCompose 输出 mem_val；未匹配返 0。
- 依据 `MemoryTraceProveCircuitBoardGenerator.cs`：每行 hash 承诺 + 排序（跨址地址递增、同址 step 递增）+ 非写行值完整性。
- 参考实现 `src/baseline/e0_linear_scan.py` 输出与 C# 相同的 5 列 trace 行 `[mem_addr, global_step_counter, is_mem_op, is_mem_write, mem_val]`。
- 边界声明：这是**选择语义**等价，不是门禁级电路等价（无 .NET，未跑原始电路）。

---

## 4. E1 双结构模型（VERIFIED）

- `CurrentStateStore.Read/Write`：O(1) 哈希查找，未写地址返 0。
- `HistoricalLog.Append`：追加 5 列行 + SHA-256 行承诺（建模 C# 的 `H(magic, step, is_mem_op, is_mem_write, addr, val, enc_key)`）。
- 固定访问顺序：读旧值 → 算返回 → 更新 CurrentStateStore → 追加 HistoricalLog。
- **非 ORAM 声明（VERIFIED）**：E1 是普通内存数据结构，不具备访问模式隐藏；其性能不是 ORAM 性能。

---

## 5. 正确性结果（全部 VERIFIED）

`python -m unittest tests.test_correctness -v`：**12/12 通过**（输出存 `data/results/correctness-output.txt`）。

| 任务 §五 要求 | 测试 | 结果 |
| --- | --- | --- |
| 从未写地址 Load → 0 | test_01 | PASS |
| Store(17,123) 再 Load → 123 | test_02 | PASS |
| 两次 Store 后 Load → 最新值 456 | test_03 | PASS |
| 地址 17/18 交替互不影响 | test_04 | PASS |
| 追加历史后重放 → 最终状态一致 | test_05 | PASS |
| 删除一条 Store → 重放结果不一致 | test_06 | PASS |
| 伪造 Load 返回值 → 一致性检查失败 | test_07 | PASS（值完整性约束） |
| 修改时间戳 → 时间顺序检查失败 | test_08 | PASS（行 hash + step 顺序双检） |
| （强化）E0/E1 返回值 == 独立 oracle，全部 16 轨迹 | test_10 | PASS |
| （强化）E0/E1 输出逐字段相同的 5 列历史行 | test_11 | PASS |
| （强化）dummy access 行数不泄露操作类型 | test_12 | PASS |

**关键结论（VERIFIED）**：E1 的历史日志能逐字段重放出与 E0 相同的 5 列 trace，因此原证明流程所需的排序/时间戳/值完整性检查数据被完整保留——这回答了任务包核心问题 2（「用 ORAM 替换在线查询后能否保留历史记录和证明输入」）在功能层面为肯定。

---

## 6. 性能结果

方法：每组独立运行 10 次（REPEATS=10），记录中位数/最小/最大；时间用 `perf_counter` 且不开启 tracemalloc（避免 2–3x 测量失真），内存用单独一次 `tracemalloc` 峰值测量。原始 320 行 + 32 组汇总见 CSV。

### 6.1 纯查询耗时（关键对比指标，VERIFIED）

| N | T | E0 查询总耗时 (ms) | E1 查询总耗时 (ms) | E0/E1 加速比 | E0 扫描行数 | E1 哈希查找数 |
| --- | --- | --- | --- | --- | --- | --- |
| 64 | 128 | 0.044 | 0.011 | 4.15× | 1,255 | 128 |
| 64 | 256 | 0.136 | 0.020 | 6.90× | 4,543 | 256 |
| 64 | 512 | 0.337 | 0.037 | 9.14× | 11,839 | 512 |
| 64 | 1024 | 0.820 | 0.075 | 10.94× | 29,311 | 1,024 |
| 128 | 1024 | 1.311 | 0.077 | 17.09× | 46,705 | 1,024 |
| 256 | 1024 | 1.682 | 0.075 | 22.58× | 61,843 | 1,024 |
| 512 | 1024 | 1.832 | 0.080 | 22.88× | 71,575 | 1,024 |

观察（VERIFIED，实测直接支持）：
1. **E0 查询耗时随 T 超线性增长**（T: 128→1024 时，N=512 从 0.050→1.832 ms，约 36×），因扫描行数随历史累积（1,633→71,575）。
2. **E1 查询耗时随 T 近线性且常数极小**（0.010→0.080 ms），因哈希查找数恰为 T。
3. 加速比从 4×（T=128）扩大到 23×（T=1024）；同 T 下 N 越大加速比越大（写操作分散使 E0 匹配更靠前扫描更多行）。
4. 这**定量回答了核心问题 1**：在当前轨迹与规模下，VDORAM 式全历史线性扫描的查询工作量随历史长度显著膨胀，双结构把它降为 O(1) 每次查找。

### 6.2 总执行时间与内存（VERIFIED）

- 总执行时间（含历史追加、行承诺计算）E1 反而普遍**高于** E0（如 N=64,T=1024：E0 0.0014s vs E1 0.0021s），原因是 E1 每行计算 SHA-256 承诺、E0 仅做列表追加。**这是重要反例**：E1 的功能模型并不比 E0 快，快的只是查询子步骤；不可把「哈希表比线性扫描快」当作本实验的价值结论（与任务包「本轮最重要成功标准」一致）。
- 峰值堆内存：E1 约为 E0 的 2–2.5×（如 N=64,T=1024：E0 129.8 KB vs E1 322.6 KB），因 E1 同时维护 CurrentStateStore 字典 + 历史行 + 承诺字符串。这提示真实 ORAM 原型需关注状态双重存储成本。
- **工作量单位不可直接比较（VERIFIED）**：E0 的「扫描行数」与 E1 的「哈希查找数」是不同操作，成本不可等同；性能结论以实际时间与内存为准。

### 6.3 E2 指标缺口（UNKNOWN，不虚构）

MPC 通信量、轮数、证明生成时间、约束数、参与方数量均未测——本轮未实现 E2、未启动 Halo2、无 .NET SDK。

---

## 7. E2 接口兼容性结论（见 source-audit.md §2）

- **VERIFIED**：①MPC 框架具备表达 ORAM 读写逻辑所需原语（add/mul/inv/bitdecomp + 秘密比较 LowBit/Beaver/edaBits）；②ORAM 返回值可通过 `in_mem_val` 命名线注入 VM（`ZkProgramExecutor` L234→L302，VM 电路 L225/L518）；③历史 trace 的逐行 hash + 排序 + 值完整性构成公开证明输入，必须保留。
- **INFERRED**：④每个 MPC session 的 witness 可落盘复用；⑤跨 step 的 ORAM 持久状态需以秘密份额显式传入下一 session（同 registers 的传递模式）；⑥存在可行 session 链（ORAM read/write → VM → append trace → Prove）。
- **UNKNOWN**：具体 Path ORAM 电路的构造/成本；ORAM 内部访问轨迹（position map/stash/tree）是否及如何进入公开 trace 与 Prove（obliviousness 与 public verifiability 的接口）；实际安全参数/参与方数。

**净判定（VERIFIED + INFERRED）**：源码级**存在可行接入路径**，但「可接入」≠「已实现」≠「有性能优势」。

---

## 8. 任务包三问逐条回答

| 验收问题 | 回答 | 标注 |
| --- | --- | --- |
| 双结构架构能否保持原始 HistoricalKV 语义？ | 能。E0/E1/oracle 返回值一致，最终状态一致，5 列历史行逐字段相同 | VERIFIED |
| 证明所需的历史记录能否完整保留？ | 能。地址/step/is_mem_op/is_mem_write/mem_val 五列 + 逐行承诺全部保留，重放与篡改检测通过 | VERIFIED |
| 当前 MPC/证明执行框架是否存在可行的 ORAM 接入路径？ | 存在源码级可行路径（命名线 + session 链），但具体构造与成本未验证 | VERIFIED（路径存在）/ UNKNOWN（构造与成本） |

---

## 9. 按 §八 决策规则的状态与下一步

| 规则条件 | 本轮是否命中 |
| --- | --- |
| E1 语义不一致 → 修复/停止 | 否（语义一致，VERIFIED） |
| E1 正确但 E2 无法接入 MPC → 暂停 | 否（E2 源码级可接入） |
| E2 可接入但成本无优势 → 比较其他 DORAM，不直接 NO-GO | 部分：可接入 VERIFIED，成本 UNKNOWN（未测，不适用「无优势」判定） |
| E2 可接入且有明显性能潜力 → 进入真实 Path ORAM 原型 | 未定：潜力存在但需实测 |
| E2 保隐私 + 公开证明完整性 + 性能有优势 → 论文级实验 | 未定：隐私与性能均未验证 |

**建议交研究负责人决策**：本轮成功标准「找到一条可实际接入 VDORAM 的 ORAM 路径」在**源码级**达成；下一步候选是启动真实 MPC Path ORAM 原型以测量 E2 成本，但应先解决 UNKNOWN 项（ORAM 内部状态如何与公开 trace/Prove 接口共存）。**本轮到此停止，不自行扩大范围。**

---

## 10. 复现命令

```bash
cd D:/Research/vdoram-historicalkv-experiment
# 1. 生成 16 个固定种子轨迹
PYTHONPATH="." python -m src.trace.generator
# 2. 正确性测试（12 项）
PYTHONPATH="." python -m unittest tests.test_correctness -v
# 3. E0/E1 benchmark（每组 10 次）
PYTHONPATH="." python -m src.benchmark.benchmark
# 4. 重新拉取源码快照（可选，需联网；本机大流被截断，走 API blob）
PYTHONPATH="." python scripts/fetch_snapshot.py
```

## 11. 边界与禁语（遵守全局硬边界）

- 不声称 E1 具备密码学安全性或访问模式隐藏；功能正确性 ≠ 隐私安全证明。
- 不把 E0 Python 模型写成「复现了原始 C# 电路」；只写「选择语义等价」。
- 不虚构 E2 的 MPC 通信量/轮数/约束数/证明时间。
- 不把草案写成已标准化机制；不启动 Halo2；不改 VDORAM 上游。
