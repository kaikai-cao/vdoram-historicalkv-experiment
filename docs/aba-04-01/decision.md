# ABA-04-01 — 研究问题立项决策

> 起点 commit：`13e8115c6734e3711972a156d3be8d6af3eb5978`。
> 输入：`problem_definition.md`（P1–P5）、`related_work.md`（六方向排查与逐项对照）、`construction_candidates.md`（四类构造）、`minimal_prototype_spec.md`（8 负面测试）、`evidence_and_references.md`（原始来源）。
> 结论标签限定五选一；不为继续项目强行 GO，也不把"工程量大"直接等同"无研究价值"。

---

## 1. 最终决策

> **`NO_GO_RESEARCH_PROBLEM`（按当前问题表述）**

**精确含义**：按当前候选问题的表述——"执行证明与事件证明**分离**时，如何证明 P1–P5"——不构成立得住的独立密码学研究问题。理由不是"做不到"，而是：

1. **P1/P2/P3/P5 已被现有工作解决**（`VERIFIED`）：VDORAM 论文本身（问题来源）在一个统一 trace/R1CS 关系内一次性解决 P1–P3 与 P5（见 `related_work.md` §6/W22，官方 PDF 全文核对）；Cairo、RISC Zero、STARK 同样在统一关系内覆盖。`problem_definition.md` 中最需要显式密码学 linking 的两项之一 P5，在这些系统里是标准能力。
2. **P4（跨证明同执行绑定）在证据充分的系统里不成立为缺口**（`INFERRED`+`VERIFIED`）：上述系统均为**单一证明**，不存在"两个独立证明靠相同 `eid`/摘要字段通过验证"的场景。P4 是**人为制造**的问题——它只在"主动把统一 trace 拆成两个证明"时产生。
3. **"同执行/同 witness 绑定"本身已有成熟密码学构造**（`VERIFIED`）：collaborative zk-SNARK 用单一公开 statement x 绑定全部 `w_i`、extractor 恢复联合 witness（`related_work.md` W16）；VDORAM 多方 witness 绑定同理（W22）；commit-and-prove（W18）与 Pedersen 绑定实例（W19）给出"先承诺 witness、后定 statement/绑定公开承诺"的范式。这些已覆盖"私有 witness 同一性"的可证明机制。
4. **剩余空间没有可辩护的必要性前提**（`UNKNOWN`）：要让 P4 成为真问题，必须证明"分离证明"有真实必要性（如跨信任域、跨组织、增量发布且不能合并为单关系），且现有 linking/commitment 机制在该场景下不足。本轮未找到任何原始来源支持这一前提。

**与历史结论的关系**：本决策**不**推翻 `ABA-03-D3-03-03` 的 `NO_GO_CURRENT_ARCHITECTURE`（那是针对 VDORAM 当前 C#/Rust 架构的实现判定），也不解除 `HOLD_INSUFFICIENT_EVIDENCE`。本决策针对的是"把问题抽离后是否值得作为独立密码学路线"——答案是按当前表述不值得。

---

## 2. 八个必答问题

### Q1. P1–P5 中哪些已被现有工作解决？

| 性质 | 是否已被解决 | 依据与等级 |
| ---- | ------------ | ---------- |
| P1 Event soundness | **是**（`VERIFIED`） | VDORAM Def IV.1 extractor 恢复合法执行 `s∈R`；事件元组在指令电路内产生；Cairo/RISC Zero 同 |
| P2 Event completeness | **是**（`VERIFIED`） | VDORAM 每周期恰好一条（含 dummy）、访问数=周期数、permutation 保证排序未改写；Cairo 每行一步 |
| P3 Event ordering | **是**（`VERIFIED`） | VDORAM `t` 单调递增 + (addr,t) 排序 + 相邻式(1)；Cairo 时钟行；RISC Zero permutation |
| P4 Cross-proof binding | 场景不存在（`INFERRED`）；绑定机制已有成熟构造（`VERIFIED`） | 上述系统单证明；collaborative zk-SNARK 单一 statement 绑定多方 witness；commit-and-prove |
| P5 Termination binding | **是**（`VERIFIED`） | VDORAM §IV-E.3 `T` 公开、halt 类型公开；Cairo final 寄存器公开；RISC Zero control 列 |

**结论**：P1/P2/P3/P5 已有可核对的正面证据（`VERIFIED`）；P4 要么不适用，要么已被通用构造覆盖。

### Q2. 剩余缺口是否具有独立密码学价值？

- 若把缺口定义为"在强制分离的场景下证明两证明同执行"：**缺口的前提（强制分离的必要性）未获任何证据支持**（`UNKNOWN`）。
- 若把缺口定义为"跨参与方私有 witness 绑定"：**已有 VERIFIED 构造**（W16/W22/W18/W19），不是开放问题。
- 因此**剩余缺口不构成有独立价值的密码学问题**（`INFERRED`）。唯一的 `UNKNOWN` 是"是否存在一个必须分离、且现有机制不足的具体应用"；没有该应用，缺口是假设性的。

### Q3. 是否只是工程接口拼接问题？

- **是**（`INFERRED`）。若真要分离，所需组件——binding 承诺、公共 statement 绑定、linking/opening、把承诺纳入 statement 后的递归——全部是已有原语。把它们组合起来属于工程接口拼接，不产生新密码学原语或新证明语句。
- 反向说明：这不意味着工程量小（`construction_candidates.md` 列出大量电路改动），但"工程量大"与"有研究价值"是两回事，本文不以前者推断后者。

### Q4. 是否存在可以证明的安全定理？

- 对 P1/P2/P3/P5 可写出 soundness/completeness 定理，但**这些定理已被 VDORAM/Cairo 等证明或形式化**（`VERIFIED`，W1/W2/W22），不构成新结果。
- 对 P4 若不加新构造，最多把定理归约到 collaborative zk-SNARK 的单 statement extractor（`VERIFIED`，W16）——是已知定理的应用，不是新定理。
- **本轮未发现可证明且新颖的安全定理**（`UNKNOWN`，因未穷尽所有文献；但现有证据已覆盖主要方向）。

### Q5. 是否需要新的 commitment / accumulator / proof composition 构造？

- **不需要新构造即可解决当前表述的 P1–P5**：统一 trace 关系（已有）+ collaborative 多方绑定（已有）足够（`INFERRED`）。
- accumulator/hash chain（W20/W21）与递归（W11–W14）单独都不解决 P1/P4，且把它们纳入 statement 的链接技巧已有先例（W18/W19）。
- 因此**没有证据支持需要新密码学构造**（`UNKNOWN`（未穷尽）+ `INFERRED`（现有已足够））。

### Q6. 是否适合使用 Halo2 / PLONK / Groth16 / recursive SNARK？

- 工具选择不是当前瓶颈：P1/P2/P3/P5 依赖的是**把执行与事件放进同一关系**（任何 PLONKish/Halo2/STARK 都能表达），而不是某个特定 SNARK（`INFERRED`）。
- 递归只压缩验证，不产生 P4（`INFERRED`，W11–W14）；Groth16 的 per-relation setup 与本研究问题正交（不应混用其假设，见 `evidence_and_references.md` §0）。
- **若未来发现问题确有独立价值，工具选择应服从证明语句需求，而非反过来以工具定义研究问题。**

### Q7. 最小原型是否能验证核心主张？

- `minimal_prototype_spec.md` 的玩具模型与 8 负面测试可以验证**实现层接口一致性**（如 T5/T6 在 linking 存在时被拒、L1–L3 被接受），但**不能验证新颖性主张**：因为 P1/P2/P3/P5 已被现有系统 VERIFIED 解决，原型只是复现已知机制（`INFERRED`）。
- **原型测试通过 ≠ 密码学安全证明**（已写入 `minimal_prototype_spec.md` §4），也**不等于研究问题成立**。
- 因此"做原型"无法挽救一个前提不成立的问题。

### Q8. 与现有 zkVM、递归证明和可验证日志相比，创新点究竟在哪里？

- 与 zkVM（Cairo/RISC Zero/Jolt/VDORAM）：它们在统一 trace 内解决 P1/P2/P3/P5；本研究若只是拆成两证明，**没有内容创新**（`INFERRED`）。
- 与递归证明（Halo/Nova/BCTV/Plonky2）：递归证明公开 statement 链，不证私有 witness 相同；但 collaborative zk-SNARK/commit-and-prove 已解决该绑定，**没有机制创新**（`INFERRED`）。
- 与可验证日志（RFC 6962/Trillian）：consistency proof 不保证事件内容与真实执行一致；但这是已知的、由应用审计填补的边界，**没有新性质**。
- **结论：在当前证据下找不到清晰、未被解决、可形式化的独立创新点**（`UNKNOWN`（未穷尽）+ `INFERRED`（主要方向已覆盖））。不得把"未找到"写成"首次提出"。

---

## 3. 结论理由（为何不是其他四项）

| 候选结论 | 为何不选 |
| -------- | -------- |
| `GO_TO_FORMAL_MODEL` | P1/P2/P3/P5 已有 VERIFIED 形式化（Cairo Lean 定理、VDORAM Def IV.1）；P4 前提未立。无独立新模型可建（`INFERRED`）。 |
| `GO_TO_MINIMAL_PROTOTYPE` | 原型只能复现已知机制，不能验证新颖性；且 Q3 判定为工程拼接（`INFERRED`）。 |
| `GO_WITH_RESTRICTED_SCOPE` | 字面可把范围缩到"强制分离场景"，但该场景必要性无任何证据（`UNKNOWN`）；缩小到一个假设性场景不构成可辩护的 GO。若未来出现真实必须分离的应用并有原始证据，可重新评估。 |
| `HOLD_INSUFFICIENT_EVIDENCE` | 本轮证据足以判定主要性质已被解决（VERIFIED），并非"不足以判断"；只是不足以支撑 GO，故应给出明确 NO_GO 而非悬置。 |
| **`NO_GO_RESEARCH_PROBLEM`** | **采纳**：现有工作已充分覆盖 P1/P2/P3/P5 与跨 witness 绑定；P4 在证据充分系统中不成立为缺口；剩余空间缺必要性前提（`INFERRED` + `VERIFIED` 证据）。 |

---

## 4. 保留的研究空间（不作为本轮 GO）

以下仅为诚实的 `UNKNOWN` 记录，**不构成立项理由**，供未来若有新证据时重新评估：

- 是否存在真实应用必须把执行证明与事件证明**分属不同信任域、不同证明系统或不同时间**生成，且无法合并为单一关系（`UNKNOWN`，本轮无原始来源支持）。
- 在该场景下，现有 collaborative zk-SNARK/commit-and-prove 绑定是否因跨信任域而失效（`UNKNOWN`）。
- 若上述两点都被具体证据证实，才可能重新评估为 `GO_WITH_RESTRICTED_SCOPE`。当前不满足。

---

## 5. 停止边界与状态冻结声明

- 本决策**不解除**任何历史 HOLD：`HOLD_INSUFFICIENT_EVIDENCE`（总决策）、`BLOCKED_BY_TRUST_MODEL`、`BLOCKED_BY_CURRENT_INTERFACE`、`NO_GO_CURRENT_ARCHITECTURE`、`B4_RELATION_PARTIALLY_FORMALIZED`、P1-A/VK/P2 既有判定均不变。
- 本轮**不修改**任何 ABA-03 及历史文档、源码快照、实验代码、数据、配置；只新增 `docs/aba-04-01/` 六份文档。
- 本轮**未实现**任何电路、verifier、commitment gadget、accumulator、MPC 或 ORAM。
- 本轮结论**不启动** ABA-04-02，也不进入原型开发；等待独立审查。
- 标签纪律：本文所有"已解决"判断均有 `VERIFIED` 原文依据；所有"未穷尽"判断标 `UNKNOWN`；未把候选构造写成安全证明，未把原型测试写成安全证明，未把"未找到相关工作"写成"首次提出"。

---

## 6. 一句话总结

把问题从 VDORAM 抽离出来后，证据显示：P1/P2/P3/P5 已被统一 trace 关系（含 VDORAM 论文本身）`VERIFIED` 解决，P4 在单证明系统中不成立为缺口且跨 witness 绑定已有成熟构造，因此按当前表述**不值得**作为独立密码学研究路线（`NO_GO_RESEARCH_PROBLEM`）；只有在出现"必须分离证明且有原始证据"的新前提时，才重新评估。
