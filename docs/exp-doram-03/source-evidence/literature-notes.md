# literature-notes.md — EXP-DORAM-03 定向文献核查证据（带 URL 与访问日期）

> 日期：2026-11-23 · 定位：**定向核查**，只覆盖任务包 §7 点名的构造相关工作，不做泛泛 ORAM 综述。
> 标记口径：VERIFIED（一手论文/权威页面直接支持）/ INFERRED（据此推导）/ UNKNOWN（未取得一手来源）。
> ⚠️ 本文件仅为协议构造提供参数与参与方模型证据；不据此宣称任何方案可直接接入 VDORAM（证明接口差异见主文档 §7）。

---

## L1. Path ORAM（Stefanov et al., CCS 2013）— VERIFIED（参数与模型）

- 模型：**客户端/服务器**。服务器存加密 block 组成的 bucket 二叉树；**客户端**持有 position map（逻辑地址→随机叶子）与 stash。非多方协议。
- 地址域：逻辑块 `a ∈ {0,…,N−1}`，固定密集域（与 VDORAM `[0,n−1]` 相容）。
- 四步 access：①重映射 leaf `x←pos[a]`, `pos[a]←x'`（新随机叶子）；②ReadPath(P(x))：读 `(L+1)·Z` 个 block 进 stash；③更新 payload；④Eviction 写回路径，dummy 填充。
- 参数（VERIFIED，多来源一致）：bucket size `Z=4 或 5`；tree height `L=⌈log₂N⌉`；stash 上界统计：`Pr[|S|>R] ≤ 14·(0.6002)^R`（Z=4 原文 Figure 3）；Z=4 时 `S=40` 使溢出 `<2⁻⁵⁰`、保守 `S=89` 达 `2⁻⁸⁰`；Z=5 时 128-bit 安全约需 `R≈100` blocks。
- 递归 position map：pos map 本身放进更小的 Path ORAM，`O(log_χ N)` 层（`χ≥2` positions/block），直到顶层装入客户端寄存器——**递归 ORAM 是标准组件，不是额外发明**。
- 来源：
  - https://docs.rs/oram/0.1.0/oram/path_oram/struct.PathOram.html （参数与溢出概率，VERIFIED）
  - https://crvscience.com/wiki/oblivious-ram （四步协议、递归 pos map、复杂度 2Z·log₂N blocks/access，VERIFIED 二手权威）
  - https://arxiv-vanity.com/papers/2206.10753 （式 2.1 与 128-bit stash≈100 blocks，VERIFIED 二手）

## L2. Keller–Scholl 2014《Efficient, Oblivious Data Structures for MPC》(ASIACRYPT 2014) — VERIFIED

- **关键存在性证据**：给出 Shi-ORAM (Asiacrypt'11) 与 Path ORAM (Stefanov'13) 的**安全多方协议**，oblivious data structures 仅 polylog overhead。
- 参与方模型：用 **SPDZ**（preprocessing model，**active security against an adversary corrupting all but one players** = dishonest majority、`t=m−1`、任意 m 方）。→ 直接证明"dishonest-majority、任意方、active-secure 的 MPC-ORAM/secret-index oblivious array 存在"。
- oblivious array = secret-shared array 用 **secret index** 访问且不泄露 index；oblivious dictionary 用 secret-shared key（可大于字典规模）。
- 性能（论文实测）：2 方、100 万元素 oblivious array，online access <100ms（ Springer 版）/ <250ms（ePrint 摘要版）。
- **限制（关键）**：纯 MPC，**无公开可验证性**；不产生 zkSNARK；无跨执行状态承诺。
- 来源：
  - https://link.springer.com/content/pdf/10.1007%2F978-3-662-45608-8_27.pdf （正文与摘要，VERIFIED）
  - https://askcryp.to/t/resource-topic-2014-137-efficient-oblivious-data-structures-for-mpc/6557 （ePrint 2014/137 摘要，VERIFIED）
  - ePrint: https://eprint.iacr.org/2014/137

## L3. 高效 3-party DORAM（SCN 2022 / TCC 2023 / DORAM Revisited EUROCRYPT 2024）— VERIFIED

- **3-Party Distributed ORAM from Oblivious Set Membership**（SCN 2022, UCLA）：`O((κ+D) log N)` 通信/access；**3-party honest-majority**；含 Distributed Oblivious Hash Table。
- **3-Party Secure Computation for RAMs: Optimal and Concretely Efficient**（TCC 2023, Ichikawa et al.）：`O(log N)` local CPU（渐近最优）；**3-party honest majority，passive security**；恶意版需更大 block `ω(log²N)`；依赖 3-party oblivious permutation + Cuckoo hashing + Goldreich–Ostrovsky 分层。
- **DORAM Revisited: Maliciously Secure RAM-MPC with Logarithmic Overhead**（EUROCRYPT 2024）：`O((κ+D) log N)`；**3-party**，UC-secure，malicious static；首个同复杂度恶意安全 DORAM。注：递归用 OMap 而非 ORAM（smaller levels 需容纳全空间 index）。
- **共同限制（关键）**：全部**固定 3 方 honest majority**（或 4 方 semi-honest，见 L4）；与 VDORAM "arbitrary number of provers + dishonest majority" 目标直接冲突。且均**无公开协作 SNARK**。
- 来源：
  - https://web.cs.ucla.edu/~rafail/PUBLIC/260.html （VERIFIED）
  - https://eprint.iacr.org.cn/2023/516 / https://dl-acm-org.acm-stag.literatumonline.com/doi/10.1007/978-3-031-48615-9_17 （VERIFIED）
  - https://iacr.org/news/item/20576 / https://rd.springer.com/chapter/10.1007/978-3-031-48615-9_16 （VERIFIED）

## L4. Multi-party PFE for RAM（Ji, Zhang, Lu, Ren, TIFS 2023 / ePrint 2022/939）— VERIFIED

- **4-server DORAM**，DPF-based，`O(log n)` amortized 通信/access，单 online round；模拟 TinyRAM，隐藏 (i) 访存模式 (ii) 机器状态 (iii) 指令；`5z+1` online rounds。
- **限制（关键）**：**固定 4 方**；**semi-honest**（不抗恶意）；**不隐藏总执行周期数**（早停会泄露）；**无公开可验证 SNARK**。
- 来源：
  - https://askcryp.to/t/resource-topic-2022-939-multi-party-private-function-evaluation-for-ram/17838 （ePrint 2022/939 摘要，VERIFIED）
  - https://search.napstic.cn/literature/periodical/0220230600261279 （TIFS 2023,18(1):1252-1267, DOI 10.1109/TIFS.2023.3236457，VERIFIED）

## L5. VDORAM 原论文对 DORAM 的讨论 — VERIFIED（本仓库固定 PDF 摘录）

- p8 Fig.5：`FHistoricalKV` 参数 `addr ∈ [0,n−1]`；aux=(t,op)；**独特的 `FHistoricalKV.Export()`（普通 DORAM 不需要）**——为公开可验证保留全部历史 (addr,val,aux) 元组。
- p9：初始方案 = 改造 DORAM 的 oblivious storage + append-only oblivious array 存历史；但因需**双份结构空间**且 **existing efficient DORAM schemes support an insubstantial number of parties**，与 **arbitrary number of provers beyond just two or three** 目标冲突 → 作者改用**单个 linearly-scanned oblivious array** + 时间戳单调。
- p8-9：由于 secret-shared 向量，需 oblivious sort（Bitonic mergesort + 复杂比较器 + padding `p−1`）。
- p4-5 威胁模型：correctness 下 **0 provers honest**（全体合谋伪造证明须可忽略）；privacy 下**至少 t（如 t=1）诚实**；**dishonest-majority MPC**（`t=m−1`，additive shares）；mixed domain `Fp + Z2ⁿ`（daBit/edaBit）。
- 来源：`docs/exp-doram-02/paper/EXCERPTS.md`（NDSS'26 官方 PDF 机器提取，带页码）。

## L6. 协作式 zkSNARK 后端（co-SNARK / SPDZ line）— INFERRED（用于证明层接口判断）

- 协作 SNARK：m 个 prover 各持 witness share `w_i`，`(x, w_0,…,w_{m−1}) ∈ R`；`(m,t)` 性质含 t-zero-knowledge（<t 合谋不泄露 witness）。对应 VDORAM 论文的引用 [66] Ozdemir et al. 与后续改进 [62][2][40]（论文 p5 原文）。
- 常见后端组合：SPDZ（dishonest majority）/ GSZ（honest majority）+ Groth16/Plonk；线性共享的线性重构使各方独立算自己的 share 部分再合成证明。
- 来源：https://deepdata.cn/anarticle_idBPGsBt--.html （co-snarks 工具链，二手，INFERRED）；VDORAM 论文 p5（一手，VERIFIED）。

---

## 差异矩阵（回答任务包 §7 四问，供主文档引用）

| 方案 | 状态转换机制 | 访问隐私 | 公开协作 SNARK | 参与方 | 关键缺口 |
| --- | --- | --- | --- | --- | --- |
| Path ORAM'13 | 有（tree+pos+stash） | 有（客户端/服务器） | 无 | 2 方 Client/Server | 非多方、无公开验证 |
| Keller–Scholl'14 | 有（MPC oblivious array） | 有（secret index, active） | **无** | **任意 m 方, dishonest majority** | 无公开可验证、无跨步状态承诺 |
| 3-party DORAM (L3) | 有 | 有（honest majority） | 无 | **固定 3 方** | 参与方受限、无公开验证 |
| PFE-RAM (L4) | 有（全机器状态） | 有（semi-honest） | 无 | **固定 4 方** | 参与方受限、不隐藏周期数、无公开验证 |
| VDORAM (L5) | 有（线性扫描 HistKV） | 有（distributed obliviousness） | **有** | **任意 m 方, dishonest majority** | 查询 O(T²) 线性扫描（本实验要替代的对象） |
| **本构造目标** | 有（跨步 R1CS） | 有（≥t 诚实） | **有（verifier 强制串联）** | **任意 m 方** | —— 需同时满足，无现成方案 |

**四问结论**：
1. 已提供状态转换机制：Path ORAM、Keller–Scholl、各 DORAM/PFE-RAM 都有（VERIFIED）。
2. 只解决访问隐私、无公开协作 SNARK：Keller–Scholl、3-party DORAM、PFE-RAM 全部（VERIFIED）——**这正是必须新增证明层的原因**。
3. 只支持少数参与方：3-party DORAM（3 方）、PFE-RAM（4 方）是硬限制（VERIFIED）；Keller–Scholl 的 SPDZ 是任意方（关键反例，破除"ORAM 必然限方"）。
4. 未隐藏 Position Map / Stash / 维护操作泄露：Path ORAM 本身把 pos map+stash 放在**可信客户端**——在多方场景若直接暴露份额则泄露；Keller–Scholl/DORAM 用 MPC 隐藏索引但无公开证明（VERIFIED/INFERRED）。
5. **本构造增量**：在 Keller–Scholl 的任意方 MPC-ORAM 状态转换之上，新增 (a) 每步 `S_i→S_{i+1}` 的 R1CS 关系、(b) verifier 强制串联的状态承诺链、(c) 与 HistoricalLog/in_mem_val 的逻辑语义绑定——**不是拼接两个已有组件，而是新增"公开可验证的跨步状态机证明层"**（CONSTRUCTED，见主文档）。
