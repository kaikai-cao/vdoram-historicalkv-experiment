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
- **`eid` 绑定精度**：`eid` 进入公开 statement 只是让它成为 verifier 检查的相对值，**不等于**已绑定到某次执行。必须把 `eid` 纳入受约束关系（例如使其进入 `D_exec` 所承诺的 trace 派生、并让 `π_event` 经 `L` 绑定同一 `D_exec`/`eid`）。共同 `eid` 或共同摘要字符串本身不构成 linking（见 T8a）。
- **原样重放不在 P4 范围**：同一有效证明组原封不动再次提交（T8b）不违反任何证明层 linking，需部署层 nonce/已消费标识/可信日志处理，不得计入 P4。
- **若无法构造 L，则 `π_exec` 与 `π_event` 可各用无关 witness 却共享相同 `eid`/摘要 → 停在 L3，原型不实现 P4。**

---

## 2. 负面测试（9 项；T8 分 T8a/T8b 两种重放情形）

每项写明：攻击者改动、当前候选能否检测、所需约束、verifier 预期、失败含义。

### T1 — 省略一个应产生的事件

- **改动**：提交 `E' = [e₁]`，删除 `e₂`（step 2 的 NOP）。
- **检测**：Joint（A）由 `∀ i∈S_req ∃ e` 约束检测；Separate（B）需 linking 中覆盖 `S_req` 检测；Recursive（C）自身不检测；Accumulator（D）不检测（少写仍自洽）。
- **所需约束**：P2 覆盖性约束 `∀ i∈S_req, ∃! e with step=i`。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，说明 `S_req` 未被证明层强制，P2 不成立。

### T2 — 复制一个已有事件

- **改动**：提交 `E' = [e₁, e₁, e₂]`（重复 step 1）。按 `problem_definition.md` §1.2/§4，复制后 `⟦E'⟧` 中 step 1 事件重数为 2，超过 `⟦E*⟧` 中的 1；唯一映射 `f` 的"每个 `i∈S_req` 恰好一个事件"随之失效。
- **检测**：Joint 由"每步至多一事件 + step 注入"检测；Separate 需 linking 中"事件重数 ≤ trace 派生重数 + step 注入"检测；D 不检测（重复项仍可原子链上）。
- **所需约束**：P1 多重集包含 `⟦E⟧ ⊆ ⟦E*⟧`（重数比较）+ P2 唯一映射 `f` 的单射性（`∀ i∈S_req ∃! e`）。仅检查集合 `{step(e)} ⊇ S_req` 无法检测本测试。
- **预期 verifier**：拒绝。
- **失败含义**：若接受，事件与步骤非一一对应，P1（重数）与 P2（唯一映射）均被破坏。

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

### T8 — `eid` 重放（须严格区分两种情形）

**先纠正一处表述**：`eid` 作为公开输入出现在 statement 里，**本身不足以**证明它绑定到某次执行——公开输入只是 verifier 会检查证明相对该值自洽，不说明该值来自可信生成或与执行 witness 有密码学联系。要绑定，必须有受约束关系把 `eid` 与执行承诺/transcript 关联（如 §1.4 的 `D_exec = Com(trace; r_exec)` 且 `eid` 进入被承诺的 trace 派生关系），并且 `π_event` 也通过 linking relation 绑定到**同一执行锚点**（同一 `D_exec`/`eid`），而非仅在外层共享字段。本测试分两种：

- **T8a — 换新 `eid` 重新包装旧证明**
  - **改动**：重用针对 `eid_old` 生成的有效 `(π_exec, π_event, D_exec, D_event)`，把外层公开 `eid` 改成 `eid_new` 提交，其余不变。
  - **检测**：若 `eid` 只是外层公开输入、未进入任何受约束关系，两证明对 `eid_new` 仍有效 → 无法检测；若 `eid` 受约束绑定到 `D_exec` 所承诺的 trace，且 `π_event` 绑定同一锚点，则改 `eid` 破坏证明 → 检测。
  - **所需约束**：`eid` 进入两证明 statement **且**与执行承诺/事件承诺在同一 linking relation 下绑定；不是"作为外部公开标签出现"。
  - **预期 verifier**：拒绝（当 `eid` 受约束绑定时）。
  - **失败含义**：若接受，说明 `eid` 只是外部标签，跨执行重新包装可行——P4 的执行同一性被破坏。

- **T8b — 相同 `eid` 的原样重放（SNARK 绑定不足）**
  - **改动**：把针对 `eid_old` 的完整有效证明组 `(π_exec, π_event, D_exec, D_event, eid_old)` 原封不动再次提交。此时所有字段一致、所有 linking relation 都成立。
  - **检测**：**任何纯 SNARK/承诺/linking 绑定都无法检测此情形**——因为被提交的就是同一执行的有效证明，密码学上无从区分"首次提交"与"再次提交"。
  - **所需约束**：需 SNARK 之外的机制——verifier 侧 nonce（挑战值进入 statement）、已消费 `eid` 集合/一次性状态、或可信时间戳/日志。这些属于**系统部署信任假设**，不是 P4 的密码学 linking 能提供的。
  - **预期 verifier**：在无任何外部状态时**接受**（这是 T8b 要如实暴露的边界，不是缺陷修复）；有 nonce/已消费标识时拒绝。
  - **失败含义**：若有人声称"仅靠 SNARK + `eid` 绑定即可阻止一切重放"，T8b 即为反例——必须把抗重放归到部署层，不得并入 P4 的证明层结论。

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
| T8a 换 eid 重包装 | P4 | eid 受约束绑定到执行/事件锚点 | 需约束 | 需 linking | 需约束 | 需约束 |
| T8b 同 eid 原样重放 | 部署层抗重放 | nonce / 已消费标识 / verifier 状态 | 不阻断 | 不阻断 | 不阻断 | 不阻断 |

> T8 注记：T8a 属证明层 P4，需 `eid` 受约束绑定（进 statement 且与执行/事件承诺在同一 linking relation 下），不是"作为外部公开输入出现"即可；T8b 属部署层抗重放，纯 SNARK 绑定一律不阻断，需 verifier 侧 nonce/已消费标识/可信日志。二者不得混为一谈，也不得把 T8b 的解决算作 P4 的密码学结论。

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
