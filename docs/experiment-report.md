# experiment-report.md — EXP-DORAM-01 实验结果（含 R1 修正轮）

> 执行日期：2026-11-23 · 基线 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 标注：**VERIFIED**（源码/测试/实测直接支持）· **INFERRED**（据已核查证据推导）· **BLOCKED**（环境/依赖阻断）· **UNKNOWN**（未验证）
>
> **本文件已按研究负责人的有条件验收意见完成 R1 修正（Fetch 工作负载一致性）。旧轮原始数据保留未覆盖，其 `4–23×` 查询加速结论已被 R1 数据取代并明确撤回（见 §6）。**
>
> 原始数据：
> - 旧轮（存档，不覆盖）：`data/results/benchmark_raw.csv`（320 行）、`benchmark_summary.csv`（32 组）、`correctness-output.txt`、`oracle.json`
> - **R1 修正轮（权威）**：`data/results/r1_benchmark_raw.csv`（320 行）、`r1_benchmark_summary.csv`（32 组）、`r1_correctness-output.txt`（7 项）、`r1_oracle.json`、`r1_fetch_sequence_evidence.json`、`r1_benchmark-run.log`
> - 轨迹：旧轮 `data/traces/`（16 个）、R1 `data/traces/r1/`（16 个，双地址格式）

---

## 0. 一句话结论（R1 修正后）

**双结构（CurrentStateStore + Append-only HistoricalLog）在统一 Fetch 工作负载下仍能保持 VDORAM HistoricalKV 语义、完整保留 5 列历史记录与逐行承诺；修正后的 E0/E1 查询对比仍然是 E1 的普通哈希查找显著快于 E0 的全历史线性扫描（9.4×–51.8×，随 T 增长），但这只是两种参考数据结构的查询复杂度差异，不是 VDORAM 加速结果，更不是 ORAM 性能。** 源码级 ORAM 接入路径仍只确认到 VM 输入接口钩子（`in_mem_val`）与 session 链，ORAM 状态如何跨 step 参与 MPC 与公开证明仍未解决（UNKNOWN）。按任务包 §八决策规则：不 NO-GO、不进论文级实验，交研究负责人决策。

---

## 0.5 R1 修正摘要（为什么修、修了什么）

研究负责人抽查后指出旧轮存在**阻断问题**：E0 只在 LOAD 时调用 `fetch()`，而 E1 每个 step 都 `read()`，两者工作负载不一致，故旧轮 `4–23×` 不能作为有效 E0/E1 对比。复核固定上游源码后，该判断成立且比原报告描述更精细：

| 源码事实（pinned commit，VERIFIED） | 位置 | 对旧轮实现的影响 |
| --- | --- | --- |
| step 0 令 `memVal = zeroShare`，**不构造 Fetch 电路** | `ZkProgramExecutor.cs` L205-207 | 旧 E0/E1 均无 step 0 特判语义说明 |
| 每个非初始 step **都**构造并执行 Fetch 电路 | L208-236 | 旧 E0 只在 LOAD fetch —— **错误** |
| `in_mem_addr = thisRegisters[0]`（Fetch 输入恒为 reg0，与 op 无关） | L230 | 旧 E1 用 `address`（含 NOOP 的 NegOne）查询 —— 语义混淆 |
| `in_mem_val = memVal`（Fetch 输出注入 VM） | L302 | 接入点，结论不变 |
| `out_trace_mem_addr` = Store/Load→实际地址、否则→NegOne（独立选择） | `ZkVmExecutorCircuitBoardGenerator.cs` L990-1000 | Fetch 输入地址 ≠ 历史记录地址，旧 trace 用单一 `address` 字段混同 |

R1 修正内容（不重新设计双结构、不实现 Path ORAM、不改上游）：

1. **轨迹格式分离**：R1 trace 用 `fetch_address`（对应 `thisRegisters[0]`）与 `trace_address`（对应 `out_trace_mem_addr`）两个字段。NOOP 的 Fetch 输入是普通地址、历史记录地址才是 NegOne。旧轨迹原样保留。
2. **E0 修正**：step 0 用 `zeroShare` 不 Fetch；其余每 step 都用 `fetch_address` 执行一次全历史扫描，结果仅 LOAD 使用，STORE/NOOP 也计入查询成本。
3. **E1 修正**：Fetch 次数、输入地址序列、step 0 特判与 E0 完全一致；普通字典查询（非 ORAM）。
4. **一致性证明**：每次 run 记录实际 Fetch 地址序列，benchmark 逐次断言 `E0.fetch_addresses == E1.fetch_addresses == [trace 的 fetch_address(step>0)]`，全部通过。
5. **结论处理**：旧 `4–23×` 撤回；R1 重测数据见 §6。

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

**BLOCKED 项**：本机无 .NET SDK，无法编译运行 VDORAM 原始 C# 工程。E0 依据 C# 源码建立可独立运行的**语义等价参考模型**，非逐 gadget 复刻；E2 为纯源码审计，未执行任何 MPC 或 Halo2。R1 未改变此边界。

---

## 2. 统一访问轨迹（VERIFIED）

- 固定种子 `20261123`；N ∈ {64,128,256,512}，T ∈ {128,256,512,1024}，R1 共 16 个文件（`data/traces/r1/`），每文件 T 行。
- 地址/值宽度 32 bit；全零初始状态；`LOAD.value = null`（期望结果不作为输入喂给被测实现）。
- 6 类模式按轮转覆盖，与旧轮**完全相同的访问分布**（复用同一 pattern builder）。
- **R1 双地址字段**：
  - `fetch_address` = `thisRegisters[0]`，每个非初始 step 都送入 Fetch；NOOP 时为普通地址（由 step 确定性哈希生成，落在写半区），不是哨兵。
  - `trace_address` = `out_trace_mem_addr`，写入历史记录；LOAD/STORE 为实际地址，NOOP 为 `2³²−1 = NegOne`。
  - 对 LOAD/STORE 两字段相等；对 NOOP 两者不同——这正是 R1 测试 R1-4 验证的语义分离。

---

## 3. E0 参考模型（R1 修正，VERIFIED）

- 依据 `MemoryTraceFetchCircuitBoardGenerator.cs`：全历史行 `FieldEquals(mem_addr)` → 逆序 LowBit 选**最新**匹配 → SelectCompose 输出 mem_val；未匹配返 0。
- **R1 执行节奏**（依据 `ZkProgramExecutor.cs` L205-236）：step 0 不 Fetch（`zeroShare`）；每个非初始 step（LOAD/STORE/NOOP）都以 `fetch_address` 执行一次 Fetch。
- 依据 `MemoryTraceProveCircuitBoardGenerator.cs`：每行 hash 承诺 + 排序（跨址地址递增、同址 step 递增）+ 非写行值完整性。
- 历史行以 `trace_address` 为键（`out_trace_mem_addr`），输出与 C# 相同的 5 列 `[mem_addr, global_step_counter, is_mem_op, is_mem_write, mem_val]`。
- 边界声明：这是**选择语义 + 执行节奏**等价，不是门禁级电路等价（无 .NET，未跑原始电路）。

---

## 4. E1 双结构模型（R1 修正，VERIFIED）

- `CurrentStateStore.Read/Write`：O(1) 哈希查找，未写地址返 0。
- `HistoricalLog.Append`：追加 5 列行 + SHA-256 行承诺（建模 C# 的 `H(magic, step, is_mem_op, is_mem_write, addr, val, enc_key)`）。
- **R1 执行节奏**：与 E0 相同的 T-1 次查找、相同地址序列、相同 step 0 特判；状态写入与历史行以 `trace_address` 为键。
- **非 ORAM 声明（VERIFIED）**：E1 是普通内存数据结构，不具备访问模式隐藏；其性能不是 ORAM 性能。

---

## 5. 正确性结果（全部 VERIFIED）

### 5.1 原有 12 项（保留，修正后重跑仍全过）

`python -m unittest tests.test_correctness -v`：**12/12 通过**（输出存 `data/results/correctness-output.txt`）。覆盖任务 §五 8 项 + E0/E1/oracle 全 16 轨迹一致 + 5 列历史行逐字段相同 + dummy 行数不泄露操作类型。

### 5.2 R1 新增 7 项（`tests/test_fetch_r1.py`，输出 `data/results/r1_correctness-output.txt`）

| 测试 | 要求 | 结果 |
| --- | --- | --- |
| R1-01 | E0/E1 每个非初始 step 的 Fetch 次数相同（均 T-1）且地址序列逐项相同 | PASS |
| R1-02 | STORE step 也执行 Fetch（step0 除外），返回值仍取写入值 | PASS |
| R1-03 | NOOP step 也执行 Fetch，返回值 0 | PASS |
| R1-04 | NOOP 的 fetch_address（普通地址）≠ 历史 NegOne 哨兵时仍正确执行 | PASS |
| R1-05 | E0/E1 对相同 fetch_address 序列产生一致的 Fetch 结果 | PASS |
| R1-06 | 删除一条历史行但保留执行期 commitment → Prove 期 hash-count 检查失败 | PASS |
| R1-07 | 全部 16 个 R1 轨迹的 Fetch 次数/序列/返回值/状态一致 | PASS |

**R1-06 说明**：原 `test_06` 同时删除行与对应 commitment，只验证重放结果变化；R1-06 补上真正的 Prove 期缺口——真实 VDORAM 在执行期累积行 hash（`AddHashMemoryTrace`），Prove 期重新计算并比对 hash 计数（L571-587）。删除历史行而保留原承诺必须被检出，测试通过。

**关键结论（VERIFIED）**：在统一 Fetch 工作负载下，E1 的历史日志仍能逐字段重放出与 E0 相同的 5 列 trace，证明所需的排序/时间戳/值完整性数据被完整保留。

---

## 6. 性能结果（R1 权威数据）

方法：每组独立运行 10 次（REPEATS=10），中位数/最小/最大；时间用 `perf_counter` 且不叠加 tracemalloc，内存用单独一次 `tracemalloc` 峰值测量。E0/E1 每次 run 均断言 Fetch 地址序列一致（`fetch_seq_ok` 全 True）。

### 6.1 ⚠️ 旧轮 `4–23×` 结论撤回

旧轮 E0 只在 LOAD 时 Fetch、E1 每 step 查找，两者**不是同一工作负载**，`4–23×` 加速比无效，不再作为结论引用。旧轮 CSV 仅作历史存档保留，已在 §0 标注。

### 6.2 纯查询耗时（R1，统一工作负载，VERIFIED）

E0/E1 均执行 T-1 次 Fetch。下表为查询总耗时中位数（ms）：

| N | T | Fetch 次数 | E0 查询 (ms) | E1 查询 (ms) | E0/E1 | E0 扫描行数 | E1 查找数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64 | 128 | 127 | 0.084 | 0.0089 | 9.44× | 2,921 | 127 |
| 64 | 256 | 255 | 0.264 | 0.0179 | 14.77× | 10,046 | 255 |
| 64 | 512 | 511 | 0.797 | 0.0355 | 22.42× | 32,001 | 511 |
| 64 | 1024 | 1023 | 2.576 | 0.0696 | 37.01× | 104,830 | 1,023 |
| 128 | 1024 | 1023 | 3.182 | 0.0734 | 43.35× | 131,575 | 1,023 |
| 256 | 1024 | 1023 | 3.648 | 0.0712 | 51.24× | 149,703 | 1,023 |
| 512 | 1024 | 1023 | 3.763 | 0.0727 | 51.76× | 159,816 | 1,023 |

观察（VERIFIED，实测直接支持）：
1. 在**相同 Fetch 次数与地址序列**下，E1 查询仍显著快于 E0，加速比 9.4×（T=128）扩大到 51.8×（T=1024、N=512）。
2. E0 扫描行数随 T 超线性增长（T=1024 时达 10 万–16 万行），因每步都重扫累积历史；E1 查找数恰为 T-1，近似常数时间。
3. 这**定量回答了核心问题 1（修正版）**：VDORAM 式全历史线性扫描在每步 Fetch 的真实节奏下，查询工作量随历史长度 O(T) 累积、总成本 O(T²) 膨胀；普通字典把它降为每次 O(1)。
4. **边界不变**：这只是两种参考数据结构的查询复杂度差异。E1 是普通哈希字典、非 ORAM，既不隐藏访问模式，也未承担 ORAM 的 stash/position map/路径读写与证明成本。不可表述为「VDORAM 加速」或「ORAM 性能」。

### 6.3 总执行时间与内存（R1，VERIFIED）

| 规模 | E0 总时间 (ms) | E1 总时间 (ms) | E0/E1 | E0 峰值 (KB) | E1 峰值 (KB) |
| --- | --- | --- | --- | --- | --- |
| N=64, T=128 | 0.182 | 0.271 | 0.67× | 21.7 | 43.1 |
| N=64, T=512 | 1.193 | 1.028 | 1.16× | 73.0 | 169.5 |
| N=64, T=1024 | 3.338 | 2.053 | 1.63× | 146.6 | 339.4 |
| N=512, T=1024 | 4.548 | 2.071 | 2.20× | 146.6 | 339.4 |

- **重要翻转（R1 新现象）**：统一工作负载后，小 T（128/256）时 E1 总时间仍略高于 E0（额外 SHA-256 承诺开销）；但 T ≥ 512 时 E0 总时间反超，T=1024 时 E0 约为 E1 的 1.6–2.2×。原因是 E0 每步全历史扫描使总扫描量 O(T²) 增长，最终超过 E1 的固定承诺开销。这与旧轮「E1 总时间普遍高于 E0」相反——**正是旧轮工作负载不一致所致，R1 数据为准**。
- 峰值堆内存：E1 约为 E0 的 2–2.3×（字典 + 历史行 + 承诺字符串）。提示真实 ORAM 原型的双重状态成本。
- **工作量单位不可直接比较**：E0「扫描行数」与 E1「哈希查找数」是不同操作，结论以实测时间与内存为准。

### 6.4 E2 指标缺口（UNKNOWN，不虚构）

MPC 通信量、轮数、证明生成时间、约束数、参与方数量均未测——R1 未实现 E2、未启动 Halo2、无 .NET SDK。

---

## 7. E2 接口兼容性结论（见 source-audit.md §2，R1 未改动）

- **VERIFIED**：①MPC 框架具备表达 ORAM 读写逻辑所需原语；②ORAM 返回值可通过 `in_mem_val` 命名线注入 VM（`ZkProgramExecutor` L234→L302）；③历史 trace 的逐行 hash + 排序 + 值完整性构成公开证明输入，必须保留。
- **INFERRED**：④每个 MPC session 的 witness 可落盘复用；⑤跨 step 的 ORAM 持久状态需以秘密份额显式传入下一 session；⑥存在可行 session 链。
- **UNKNOWN**：具体 Path ORAM 电路构造/成本；**ORAM 的 stash、position map、路径读写等内部状态是否及如何参与跨 step 的 MPC 与公开 trace/Prove**；实际安全参数/参与方数。

**净判定**：源码级存在可行接入路径，但只确认到 VM 输入接口钩子与 session 链；「可接入」≠「已实现」≠「有性能优势」≠「保隐私」。

---

## 8. 任务包三问逐条回答（R1 修正）

| 验收问题 | 回答 | 标注 |
| --- | --- | --- |
| 双结构架构能否保持原始 HistoricalKV 语义？ | 能。统一 Fetch 工作负载下 E0/E1/oracle 返回值、最终状态一致，5 列历史行逐字段相同 | VERIFIED |
| 证明所需的历史记录能否完整保留？ | 能。5 列 + 逐行承诺完整保留；删行（保留承诺）/伪造 Load/改时间戳均被检出 | VERIFIED |
| 当前 MPC/证明执行框架是否存在可行 ORAM 接入路径？ | 存在源码级接口钩子与 session 链，但 ORAM 内部状态跨 step 参与 MPC/证明未解决 | VERIFIED（钩子）/ UNKNOWN（状态与成本） |

---

## 9. 按 §八 决策规则的状态与下一步

| 规则条件 | 本轮是否命中 |
| --- | --- |
| E1 语义不一致 → 修复/停止 | 否（语义一致，VERIFIED；R1 修正了工作负载一致性） |
| E1 正确但 E2 无法接入 MPC → 暂停 | 否（E2 接口钩子 VERIFIED，但完整接入 UNKNOWN） |
| E2 可接入但成本无优势 → 比较其他 DORAM，不直接 NO-GO | 不适用（E2 成本未测） |
| E2 可接入且有明显性能潜力 → 进入真实 Path ORAM 原型 | 未定：E1 查询优势明确但非 ORAM 实测 |
| E2 保隐私 + 公开证明完整性 + 性能有优势 → 论文级实验 | 未定：隐私与 ORAM 性能均未验证 |

**研究负责人的下一步建议（记录在案，本轮不执行）**：R1 通过后不立即写完整 Path ORAM，而是先针对 stash、position map、路径读写等状态组件做一次有边界的 MPC/证明兼容性设计，避免投入数周实现后发现无法进入 VDORAM 证明流程。**本轮到此停止，不自行扩大范围，等待研究负责人验收。**

---

## 10. 复现命令

```bash
cd D:/Research/vdoram-historicalkv-experiment
# 1a. 旧轮 16 个固定种子轨迹（存档）
PYTHONPATH="." python -m src.trace.generator
# 1b. R1 16 个双地址轨迹
PYTHONPATH="." python -m src.trace.generator_r1
# 2a. 原有 12 项测试
PYTHONPATH="." python -m unittest tests.test_correctness -v
# 2b. R1 7 项 Fetch 一致性测试
PYTHONPATH="." python -m unittest tests.test_fetch_r1 -v
# 3a. 旧轮 benchmark（存档）
PYTHONPATH="." python -m src.benchmark.benchmark
# 3b. R1 benchmark（权威，相同 Fetch 工作负载）
PYTHONPATH="." python -m src.benchmark.benchmark_r1
```

---

## 11. 边界与禁语（遵守全局硬边界）

- 不声称 E1 具备密码学安全性或访问模式隐藏；功能正确性 ≠ 隐私安全证明。
- 不把 E0 Python 模型写成「复现了原始 C# 电路」；只写「选择语义 + 执行节奏等价」。
- **不引用旧轮 `4–23×` 作为有效对比**（工作负载不一致，已撤回）；以 R1 数据为准。
- 不把 R1 的查询加速包装为 VDORAM 加速或 ORAM 性能；不把接口钩子当作完整 ORAM 接入证明。
- 不虚构 E2 的 MPC 通信量/轮数/约束数/证明时间；不启动 Halo2；不改 VDORAM 上游。
