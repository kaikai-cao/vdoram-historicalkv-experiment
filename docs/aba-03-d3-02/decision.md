# ABA-03-D3-02 / Phase 5：B4 事件完整性关系形式化决策

> 实验仓起点：`e93e882ab01dca5c44768f0be8a1a81a246c4318`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读形式化与反例分析；不实现电路、不重抓源码、不解除任何 HOLD、不启动 D3-03、不改 P1-A / VK / P2。
>
> 候选结论：`B4_RELATION_FORMALIZED` / `B4_RELATION_PARTIALLY_FORMALIZED` / `HOLD_INSUFFICIENT_EVIDENCE`。
>
> 证据来源：`b4_security_goal.md`、`event_sequence_relation.md`、`completeness_attack_matrix.md`、`candidate_constructions.md`；既有证据见文内逐项引用。

---

## 1. 决策：`B4_RELATION_PARTIALLY_FORMALIZED`

**理由**：本轮成功把 B4 表达为明确的验证关系问题，并给出本轮核心验收要求的**形式化答案**——计数相等无法区分“数量相同但内容不同”的序列，而能区分它们的最小关系集合可明确写出（`R2 覆盖 + R3 注入 + R5 step 绑定 + R6 类型 + R7 trace + R8 终止`，配合 verifier 固定的 `T`）。八项关系（R1–R8）已有约束草案、输入、生成者、verifier 可检查性与上游现状；九类攻击有决定性关系映射；四种候选构造有统一比较。

**为什么不是 `B4_RELATION_FORMALIZED`**：关系骨架虽已写出，但其中若干**构成项缺乏 verifier 可检查的落地定义**——`R5` 的 step 索引当前是宿主公开注入而非电路约束产生（`ZkProgramExecutor.cs:393-395`）、`R6` 的 `is_mem_op` 被 Prove 电路忽略（原始 L164-165）、`R7` 的 step↔row 对应未证、`R8` 的真实终止步 `T` 无 verifier 锚定（`globalStepsNoMoreThan` 仅是执行器阈值 `:114-116`）。这些在 `event_sequence_relation.md` 中为 `UNKNOWN`/`BLOCKED`/`CONSTRUCTED`；“关系草案存在”不等于“关系已可验证地形式化闭合”。因此只给部分形式化。

**为什么不只写 `HOLD_INSUFFICIENT_EVIDENCE`**：本轮不是无产出——核心判别问题（count 相同、内容不同的序列如何区分）已被正面回答并形式化，攻击矩阵与关系集合明确。若退回纯 `HOLD_INSUFFICIENT_EVIDENCE`，会抹去这一实质性进展。但注意：本决策**仅针对 B4 关系的形式化程度**，不改变总决策。

**关键边界（必须同时声明）**：
- 关系形式化成功 **不意味着** 现有实现满足 B4；固定 commit 无独立 verifier、无事件序列 statement、无 step 覆盖/终止约束，B4 仍为独立阻断项。
- 关系形式化成功 **不意味着** 可以进入电路实现、接口规格或解除任何 HOLD。
- 总决策仍为 `HOLD_INSUFFICIENT_EVIDENCE`（见 §5）。

---

## 2. 六个必答问题

### Q1. B4 是否能被表达为一个明确的验证关系？

**部分能。** 安全目标已精确定义为 `Accept(P) ⇒ P ≡ E*`（`b4_security_goal.md` §1），并分解为 R1–R8 八项关系草案（`event_sequence_relation.md` §2）。其中：
- 可清晰表达：`E*`/`P` 的序列等价、count 必要非充分性、step 覆盖/注入、type/trace/termination 绑定的约束形态；
- 尚不能 verifier 可检查地表达：step 的可信产生（R5）、`is_mem_op` 的证明层绑定（R6）、step↔row 映射（R7）、真实终止步 `T`（R8）——这些缺具体电路/接口定义，标 `UNKNOWN`/`BLOCKED`。
- 因此是“关系问题明确、构成项部分落地”，非完整形式化。

### Q2. 哪些条件是必要条件，哪些只是充分条件？

**必要条件**（缺一则 B4 不成立）：
- 三类计数：`N_all=T−1`、`N_real=M`、`N_dummy=T−1−M`、加和式（`event_completeness.md` E1a–E1d）——**必要非充分**；
- R2 覆盖、R3 注入、R5 step 绑定、R6 类型绑定、R7 trace 绑定、R8 终止绑定——每一类攻击对应一类必要关系（`completeness_attack_matrix.md` §3）。

**充分条件（仅在抽象关系层、关系被完美执行且 T 可信的前提下）**：
- 合取 `R2 ∧ R3 ∧ R5 ∧ R6 ∧ R7 ∧ R8` 配合 verifier 固定的 `T`，在 `event_sequence_relation.md` §4 的鸽巢论证下足以排除本轮列举的九类攻击（同数量不同内容、step/type/row 伪造、前缀截断）。
- 该充分性是**逻辑层充分**，不是实现层充分：关系若未被正确电路约束/验证，充分性不成立；也未证明可抵御未列举的攻击。

**明确不充分**：`count(P)=T−1` 与三类计数相等单独均不充分——反例见 `b4_security_goal.md` §1.2、`event_sequence_relation.md` §4。

### Q3. 哪些候选构造至少在逻辑上覆盖了所有攻击类别？

**没有一个候选单独覆盖全部九类**（`candidate_constructions.md` §2）：
- A（连续 step-index）对遗漏/复制/多余/重排最直接，但不能单独处理 type/trace 伪造与前缀截断（需叠加 R5/R6/R7/R8）；
- B（累积承诺）若无可信终值等于无完整性，且不能单独处理 step/type/trace 伪造；
- C（电路内直接绑定）在 step/type/row 上最强，但仍需终止步 `T`/halt 进入 statement（R8）；
- D（递归/组合）受“递归不能读子证明私有 witness”硬约束，把问题转移为子证明自身完整性，未消除核心难点。
- **共同必需**：任何方案都必须额外补齐 `R8`（真实终止步）与 `R5/R6/R7`（每步内容绑定）；四方案都只是关系骨架的一部分。

### Q4. 哪些性质依赖 VM 执行电路本身，而不能由独立 Fetch 证明补足？

以下性质依赖 VM 执行电路（或其与证明系统的接口），独立 Fetch 证明无法补足（`event_sequence_relation.md` R5–R8、`completeness_attack_matrix.md` §3）：
- **R8 真实终止步与 halt 边界**：`T` 必须是真实执行终止步，不是 prover 自报；`globalStepsNoMoreThan` 为执行器阈值（`:114-116`），非电路约束。
- **R6 事件类型来源**：`is_mem_op` 由 opcode 在 VM 电路派生（`ZkVmExecutor...cs:968-976`），Prove 忽略它（原始 L164-165）；独立 Fetch 证明无法证明类型来自 opcode。
- **R5 step 的可信产生**：step 当前是宿主公开注入值（`:393-395`），与 pc/opcode/addr 无同电路公开绑定（`source_trace_audit.md` A1 末行）。
- **R7 step↔trace row 对应**：trace 行由执行器 append（`:389-402`），Prove 只查 trace 内部排序/同址值（原始 L80-158/L167-193），不含 step↔row 映射。
- 这些正是 B4 相对单步地址相等（B1）的 harder problem（`p2_binding_semantics.md` §3 B4）。

### Q5. 是否存在不改变地址隐私目标的候选方案？

**存在候选表述，但未闭合**。四种构造均可在“不公开真实 `reg0`、不把 dummy lookup 强设为 `p−1`”的隐私目标下表述（`candidate_constructions.md` §0、§2）：step/trace 地址以隐藏承诺或公开 step/类型（不含真实地址）形式处理；dummy 只承诺 `p−1`，lookup `reg0` 保持私有。C1 直接公开地址路径因隐私退化被排除（`design_options.md` §1）。
但**隐私目标能否成立仍依赖未决的承诺层**：MiMC binding 无公开归约、Pedersen 当前 PLONK/MPC 路径不承载（`../aba-03-d2/decision.md`），内容绑定与 hiding 尚未同时闭合 → 标 `UNKNOWN`/`BLOCKED`，不得声称已有满足隐私目标的可用方案。

### Q6. 现有固定上游接口距离该方案还缺少什么？

按类别列出缺口（均为本轮分析所得，不改 P1-A/VK/P2 既有结论）：

| 缺口 | 上游现状 | 标签 |
| --- | --- | --- |
| verifier 固定的真实 `T` / halt 边界 | 执行器阈值 `:114-116`，非电路约束 | `UNKNOWN` |
| 电路约束产生的 step 索引 | 宿主公开注入 `:393-395` | `CONSTRUCTED` / `UNKNOWN` |
| `is_mem_op` 证明层公开绑定 | 派生存在 `:968-976`，Prove 忽略 L164-165 | `CONSTRUCTED` / `UNKNOWN` |
| step↔trace row 映射 + dummy row 哨兵绑定 | Fetch 只按地址查 `mem_val`（`MemoryTraceFetch...cs:48-56,75-85`），不输出/强制 trace_addr | `CONSTRUCTED` / `UNKNOWN` |
| 事件序列 statement（R2/R3 覆盖/注入） | 无事件序列概念 | `BLOCKED` |
| real 地址完整字段范围 `0≤addr<n`、`n≤p−1` | 无范围约束（`source_trace_audit.md` A4） | `UNKNOWN` |
| 承诺方案定型与内容绑定（若走隐藏路径） | MiMC binding 无归约 / Pedersen 不承载 | `UNKNOWN` / `BLOCKED` |
| 独立 verifier / 固定 VK | 现场 `test_rng()` 同函数 setup/prove/verify（`plonk.rs:293-315`）| 既有 P1-A/VK 结论不变，独立未决 |

**这些缺口都不是本轮能补齐的**：本轮只做关系形式化与反例分析。

---

## 3. UNKNOWN / BLOCKED 清单（本轮新增与沿用）

- `UNKNOWN`：真实终止步 `T` 的 verifier 锚定；step 索引的电路可信产生；`is_mem_op` 证明层绑定；step↔row 对应；四类方案的任何具体成本（门数、时间、字节、轮次）；承诺层内容绑定与 hiding 同时闭合；地址隐私目标在可用方案中成立。
- `BLOCKED`：固定 commit 无独立 verifier / 事件序列 statement；R2/R3 verifier 可检查的覆盖/注入关系；Pedersen 接入当前 PLONK/MPC 路径。
- `CONDITIONAL INFERENCE`：无（本轮未新增 VK 相关条件推论，沿用 D1-C1 既有分级）。
- 攻击判定：全部为候选关系下的**可能性分析**，无一写成已复现攻击（`completeness_attack_matrix.md` §0/§3）。

---

## 4. 证据纪律与停止声明

- 本轮只新增五份 D3-02 文档，未改任何既有文档（D3-01、D1、D2、C2、ABA-03、EXP-DORAM），未改源码、测试、数据或配置。
- 只复用既有固定 commit 证据与行号，未重抓上游源码；未实现电路、未原型、未跑测试或基准。
- 所有上游事实提供文件路径 + 行号（`ZkProgramExecutor.cs:201-203/205-228/226/389-402/393-395/114-116`、`ZkVmExecutor...cs:224-227/941-943/968-976/989-997`、`MemoryTraceFetch...cs:41-43/48-56/75-85`、`MemoryTraceProve...cs` 原始 L80-158/L164-165/L167-193 等）；所有候选约束标 `CONSTRUCTED`、无证据项标 `UNKNOWN`/`BLOCKED`。
- 未把“理论上可攻击”写成“已复现”；未把文档形式化等同于电路实现或安全证明；未把普通哈希链等同于完整性证明。
- **未修改 P1-A / VK / P2 的既有结论；总决策 `HOLD_INSUFFICIENT_EVIDENCE` 保持不变**；ABA-03、C2、D1、D2、D3-01 的状态标签全部不变。
- **完成后停止**：不启动 D3-03，不实现接口或电路，不扩展其他阻断项，不重新审查已冻结旧阶段。

---

## 5. 总决策与下一步建议

- **本阶段结论**：`B4_RELATION_PARTIALLY_FORMALIZED`（本轮 B4 关系的形式化程度）。
- **总决策**：`HOLD_INSUFFICIENT_EVIDENCE`（不变）。
- **是否建议进入 D3-03 或实现**：不建议。B4 的核心难点（step 可信产生、内容绑定、真实终止步锚定、承诺层）仍未闭合，形式化关系尚无可实现的电路/接口支撑。若后续继续，应另行授权“条件闭合 / 规格前置”工作，优先处理 R8 终止锚定、R5 step 可信来源、R6/R7 证明层绑定，再谈接口规格。
- 本轮到此停止，等待独立审查。
