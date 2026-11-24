# ABA-04-01 — 证据与原始来源登记

> 起点 commit：`13e8115c6734e3711972a156d3be8d6af3eb5978`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
> 性质：定向证据登记，不做全领域综述；本轮不重新下载上游、不重跑实验。
> 标签：`VERIFIED`（原文/规范/源码可直接核对）/ `PAPER_CLAIM`（论文自身声称，可核对摘要或正文）/ `CONSTRUCTED`（本轮构造）/ `INFERRED`（据证据推导）/ `UNKNOWN`（证据不足）/ `BLOCKED`（明确前置缺失）。

---

## 0. 纪律

1. 不以论文未使用 "Execution Event Completeness" 这个名称判定其未解决该问题；以实际证明关系为准。
2. 不混用不同证明系统的 setup/verifier 假设（Groth16 预处理、PLONK 通用可更新 SRS、Halo 无 trusted setup、STARK 透明、Nova folding 无 SNARK setup 分别记录）。
3. "论文声称"不等于"本研究可直接使用"，也不等于"VDORAM 已采用"。
4. 普通签名、相同 `eid`、相同摘要、hash chain、递归证明本身都不自动等于电路内语义约束或跨证明 witness 绑定。

---

## 1. 本轮亲自核实的原始来源

| ID | 作者/年份 | 标题 | 原始链接 | 可核对要点 | 边界 | 标签 |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | Eli Ben-Sasson, Iddo Bentov, Yinon Horesh, Michael Riabzev / 2018 | Scalable, transparent, and post-quantum secure computational integrity (ZK-STARK) | <https://eprint.iacr.org/2018/046> | 摘要给出透明 ZK、无 trusted party、验证与数据规模指数级解耦；基于 IOP 与纠错码 | 摘要未逐字给出 trace 行间转移/边界约束细节；"trace 完整性"的具体约束属正文范畴，本轮未逐句核实 | `PAPER_CLAIM`（摘要） |
| L2 | Ariel Gabizon, Zachary J. Williamson / 2020 | plookup: A simplified polynomial protocol for lookup tables | <https://eprint.iacr.org/2020/315> | 摘要给出：检查承诺多项式 f 在 H 上的值是否都包含在表 t 的值中（multiset inclusion）；用于 batched range proof | lookup 证明的是"值属于表"的包含关系；是否覆盖执行 trace 跨表一致性取决于如何构造表与查询，属应用 | `PAPER_CLAIM`（摘要） |
| L3 | Abhiram Kothapalli, Srinath Setty, Ioanna Tzialla / 2021（CRYPTO 2022） | Nova: Recursive Zero-Knowledge Arguments from Folding Schemes | <https://eprint.iacr.org/2021/370> | 摘要给出 IVC 的 folding scheme：把"检查两个 instance"归约为"检查一个 instance"；无 trusted setup、无 FFT | folding 针对同一关系 R 的两个 instance；不自动证明两个**不同证明**的私有 witness 相同；递归开销为常数（论文声称） | `PAPER_CLAIM`（摘要） + `INFERRED`（边界） |
| L4 | B. Laurie, A. Langley, E. Kasper / 2013（RFC 6962，已由 RFC 9162 取代） | Certificate Transparency | <https://www.rfc-editor.org/rfc/rfc6962> | §2.1.2：Merkle consistency proof 证明 append-only 属性、特定版本日志是先前版本超集、前 m 个输入两树相同；§1/§7.2：日志本身不阻止/检测错误签发 | consistency proof 保证的是树结构 append-only 与摘要一致，**不保证被追加数据的语义内容或来源可信**（规范明确日志依赖外部监督检测误发） | `VERIFIED`（规范原文） |

> 勘误记录：初稿曾把 plookup 记为 ePrint `2020/1166`，经核实该编号为 Nakahara 关于有限域逆映射微分线性分析的文章；plookup 正确编号为 `2020/315`（Gabizon/Williamson）。本文件已采用核实后的编号。

---

## 2. 复用上一轮已核实的原始来源

| ID | 作者/年份 | 标题 | 原始链接 | 可核对要点 | 标签 |
| --- | --- | --- | --- | --- | --- |
| L5 | Huayi Qi, Minghui Xu, Xiaohua Jia, Xiuzhen Cheng / 2026 | VDORAM: Towards a Random Access Machine with Both Public Verifiability and Distributed Obliviousness | NDSS 2026 官方论文页 <https://www.ndss-symposium.org/ndss-paper/vdoram-towards-a-random-access-machine-with-both-public-verifiability-and-distributed-obliviousness>；PDF <https://www.ndss-symposium.org/wp-content/uploads/2026-s16-paper.pdf>；ePrint 2025/039 <https://eprint.iacr.org/2025/039>；DOI 10.14722/ndss.2026.230016 | NDSS 2026 官方 PDF 全文逐段核对：Def IV.1 的 `Prove/Verify` 与 extractor 恢复 `(I,E,inpub,outpub,inpriv,outpriv,s)∈R`；§IV-D 步 7 每周期生成 `m=(addr,t,op,val)` 含 dummy；§IV-C 排序+permutation+相邻一致性式(1)；§IV-E.3 `T` 公开且访问数=周期数；§IV-D 步 11 单一证明 π | 全文声称已由官方 PDF 核对，`VERIFIED`；P1–P3/P5 `VERIFIED`，P4 场景不存在（单证明），多方绑定 `VERIFIED` | `VERIFIED`（全文，本轮收紧） |
| L6 | Jens Groth / 2016 | On the Size of Pairing-based Non-interactive Arguments | <https://eprint.iacr.org/2016/260> | 摘要：pairing-based preprocessing SNARK for circuit satisfiability，3 群元素 proof，单 pairing product equation 验证 | `PAPER_CLAIM`（摘要）/ `UNKNOWN`（全文细节） |
| L7 | Ariel Gabizon, Zachary J. Williamson, Oana Ciobotaru / 2019 | PLONK: Permutations over Lagrange-bases for Oecumenical Noninteractive arguments of Knowledge | <https://eprint.iacr.org/2019/953> | 摘要：universal、updatable SRS，全简洁验证；grand product/permutation argument | `PAPER_CLAIM` |
| L8 | Nir Bitansky, Ran Canetti, Alessandro Chiesa, Eran Tromer / 2012 | Recursive Composition and Bootstrapping for SNARKs and Proof-Carrying Data | <https://eprint.iacr.org/2012/095> | 摘要：SNARK 递归组合与 PCD，用于分布式计算正确性执行 | `PAPER_CLAIM` |
| L9 | Sean Bowe, Jack Grigg, Daira Hopwood / 2019 | Recursive Proof Composition without a Trusted Setup (Halo) | <https://eprint.iacr.org/2019/1021> | 摘要：普通椭圆曲线循环上无 trusted setup 的递归证明组合 | `PAPER_CLAIM` + `INFERRED`（边界） |
| L10 | Tim Dokchitser, Alexandr Bulkin / 2023 | Zero Knowledge Virtual Machine step by step | <https://eprint.iacr.org/2023/1032> | zkVM 的 step/time column、边界约束、public input/output hash、递归拆分 | `PAPER_CLAIM` |
| L11 | Vineet Nair, Justin Thaler, Michael Zhu / 2025 | Proving CPU Executions in Small Space | <https://eprint.iacr.org/2025/611> | zkVM 证明 CPU 执行；先承诺 trace 再证明有效；shard/recursion 扩大外部 statement | `PAPER_CLAIM` |

---

## 2b. 本轮定向核实新增来源（子代理原文核对）

| ID | 作者/年份 | 标题 | 原始链接 | 可核对要点 | 标签 |
| --- | --- | --- | --- | --- | --- |
| L12 | Lior Goldberg, Shahar Papini, Michael Riabzev / 2021 | Cairo – a Turing-complete STARK-friendly CPU architecture | <https://eprint.iacr.org/2021/1063> | 正文 §1.2/§4/§9：统一 AIR trace，initial/final 寄存器公开约束；形式化版 arXiv:2109.14534 定理 `final_correctness` 给出 `∀ i:fin T, next_state ...` | `PAPER_CLAIM` + `VERIFIED`（形式化定理） |
| L13 | Jeremy Bruestle, Paul Gafni, RISC Zero Team / 2023 (DRAFT) | RISC Zero zkVM: Scalable, Transparent Arguments of RISC-V Integrity | <https://www.risczero.com/proof-system-in-detail.pdf> | 官方 PDF §3.1.2：RAP 见证、grand-product permutation 内存验证、control 列标记终止、imageID 绑定输出 | `VERIFIED` |
| L14 | Arasu Arun, Srinath Setty, Justin Thaler / 2023 | Jolt: SNARKs for Virtual Machines via Lookups | <https://eprint.iacr.org/2023/1217> | 摘要：lookup singularity，每 RISC-V 步承诺约 6 个域元素 | `PAPER_CLAIM` |
| L15 | Srinath Setty, Justin Thaler, Riad Wahby / 2023 | Unlocking the lookup singularity with Lasso | <https://eprint.iacr.org/2023/1216> | 摘要：lookup argument，证明承诺向量各项属于预定表 | `PAPER_CLAIM` |
| L16 | Eli Ben-Sasson, Alessandro Chiesa, Eran Tromer, Madars Virza / CRYPTO 2014 | Scalable Zero Knowledge via Cycles of Elliptic Curves | <https://eprint.iacr.org/2014/595> | 正式版 PDF：首个实用递归组合；公开的是程序与输出链，非两证明 witness 相等 | `VERIFIED` |
| L17 | Alex Ozdemir, Dan Boneh / USENIX Security 2022 | Experimenting with Collaborative zk-SNARKs: Zero-Knowledge Proofs for Distributed Secrets | <https://eprint.iacr.org/2021/1530> | 正文 §4：`(x,w_0,...,w_{N-1})∈R`，MPC 中生成**单一证明** π，extractor 恢复联合 witness | `VERIFIED` |
| L18 | Carmit Hazay, Muthuramakrishnan Venkitasubramaniam / 2016 | On the Power of Secure Two-Party Computation (commit-and-prove) | <https://eprint.iacr.org/2016/074> | 摘要：先承诺 witness、后确定 statement 的绑定模式 | `PAPER_CLAIM` |
| L19 | Polygon Zero Team / 2022 (DRAFT) | Plonky2: Fast Recursive Arguments with PLONK and FRI | <https://docs.rs/crate/plonky2/latest/source/plonky2.pdf> | §3.5：公开输入哈希入电路，电路仅保留 4 个域元素；递归 gadget 校验公开输入哈希与 verifier | `PAPER_CLAIM` |
| L20 | Nicholas Franzese 等 / CCS 2021 | Constant-Overhead Zero-Knowledge for RAM Programs | <https://eprint.iacr.org/2021/979> | 访问向量排序 + permutation + T−1 次时间戳检查（经 VDORAM 引用，未直读正文） | `PAPER_CLAIM` |
| L21 | IETF / 2013 | RFC 6962 Certificate Transparency（另见官方 VDS/Trillian 文档 <https://transparency.dev/verifiable-data-structures/>） | <https://www.rfc-editor.org/rfc/rfc6962> | §2.1.2/§5.4：consistency proof 只保证 append-only/前缀包含；内容良善性 depends on the application | `VERIFIED` |

> 编号/作者勘误（两处）：① plookup = ePrint 2020/315（非 2020/1166）；② ePrint 2012/095 作者为 Bitansky/Canetti/Chiesa/Tromer（非 Ben-Sasson 等的 BCTV）；BCTV 递归实现论文为 ePrint 2014/595（CRYPTO 2014）。`evidence_and_references.md` 与 `related_work.md` 已采用核实后的编号/作者。

---

## 3. 本仓历史案例证据（只读，来自 HOLD 冻结文档）

| ID | 事实 | 位置 | 标签 |
| --- | --- | --- | --- |
| S1 | 当前固定 commit 无独立 verifier；同函数 setup→prove→verify；VK 由 `test_rng()` 现场生成 | `docs/aba-03-d3-03-02/verifier_vk_trust_model.md`；`docs/aba-03-d3-03-02/decision.md` | `SOURCE_VERIFIED` |
| S2 | public inputs 来自 prover JSON；`verify_proof` 只做长度 + pairing；进入 statement ≠ 来源可信 | `docs/aba-03-d3-03-02/trust_boundary_inventory.md`；`docs/aba-03-d3-03-02/verifier_vk_trust_model.md` | `SOURCE_VERIFIED` |
| S3 | R5–R8 判 `BLOCKED_BY_CURRENT_INTERFACE`：step/is_mem_op/step↔row/T 多为 host 或 prover 自报 | `docs/aba-03-d3-03-01/{r5_step_provenance,r6_r7_event_trace_binding,r8_termination_anchor,decision}.md` | `SOURCE_VERIFIED`（既有判定） |
| S4 | B4 充分条件 `R2∧R3∧R4∧R5∧R6∧R7∧R8`，T 须 verifier 固定/可信；R4 顺序不可省（纯重排反例） | `docs/aba-03-d3-02/{decision,event_sequence_relation,completeness_attack_matrix}.md` | `CONSTRUCTED`（反例）+ `SOURCE_VERIFIED`（判定） |
| S5 | 主证明路径为 Plonk（非 Groth16）；`groth16/verifier.rs` 是另存泛型快照，与主路径关系 `UNKNOWN` | `docs/exp-doram-04/{backend-facts,decision}.md` | `SOURCE_VERIFIED` + `UNKNOWN` |
| S6 | 跨 proof 只有宿主内部哈希比对；无共享公开承诺/递归接口 | `docs/aba-03-d3-02/proof_composition_binding.md`；`docs/aba-03-d3-03-02/decision.md` | `SOURCE_VERIFIED` |
| S7 | 上轮结论 `NO_GO_CURRENT_ARCHITECTURE`；总决策 `HOLD_INSUFFICIENT_EVIDENCE`；P1-A/VK/P2/B4 标签不变 | `docs/aba-03-d3-03-03/decision.md` | `SOURCE_VERIFIED` |

---

## 4. 由证据支持的构造与推断（非文献直接声称）

| ID | 结论 | 依据 | 标签 |
| ---- | ---- | ---- | ---- |
| I1 | 递归/folding 证明子证明对公开 statement 有效，压缩验证；不自动证明两子证明私有 witness 相同，除非把公开承诺/opening/linking 写进上层 statement | L8/L9/L3 + 公开验证语义 | `INFERRED` |
| I2 | Merkle consistency proof 只保证 append-only/包含关系，不保证被追加事件的内容语义或来源可信 | L4 §2.1.2/§7 + 规范边界 | `VERIFIED`（规范）+ `INFERRED`（映射到事件） |
| I3 | lookup/permutation 证明集合包含或置换关系；用于事件- trace 跨表一致性是可构造的应用，但"值属于表"不等于"来自真实执行步骤" | L2/L7 + S4 | `PAPER_CLAIM` + `CONSTRUCTED` |
| I4 | 相同 `eid`、相同摘要、hash chain、签名只能作公开引用；witness 同一性与事件内容完整性仍需电路约束 + linking/opening proof | S1/S2/S6 + L8/L9 | `CONSTRUCTED` |
| I5 | zkVM 若用统一 trace 关系（step column + 边界约束）已覆盖 P1/P2/P3/P5，本研究仅拆成两证明再声称"跨证明绑定"为新贡献不能成立 | L1/L10/L11 + I1 | `INFERRED`（待 `related_work.md` 逐项核实） |

---

## 5. 未决与不得写成已验证的事项

- `UNKNOWN`：NDSS 2026 VDORAM 论文全文声称与具体证明关系的逐项对应；本轮只读录用元数据与历史冻结文档。
- `UNKNOWN`：各 zkVM 实际证明关系是否覆盖 P1–P5 的逐项判断——以 `related_work.md` 的对照表为准，且需原文/规范依据。
- `UNKNOWN`：本研究相对既有工作是否具有可发表新颖性；需逐项对照 + 可证定理 + 最小实验后判断。
- `UNKNOWN`：候选构造的具体门数、证明大小、时间成本；本轮不实测。
- `BLOCKED`：跨证明同 witness linking relation 若无法明确构造，则 P4 不可验证，相关方案不可标为实现可行。

---

## 6. 本文件不得支持的说法

- 不得写"已有工作完全未触及事件完整性"——I5 明确保留统一 trace 已覆盖的可能。
- 不得写"递归证明能比较私有 witness"——I1 明确禁止。
- 不得写"hash chain/Merkle consistency 保证事件内容正确"——I2 明确禁止。
- 不得写"plookup/permutation 本身证明事件来自真实执行"——I3 明确禁止。
- 不得把 L5–L11 的不同系统假设混成通用结论。
- 不得把"未找到相关工作"写成"首次提出"。
