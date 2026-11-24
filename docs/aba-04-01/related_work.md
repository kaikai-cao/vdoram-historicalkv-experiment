# ABA-04-01 — 相关工作与新颖性排查

> 起点 commit：`13e8115c6734e3711972a156d3be8d6af3eb5978`。
> 性质：定向调查六个方向，不做全领域 ZKP 综述；每个判断标 `VERIFIED / INFERRED / UNKNOWN` 并给原文依据或章节。
> 原始来源元数据与边界见 `evidence_and_references.md`；本文判断不得与之冲突。
> 重要更正：VDORAM 论文全文已由 NDSS 2026 官方 PDF 逐段核对，结论见 §6；初稿把全文标 `UNKNOWN` 属保守未核实状态，本版已收紧。

---

## 0. 排查纪律

1. **不因命名判定新颖性**。论文未使用 "Execution Event Completeness" 不等于未解决 P1–P5；一律看实际证明关系。
2. **重点反证检查**：zkVM/可验证 RAM 是否通过统一 trace 关系已完成 P1–P5。若是，"拆成两个证明再声称跨证明绑定是新贡献"不成立。结论见 §7。
3. **区分构件与方案**：lookup/permutation/accumulator 是构件，单独不构成 P1–P5 的完整方案。
4. **区分递归的两种作用**：压缩验证 vs 证明跨证明私有 witness 相同——后者递归本身做不到，除非先把承诺纳入公开 statement。
5. **区分"单证明内多方 witness 绑定"与"两独立证明靠相同字段绑定"**：前者已有成熟构造（collaborative zkSNARK），后者才是本研究候选问题。

---

## 1. 方向一：zkVM / verifiable computation 的执行 trace 完整性

### W1 — Cairo: a Turing-complete STARK-friendly CPU architecture（Goldberg, Papini, Riabzev, 2021, ePrint 2021/1063）

- **解决的语义**：固定 STARK 友好 CPU/AIR，用统一约束证明"存在从给定初始寄存器到给定最终寄存器的 n 步合法执行，内存只读/连续/与公开内存一致"（§1.2；形式化版 arXiv:2109.14534）。
- **P1–P5**：P1 `VERIFIED`（trace 是 witness，转移约束逐行约束状态，§4/§9）；P2 `VERIFIED`（每行一步，转移作用于相邻行，§2.6/§9.7）；P3 `VERIFIED`（trace 按时钟排序，转移是 row i→i+1 局部关系）；P5 `VERIFIED`（initial/final 寄存器作为公开数据被约束）；P4 `UNKNOWN`（单证明，无跨证明机制）。
- **差异**：事件是应用级抽象；若事件在证明外发布，本系统不提供绑定。

### W2 — A verified algebraic representation of Cairo program execution（Avigad 等, 2021, arXiv:2109.14534）

- **解决的语义**：在 Lean 3 中形式化"满足 AIR 的数据 ⇒ 存在相应 Cairo 执行 trace"；定理 `final_correctness` 给出 `∀ i:fin T, next_state ...`，且 exec 0 与 exec(fin.last T) 绑定公开 initial/final。
- **P1/P2/P3/P5**：均 `VERIFIED`（形式化定理覆盖全步、相邻状态、起止绑定）；P4 `UNKNOWN`。
- **差异**：验证 Cairo 编码层，不含事件分离。

### W3 — RISC Zero zkVM（Bruestle, Gafni, RISC Zero Team, 2023 DRAFT，官方 PDF + 开发者文档）

- **解决的语义**：zk-STARK（FRI+DEEP-ALI+HMAC-SHA256 PRF）证明 RISC-V 执行；RAP 见证，control/data 列 + auxiliary trace 的 grand-product permutation（内存验证）与 plookup range check；receipt 把 `imageID` 绑定到断言输出。
- **P1–P5**：P1 `VERIFIED`（内存操作进 trace 且由 permutation 约束，§3.1.2）；P2 `VERIFIED`（每周期一行，删除/替换访问破坏多重集等式）；P3 `VERIFIED`（两种顺序承诺由 permutation 连接）；P5 `VERIFIED`（control 列标记终止、imageID 与输出绑定；终止行号未单列公开字段）；P4 `UNKNOWN`（单 receipt）。
- **差异**：事件即 trace 行，无独立事件证明。

### W4 — Jolt（Arun, Setty, Thaler, 2023, ePrint 2023/1217）与 Lasso（Setty, Thaler, Wahby, 2023, ePrint 2023/1216）

- **解决的语义**：lookup singularity——把 zkVM 前端化为对 ISA 相关结构化大表（>2^128）的查找；Lasso 证明承诺向量各项属于表；每 RISC-V 步承诺约 6 个域元素。
- **P1–P5**：P1 `VERIFIED`（每步被约束为 ISA 表内合法条目）；P2 `INFERRED`（每步进承诺向量，但"应用必录事件"是应用级概念）；P3 `INFERRED`（lookup 本身是多重集关系，顺序为 trace 原生）；P4 `UNKNOWN`；P5 `UNKNOWN`（未给公开终止位置字段）。
- **差异**：查找保证"取值合法"，不保证"事件集合完备/顺序"。

### W5 — vnTinyRAM（Ben-Sasson, Chiesa, Tromer, Virza, USENIX Security 2014）

- **解决的语义**：通用电路生成器，只需程序运行时间上界即可证明执行正确，无需知道程序本身。
- **P1/P2/P3**：`VERIFIED`（执行正确性由电路约束覆盖）；P5 `INFERRED`（公开的是运行时间上界，非实际停机步）；P4 `UNKNOWN`。
- **差异**：上界式电路 ≠ 真实终止位置绑定。

### W6 — STARK（Ben-Sasson 等, 2018, ePrint 2018/046）

- **解决的语义**：透明、可扩容、后量子计算完整性；执行转代数 trace，AIR 约束转移，Merkle+FRI；无 trusted setup，哈希假设。
- **P1/P2/P3**：`VERIFIED`（trace 语义层，§AIR/Appendix D）；P5 `INFERRED`（证明计算完整性但无独立终止位置公开字段）；P4 `UNKNOWN`。

### W7 — SP1 / zkSync Era

- 未找到原始论文或正式规范（仅官方博客/仓库/第三方综述）。P1–P3 `INFERRED`，P4/P5 `UNKNOWN`，原始来源 `UNKNOWN`。不编造作者/年份。

---

## 2. 方向二：trace commitment / lookup / permutation 与跨表一致性

### W8 — PLONK（Gabizon, Williamson, Ciobotaru, 2019, ePrint 2019/953）

- **解决的语义**：universal/updatable SRS；grand product/permutation argument 强制 copy constraint。
- **P1/P2** `INFERRED`；**P3** `UNKNOWN`（permutation 是多重集/置换一致性，不是时序；把 permutation 当 ordering 是误读）；P4/P5 `UNKNOWN`。
- **差异**：universal updatable SRS，不与 STARK/FRI 假设混用。

### W9 — plookup（Gabizon, Williamson, 2020, ePrint 2020/315）

- **解决的语义**：把查找重写为 lookup multiset relation，证明 witness 值属于表；用于 batched range proof。
- **P1/P2** `INFERRED`（值域/多重集记账）；**P3** `UNKNOWN`（multiset 丢序）；P4/P5 `UNKNOWN`。
- **链接更正**：任务书写的 2020/1166 未找到；正确为 2020/315（VDORAM 参考文献 [27] 同）。

### W10 — Plonky2（Polygon Zero Team, 2022 DRAFT，官方 PDF）

- **解决的语义**：TurboPLONK + FRI，Goldilocks 域；§3.5：公开输入多时哈希入电路，电路只保留 4 个域元素。
- **P1/P2/P3** `INFERRED`；**P4** `UNKNOWN`（递归 gadget 校验子证明公开输入哈希与 verifier，不校验两个子证明私有 witness 相同）；P5 `UNKNOWN`。透明 FRI 假设，不与 KZG 混用。

---

## 3. 方向三：递归 SNARK / proof aggregation 的公开 statement 绑定

### W11 — 递归组合基础（Bitansky, Canetti, Chiesa, Tromer, 2012, ePrint 2012/095）

- **解决的语义**：把任意 SNARK bootstrap 为 complexity-preserving SNARK；构造 PCD 系统。
- **P1/P2/P3/P5** `UNKNOWN`（一般框架，无执行事件概念）；**P4** `UNKNOWN`（递归证明子证明有效性或消息合规，不证明两方私有 witness 相同）。
- **作者更正**：2012/095 为 Bitansky/Canetti/Chiesa/Tromer，非 Ben-Sasson 等的 BCTV。

### W12 — BCTV: Scalable Zero Knowledge via Cycles of Elliptic Curves（Ben-Sasson, Chiesa, Tromer, Virza, CRYPTO 2014, ePrint 2014/595）

- **解决的语义**：首个实用递归组合；RAM 正确执行证明，密钥生成与运行时间无关；两系统交替验证对方 verifier。
- **P1/P2/P3** `VERIFIED`（正确执行/RAM 步序）；P5 `INFERRED`；**P4** `UNKNOWN`（证明"对方 verifier 接受"而非"witness 相同"）。MNT 曲线假设，不与 Halo/Nova 混用。

### W13 — Halo（Bowe, Grigg, Hopwood, 2019, ePrint 2019/1021）

- **解决的语义**：无 trusted setup 的递归证明组合，摊还 inner product argument 验证成本。
- **P1/P2/P3** `INFERRED`（仅在单个被验证证明内部）；**P4** `UNKNOWN`（递归只压缩验证）；P5 `UNKNOWN`。

### W14 — Nova（Kothapalli, Setty, Tzialla, 2021/CRYPTO 2022, ePrint 2021/370）

- **解决的语义**：folding scheme 把两个 NP 实例折成一个（"folded 可满足 iff 原实例可满足"）；IVC 每步折叠当前 R1CS 实例与前一步 verifier 电路，链接公开输出 z_{i-1}→z_i。
- **P1/P2/P3** `INFERRED`；**P4** `UNKNOWN`（folding 证明两实例各自可满足，**不证明 private witness 相同**；相同的是公开输入输出链）；P5 `INFERRED`（IVC 可验证任意前缀，实际终止位置未单列公开）。

### W15 — PCD / Hearsay（Chiesa, Tromer, 2010, DOI 10.1109/NEMS.2011.6017338）

- **解决的语义**："Each such proof attests that the message's data and all of its history comply with the specified properties"——绑定公开消息数据及其历史。
- **P4** `INFERRED`（对公开数据/历史的跨参与方绑定）；对私有 witness 相同 `UNKNOWN`；其余 `UNKNOWN`。

---

## 4. 方向四：MPC 与 SNARK 组合中的跨参与方 witness / commitment 绑定

### W16 — Collaborative zk-SNARKs（Ozdemir, Boneh, USENIX Security 2022 / ePrint 2021/1530）

- **解决的语义**：把单 prover zkSNARK 提升为 N 个 prover 对分布式秘密的联合证明：`(x, w_0,...,w_{N-1}) ∈ R`，MPC 中生成**单个证明 π**，`Verify(pp, x, π)`；knowledge soundness 保证 extractor 得到完整 witness 元组（§4）。
- **P1/P2/P3** `INFERRED`（取决于 R）；**P4** `VERIFIED`（**跨参与方层面**：单一公开 statement x 绑定全部 w_i，extractor 恢复联合 witness）——但这是**一份证明内**的多方绑定，不是"两证明靠相同 eid/摘要"场景；P5 `UNKNOWN`。
- **差异（关键）**：本方向与本研究 P4 概念邻近，且已给出成熟构造。若两证明各自有效但需证明 witness 同执行，可归约为单一公开 statement 下的联合见证关系——这正是 collaborative zkSNARK 的语义。

### W17 — MPC-in-the-head（Ishai, Kushilevitz, Ostrovsky, Sahai, STOC 2007）

- 单 prover 模拟多方；**P4** `UNKNOWN`（非跨参与方 witness 绑定机制）；其余 `UNKNOWN`。

### W18 — commit-and-prove（Hazay, Venkitasubramaniam, ePrint 2016/074）

- **解决的语义**：prover 第二轮承诺 witness w，最后轮才确定要证明的 statement x。
- **P4** `INFERRED`（"先承诺 witness 后定 statement" 的绑定模式）；其余 `UNKNOWN`。这是"绑定私有 witness 到公开承诺"的成熟范式。

### W19 — Cross-domain NIZK（ePrint 2019/063）

- **解决的语义**：跨域 NIZK 的一个具体实例——把基于 MPC-in-the-head（ZKB++）的证明与公开 Pedersen 承诺 C 关联，示例为证明"对 RSA/DSA 签名的知识"与承诺 C 中是同一值。它是**针对特定跨域承诺关联的一次构造展示**，不是通用的"跨证明同执行绑定"方案，也不是通用"MPC 视图绑定公开承诺"框架。
- **P4** `INFERRED`（仅作为一种特定跨域承诺关联实例，提示"可把公开承诺纳入证明关系"这一思路；不足以据此声称一般性 P4 已解决）；其余 `UNKNOWN`。

---

## 5. 方向五：可验证日志 / append-only log / Merkle consistency proof

### W20 — RFC 6962 Certificate Transparency（Laurie, Langley, Kasper, IETF 2013；由 RFC 9162 取代）

- **解决的语义**：§2.1.2 原文 "Merkle consistency proofs prove the append-only property of the tree"；对 MTH(D[n]) 与旧 MTH(D[0:m]) 证明左子树两树相同；§5.4 明确内容良善性 "depends on the application"，由 auditor 检查。
- **P1/P2** `UNKNOWN`（consistency 只保旧条目未改写，不规定哪些事件必录、不保证内容与真实执行一致）；**P3** `INFERRED`（同序追加，但这是日志追加顺序 ≠ 执行步序）；P4/P5 `UNKNOWN`。
- **差异（明确）**：consistency proof 保证 append-only/包含关系，**不等于事件内容完整性**；split-view 检测需客户端保存/交换历史 tree head。

### W21 — Trillian / Verifiable Data Structures（Google 官方文档）

- **解决的语义**："later version includes everything in the earlier version, in the same order, and all new entries come after"；README：append-only 高效可证，split-view 可高效检测但需完整审计。
- **P1/P2/P4/P5** `UNKNOWN`（"Clients must calculate inclusion proofs for every record they use"）；**P3** `INFERRED`。同 W20 边界。

---

## 6. 方向六：ORAM / DORAM 访问事件与状态更新的完整性

### W22 — VDORAM: Towards a Random Access Machine with Both Public Verifiability and Distributed Obliviousness（Qi, Xu, Jia, Cheng, NDSS 2026；DOI 10.14722/ndss.2026.230016；ePrint 2025/039）

- **解决的语义（NDSS 2026 官方 PDF 全文逐段核对，非仅元数据）**：
  - `Prove(pp, I, E, inpub, outpub, inpriv, outpriv, s) → π`，`Verify(pp, I, E, inpub, outpub, π)`（Def IV.1, p.11）；knowledge soundness 的 extractor 恢复 `(I,E,inpub,outpub,inpriv,outpriv,s) ∈ R`，R 为合法 RAM 执行集合。
  - 每个指令周期在指令执行电路内生成 `m = (addr, t, op, val)` 并插入 `[M]`；非内存指令插入 dummy 访问（§IV-D 步 7, p.10；§IV-A 图 2, p.6）；`t` 为 public timestamp 单调递增，halt 时停止（§IV-C/§IV-D 步 3/8）；停机后 sort + permutation check + 相邻一致性式 (1)（§IV-C, p.8）。
  - §IV-E.3 明确 "Total number of iterations (T)... made public. This is necessary to halt the machine"；"The number of memory accesses equals to the total number of instruction cycles"；I/O 与 halt 指令类型公开。
  - 所有电路调用 collaborative zkSNARK 得到**一个**非交互简洁证明 π（§IV-D 步 11）。
- **P1–P5（适用范围限定）**：以下判断的对象是 **VDORAM 自身定义的事件语义**——"每个指令周期恰好产生一条访问记录 `m=(addr,t,op,val)`，非内存周期为 dummy"，且其事件生成条件与必需记录集合由该系统固定（等价于 `problem_definition.md` 中 `φ` = 逐周期记录、`S_req` = 全部周期）。P1 `VERIFIED`（访问元组在指令执行电路内产生，extractor 恢复完整执行）；P2 `VERIFIED`（每周期恰好一条含 dummy，访问数=周期数，permutation 保证排序未改写值）；P3 `VERIFIED`（t 单调递增 + 按 (addr,t) 排序 + 式 (1) 相邻检查）；P5 `VERIFIED`（T 公开、halt 类型公开、最终状态被 extractor 恢复并在 T 次访问上 trace verification）；P4 `UNKNOWN`（**单证明，无两证明绑定场景**；多方 witness 绑定 `VERIFIED`：单一公开 x 下 `(x,w_0,...,w_{m-1}) ∈ R`，extractor 恢复联合 witness，§III-B.1/Def IV.1）。
- **外推边界（不得越过）**：上述 `VERIFIED` **不能直接外推**到 `problem_definition.md` 中任意应用事件策略 `φ` 与任意必需集合 `S_req`。论文证明的是它自己固定的"逐周期记录"语义；对条件触发、只记录子集、或自定义事件类型的应用，必须把该应用的 `φ` 与 `S_req` 显式纳入证明关系后重新判断，不能仅凭 VDORAM 结果给任意 `φ` 标 `VERIFIED`。
- **差异（决定性）**：在其固定语义下，**P1–P3、P5 以及多方 witness 绑定由一个统一 trace/R1CS 关系一次性解决**；"拆成执行证明 + 事件证明后再声称跨证明绑定"在本论文框架内**没有对应缺口**；公开 statement 不含独立 eid/事件列表/事件摘要字段。
- **与历史案例的关系**：本仓 HOLD 文档对固定 artifact commit 的实现判定（`BLOCKED_BY_CURRENT_INTERFACE`）是**该实现**的事实，不等于论文主张的上限；论文全文 P1–P3/P5 已 VERIFIED，二者需区分（见 `evidence_and_references.md`）。

### W23 — Constant-Overhead ZK for RAM Programs（Franzese, Katz, Lu, Ostrovsky, Wang, Weng, CCS 2021 / ePrint 2021/979）

- 访问向量排序 + permutation proof + T−1 次相邻时间戳检查（经 VDORAM §IV-C 引用，未直读正文）；P1/P2/P3 `INFERRED`，P5 `INFERRED`，P4 `UNKNOWN`。交互式 ZK，非公开可验证 collaborative 设置。

### W24 — MacORAMa（ePrint 2023/083）/ Freecursive ORAM（ASPLOS 2015）/ Externally Verifiable ORAM（PoPETs 2017）

- 分别：内存完整性/位置图 MAC/争议裁决模型；目标是 ORAM 完整性或防篡改服务器，**无公共可验证执行 trace、无事件分离语义**；P1 `INFERRED`（各自完整性维度），P2/P3/P4/P5 `UNKNOWN`。假设与场景不同，不与 VDORAM 混用。

---

## 7. 关键反证结论：统一 trace 关系已覆盖哪些性质

综合 W1–W6、W22，现代 zkVM / 可验证 RAM 的**统一 trace 关系**（执行 + 事件生成在同一证明关系）已覆盖：

| 性质 | 统一 trace 是否覆盖 | 依据 |
| ---- | ------------------ | ---- |
| P1 Event soundness | **VERIFIED** | Cairo/RISC Zero/VDORAM：事件在 trace/电路内产生，extractor 恢复合法执行 |
| P2 Event completeness | **VERIFIED**（VDORAM/Cairo/RISC Zero）/ `INFERRED`（Jolt） | 每步一行（含 dummy）、访问数=周期数、permutation 不变量 |
| P3 Event ordering | **VERIFIED**（VDORAM 时间戳排序+相邻检查、Cairo 时钟行、RISC Zero permutation） | 步序即执行顺序 |
| P4 Cross-proof binding | **不适用**（单证明，`INFERRED`）；多方绑定已有 `VERIFIED` 构造（W16/W22） | 这些系统无"两独立证明靠相同字段"场景 |
| P5 Termination binding | **VERIFIED**（VDORAM T 公开、Cairo final 寄存器公开、RISC Zero control 列）/ `INFERRED`（vnTinyRAM 上界） | 终止位置/公开 T 被约束 |

**适用范围限定（重要）**：上表 P1/P2/P3/P5 的 `VERIFIED` 指这些系统**各自固定的事件语义**——VDORAM 的"逐周期访问记录（含 dummy）"、Cairo 的 trace 行、RISC Zero 的 trace 行。它证明的是"系统自身定义的事件在其统一关系内完整、有序、绑定终止"，**不等于**任意应用自定义 `φ`/`S_req` 下的事件完整性已被普遍解决。把具体系统的证明能力外推到任意应用事件策略，需要把该应用的 `φ`/`S_req` 纳入证明关系后重新判断（`UNKNOWN`）；这一点不改变"主流系统用统一关系、无两证明分离场景"的核心观察。

**因此**：

1. **P1/P2/P3/P5 不是开放问题**（`VERIFIED`/强 `INFERRED`）：VDORAM 论文全文已明确在一个统一关系内解决，Cairo/RISC Zero 等同样如此。
2. **P4 只在"执行证明与事件证明分离"时产生**。主流可验证计算系统没有这种分离；若分离无独立必要性，P4 是人为制造的问题（`INFERRED`）。
3. **"一份证明内同执行/同 witness 绑定"本身已有成熟密码学机制**（`INFERRED`）：collaborative zkSNARK 的单一公开 statement + extractor（W16, `VERIFIED`）、VDORAM 的多方 witness 绑定（W22, `VERIFIED`）、commit-and-prove（W18）。W19 仅是"把公开承诺纳入证明关系"的一个特定跨域关联实例，**不是通用跨证明绑定方案**，不得据此声称一般性 P4 已解决。递归/folding（W11–W14）与 accumulator（W20/W21）默认不提供，但把承诺纳入公开 statement 即可（已有构造）。这些针对的是**单证明/联合 witness**场景；"两独立证明靠相同字段绑定"的通用情形仍 `UNKNOWN`，只是当前无必须分离的用例。
4. 唯一可能的研究空间：证明**"必须分离证明"**的场景有真实必要性，且在该场景下现有 linking/commitment 机制不足。当前**无任何证据支持该前提**（`UNKNOWN`）。交 `decision.md` 裁决。

---

## 8. 逐项对照表

| 文献 | P1 | P2 | P3 | P4 | P5 | 尚未解决的具体缺口 |
| ---- | ---- | ---- | ---- | ---- | ---- | ------------------ |
| STARK 2018/046 | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | INFERRED | 无独立事件对象；终止位置非公开字段 |
| Cairo CPU 2021/1063 | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | VERIFIED | 事件为应用级抽象，证明外发布无绑定 |
| Cairo AIR 形式化 2109.14534 | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | VERIFIED | 仅形式化编码，不含事件分离 |
| vnTinyRAM USENIX'14 | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | INFERRED | 公开运行时间上界 ≠ 真实停机步 |
| RISC Zero 2023 | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | VERIFIED | 终止行号未单列公开；无事件分离 |
| Jolt 2023/1217 / Lasso 2023/1216 | VERIFIED | INFERRED | INFERRED | UNKNOWN | UNKNOWN | 应用级必录事件与终止位置未定义 |
| SP1 / zkSync Era | INFERRED | INFERRED | INFERRED | UNKNOWN | UNKNOWN | 无原始论文可核对 |
| PLONK 2019/953 | INFERRED | INFERRED | UNKNOWN | UNKNOWN | UNKNOWN | permutation 非事件时序 |
| plookup 2020/315 | INFERRED | INFERRED | UNKNOWN | UNKNOWN | UNKNOWN | multiset 丢序；无跨证明语义 |
| Halo 2019/1021 | INFERRED | INFERRED | INFERRED | UNKNOWN | UNKNOWN | 递归只压缩验证 |
| Bitansky 等 2012/095 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 一般框架，无执行事件 |
| BCTV CRYPTO'14 2014/595 | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | INFERRED | 验证对方 verifier，非 witness 相等 |
| PCD Chiesa–Tromer 2010 | UNKNOWN | UNKNOWN | UNKNOWN | INFERRED* | UNKNOWN | *仅公开数据/历史绑定 |
| Nova 2021/370 | INFERRED | INFERRED | INFERRED | UNKNOWN | INFERRED | folding 不保证 witness 相同 |
| Plonky2 2022 | INFERRED | INFERRED | INFERRED | UNKNOWN | UNKNOWN | 公开输入哈希只绑定被哈希项 |
| Collaborative zkSNARK 2021/1530 | INFERRED | INFERRED | INFERRED | VERIFIED† | UNKNOWN | †单证明内多方绑定，非两证明 |
| MPC-in-the-head STOC'07 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 单 prover 模拟多方 |
| commit-and-prove 2016/074 | UNKNOWN | UNKNOWN | UNKNOWN | INFERRED | UNKNOWN | 先承诺后定 statement |
| Cross-domain NIZK 2019/063 | UNKNOWN | UNKNOWN | UNKNOWN | INFERRED | UNKNOWN | 特定跨域承诺关联实例，非通用跨证明绑定 |
| RFC 6962 / Trillian | UNKNOWN | UNKNOWN | INFERRED | UNKNOWN | UNKNOWN | consistency 仅 append-only；内容靠应用 |
| **VDORAM NDSS'26**（逐周期记录语义） | **VERIFIED** | **VERIFIED** | **VERIFIED** | **UNKNOWN‡** | **VERIFIED** | ‡单证明无两证明场景；多方绑定 VERIFIED；无 eid/事件摘要公开字段；P1–P3/P5 仅限其自身事件语义，不外推任意 φ/S_req |
| RAM ZK CCS'21 2021/979 | INFERRED | INFERRED | INFERRED | UNKNOWN | INFERRED | 未直读正文 |
| MacORAMa / Freecursive / EVO | INFERRED | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 内存/硬件完整性，非执行事件 |

\* 见正文对应脚注；† 单证明内多方 witness 绑定；‡ 两证明绑定场景不存在于该系统。

---

## 9. 排查小结

| 性质 | 现有工作是否已解决 | 判断依据 |
| ---- | ------------------ | -------- |
| P1 | **是**（`VERIFIED`，各自固定语义） | VDORAM/Cairo/RISC Zero：事件在电路/trace 内产生，extractor 恢复合法执行 |
| P2 | **是**（`VERIFIED`，各自固定语义；VDORAM/Cairo/RISC Zero） | 每步记账含 dummy、访问数=周期数、permutation 不变量 |
| P3 | **是**（`VERIFIED`，各自固定语义；VDORAM 时间戳/Cairo 时钟/RISC Zero permutation） | 步序即执行顺序 |
| P4 | 场景在主流系统中不存在；"同 witness 绑定"已有 `VERIFIED` 成熟构造（W16/W22） | collaborative 单 statement + extractor；commit-and-prove |
| P5 | **是**（`VERIFIED`，VDORAM T 公开/Cairo final 公开/RISC Zero control 列） | 终止位置/公开 T 被约束 |

> 上表"已解决"指各系统**自身事件语义**下由统一 trace 关系解决；对任意应用自定义 `φ`/`S_req` 的外推不在其证明范围内（`UNKNOWN`）。这一限定不改变 NO_GO 的核心依据（主流系统统一关系、无两证明分离场景）。

- **总体**：候选问题表述中的 P1/P2/P3/P5 已被现有工作解决；P4 在统一 trace 系统里不构成缺口，而"跨实体/跨参与方同 witness 绑定"已有成熟密码学构造。
- **不得写成"首次提出"**：本轮只是标记一个待裁决的研究空间，不断言新颖性。
- 最终裁决见 `decision.md`。
