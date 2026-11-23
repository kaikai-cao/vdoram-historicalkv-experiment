# literature-evidence.md — 定向文献与证据核查

> 2026-11-23 · 起点 `b88f3db` · **只围绕任务包点名文献**，不做泛泛综述。
> 标记：**VERIFIED** 一手论文/权威页面直接支持 · **INFERRED** 据此推导 · **UNKNOWN** 固定证据内无法判断。
> 纪律：不因 Merkle tree / Path ORAM / Poseidon / SNARK 单独已存在就 NO_GO；也不把已有组件拼接宣称创新。

---

## H1. 固定证据清单（沿用 EXP-DORAM-03 + 本轮定向补充）

| # | 文献 | 关键事实（与 R1 相关） | 标记 | 来源 |
| --- | --- | --- | --- | --- |
| L1 | Stefanov et al., *Path ORAM*, CCS 2013 | 客户端/服务器；tree+pos map+stash；access 四步；bucket `Z=4/5`；递归 pos map 是标准组件；stash 溢出概率讨论 | VERIFIED | https://eprint.iacr.org/2013/280 ；参数摘录 https://docs.rs/oram/0.1.0/oram/path_oram/struct.PathOram.html |
| L2 | Keller & Scholl, *Efficient, Oblivious Data Structures for MPC*, ASIACRYPT 2014 / ePrint 2014/137 | 摘要原文：“polylogarithmic overhead”；用 SPDZ，“active security against an adversary corrupting all but one players”；2 方 100 万元素 array access <250 ms；**无公开验证、无 SNARK、无跨步状态承诺** | VERIFIED | https://eprint.iacr.org/2014/137 |
| L3 | 3-party DORAM 系列（SCN 2022 / TCC 2023 / EUROCRYPT 2024） | 固定 3 方，多为 honest majority / passive 或 static malicious；`O((κ+D)log N)`；**无公开协作 SNARK** | VERIFIED | https://web.cs.ucla.edu/~rafail/PUBLIC/260.html ；https://eprint.iacr.org/2023/516 ；https://iacr.org/news/item/20576 |
| L4 | Ji, Zhang, Lu, Ren, *Multi-party PFE for RAM*, TIFS 2023 / ePrint 2022/939 | 固定 4 server、DPF、semi-honest；隐藏访问模式/机器状态/指令；不隐藏总执行周期；无公开 SNARK | VERIFIED | https://eprint.iacr.org/2022/939 ；DOI 10.1109/TIFS.2023.3236457 |
| L5 | Qi, Xu, Jia, Cheng, *VDORAM*, NDSS 2026 / ePrint 2025/039 | 摘要原文：“existing DORAMs lack public verifiability”；首次 publicly verifiable distributed ORAM；任意 m 方、dishonest majority；在线用 **single linearly-scanned oblivious array**；MPC 中间值作 co-SNARK witness | VERIFIED | https://eprint.iacr.org/2025/039 ；本地摘录 `../exp-doram-02/paper/EXCERPTS.md` p4-5/p9 |
| L6 | Ozdemir et al. 等协作 zkSNARK 线（经 VDORAM p5 引用） | `(m,t)` 协作 SNARK：Prove 在 MPC 中执行；knowledge soundness；t-zero-knowledge（<t 合谋不学 witness）；succinct verification | VERIFIED（定义层面） | `EXCERPTS.md` L134-162；原文链接见论文参考文献 [66][62][2][40] |
| L7 | Feng et al., *Towards Practical Oblivious Map*, ePrint 2024/1650 | OMap 基于 tree-based ORAM/ODS；客户端—服务器；交互轮 `O(log n/log log n)+O(log λ)`；**无多方协作证明接口** | VERIFIED | https://eprint.iacr.org/2024/1650 |
| L8 | VDORAM artifact `10c90d3` 源码（固定 commit） | MiMC 默认 65 rounds、SBox=7；`FieldEqualsGadget`/`FieldLessThanGadget`/`SelectComposeGadget`；回调落盘；宿主 hash 检查；无 verifier 跨电路串联 | VERIFIED | 本地快照 `../exp-doram-02/source-evidence/`；`../exp-doram-02-r1/verifier-chain-check.md` |

---

## H2. 三个必答问题（本轮定向结论）

### H2.1 Merkle 增量承诺是否已有直接相关构造？

**固定集合内：UNKNOWN（未发现直接构造）。**

- L1 Path ORAM 的 tree 是加密 block 的容器，**不是**面向公开验证的 Merkle 承诺；客户端持有 pos/stash，没有“每步公开根 + R1CS 打开”的接口。
- L5 VDORAM 有逐 trace 行的公开 hash 承诺（`MemoryTraceProve` L64-83）和 append-only 链，但这是**线性历史日志承诺**，不是覆盖 ORAM Tree/PositionMap/Stash 的增量 Merkle 状态承诺。
- L2/L3/L4/L7 均无公开状态承诺接口。
- 因此：本轮提出的是**候选构造**（CONSTRUCTED），不是引用已有现成方案；固定集合外是否存在更接近的构造本轮未核查，标 UNKNOWN，且**不据此否决**。

### H2.2 是否已有 ORAM state transition SNARK？

**固定集合内：UNKNOWN（未发现直接实例）。**

- L5 VDORAM 证明的是 memory trace fetch/sort/prove 电路，论文 p9 明确因高效 DORAM 参与方受限与双结构开销，改用**单个线性扫描 oblivious array**；它没有把 Path ORAM 的 `(Tree,pos,stash)` 状态转换写成 R1CS 关系。
- L2/L3/L4/L7 提供状态转换/访问隐私，但**无公开证明层**。
- 本轮 `r1cs-constraints.md` 给出关系定义与约束族，属于 CONSTRUCTED，不能写成“已有方案证明过”。

### H2.3 是否已有 MPC-ORAM 与 public verifiability 同时实现？

**固定集合内：没有直接实例（VERIFIED 为“集合内否定”），全局命题 UNKNOWN。**

| 方案 | 访问隐私 | 公开可验证 | 任意方 | 本轮可用性 |
| --- | --- | --- | --- | --- |
| Path ORAM (L1) | 客户端/服务器 | 无 | 不适用（非 MPC） | 状态组件来源，非直接方案 |
| Keller–Scholl (L2) | 有，active，dishonest majority | **无** | **任意 m** | 隐私/秘密索引存在性依据 |
| 3-party DORAM (L3) | 有，固定 3 方 | 无 | 否 | 直接移植违约，仅对照 |
| PFE-RAM (L4) | 有，4 方 semi-honest | 无 | 否 | 对照 |
| OMap (L7) | 客户端/服务器 | 无 | 不适用 | 对照 |
| VDORAM (L5) | 有，任意方 dishonest majority | **有** | **任意 m** | 证明层范式来源；但在线查询线性扫描 |

**关键**：L2 与 L5 各占一半——L2 给任意方 MPC-ORAM，L5 给任意方公开协作证明；本轮新增的是把 ORAM 状态转换纳入公开可验证关系，并让 Merkle 根可增量更新。是否已有文献做过同一件事，固定集合内无证据（UNKNOWN）；**不把拼接本身称为创新**。

---

## H3. 参与方 / 腐化模型 / 泄露信息 / 证明接口对照

| 方案 | 参与方 | 腐化模型 | 已知泄露 | 证明接口 |
| --- | --- | --- | --- | --- |
| L1 Path ORAM | 1 client + 1 server | server 好奇；client 可信 | 访问模式对 server 隐藏；client 知全部 | 无 |
| L2 Keller–Scholl | 任意 m | active, all-but-one（t=m−1） | `<m` 合谋不泄露 index；全体合谋隐私不适用 | 无 SNARK / 无公开验证 |
| L3 3-party DORAM | 固定 3 | honest majority 或 static malicious | 与 3 方模型绑定 | 无 |
| L4 PFE-RAM | 固定 4 | semi-honest | 不隐藏总执行周期数 | 无 |
| L5 VDORAM | 任意 m | correctness: 0 honest；privacy: ≥t honest | proof/trace 公开输入；隐藏 witness | collaborative zkSNARK，逐电路手动 |
| L7 OMap | client/server | server 不可信 | 对 server 隐藏访问模式 | 无 |
| **本轮候选** | 任意 m（继承 L2+L5） | correctness 全体合谋；privacy `<t` | step/根/历史承诺公开；地址/叶子/路径 witness 秘密 | `R_i` + verifier 根链（CONSTRUCTED，未实现） |

---

## H4. 参数核对（stash 数值冲突）

- `docs.rs/oram`（L1 页面）原文：`Z=4` 时 `SO=40 → below 2^{-50}`、`SO=89 suffices for 2^{-80}`，并称来自原论文 Figure 3 的**实验/保守估计**（VERIFIED 页面文本）。
- 任务给定解析界 `14·0.6002^R` 的数值计算结果：`R=89 → 2^-61.74`、`R=100 → 2^-69.84`、`R=114 → 2^-80.15`、`R=179 → 2^-128.02`（CONSTRUCTED 计算，见 `merkle-oram-construction.md` §A3.1）。
- 二者不是同一推导路径；本轮按任务要求使用解析界，故修正为 114/179，并把差异明确记录，不静默采用任一数字。

---

## H5. 纪律声明

- 未做泛泛综述；固定集合外的工作（例如 zk-EVM Merkle state、动态 SNARK 等）虽在定向搜索中出现，但**未纳入 VERIFIED 证据**，不作为 GO 或 NO_GO 依据。
- 未因“组件已存在”NO_GO；也未把 Merkle + Path ORAM + co-SNARK 拼接直接称为创新。
- 所有 UNKNOWN 均按未知处理：没有 ORAM-state SNARK 先例 ≠ 不存在；没有直接 Merkle 构造 ≠ 不可构造。
