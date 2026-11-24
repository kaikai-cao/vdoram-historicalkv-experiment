# ABA-04-01 — 最小原型可行性设计（仅设计，不写代码）

> 起点 commit：`13e8115c6734e3711972a156d3be8d6af3eb5978`。
> 本阶段**只设计玩具模型与负面测试**，不实现任何电路、verifier、commitment gadget、accumulator、MPC 或 ORAM。
> 证据等级：`CONSTRUCTED`（本轮设计）/ `INFERRED`（推断）/ `UNKNOWN`（未实现）/ `BLOCKED`（无明确 linking relation 时不可标可实现）。

---

## 0. 原型要区分的四个层次

原型存在的唯一目的，是把下面四个常被混为一谈的层次分开：

| 层次 | 含义 | 是否足以通过验证 |
| ---- | ---- | ---------------- |
| L1 | 两个各自有效的独立证明 | 否 |
| L2 | L1 + 两证明引用相同 `eid` | 否 |
| L3 | L2 + 两证明引用相同公开摘要 | 否 |
| L4 | L3 + 两证明通过真正的密码学 linking relation 绑定同一次执行 | 才是待验证主张 |

**验收判据**：只有当 L2/L3 的攻击样本被 verifier 拒绝、而 L4 的合法样本被接受时，原型才能支撑"跨证明同执行绑定"这一主张。若无法给出明确的 linking relation，则候选方案留在 L3，**不得标为可实现**（`BLOCKED`）。

---

## 1. 玩具模型

### 1.1 有限状态程序 `P_toy`

```
状态: pc ∈ {0,1,2,3},  reg ∈ F_q
指令集:
  pc0: NOP        → pc=1              (step 0, 不产生事件)
  pc1: LOAD addr=a → reg = M[a], pc=2 (产生事件 type=LOAD)
  pc2: NOP        → pc=3              (产生事件 type=NOP, 依策略)
  pc3: HALT                            (停机)
```

- `S_req = {1, 2}`：应用要求 step 1 与 step 2 各产生一个事件；step 0、step 3 不要求（对应冻结语义中 step 0 无事件）。
- 事件结构 `e = (step, type, addr_or_na)`。

### 1.2 确定性执行轨迹

```
step 0: pc0 NOP          → 无事件
step 1: pc1 LOAD addr=5  → e₁ = (1, LOAD, 5)
step 2: pc2 NOP          → e₂ = (2, NOP, -)
step 3: pc3 HALT         → 终止
```

- `T = 4`，`last_step_index = 3`。
- 真实事件序列 `E* = [e₁(1,LOAD,5), e₂(2,NOP,-)]`，`|E*| = 2`。

### 1.3 证明与主体

- `π_exec`：证明"存在一条从初始状态到 halt 的合法轨迹，长度 T=4，trace 承诺为 `D_exec`"。
- `π_event`：证明"提交的事件序列 `E` 满足事件关系，事件承诺为 `D_event`"。
- `Public anchor`：`eid, T, program_id, D_exec, D_event`。
- `Verifier`：独立主体，仅凭公开锚点 + 两证明 + linking proof 判定。

### 1.4 承诺/linking 需求（决定原型能否达到 L4）

```
D_exec = Com(trace; r_exec)        —— 承诺整条执行轨迹（step→opcode→addr→state）
D_event = Com(E; r_event)          —— 承诺事件序列
Linking proof L: 证明 π_event 中每个 e 的 (step, type, addr) 等于 D_exec 所承诺 trace 在对应 step 的合法派生，且两侧 T、program_id、eid 一致
```

- 承诺需 **binding**（防同摘要不同 witness）；hiding 视隐私目标可选。
- randomness `r_exec, r_event` 由证明者生成但须在 opening 时确定；verifier 不信任其来源，只依赖 binding。
- **若无法构造 L，则 `π_exec` 与 `π_event` 可各用无关 witness 却共享相同 `eid`/摘要 → 停在 L3，原型不实现 P4。**

---

## 2. 负面测试（8 项）

每项写明：攻击者改动、当前候选能否检测、所需约束、verifier 预期、失败含义。

### T1 — 省略一个应产生的事件

- **改动**：提交 `E' = [e₁]`，删除 `e₂`（step 2 的 NOP）。
- **检测**：Joint（A）由 `∀ i∈S_req ∃ e` 约束检测；Separate（B）需 linking 中覆盖 `S_req` 检测；Recursive（C）自身不检测；Accumulator（D）不检测（少写仍自洽）。
- **所需约束**：P2 覆盖性约束 `∀ i∈S_req, ∃! e with step=i`。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，说明 `S_req` 未被证明层强制，P2 不成立。

### T2 — 复制一个已有事件

- **改动**：提交 `E' = [e₁, e₁, e₂]`（重复 step 1）。
- **检测**：Joint 由"每步至多一事件 + step 唯一"检测；Separate 需 linking 中 step 注入性检测；D 不检测（重复可链上）。
- **所需约束**：R3 注入性 `step_j ≠ step_k (j≠k)` + `∀ i∈S_req ∃! e`。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，事件与步骤非一一对应，P1/P2 被破坏。

### T3 — 重排事件

- **改动**：提交 `E' = [e₂(2), e₁(1)]`（step 顺序倒置）。
- **检测**：Joint 由"事件按 step 顺序写出"检测；Separate 需 linking 中 step 单调约束检测；D 的哈希链顺序若与 step 绑定可检测，否则不能。
- **所需约束**：P3 顺序约束 `step_1 < step_2 < ...`，且顺序绑定真实执行顺序（非 prover 自报单调）。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，P3 不成立（对应 D3-02-C1 纯重排反例）。

### T4 — 修改事件类型

- **改动**：把 `e₁` 的 type 由 `LOAD` 改为 `STORE`（或把 NOP 伪造成 LOAD）。
- **检测**：Joint 由"事件 type 从 opcode 派生"检测；Separate 需 linking 中 type↔opcode 绑定检测；D 不检测（链上内容可任意）。
- **所需约束**：P1 事件 type ↔ 执行 opcode 的电路绑定。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，P1 soundness 不成立。

### T5 — 相同 `eid`，不同执行（核心 P4 测试）

- **改动**：`π_exec` 用真实轨迹（LOAD addr=5），`π_event` 用另一条轨迹的事件（如 LOAD addr=9），但两证明提交相同 `eid` 与相同 `program_id`，`D_event` 对应 addr=9 的事件序列。
- **检测**：L1/L2/L3 均**不能**检测（两证明各自有效、字段相同）；只有 L4 的 linking proof `L` 检测——因为 `D_event` 中的 addr=9 无法 opening 到 `D_exec` 承诺的 addr=5 trace。
- **所需约束**：P4 linking relation（事件字段对 `D_exec` 的 opening/lookup）。
- **预期 verifier**：在 L4 下拒绝；在 L1–L3 下接受。
- **失败含义**：若 L4 仍接受，则 linking relation 未真正绑定 witness，`eid` 相同被误当同执行——整个 P4 主张失败。

### T6 — 相同公开摘要，底层 witness 不一致

- **改动**：让 `π_exec` 与 `π_event` 都提交同一个 `D_shared`，但 `π_exec` 的 trace witness 与 `π_event` 打开出的 witness 不同（承诺非 binding，或 prover 找到碰撞）。
- **检测**：依赖承诺 binding；若 binding 成立，prover 无法为不同 witness 给出同一有效 opening，检测在 opening 验证处。
- **所需约束**：承诺 binding + linking 中 opening 一致性。
- **预期 verifier**：拒绝（假定 binding 成立）。
- **失败含义**：若接受，承诺不 binding 或 linking 缺失——P4 失败，且可能意味着底层假设被破坏。

### T7 — 修改 `total_steps`

- **改动**：把公开 `T` 由 4 改为 3（前缀截断：删去 halt，声称 `last_step_index=2`），但事件序列仍含 step 2。或把 `T` 改为 5（虚增）。
- **检测**：Joint 由 counter 终止 + halt↔末项检测（声称 T=3 时末项非 halt）；Separate 需 `D_exec` 绑定 T 且 verifier 核对；D 无可信终值时无法检测。
- **所需约束**：P5 终止绑定（counter + halt↔末项，或 verifier 固定 T）。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，说明 `T` 可 self-report，`expected_step_bound` 或 `count(E)=T-1` 被误当真实 T——P5 不成立。

### T8 — 合法旧证明 + 新 `eid` 重放

- **改动**：重用针对 `eid_old` 生成的有效 `(π_exec, π_event, D_exec, D_event)`，把公开 `eid` 改成 `eid_new` 提交。
- **检测**：若 `eid` 未进入任何证明 statement，两证明对新 `eid` 仍有效 → 无法检测；若 `eid` 被绑定进 statement（如 `D_exec = Com(trace, eid)` 且 statement 含 `eid`），则改 `eid` 破坏证明 → 检测。
- **所需约束**：`eid` 必须作为公开输入进入两证明的 statement 并被约束，而非仅作外部标签。
- **预期 verifier**：拒绝（当 `eid` 进 statement）。
- **失败含义**：若接受，说明 `eid` 只是外部标签，跨执行重放/拼接可行——P4 的执行同一性被破坏。

---

## 3. 测试矩阵小结

| 测试 | 攻击目标 | 阻止所需性质 | A Joint | B Separate+L | C Recursive | D Accumulator |
| ---- | -------- | ------------ | ------- | ------------ | ----------- | ------------- |
| T1 省略 | P2 | 覆盖性 | 需约束 | 需 linking | 不自动 | 否 |
| T2 复制 | P1/P2 | 注入性 | 需约束 | 需 linking | 不自动 | 否 |
| T3 重排 | P3 | 顺序绑定 | 需约束 | 需 linking | 不自动 | 结构部分 |
| T4 类型伪造 | P1 | type↔opcode | 需约束 | 需 linking | 不自动 | 否 |
| T5 同 eid 异执行 | P4 | linking relation | 天然阻断 | **核心依赖 L** | 不自动 | 否 |
| T6 同摘要异 witness | P4 | 承诺 binding | 天然阻断 | 依赖 binding+L | 不自动 | 否 |
| T7 改 T | P5 | 终止绑定 | 需 counter | 需可信 T | 需可信 T | 需可信终值 |
| T8 eid 重放 | P4 | eid 进 statement | 需约束 | 需约束 | 需约束 | 需约束 |

---

## 4. 可实现性判定

- **达到 L4 的最小充分条件**（`CONSTRUCTED`）：
  1. 一个 binding 承诺方案，使 `D_exec = Com(trace)` 唯一绑定 trace；
  2. 一个 linking relation，证明事件字段是 `D_exec` 所承诺 trace 的合法派生（可用 lookup/argument 或电路内 opening）；
  3. `eid, T, program_id` 作为公开输入进入两证明 statement 并被约束；
  4. `T` 由 counter+halt 或 verifier 固定来源锚定。
- 满足以上四点后，玩具原型可验证 P1–P5 的核心机制（`CONSTRUCTED`），但**原型测试通过 ≠ 密码学安全证明**（`INFERRED`）。
- 若缺第 2 条（linking relation），原型只能到 L3，P4 不可验证，该候选标 `BLOCKED`。
- 玩具模型刻意排除真实 ORAM、完整 VM、MPC 网络与大数据集；本轮不引入这些复杂度（`CONSTRUCTED`）。
