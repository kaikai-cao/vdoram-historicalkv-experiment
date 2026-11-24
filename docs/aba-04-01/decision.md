# ABA-04-01 — 研究问题立项决策

> 起点 commit：`13e8115c6734e3711972a156d3be8d6af3eb5978`。
> 输入：`problem_definition.md`（P1–P5）、`related_work.md`（六方向排查与逐项对照）、`construction_candidates.md`（四类构造）、`minimal_prototype_spec.md`（9 负面测试，T8 分 T8a/T8b）、`evidence_and_references.md`（原始来源）。
> 结论标签限定五选一；不为继续项目强行 GO，也不把"工程量大"直接等同"无研究价值"。

---

## 1. 最终决策

> **`NO_GO_RESEARCH_PROBLEM`（按当前问题表述）**

**精确含义**：按当前候选问题的表述——"执行证明与事件证明**分离**时，如何证明 P1–P5"——不构成立得住的独立密码学研究问题。**NO_GO 的首要依据是"缺乏必要性前提"，而非"所有跨证明绑定问题都已被彻底解决"。** 论据分四层，按强度排列：

1. **可统一建模的场景已有联合证明关系**（`VERIFIED`）：执行与事件能放进同一 trace 关系时，现有系统（VDORAM 官方 PDF 全文 W22、Cairo、RISC Zero、STARK）直接这么做——在其**自身固定事件语义**下 P1–P3/P5 于一个关系内一次性解决。问题来源 VDORAM 本身就是反证：它没有"独立事件证明"，从而没有 P4。
2. **多方持有 witness 已有成熟路径**（`VERIFIED`，但须正确理解其含义）：collaborative zk-SNARK 生成的是**单一证明**、针对一个公开 statement x 绑定联合 witness `(x,w_0,...,w_{N-1})∈R`，extractor 恢复完整 witness 元组（W16）；commit-and-prove（W18）给出"先承诺 witness、后定 statement"的范式。这里**必须纠正一处过度解读**：这些工作解决的是"一份证明内多参与方 witness 的联合绑定"，**并不**声称"自动解决了任意两份独立证明仅靠相同字段通过的绑定问题"（W19 只是一个特定跨域承诺关联实例，不是通用跨证明方案）。NO_GO 不依赖这个不成立的最强解读。
3. **没有"必须分离"的应用证据**（`UNKNOWN`，是决定性缺口）：本轮未找到任何可信原始来源表明存在这样的实际应用——执行证明与事件证明必须分离、且无法合并为单一关系（如跨信任域/跨组织/不可控增量发布）。P4 只在"主动把统一 trace 拆成两份证明"时人为产生；没有分离的必要性，拆开后再研究绑定就是无的放矢。
4. **因此"分离后如何绑定"不足以单独立项**（`INFERRED`）：以上三点合起来说明——统一场景（A）有联合关系、多方场景（B）有一份证明内的 collaborative 路径、分离场景（C）缺必要性证据。所谓"剩余缺口"即通用两独立证明同执行绑定，当前仍为 `UNKNOWN`、**并未被 A/B 覆盖**；但它建立在一个尚未证实的强制分离用例之上，故不足以单独立项。NO_GO 来自"用例缺失"，不是来自"C 已被解决"。

**适用范围限定**：论据 1 中 P1–P3/P5 的 `VERIFIED` 仅指这些系统**各自固定的事件语义**（VDORAM 为逐周期访问记录含 dummy，Cairo/RISC Zero 为 trace 行），不外推到 `problem_definition.md` 中任意应用 `φ`/`S_req`（后者为 `UNKNOWN`，见 `related_work.md` §7 限定段）。此限定不推翻 NO_GO——它反而说明：若真要研究"任意 `φ`",需先有该应用的必要性证据与显式证明关系，仍回到论据 3。

**与历史结论的关系**：本决策**不**推翻 `ABA-03-D3-03-03` 的 `NO_GO_CURRENT_ARCHITECTURE`（那是针对 VDORAM 当前 C#/Rust 架构的实现判定），也不解除 `HOLD_INSUFFICIENT_EVIDENCE`。本决策针对的是"把问题抽离后是否值得作为独立密码学路线"——答案是按当前表述不值得。

---

## 2. 八个必答问题

### Q1. P1–P5 中哪些已被现有工作解决？

| 性质 | 是否已被解决 | 依据与等级 |
| ---- | ------------ | ---------- |
| P1 Event soundness | **是**（`VERIFIED`，仅各自固定语义） | VDORAM Def IV.1 extractor 恢复合法执行 `s∈R`；访问元组在指令电路内产生；Cairo/RISC Zero 同 |
| P2 Event completeness | **是**（`VERIFIED`，仅各自固定语义） | VDORAM 每周期恰好一条（含 dummy）、访问数=周期数、permutation 保证排序未改写；Cairo 每行一步 |
| P3 Event ordering | **是**（`VERIFIED`，仅各自固定语义） | VDORAM `t` 单调递增 + (addr,t) 排序 + 相邻式(1)；Cairo 时钟行；RISC Zero permutation |
| P4 Cross-proof binding | 统一场景中场景不存在（`INFERRED`）；一份证明内多方 witness 绑定已有构造（`VERIFIED`，≠通用两证明绑定） | 上述系统单证明；collaborative zk-SNARK 单一 statement 绑定多方 witness（W16）；commit-and-prove（W18）；W19 仅是特定跨域关联实例 |
| P5 Termination binding | **是**（`VERIFIED`，仅各自固定语义） | VDORAM §IV-E.3 `T` 公开、halt 类型公开；Cairo final 寄存器公开；RISC Zero control 列 |

**结论**：在各系统**自身固定事件语义**下，P1/P2/P3/P5 有可核对的正面证据（`VERIFIED`），但不外推任意应用 `φ`/`S_req`（`UNKNOWN`）。P4 在统一场景中不适用；"一份证明内多方绑定"有成熟构造，但**不等于**通用"两独立证明靠相同字段绑定"已被解决——NO_GO 依据的是分离缺必要性，而非 P4 被普遍攻破。

### Q2. 剩余缺口是否具有独立密码学价值？

- 若把缺口定义为"在强制分离的场景下证明两证明同执行"：**缺口的前提（强制分离的必要性）未获任何证据支持**（`UNKNOWN`）——这是决定性的一点。
- 若把缺口定义为"一份证明内跨参与方私有 witness 绑定"：**已有 `VERIFIED` 构造**（W16/W22/W18），不是开放问题；但须明确它**不是**"两份独立证明靠相同字段绑定"的解法（W19 仅为特定跨域实例）。不得用前者冒充后者已解决。
- 因此**剩余缺口不构成有独立价值的密码学问题**（`INFERRED`）。唯一的 `UNKNOWN` 是"是否存在一个必须分离、且现有机制不足的具体应用"；没有该应用，缺口是假设性的。

### Q3. 是否只是工程接口拼接问题？

- **条件性回答**（`INFERRED`）：**若**将来证明分离确有必要，则所需组件——binding 承诺、公共 statement 绑定、linking/opening、把承诺纳入 statement 后的递归——全部是已有原语，组合它们属工程拼接，不产生新密码学原语或新证明语句。
- 但"是否只是拼接"的前提是"分离有必要"，该前提当前 `UNKNOWN`。因此更准确的裁决是：当前连"值得拼接的应用必要性"都没有，而非单纯"拼接没价值"。
- 反向说明：这不意味着工程量小（`construction_candidates.md` 列出大量电路改动），但"工程量大"与"有研究价值"是两回事，本文不以前者推断后者。

### Q4. 是否存在可以证明的安全定理？

- 对 P1/P2/P3/P5 可写出 soundness/completeness 定理，但**这些定理已被 VDORAM/Cairo 等证明或形式化**（`VERIFIED`，W1/W2/W22），不构成新结果。
- 对 P4 若不加新构造，最多把"一份证明内多方 witness 绑定"归约到 collaborative zk-SNARK 的单 statement extractor（`VERIFIED`，W16）——是已知定理的应用，不是新定理；且它不覆盖"两独立证明"场景。
- **本轮未发现可证明且新颖的安全定理**（`UNKNOWN`，因未穷尽所有文献；但现有证据已覆盖主要方向）。

### Q5. 是否需要新的 commitment / accumulator / proof composition 构造？

必须先区分三个**不同**的问题，不得把前两者的成熟路径组合成未经证明的通用结论：

- **情况 A：执行与事件可统一建模。** VDORAM、Cairo、RISC Zero 等系统在**各自固定事件语义**下使用统一关系（`VERIFIED`，见 Q1/§1 适用范围限定）。其结论只在各自语义内成立，**不外推**到 `problem_definition.md` 中任意应用 `φ`/`S_req`（后者为 `UNKNOWN`）。此情形不产生"两份独立证明绑定"问题。
- **情况 B：多个参与方共同持有 witness，但只生成一份证明。** collaborative zk-SNARK 已有联合 witness 绑定路径（`VERIFIED`，W16）：它证明的是**一份证明中**的联合关系 `(x,w_0,...,w_{N-1})∈R`，extractor 恢复完整 witness 元组；commit-and-prove（W18）给出"先承诺 witness、后定 statement"的范式。这**不是**任意两份独立证明之间的通用绑定，W19 亦仅为特定跨域承诺关联实例。
- **情况 C：必须分离为两份独立证明。** 通用"两独立证明同执行绑定"是否能由已有 commitment / opening / linking 机制充分实现，仍为 `UNKNOWN`。accumulator/hash chain（W20/W21）与递归（W11–W14）单独都不产生 P4，把它们纳入 statement 的链接技巧虽有先例（W18；W19 仅特定实例），但**不能因为 A、B 已有成熟路径就推断 C 已被解决**。

- 结论边界：**当前证据不支持"必须提出新密码学构造"**（`INFERRED`）；但**也不能据此断言所有分离证明场景都不需要新构造**（`UNKNOWN`，且本轮为定向排查、非穷尽）。真正决定性的是：**目前没有足以支撑开展该方向的真实强制分离应用证据**（`UNKNOWN`，见论据 3）。

### Q6. 是否适合使用 Halo2 / PLONK / Groth16 / recursive SNARK？

- 工具选择不是当前瓶颈：P1/P2/P3/P5 依赖的是**把执行与事件放进同一关系**（任何 PLONKish/Halo2/STARK 都能表达），而不是某个特定 SNARK（`INFERRED`）。
- 递归只压缩验证，不产生 P4（`INFERRED`，W11–W14）；Groth16 的 per-relation setup 与本研究问题正交（不应混用其假设，见 `evidence_and_references.md` §0）。
- **若未来发现问题确有独立价值，工具选择应服从证明语句需求，而非反过来以工具定义研究问题。**

### Q7. 最小原型是否能验证核心主张？

- `minimal_prototype_spec.md` 的玩具模型与 9 负面测试（T8 分 T8a/T8b）可以验证**实现层接口一致性**（如 T5/T6 在 linking 存在时被拒、L1–L3 被接受），但**不能验证新颖性主张**：因为 P1/P2/P3/P5 已在各系统自身语义下被 VERIFIED 解决，原型只是复现已知机制（`INFERRED`）。
- 其中 T8b（相同 `eid` 原样重放）**纯 SNARK 绑定一律不阻断**，需部署层 nonce/已消费标识/可信日志；原样重放不构成 P4 的证明层失败，不得计入 P4 结论。
- **原型测试通过 ≠ 密码学安全证明**（已写入 `minimal_prototype_spec.md` §4），也**不等于研究问题成立**。
- 因此"做原型"无法挽救一个前提不成立的问题。

### Q8. 与现有 zkVM、递归证明和可验证日志相比，创新点究竟在哪里？

- 与 zkVM（Cairo/RISC Zero/Jolt/VDORAM）：它们在统一 trace 内解决 P1/P2/P3/P5；本研究若只是拆成两证明，**没有内容创新**（`INFERRED`）。
- 与递归证明（Halo/Nova/BCTV/Plonky2）：递归证明公开 statement 链，不证私有 witness 相同；collaborative zk-SNARK/commit-and-prove 解决的是**一份证明内**多方 witness 或承诺绑定（W16/W18），W19 仅为特定跨域关联实例——**都不覆盖"两独立证明靠相同字段绑定"**，但当前也没有该场景的必要性证据，故**没有可辩护的机制创新**（`INFERRED`）。
- 与可验证日志（RFC 6962/Trillian）：consistency proof 不保证事件内容与真实执行一致；但这是已知的、由应用审计填补的边界，**没有新性质**。
- **结论：在当前证据下找不到清晰、未被解决、可形式化的独立创新点**（`UNKNOWN`（未穷尽）+ `INFERRED`（主要方向已覆盖））。不得把"未找到"写成"首次提出"。

---

## 3. 结论理由（为何不是其他四项）

| 候选结论 | 为何不选 |
| -------- | -------- |
| `GO_TO_FORMAL_MODEL` | P1/P2/P3/P5 已有 VERIFIED 形式化（Cairo Lean 定理、VDORAM Def IV.1）；P4 前提未立。无独立新模型可建（`INFERRED`）。 |
| `GO_TO_MINIMAL_PROTOTYPE` | 原型只能复现已知机制，不能验证新颖性；且 Q3 判定为工程拼接（`INFERRED`）。 |
| `GO_WITH_RESTRICTED_SCOPE` | 字面可把范围缩到"强制分离场景"，但该场景必要性无任何证据（`UNKNOWN`）；缩小到一个假设性场景不构成可辩护的 GO。若未来出现真实必须分离的应用并有原始证据，可重新评估。 |
| `HOLD_INSUFFICIENT_EVIDENCE` | 本轮证据足以给出明确判断：主流系统用统一关系、分离缺必要性（`UNKNOWN` 的是"是否存在必要应用"，不是"无法判断"）；故应明确 NO_GO 而非悬置。 |
| **`NO_GO_RESEARCH_PROBLEM`** | **采纳**：首要依据是**分离的必要性前提缺失**（`UNKNOWN` 关键的用例）；辅助依据是统一场景有联合关系、多方场景有 collaborative 路径（均 `VERIFIED`，各自语义范围内）。**不**声称"所有跨证明绑定问题已被解决"——通用"两独立证明同执行绑定"未被 W16/W19 覆盖，只是当前缺乏必须分离的应用场景。 |

---

## 4. 保留的研究空间（不作为本轮 GO）

以下仅为诚实的 `UNKNOWN` 记录，**不构成立项理由**，供未来若有新证据时重新评估：

- 是否存在真实应用必须把执行证明与事件证明**分属不同信任域、不同证明系统或不同时间**生成，且无法合并为单一关系（`UNKNOWN`，本轮无原始来源支持）。
- 在该强制分离场景下，通用"两独立证明同执行绑定"是否可由现有机制达成，或现有 collaborative zk-SNARK/commit-and-prove（解决的是**一份证明内**绑定，W16/W18；W19 仅特定实例）是否因跨信任域而失效（`UNKNOWN`）。**本轮已核实的工作尚未建立对一般两独立证明同执行绑定情形的覆盖；其是否可以由现有原语组合实现仍为 `UNKNOWN`。** 本轮是定向文献排查，**不是对全部相关文献的穷尽性证明**；当前没有使该问题成立的用例。
- 应用自定义 `φ`/`S_req` 下的事件完整性是否在某个具体应用中既必要又未被统一 trace 关系覆盖（`UNKNOWN`；不能拿 VDORAM 的逐周期记录语义外推）。
- 若上述前提都被具体证据证实，才可能重新评估为 `GO_WITH_RESTRICTED_SCOPE`。当前不满足。

---

## 5. 停止边界与状态冻结声明

- 本决策**不解除**任何历史 HOLD：`HOLD_INSUFFICIENT_EVIDENCE`（总决策）、`BLOCKED_BY_TRUST_MODEL`、`BLOCKED_BY_CURRENT_INTERFACE`、`NO_GO_CURRENT_ARCHITECTURE`、`B4_RELATION_PARTIALLY_FORMALIZED`、P1-A/VK/P2 既有判定均不变。
- 本轮**不修改**任何 ABA-03 及历史文档、源码快照、实验代码、数据、配置；只新增 `docs/aba-04-01/` 六份文档。
- 本轮**未实现**任何电路、verifier、commitment gadget、accumulator、MPC 或 ORAM。
- 本轮结论**不启动** ABA-04-02，也不进入原型开发；等待独立审查。
- 标签纪律：本文所有"已解决"判断均有 `VERIFIED` 原文依据；所有"未穷尽"判断标 `UNKNOWN`；未把候选构造写成安全证明，未把原型测试写成安全证明，未把"未找到相关工作"写成"首次提出"。

---

## 6. 一句话总结

把问题从 VDORAM 抽离出来后，证据显示：各系统**自身事件语义**下 P1/P2/P3/P5 已由统一 trace 关系（含 VDORAM 论文本身）`VERIFIED` 解决；主流系统为单证明、无两证明分离场景，一份证明内多方 witness 绑定已有 collaborative 成熟路径；而"必须分离证明"的必要性缺任何原始证据——故 NO_GO 的首要依据是**必要性前提缺失**，不是声称所有跨证明绑定都已解决（通用"两独立证明同执行绑定"仍 `UNKNOWN`，只是无用例支撑）。结论：按当前表述**不值得**作为独立密码学研究路线（`NO_GO_RESEARCH_PROBLEM`）；只有当出现"必须分离证明且有原始证据"的新前提，才重新评估。
