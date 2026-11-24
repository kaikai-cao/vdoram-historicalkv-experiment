# ABA-03-D3-03-02 / Phase 4–5：跨 Proof Composition 绑定与攻击面反例

> 实验仓起点：`62ec3827bc89fb495daf68735ab93d1ea0b1e7c0`；固定上游 `10c90d35…`。
>
> 性质：结合 VM / Fetch / MemoryTrace proof 路径分析"如何证明它们属于同一次 execution"；不实现 commitment / 递归 / 联合证明，不解除 HOLD。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 证据来源：`trust_boundary_inventory.md`；`../aba-03-d3-03-01/interface_evidence_inventory.md`；`../aba-03-d3-03-01/decision.md` §4（Option A/B）；`../aba-03-d2/context_and_replay.md` §3；`../aba-03-d2/decision.md`（承诺层）。

---

## 0. 四条禁止的错误推论（本轮硬约束）

所有跨 proof 绑定**必须**经由受约束公共输入、承诺及其 opening，或联合证明关系建立。以下推论一律禁止：

1. **相同 `execution_id` ⇒ 两个 proof 已绑定**：否。若 id 是各 proof 自行声明的公开值，prover 可给两个来自不同执行的 proof 填同一个 id。
2. **相同 hash / commitment ⇒ 两个 proof 已绑定**：否。相同承诺只说明"两边都声称开到这个承诺"；需 commitment 的 binding + 各自 opening 受约束 + 同一 context（`../aba-03-d2` 已明确 binding 未闭合）。
3. **proof chain 存在 ⇒ 链条完整**：否。hash 链对 prover 自选终值/前缀自洽，无可信终值则无完整性（R8）。
4. **递归验证器可直接读取子 proof 的 private witness**：否（D1-C1 已修正）。递归验证只读子 proof 的公开输入；跨证明私有量必须经受约束公共输入或承诺建立。

当前固定 commit 无递归/组合证明接口、无跨 proof 共享公开承诺（`plonk.rs:293-315` 单电路自测，`../aba-03-c2/verifier_interface_audit.md` §C），三类绑定机制**全部缺失** → 现状 `BLOCKED`。

---

## 1. 现有三条 proof 路径的绑定现状（`VERIFIED`）

| proof 路径 | 公开可见输出 | 跨 proof 绑定 | 绑定位置 | 标签 |
| --- | --- | --- | --- | --- |
| VM 执行（每步一个 session） | 逐步哈希 public output、halt、public input、step counter public input | 靠宿主哈希链自洽（前步输出哈希 = 后步输入哈希） | 宿主 `ZkProgramExecutor.cs` 快照 L174-181/L306-332 的 `if(...)throw` | `VERIFIED`（宿主检查，非 verifier） |
| Fetch（每步≥1） | 无专属 public input/output；地址与 trace 行私有 | 无跨 proof 公开绑定 | 宿主构造（快照 L216-230） | `VERIFIED`（缺失） |
| MemoryTrace Prove | `out_{i}_hash_mem_trace`、`out_is_satisfied` public output | 与 VM `out_hash_mem_trace` 靠宿主多重集计数比对 | 宿主 `ZkProgramExecutor.cs` 快照 L410 附近 / L551-583 | `VERIFIED`（宿主比对，非 verifier） |

**结论（`VERIFIED`）**：三条路径之间唯一的"绑定"是宿主执行器内部的哈希连续性/多重集比对，既不进 R1CS 也不进 verifier 可见 statement。verifier 当前无任何手段确认三个 proof 属于同一次执行。

---

## 2. Option A：统一 execution anchor

每个 proof 都公开或绑定同一个 execution anchor commitment。

| 要素 | 分析 | 标签 |
| --- | --- | --- |
| anchor commitment 如何生成 | 候选：由 `execution_anchor_statement.md` 的最小字段集 canonical 编码后 hash/承诺；生成者必须是 verifier 或受约束电路，**不能**是 prover 任意填的 hash | `CONSTRUCTED` |
| 各 proof 如何受约束绑定 anchor | 每个 proof 的 statement 必须把 anchor 作为公共输入，并在电路内约束本 proof 的 program/step/T/type 与该 anchor 一致（或提供受约束 opening） | `CONSTRUCTED` |
| verifier 如何检查 | 比对三个 proof 的 anchor 公共值相等 + 等于 verifier 固定的期望 anchor；相等本身不足（见 §0 第 2 条） | `CONSTRUCTED` |
| binding/hiding/opening 要求 | 若 anchor 是承诺：需 binding（防同承诺不同字段）、hiding（若字段敏感）、opening 受电路约束；当前 MiMC binding `UNKNOWN`、Pedersen 接入 `BLOCKED`（`../aba-03-d2/decision.md`） | `UNKNOWN`/`BLOCKED` |
| 相同 anchor 是否足以保证 proof 语义一致 | **否**：还需每个 proof 内部把其私有量正确绑定到 anchor 的受约束 opening；且 anchor 字段本身要覆盖 program/execution/T/type（否则遗漏维度） | `INFERRED` |

**Option A 状态**：逻辑骨架可写（`CONSTRUCTED`），但依赖承诺层（未决）与 verifier 固定 anchor（当前无）。相同 anchor 不是充分条件。

---

## 3. Option B：分层 transcript / proof chain

VM proof 输出执行摘要，Fetch proof 引用该摘要，MemoryTrace proof 再引用 Fetch/trace 摘要。

| 要素 | 分析 | 标签 |
| --- | --- | --- |
| 每个摘要绑定哪些字段 | 候选：VM 摘要绑定 program/execution_id/T/每步事件承诺；Fetch 摘要绑定 step/type/trace 承诺；终摘要绑定最终状态/T | `CONSTRUCTED` |
| 前后 proof 如何验证摘要来源 | 后一 proof 把前一摘要作为公共输入，并要求"前摘要是前一 proof 的公开输出"——这在当前分离证明路径中**无电路接口**支持（无递归/组合） | `BLOCKED` |
| 最终 verifier 如何获得可信终值 | 需 verifier 固定终摘要或可信推导；若终值由 prover 提供，则链对自报终值自洽 → 无完整性（R8） | `UNKNOWN`/`INFERRED` |
| 是否存在 prover 自选中间摘要/截断链条 | **存在**：若摘要无 verifier 锚点，prover 可截断到任意前缀并生成自洽链（Prefix truncation，§4 A8）；链存在 ≠ 完整 | `CONSTRUCTED_ATTACK` |

**Option B 状态**：链结构可写（`CONSTRUCTED`），但"后 proof 验证前摘要来源"需递归/组合接口（当前 `BLOCKED`），且终值可信来源未决。不得把"有链"写成"链完整"。

---

## 4. Option C：联合证明关系

把 execution anchor 与 VM/Fetch/MemoryTrace 关系放在同一证明 statement 或组合证明中。

| 要素 | 分析 | 标签 |
| --- | --- | --- |
| 哪些现有关系需合并/重写 | VM 逐步 session、Fetch 逐步 session、Prove session 需合并为单一关系或组合证明；`plonk.rs:293-315` 是单电路路径，无组合接口 | `CONSTRUCTED`；改造量 `BLOCKED` |
| 能否减少跨 proof 信任边界 | 能（`INFERRED`）：同关系内共享 witness（step/type/addr/T），无需跨 proof 承诺桥接；但把 R5–R8 全部纳入同一电路，代价大（`../aba-03-d3-03-01/decision.md` Option A） | `INFERRED` |
| 成本未知项 | 合并后门数、证明时间、VK 重设、MPC additive-only 路径兼容性全 `UNKNOWN` | `UNKNOWN` |
| 地址隐私与 dummy 影响 | 可保持：同关系内 reg0 保持私有、dummy 只承诺 `p−1`（冻结语义）；但需承诺层承载类型/trace 绑定，仍未决 | `CONSTRUCTED`（隐私目标）/ `UNKNOWN`（承诺层） |

**Option C 状态**：逻辑上最直接（减少跨 proof 边界），但改造量最大、依赖承诺层与 circuit 重写，当前不可接入。

---

## 5. 三方案对比小结（不选择胜者）

| 方案 | 跨 proof 边界 | 依赖承诺层 | 依赖递归/组合接口 | 当前可接入 | 主要缺口 |
| --- | --- | --- | --- | --- | --- |
| A 统一 anchor | 各 proof 共享 anchor | 是（binding/hiding/opening） | 否（但要各 proof 电路内绑定 anchor） | 否 | 承诺层未决 + verifier 固定 anchor 缺失 |
| B 分层链 | 相邻 proof 引用摘要 | 部分（摘要若隐藏） | 是（当前 `BLOCKED`） | 否 | 无递归接口 + 终值可信来源缺失 |
| C 联合证明 | 无跨 proof（合并） | 是（承载类型/trace） | 是（需重写为单关系） | 否 | 改造量大 + 承诺层未决 |

**共同缺口（`INFERRED`）**：三方案都要求"执行身份 + program + T 的可信来源"这一前置（`execution_anchor_statement.md`），当前无 → 都不构成当前可实现方案。本轮不选择胜者。

---

## 6. Phase 5：攻击面与反例（八类）

等级定义：`REPRODUCED`（真实复现）· `SOURCE_SUPPORTED`（源码接口支持风险判断）· `CONSTRUCTED_ATTACK`（逻辑构造，未复现）· `UNKNOWN`（缺验证证据）。**本轮不要求也不执行实际攻击复现**，故无 `REPRODUCED` 项。

| # | 攻击场景 | 攻击者改什么 | 当前实现能否阻止 | 等级 | 缺什么证据 |
| --- | --- | --- | --- | --- | --- |
| 1 | Program substitution | 替换 JSON 中 opcode public wire + 生成匹配 proof | 无独立 verifier 持有预期表；`verify_proof` 对自报 public 自洽 → 无法阻止（单独替换是否证明成功 = UNKNOWN） | `SOURCE_SUPPORTED`（无 verifier 期望值）+ `UNKNOWN`（攻击结果） | 固定表逐项比较是否实现、单独替换的约束关系分析 |
| 2 | Execution replay | 用旧执行 proof 应答新请求 | 无 execution_id、无 context 绑定、无 verifier 请求锚点 → 无法阻止 | `SOURCE_SUPPORTED` + `CONSTRUCTED_ATTACK` | verifier 生成的 execution_id 与请求绑定 |
| 3 | Cross-execution composition | VM proof 来自 A、Fetch proof 来自 B | 三 proof 无共享公开绑定，只有宿主内部比对 → verifier 无法识别 | `SOURCE_SUPPORTED` | 跨 proof 受约束公共锚点（§2/§3/§4） |
| 4 | T truncation | prover 声明较小 T、只提交前缀 | T 不进 statement、break 由 host、无电路 counter → verifier 无法识别 | `SOURCE_SUPPORTED` | 电路 counter + halt↔末项绑定 + 可信 T |
| 5 | VK substitution | prover 换 VK + 提供相应 proof | 当前 VK 现场 `test_rng()` 生成 → 若外部接受 prover 自提 VK 则无法阻止（条件前提） | `CONDITIONAL INFERENCE`（前提成立时）+ `UNKNOWN`（外部模型） | 外部 verifier 是否固定 VK（D1-C1 分级） |
| 6 | Statement substitution | proof 对 prover 自选 public input 有效但非应用预期 | `verify_proof` 只验证相对给定 public 的自洽 → 无法阻止 | `SOURCE_SUPPORTED` | verifier 固定的 statement 期望值（Model A） |
| 7 | Anchor equivocation | 不同 proof 对同一 execution_id 用不同 anchor 内容 | 无 anchor 概念、无 execution_id → 无法阻止 | `CONSTRUCTED_ATTACK`（依赖候选 anchor 存在） | anchor 的 binding + 各 proof 受约束绑定 + verifier 比对 |
| 8 | Chain truncation | transcript/proof chain 在非最终位置终止 | 无链接口；即使构造链，终值由 prover 提供则自洽 → 无法阻止 | `CONSTRUCTED_ATTACK` + `INFERRED` | 可信终值 + 完整链约束 |

**攻击面小结（`INFERRED`）**：八类场景在当前架构下**均无 verifier 侧阻止路径**，根因是同一个——verifier 无独立可信来源（VK、statement、execution_id、T 全缺）。所有等级均为源码接口支持的风险判断或逻辑构造，**无一写成已复现攻击**。

---

## 7. 本阶段结论

- 跨 proof 绑定在当前固定 commit `BLOCKED`：无共享公开承诺、无递归/组合接口、三条 proof 路径只靠宿主内部哈希比对。
- Option A/B/C 均可写出逻辑骨架（`CONSTRUCTED`），但都依赖"可信 execution anchor + 承诺层 + verifier 固定来源"前置，当前不可接入；相同 id/hash/链存在都不构成已绑定。
- 八类攻击面均无当前阻止路径，但均标为风险判断/逻辑构造，不作已复现声称。
- 与 `verifier_vk_trust_model.md` 的结论一致：绑定问题的根在信任模型（verifier 无可信来源），不在"能否设计一个 commitment/chain 结构"。这支撑 `decision.md` 的 `BLOCKED_BY_TRUST_MODEL`。
