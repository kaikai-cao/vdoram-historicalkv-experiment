# ABA-03-D3-03-02 / Phase 2：Execution Anchor Statement 候选设计

> 实验仓起点：`62ec3827bc89fb495daf68735ab93d1ea0b1e7c0`；固定上游 `10c90d35…`。
>
> 性质：只做候选 statement 设计与信任来源分析；不实现 commitment / anchor / verifier / 电路，不解除 HOLD。
>
> 标签：`VERIFIED` / `CONSTRUCTED`（本轮候选字段与约束） / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 证据来源：`trust_boundary_inventory.md`；`../aba-03-d2/context_and_replay.md`；`../aba-03-d3-01/verifier_independence.md`；`../aba-03/source_trace_audit.md`。

---

## 0. 前置警告：结构体 ≠ 可信 anchor

任务给出的 `ExecutionAnchor` 只是**候选字段清单**。设计一个结构体是密码学上平凡的；本轮的关键判据是：**verifier 是否有独立于 prover 的可信依据来接受这个 anchor 的每个字段**。若某字段最终只能由 prover 提供且无验证/可信来源，把它写进 anchor 只是把自我声明换了一种封装，不构成可信 execution statement。本文对每个字段都标注"生成者 / verifier 来源 / 约束位置 / 隐私影响"，而不只是列出字段名。

**禁止把 hash 当作自动可信来源**：一个字段是 hash 还是明文，不改变其信任来源。若 `program_commitment` 由 prover 生成且 verifier 无独立预期值，它不比明文 program 更可信。

---

## 1. 候选字段逐项分析

候选字段集（任务给出，非全部必要、非已存在）：

```
ExecutionAnchor = {
    protocol_version,
    program_id,
    program_commitment,
    public_input_commitment,
    initial_state_commitment,
    execution_id,
    expected_step_bound,
    final_step,
    final_state_commitment,
    vk_id
}
```

逐字段表：

| 字段 | 必要性 | 生成者 | verifier 来源 | 约束位置 | 隐私影响 | 标签 |
| --- | --- | --- | --- | --- | --- | --- |
| `protocol_version` | 必要（防跨域/版本重放，域分离） | 协议规范常量 | verifier 固定常量；进入 statement | statement 域标签（约束 hash preimage 前缀） | 无（公开常量） | `CONSTRUCTED` |
| `program_id` | 需与承诺二选一或并用（见 Q1） | 由固定程序离线派生 | verifier 固定/可信分发的期望 id | 需电路把 opcode table→id 绑定，或 verifier 逐项比表后本地派生 | 公开 id 泄露"用哪个程序"（通常可接受） | `CONSTRUCTED`；当前无实体（`VERIFIED` 缺失） |
| `program_commitment` | 与 `program_id` 功能重叠（见 Q1） | prover 生成承诺 / 电路内计算 | verifier 需独立预期承诺值或受约束生成关系 | 电路内 table→commitment 绑定 + opening 约束 | 隐藏具体程序（若需）但引入 binding/hiding 信任面 | `CONSTRUCTED`；承诺层 `UNKNOWN`/`BLOCKED`（`../aba-03-d2/decision.md`） |
| `public_input_commitment` | 可选（若 public input 直接公开比对则可省） | prover / 电路 | verifier 需期望值或核对明文 | 电路内 input→commitment 绑定 | 可隐藏输入；但公开输入本已可见（n 等），压缩收益小 | `CONSTRUCTED` |
| `initial_state_commitment` | 可选但有用（绑定初始 pc/reg） | prover / 电路 | verifier 需可信初始值或承诺 | VM 电路初值约束 | 隐藏初始寄存器（多为固定零），收益小 | `CONSTRUCTED` |
| `execution_id` | 必要（防跨执行拼接，见 Q2/Q6） | **必须**由 verifier 或可信调用方生成（非 prover） | verifier 固定本次请求唯一 id | 进入所有相关 proof 的 statement / 承诺 context | 公开 id 通常可接受；若含随机需防链接 | `CONSTRUCTED`；当前无实体（`VERIFIED` 缺失） |
| `expected_step_bound` | 与 `final_step` 分工（见 Q3） | verifier / 程序规范固定上界 | verifier 固定 | 电路步数上限检查（当前 `GlobalStepsNoMoreThan` 是 host 阈值，非电路约束） | 公开上界通常可接受 | `CONSTRUCTED`；当前仅 host 阈值（`VERIFIED`） |
| `final_step` | 必要（T 的证明层表示，见 Q3/Q4） | **必须**由电路 counter 状态产生并受约束 | verifier 需可信 T 或受约束推导 | 电路内 counter 递增 + halt↔末项绑定 + 进 statement | 公开 T 泄露执行步数（程序相关，通常可接受） | `CONSTRUCTED`；当前 T 是 host 记录、不进 statement（`VERIFIED` 缺失） |
| `final_state_commitment` | 可选但有用（绑定最终 pc/reg/output） | prover / 电路 | verifier 需可信预期输出 | 电路内终态→commitment 绑定 | 可隐藏最终寄存器；public output 已部分公开 | `CONSTRUCTED` |
| `vk_id` | 必要（绑定 VK↔program/circuit，见 Phase 3） | 可信分发/注册 | verifier 固定 VK 及其 id | 不进电路；是 verify 的配置输入 | 无（公开标识） | `CONSTRUCTED`；当前现场 `test_rng()`（`VERIFIED` 缺失） |

---

## 2. 七个必答题

### Q1. `program_id` 与 `program_commitment` 是否冗余？

- **功能上重叠**：两者都旨在给"预期程序"一个稳定引用。若 `program_id` 由 verifier 从固定 opcode table 可信派生（P1-A-1 的 table 比较后本地计算 id），则 `program_commitment` 冗余；若选择用承诺隐藏程序内容或需要电路内绑定，则 `program_commitment` 提供 `program_id` 无法提供的"隐藏 + 电路内可约束"能力。
- **信任面不同**：`program_id`（verifier 固定派生）**不引入**承诺 binding/hiding 信任面；`program_commitment` **引入**（MiMC binding 无归约 / Pedersen 当前 PLONK/MPC 路径不承载，`../aba-03-d2/decision.md`）。
- **结论（`INFERRED`）**：最小集合取 `program_id`（verifier 派生）即可闭合"程序身份"；`program_commitment` 仅在"需隐藏程序"或"需电路内承诺绑定"时作为额外字段，非必需。不得同时要求两者却说不清分工。

### Q2. `execution_id` 应绑定哪些字段，才能避免跨执行拼接？

- 应绑定：`program_id`（或承诺）、`public_input_commitment`（或明文输入摘要）、`initial_state_commitment`、`expected_step_bound`/`final_step`、`vk_id`，并绑定到 proof transcript（`CONSTRUCTED`）。
- **关键约束**：`execution_id` 必须由 **verifier 或可信调用方**在本请求开始时生成并固定，写入所有相关 proof 的 statement（`verifier_independence.md` §1；`context_and_replay.md` §1 execution_id 行）。**不能**由 prover 生成——prover 生成的 id 只是又一个自我声明字段。
- 当前 `enc_key = Random()`（每执行一值）不满足：它是 prover 侧私有 witness、未被 verifier 持有、未绑定上述字段（`VERIFIED` 缺失 + `UNKNOWN`）。
- 若 `execution_id` 仅进部分 proof 而非全部，跨 proof 拼接仍有缝（见 `proof_composition_binding.md`）。

### Q3. `expected_step_bound` 与 `final_step` 是否必须同时存在？

- **功能不同**：`expected_step_bound` 是程序规范给出的**上界/预期**（如 `GlobalStepsNoMoreThan`，可公开固定），用于拒绝超长执行；`final_step` 是本次执行的**实际末步 T**，用于确定完整 step 域 `[1,T−1]`（R8）。
- 上界不能替代实际 T：`count(events)=T−1` 需要真实 T 才成立，`expected_step_bound` 只是 `T ≤ bound` 的约束，无法排除 prover 声明较小 T 的前缀截断。
- **结论（`INFERRED`）**：R8 的最小可信表示需要 `final_step` 来自受约束 counter；`expected_step_bound` 是**额外的上界防护**，二者不互相替代。是否两者都进 statement 取决于是否需要"拒绝超长"这一独立策略；本轮不强制，但明确不能用上界充当 T。

### Q4. `final_step` 如何证明来自真实 halt，而不是 prover 自报？

- **当前做不到**（`VERIFIED` 缺失）：`out_halt` 是 VM 电路 public output（`ZkVmExecutor...cs:902-906`），但 `break` 由 host C# 控制（`ZkProgramExecutor.cs` 快照 L419-421），最终 T 由 host 记录（快照 L601），T 不进 statement，且无电路内 counter 递增约束。
- **候选约束（`CONSTRUCTED`）**：① 电路内 step counter 从初值逐步递增（R5-A）；② halt 状态与事件序列末项在同一电路/同一关系内绑定，使"末个事件 step = halt 时 counter"；③ `final_step` 作为该 counter 的 public output 进 statement，由 verifier 核对或可信取得。
- **仍需**：verifier 对 `final_step` 的可信预期或受约束推导（R8-A/B）。若 verifier 只接受 prover 报的 `final_step`，问题回到原点。
- 该候选依赖 R5/R8 电路改造（当前 `BLOCKED_BY_CURRENT_INTERFACE`，`../aba-03-d3-03-01/decision.md`）。

### Q5. 是否需要绑定 initial/final state？

- **非严格必需但强烈有益（`INFERRED`）**：不绑定初态，则 prover 可从任意初始 pc/reg 开始执行（只要满足 opcode 表与 step 约束），"程序从预期入口开始"无法证明；不绑定终态，则"执行结果正确"无法证明。
- 当前初态 pc/reg 是私有输入、逐步哈希链只在执行内部自洽（`source_trace_audit.md` A1）；终态 public output 已部分公开但无 verifier 预期值。
- **结论**：最小 anchor 可先用 `program_id` + 公开输入 + `execution_id` + `final_step` + `vk_id` 闭合"是哪次执行、什么程序、跑到哪、用什么 VK"；`initial/final_state_commitment` 属于"执行结果正确性"的额外声明，视应用需求加入，加入即引入承诺信任面。

### Q6. memory trace commitment 应属于 execution anchor，还是独立 proof 输出后再绑定？

- 两种位置均可，但**信任含义不同**：
  - 放进 anchor：要求 anchor 生成时已知 trace 摘要，且该摘要受电路约束（Prove 电路的 `out_{i}_hash_mem_trace` 是 public output，行内一致但排序/值完整性在 Prove 内检查）；verifier 需预期值或受约束推导。
  - 独立 proof 输出后再绑定：MemoryTrace proof 输出摘要，Fetch/VM proof 引用它；必须说明引用是受约束公共输入/opening，而非 prover 声称相等（`proof_composition_binding.md`）。
- 当前跨电路 trace 哈希比对是 **host 多重集计数比对**（`ZkProgramExecutor.cs` 快照 L410 附近、`source_trace_audit.md` A2），不是电路内等式、不是 verifier 检查 → 无论放哪，当前都不可信（`VERIFIED`）。
- **结论（`INFERRED`）**：更自然的是让 MemoryTrace proof 输出受约束摘要，再由统一 anchor 引用；但两者当前都缺 verifier 可信来源，选择不改变"当前不可闭合"的结论。

### Q7. 哪些字段可以公开，哪些应保持隐藏承诺？

- **可公开且通常无隐私代价**：`protocol_version`、`program_id`（或 `vk_id`、`execution_id`、`expected_step_bound`、`final_step`（执行步数通常程序相关可接受）。
- **需权衡**：`public_input`（当前 n 已是 public input，`ZkProgramExecutor.cs` 快照 L265/L268/L283）；`initial/final_state`（多为固定值或 public output）。
- **应保持隐藏**：真实地址 `reg0`、dummy 的 `reg0`（冻结语义：**dummy 只承诺 `p−1`，不承诺/不公开 `reg0`**，`../aba-03-d2/context_and_replay.md` §2.2）、`enc_key`（承诺随机盐）。
- **关键边界（`INFERRED`）**：把字段做成"隐藏承诺"不自动提升可信度——承诺的 binding/hiding/opening 未闭合（`../aba-03-d2/decision.md`），隐藏承诺 vs 公开字段的取舍是**隐私 vs 信任面大小**的权衡，不是"隐藏即安全"。

---

## 3. 最小 anchor 与完整 anchor 的区分

| 集合 | 字段 | 能回答的问题 | 不能回答 |
| --- | --- | --- | --- |
| **最小可信 anchor**（`CONSTRUCTED`） | `protocol_version`, `program_id`（verifier 派生）, `execution_id`（verifier 生成）, `public_input`（明文）, `final_step`, `vk_id` | 哪个程序、哪次执行、什么公开输入、跑到哪、用什么 VK | 初/终态正确性、地址隐私下的承诺绑定、完整事件序列（B4） |
| **完整 anchor**（含承诺） | 再加 `program_commitment`, `public_input_commitment`, `initial/final_state_commitment`, `memory_trace_commitment` | 覆盖初终态与隐藏承诺 | 仍不自动闭合 B4；且引入未决承诺信任面 |

**结论（`INFERRED`）**：最小 anchor 在 verifier 侧字段全部可信的前提下可回答本轮六问中的"程序/执行/终止/VK"四问，但 (a) 这些字段当前**无一**具备 verifier 可信来源，(b) 完整 anchor 的承诺层未决。因此最小 anchor 也只是**候选设计**，不构成当前可实现接口。

---

## 4. 本阶段结论

- `ExecutionAnchor` 可写成一个字段完备的候选 statement（`CONSTRUCTED`），但**字段完备 ≠ 可信**：十个字段中，当前固定 commit 能为 verifier 提供独立可信来源的为**零**（`protocol_version` 是协议常量除外，但它本身不承载身份）。
- 三个最关键字段——`execution_id`、`final_step`、`vk_id`——的当前状态分别是：不存在（无 execution_id）、host 记录且不进 statement（final_step）、现场 `test_rng()` 生成（vk_id）（均 `VERIFIED` 缺失）。
- 因此本轮结论不是"设计一个 anchor 结构体"，而是：**要让 anchor 可信，必须新增 verifier 侧可信来源（固定 VK、verifier 生成的 execution_id、电路 counter 产生的 final_step、固定 program_id）——这些都属于改变信任模型/新增信任根，而非复用现有接口。** 详见 `verifier_vk_trust_model.md` 与 `decision.md`。
