# ABA-03-D3-03-03 / 证据与定向文献

> 实验仓起点：`5c84f38c6df17acd458c1681a8ca18da0377281a`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：定向证据登记；不重新下载上游源码，不重跑实验，不做全领域文献综述。
>
> 标签：`SOURCE_VERIFIED` / `PAPER_CLAIM` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN`。

---

## 0. 使用边界

1. 本文件只登记与本轮四个定向问题直接相关的来源：独立 verifier / trusted setup / VK registry 信任模型；SNARK proof composition 与 public statement binding；VM execution trace completeness；ORAM/MPC proof 的跨关系绑定。
2. 文献中的系统假设不得互相搬运：Groth16 的 preprocessing/per-relation setup 语境、PLONK 的 universal/updatable SRS 语境、Halo 的无需 trusted setup 的递归语境，分别记录，不合并成“SNARK 的一般假设”。
3. `PAPER_CLAIM` 只表示该原始来源的摘要/正文可被核对；不表示 VDORAM 已采用该系统，也不表示该声明能解决本仓 B4/R5–R8。
4. `SOURCE_VERIFIED` 指本仓既有固定上游快照/审计文档中的可核对事实；本轮未重新抓取上游源码。
5. `CONSTRUCTED` / `INFERRED` 是本轮基于证据的构造或推论，不是已实现能力，也不是安全证明。
6. 普通签名、相同 `execution_id`、相同哈希字段、hash chain 都不自动等于电路内语义约束或跨 proof witness 绑定。

---

## 1. 原始文献与官方来源

| ID | 作者 / 年份 | 标题 | 原始链接 | 可核对声明 | 适用边界 | 标签 |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | Huayi Qi, Minghui Xu, Xiaohua Jia, Xiuzhen Cheng / 2026（NDSS 2026 accepted） | VDORAM: Towards a Random Access Machine with Both Public Verifiability and Distributed Obliviousness | <http://ndss-symposium.org/ndss2026/accepted-papers> | NDSS 2026 官方录用列表给出标题与作者；固定 artifact commit 由本仓 README 与脚本锚定 | 仅核实题名/作者/会议元数据；本轮未取得并逐句核实论文全文，不把论文整体安全声明记为 `PAPER_CLAIM` | `SOURCE_VERIFIED`（元数据） / `UNKNOWN`（全文声称） |
| L2 | Jens Groth / 2016 | On the Size of Pairing-based Non-interactive Arguments | <https://eprint.iacr.org/2016/260> | 摘要给出 pairing-based **preprocessing SNARK for arithmetic circuit satisfiability**；proof 为 3 个群元素，验证为单个 pairing product equation（3 pairings） | 用于说明“预处理 SNARK 的验证密钥/结构与应用 statement 不能混同”的文献语境；不声称 VDORAM 使用 Groth16。ePrint PDF 全文页本轮受 Cloudflare 拦截，未逐句核实 CRS/VK 与关系绑定的原文 | `PAPER_CLAIM`（摘要） / `UNKNOWN`（全文细节） |
| L3 | Ariel Gabizon, Zachary J. Williamson, Oana Ciobotaru / 2019 | PLONK: Permutations over Lagrange-bases for Oecumenical Noninteractive arguments of Knowledge | <https://eprint.iacr.org/2019/953> | 摘要给出 universal、updatable SRS 与 fully succinct verification；证明者开销相对 Sonic 更低 | 用于区分 setup 信任模型：通用/可更新 SRS 不等于应用级 program identity 或 statement 可信；不声称固定 VDORAM 完整后端等同原始 PLONK | `PAPER_CLAIM` |
| L4 | Nir Bitansky, Ran Canetti, Alessandro Chiesa, Eran Tromer / 2012 | Recursive Composition and Bootstrapping for SNARKs and Proof-Carrying Data | <https://eprint.iacr.org/2012/095> | 摘要给出 SNARK 的 recursive composition 与 proof-carrying data，用于分布式计算正确性执行 | 理论递归组合/PCD 语境；不直接给出 VDORAM 事件完整性或跨私有 witness 相等性 | `PAPER_CLAIM` |
| L5 | Sean Bowe, Jack Grigg, Daira Hopwood / 2019 | Recursive Proof Composition without a Trusted Setup | <https://eprint.iacr.org/2019/1021> | 摘要给出 Halo：在普通椭圆曲线循环上实现无需 trusted setup 的递归证明组合 | “无需 trusted setup”只移除该类 setup 信任，不移除 verifier 主体、固定 statement、公开输入来源或递归电路正确性信任 | `PAPER_CLAIM` + `INFERRED`（边界解释） |
| L6 | Tim Dokchitser, Alexandr Bulkin / 2023 | Zero Knowledge Virtual Machine step by step | <https://eprint.iacr.org/2023/1032> | 文中给出 zkVM 的 time/step column、边界约束、public input/output hash 与递归拆分思路 | 入门/构造性综述；用于说明“step 列与终止边界需要显式约束”，不是 B4 完整性证明，也不针对 VDORAM | `PAPER_CLAIM` |
| L7 | Vineet Nair, Justin Thaler, Michael Zhu / 2025 | Proving CPU Executions in Small Space | <https://eprint.iacr.org/2025/611> | 摘要/正文给出 zkVM 证明 CPU 执行；典型流程先承诺 execution trace，再证明 trace 有效；shard/recursion 会把外部 statement 变为“持有多个分片证明”并增加审计面 | Jolt/sum-check 与内存优化语境；不用于推导 VDORAM 当前实现能力，也不把递归缺点写成 VDORAM 已复现攻击 | `PAPER_CLAIM` |

---

## 2. 本仓源码与既有审计证据（只读）

| ID | 事实 | 位置 | 边界 | 标签 |
| --- | --- | --- | --- | --- |
| S1 | 固定上游为 `BDS-SDU/vdoram-artifacts@10c90d35464620a35ddb1e2c29d2e8725acedd52`；本轮未重新下载、未改快照 | `README.md:5`；`scripts/fetch_snapshot.py:6`；`scripts/fetch_snapshot_exp02.py:6` | 证明锚点一致，不证明上游之外的部署事实 | `SOURCE_VERIFIED` |
| S2 | 当前固定 commit 无独立 verifier；同一函数内 setup→prove→verify，VK 由 `test_rng()` 现场生成 | `docs/aba-03-d3-03-02/verifier_vk_trust_model.md:17-20`；`docs/aba-03-d3-03-02/decision.md:15,80` | “现场生成”是源码事实；外部是否另有 verifier 仍 `UNKNOWN` | `SOURCE_VERIFIED` |
| S3 | public inputs 来自 prover JSON；`verify_proof(pvk, proof, public_inputs)` 只做长度 + pairing 等式 | `docs/aba-03-d3-03-02/trust_boundary_inventory.md:19,38`；`docs/aba-03-d3-03-02/verifier_vk_trust_model.md:19-20` | 进入 proof statement ≠ 来源可信 | `SOURCE_VERIFIED` |
| S4 | opcode table 是 prover JSON public wire；整表无约束；固定快照无 `execution_id`/`program_id`/`program_hash` | `docs/aba-03-d3-03-02/trust_boundary_inventory.md:39,66`；`docs/aba-03-d3-03-02/decision.md:15,81` | 通道层可填 ≠ verifier 期望值已固定；攻击结果另标 `UNKNOWN` | `SOURCE_VERIFIED` |
| S5 | `enc_key = Random()` 为 prover 侧私有 witness，不满足 verifier 生成/固定 execution identity | `docs/aba-03-d3-03-02/execution_anchor_statement.md` Q2；`docs/aba-03-d3-03-02/decision.md:36,49` | 当前无 `execution_id` 实体 | `SOURCE_VERIFIED` |
| S6 | `total_steps = T` 含 step 0；`last_step_index = T-1`；Fetch 索引 `[1,T-1]`、事件数 `T-1`；step 0 有 VM 执行与 trace row，无 Fetch proof、无 Fetch commitment event | `docs/aba-03-d3-03-02/execution_anchor_statement.md:11,80`；`docs/aba-03-d3-03-02/decision.md:33,96-97` | 本轮严格沿用，不重定义 | `SOURCE_VERIFIED`（本仓冻结） |
| S7 | R5–R8 当前判 `BLOCKED_BY_CURRENT_INTERFACE`：step/is_mem_op/step↔row/T 多为 host 或 prover 自报，无电路可信来源 | `docs/aba-03-d3-03-01/{r5_step_provenance,r6_r7_event_trace_binding,r8_termination_anchor,decision}.md` | 是接口阻断，不是密码学不可能性证明 | `SOURCE_VERIFIED`（既有判定） |
| S8 | B4 充分条件为 `R2 ∧ R3 ∧ R4 ∧ R5 ∧ R6 ∧ R7 ∧ R8`，且 T 必须 verifier 固定或可信锚定；R4 ordering 不可由 R2+R3 替代 | `docs/aba-03-d3-02/decision.md`；`docs/aba-03-d3-02/event_sequence_relation.md`；`docs/aba-03-d3-02/completeness_attack_matrix.md` | 反例 `E*=[e1(1),e2(2),e3(3)]` vs `P=[e1(1),e3(3),e2(2)]` 为逻辑构造，非执行复现 | `CONSTRUCTED` + `SOURCE_VERIFIED`（既有判定） |
| S9 | 当前跨 proof 只有宿主内部哈希比对；无共享公开承诺、无递归/组合证明接口 | `docs/aba-03-d3-02/proof_composition_binding.md:22,75`；`docs/aba-03-d3-02/decision.md:53,84` | 宿主键不等于 proof soundness | `SOURCE_VERIFIED` |
| S10 | `expected_step_bound` / `GlobalStepsNoMoreThan` 是 host 阈值；最终 T 由 host 记录且不进 statement | `docs/aba-03-d3-03-02/execution_anchor_statement.md:55,87`；`docs/aba-03-d3-02/decision.md:51` | 上界不等于实际 `total_steps` | `SOURCE_VERIFIED` |
| S11 | 冻结文件 `docs/aba-03-d3-03-02/verifier_vk_trust_model.md` 仍含 `final_step` 旧字段（第 38、41、50、93、94 行） | 本仓只读 grep | 本轮授权范围仅六份新文档，未改该文件 | `SOURCE_VERIFIED` |
| S12 | 当前阶段标签：`BLOCKED_BY_TRUST_MODEL`；B4：`B4_RELATION_PARTIALLY_FORMALIZED`；总决策：`HOLD_INSUFFICIENT_EVIDENCE`；P1-A/VK/P2 不变 | `docs/aba-03-d3-03-02/decision.md:91-98` | 本轮不解除或改写 | `SOURCE_VERIFIED` |
| S13 | 主证明路径为 Plonk（非 Groth16）；`groth16/verifier.rs` 是另存泛型 `verify_proof` 快照，与主路径关系 `UNKNOWN`；Marlin 仅见文献引述 | `docs/exp-doram-04/backend-facts.md:45-51,99`；`docs/exp-doram-04/decision.md:59,94` | 文献 L2 的 Groth16 setup 语境不得套到主路径；Groth16 快照存在 ≠ 主路径使用 | `SOURCE_VERIFIED`（角色定位） + `UNKNOWN`（关系） |

---

## 3. 由证据支持的构造与推断（非文献直接声称）

| ID | 结论 | 依据 | 标签 |
| --- | --- | --- | --- |
| I1 | verifier 信任某个执行锚点，不能推出 Fetch 事件序列完整；完整性必须由证明关系实际约束 | S7/S8/S9 + 证明验证语义 | `INFERRED` |
| I2 | 递归证明可以验证子 proof 对公开 statement 成立；除非把公共承诺/opening/linking 写进上层 statement，否则它不能比较两份子 proof 的私有 witness | L4/L5 + 公开验证语义 | `CONSTRUCTED` + `INFERRED` |
| I3 | 相同 `execution_id`、相同哈希字段或 hash chain 只能作为公开引用；witness 同一性与事件内容完整性仍需电路约束和 linking/opening proof | S4/S9 + L4/L5 | `CONSTRUCTED` |
| I4 | 普通独立软件 verifier 可以满足“验证固定 statement 上的 proof”这一最小目标；TEE 只在需保护 verifier 代码/配置免受宿主篡改时才成为额外信任根 | L2/L3/L5 + S2/S3 | `INFERRED` |
| I5 | `expected_step_bound` 只能排除超长执行，不能排除前缀截断，因为 `count(events)=T-1` 依赖真实 `total_steps` | S6/S10 + D3-02 计数语义 | `INFERRED` |
| I6 | 固定 VK 只保证验证某个证明系统/电路结构；不保证该电路对应预期 program，需显式 `vk_id↔program_id` 绑定 | S2/S4 + L2/L3 语境区分 | `INFERRED` |

---

## 4. 未决与不可写成已验证的事项

- `UNKNOWN`：Groth16 原文中 CRS/VK 与具体关系绑定的逐句表述尚未从 PDF 全文核实；本文件只使用 ePrint 摘要可核对部分。
- `UNKNOWN`：NDSS 2026 VDORAM 论文全文声称与固定 artifact 实现之间的逐项对应关系；本轮只读已固定快照与本仓既有审计。
- `UNKNOWN`：外部部署是否已有独立 verifier、固定 VK、registry 或 TEE；现有证据只覆盖固定 commit 内现场 setup/prove/verify 路径。
- `UNKNOWN`：针对 VDORAM 的跨 proof 拼接、statement substitution、T 截断是否可在外部系统实际复现；本轮只做逻辑构造与接口分析。
- `UNKNOWN`：本轮提出的研究问题相对既有 zkVM/PCD/可验证计算文献是否具有可发表新颖性；需独立 related-work 与最小可证结果后再判断。

---

## 5. 本文件不得支持的说法

- 不得写“已有独立 verifier”——S2/S3 相反。
- 不得写“固定 VK 已存在”或“prover 本地 `test_rng()` 说明外部不支持固定 VK”——前者无证据，后者是 D1-C1 已纠正的 overclaim。
- 不得写“增加 verifier 后 R5–R8/B4 自动闭合”——I1/I4 明确保留证明层缺口。
- 不得写“hash chain 保证事件内容完整性”——I3 明确禁止。
- 不得写“递归证明能读私有 witness 做同一性比较”——I2 明确禁止。
- 不得把 L2/L3/L5 的不同 setup 模型混成一条通用结论。

**结论（`INFERRED`）**：现有证据足以判定本轮信任根缺口的类型与边界，但不足以支持当前架构下的接口设计 GO；任何闭合路径都必须同时给出 verifier 侧可信来源与证明层语义约束。
