# ABA-04-01 — 候选密码学构造比较

> 起点 commit：`13e8115c6734e3711972a156d3be8d6af3eb5978`。
> 比较对象严格限定四类：Joint proof / Separate proofs + commitment bridge / Recursive composition / Authenticated accumulator。
> 证据等级：`CONSTRUCTED`（本轮比较框架）/ `INFERRED`（由证明语义与已核实文献推断）/ `UNKNOWN`（尚无成本或实现证据）/ `BLOCKED`（明确前置缺失）。
> **不宣布任何方案最优。** "满足 P1–P5" 一律指"在列出的约束与假设成立时理论上可覆盖"，从不表示已实现或已证明安全。

---

## 0. 比较标准

沿用 `problem_definition.md` 的 P1–P5 与三类边界（密码学性质 / 部署假设 / 应用策略）。八个统一指标：

| 指标 | 本文回答口径 |
| ---- | ------------ |
| P1–P5 | 是否满足，依赖哪些**证明层约束**；不把部署信任当满足 |
| Trust assumptions | 额外引入哪些 verifier 侧/外部信任根 |
| Proof soundness | 关键安全性质最终依赖什么（soundness / binding / 可信锚点） |
| Witness binding | 是否真正建立"同执行"绑定，还是只对齐公开字段 |
| Privacy | 是否暴露 trace、事件内容、执行长度等额外信息 |
| Complexity | 证明/验证/通信成本的量级与已知度 |
| Implementation | 在有资源时的最小可实现路径 |
| Novelty | 相对已核实相关工作（`related_work.md`）的实际差异 |

---

## 1. 方案 A — Joint proof（执行与事件同一证明关系）

**结构**：执行 trace、事件生成、执行锚点全部写进**一个**证明关系 `R_joint`。step counter 在电路内从 0 递增到 `T-1`；每条 trace row 依 opcode 决定是否产生事件；事件序列按 step 顺序在电路内写出；halt 与末项绑定；`T`、`program_id`、`eid` 作为公开 statement。

| 指标 | 回答 |
| ---- | ---- |
| P1–P5 | P1：事件由 trace row 在电路内派生 → 可覆盖（`CONSTRUCTED`）。P2：`∀ i∈S_req` 事件存在性由电路约束 → 可覆盖。P3：事件按 step 顺序写出 → 可覆盖。P4：**结构上消除**——只有一组 witness，不存在两证明 witness 不一致（`INFERRED`）。P5：`T` 由 counter 终止 + halt 绑定 → 可覆盖，前提是 `T` 进 statement 且 verifier 固定/核对。 |
| Trust assumptions | verifier 固定 `program_id`、`T`（或核对 counter 输出）、VK；`S_req` 为应用可信输入。不新增 commitment 信任根。 |
| Proof soundness | 依赖单一关系的 soundness + counter/事件生成约束的正确性。 |
| Witness binding | 天然满足同执行绑定（同一 witness），这是本方案相对分离方案的结构性优势（`INFERRED`）。 |
| Privacy | 事件序列若明文进 statement 会泄露事件内容/长度；可通过事件序列承诺 + 选择性公开缓解，但引入承诺层。 |
| Complexity | 电路规模随真实执行步数与事件数增长；VK 随程序固定。具体门数/证明时间 `UNKNOWN`（本轮不实测）。 |
| Implementation | 需改执行电路：加 counter、事件派生列、halt↔末项、事件序列输出；重做 setup/VK。 |
| Novelty | **低**：zkVM 的统一 trace 关系通常已在同一关系内做 step/counter/边界约束；把事件作为 trace 的一列并非新原语（`INFERRED`，见 `related_work.md` STARK/zkVM 方向）。 |

---

## 2. 方案 B — Separate proofs + commitment bridge（分离证明 + 公共承诺桥）

**结构**：`π_exec` 证明执行关系并对 `(trace_root, T, program_id)` 出承诺 `D_exec`；`π_event` 证明事件序列关系并对事件序列出承诺 `D_event`。两证明把 `D_exec`、`D_event`、`eid` 作为公共 statement；额外 opening/linking proof 证明事件证明中使用的 step/type 来自 `D_exec` 所承诺的 trace。

| 指标 | 回答 |
| ---- | ---- |
| P1–P5 | P1：需事件内容对 trace 的 opening/lookup 约束，不能只靠 `D_event` 自洽（`CONSTRUCTED`）。P2/P3：需在 linking 约束中覆盖域与顺序。P4：**关键难点**——仅在两证明里放相同 `D_exec/D_event` 不够，必须证明两证明"打开的是同一个承诺且 witness 一致"（`INFERRED`）。P5：`T` 须由 `D_exec` 绑定且 verifier 可信核对。 |
| Trust assumptions | 承诺方案 binding（必须）、hiding（视隐私）；randomness 生成与认证方式；若用电路内可验证哈希承诺（如 Poseidon），其 collision resistance 假设。verifier 固定 `program_id`/`T`。 |
| Proof soundness | 依赖两侧 soundness + 承诺 binding + **linking proof** 的 soundness。缺 linking 则 P4 不成立。 |
| Witness binding | 只有引入真正的 opening/linking relation 才建立；相同摘要字段本身**不构成**绑定（`CONSTRUCTED`，核心结论）。 |
| Privacy | 承诺天然隐藏 trace/事件内容，隐私较好；但 `T`、`program_id` 公开仍泄露执行规模/身份。 |
| Complexity | 两侧证明 + linking proof；承诺与 opening 在电路内的开销。具体成本 `UNKNOWN`。 |
| Implementation | 最小路径：选定电路内可验证承诺；执行侧输出 `D_exec`；事件侧约束对 `D_exec` 的 opening；写 linking relation。**若无法给出明确 linking relation，本方案不可标为实现可行**（`BLOCKED`）。 |
| Novelty | 若 linking relation 是新的"跨证明同 witness"证明技术，可能有差异（`UNKNOWN`）；若只是标准承诺 opening，则属工程拼接（`INFERRED`）。 |

**防"两组 witness 不一致"的必要条件**（`CONSTRUCTED`）：`π_event` 必须证明其事件所引用的 `(step, type, state)` 是 `D_exec` 承诺 trace 的一次合法 opening，且该 opening 与 `π_exec` 中使用的 trace 位置一致。仅当 verifier 能验证这一 linking proof，P4 才可能成立。

---

## 3. 方案 C — Recursive proof composition（递归证明组合）

**结构**：用递归验证把执行子证明与事件子证明聚合为一个顶层证明，顶层 statement 包含两子证明的公开 statement 与锚点。

| 指标 | 回答 |
| ---- | ---- |
| P1–P5 | 递归保证的是"子证明对其**公开 statement** 有效"，即压缩验证（`INFERRED`，依据 Nova/BCTV/Halo 的公开语义）。P1–P3：不自动成立，取决于子证明关系是否约束事件语义。P4：**递归不自动证明两子证明私有 witness 相同**——除非先把要比较的量公开承诺，并在递归电路里约束这些承诺相等且可 opening（`CONSTRUCTED`）。P5：顶层 statement 的 `T` 仍需可信来源。 |
| Trust assumptions | 递归电路正确性、循环曲线/DLOG 假设或 folding setup（依实例化而定）；verifier 固定顶层 statement。 |
| Proof soundness | 依赖递归 step 的 soundness + 子证明 soundness + 公开 statement 绑定。 |
| Witness binding | 默认不满足 P4；只有把跨证明一致性写进顶层公开 statement（承诺相等 + linking）才可能满足（`INFERRED`）。 |
| Privacy | 公开 statement 若含事件/`T` 则泄露；可用承诺压缩公开量。 |
| Complexity | 递归开销（Nova 为常数级 recursion overhead，`PAPER_CLAIM`）；但聚合不改变子证明关系本身的语义覆盖。 |
| Implementation | 最小路径：先有 B 的承诺/linking，再用递归压缩验证。**递归不能替代 B 的 linking relation**——它是压缩器不是语义证明（`CONSTRUCTED`）。 |
| Novelty | **低**：递归证明公开 statement 绑定是成熟方向（BCTV/Halo/Nova）；把两个已有证明聚合不构成新密码学问题（`INFERRED`）。 |

**关键边界**（`INFERRED`）：递归/folding 把"检查两个 instance"归约到"检查一个"（Nova `PAPER_CLAIM`），前提是它们在**同一关系**且 instance 被正确公开。若执行关系与事件关系是不同关系，或 witness 相同性未被公开承诺捕获，递归无从比较私有 witness。

---

## 4. 方案 D — Authenticated execution/event accumulator（认证累加器 / 哈希链）

**结构**：执行每步把事件写入一个累加器（哈希链或 Merkle 树），累加器根作为执行公开输出；验证者用包含证明/一致性证明检查事件在累加器中的位置与顺序。

| 指标 | 回答 |
| ---- | ---- |
| P1–P5 | P1：累加器只保证"某事件在链上"，不保证该事件内容与真实执行一致——**来源绑定仍需执行关系约束**（`INFERRED`，RFC 6962 明确 consistency proof 不保证被追加数据的语义/来源，`VERIFIED` 规范声明）。P2/P3：哈希链/Merkle consistency 保证 append-only 与顺序结构，但**不保证无遗漏**——少写几条事件后链依然自洽（`CONSTRUCTED`）。P5：终点累加器值须 verifier 可信固定，否则前缀截断无法发现（`INFERRED`）。 |
| Trust assumptions | 累加器抗碰撞/抗第二原像；起点（genesis）与终点根由 verifier 固定或可信锚定；写链逻辑正确。 |
| Proof soundness | 依赖哈希函数性质 + 执行关系对"每步写链"的约束 + 可信终值。 |
| Witness binding | 单独累加器**不建立跨证明同执行绑定**；它只是可公开引用的摘要（`CONSTRUCTED`）。 |
| Privacy | 哈希链隐藏事件细节（若事件不公开），但链长度/位置信息泄露执行规模。 |
| Complexity | 累加器更新与包含证明开销相对温和；但完整 P1–P5 仍需叠加执行证明，总成本不低（`UNKNOWN` 具体值）。 |
| Implementation | 最小路径：执行电路每步更新累加器根并公开；用包含/一致性证明查事件。**必须配合 A 或 B 才能闭合 P1/P5**；单独 D 不可标为可实现（`BLOCKED`）。 |
| Novelty | **低**：Merkle consistency/append-only log 是成熟原语（RFC 6962 `VERIFIED`）；把它用于事件序列是应用而非新原语（`INFERRED`）。 |

**为什么单纯 hash chain 不足**（`CONSTRUCTED` + `VERIFIED` 规范边界）：
1. 无来源绑定：链上事件是谁、由哪一步产生，链本身不回答。
2. 无终止可信：无 verifier 固定终值时，前缀截断产生一条"合法但短"的链。
3. 无内容语义：consistency proof 只证明"新树是旧树的超集/前 m 项相同"（RFC 6962 §2.1.2），不证明这些项语义正确或来自真实执行。

---

## 5. 横向对照

| 方案 | P1 | P2 | P3 | P4 | P5 | 主要信任根 | 同执行绑定 | 隐私 | 结构性 novelty |
| ---- | ---- | ---- | ---- | ---- | ---- | ---------- | ---------- | ---- | -------------- |
| A Joint | 可覆盖* | 可覆盖* | 可覆盖* | 天然满足 | 可覆盖* | VK、可信 T、program_id | 是（单 witness） | 事件公开时较差 | 低 |
| B Separate+bridge | 需 linking | 需 linking | 需 linking | 需真 linking relation | 需可信 T | binding/hiding 承诺、可信 T | 仅当 linking 成立 | 较好 | 取决于 linking 是否新 |
| C Recursive | 不自动 | 不自动 | 不自动 | 不自动（除非 B 的承诺进 statement） | 需可信 T | 递归电路、子证明 statement | 默认否 | 取决于 statement | 低 |
| D Accumulator | 否（需执行绑定） | 否（漏写自洽） | 结构有保证 | 否 | 需可信终值 | 哈希性质、可信起终点 | 否 | 较好 | 低 |

\* 指"在 counter/事件生成/halt 约束正确且 `T` 可信时"，非已实现。

---

## 6. 本轮比较结论（仅分类，不宣布最优）

- **P4（跨证明同执行绑定）只在 A 中被结构消除；在 B/C/D 中必须显式构造 linking relation，否则不成立**（`INFERRED`）。这是四类方案最本质的差异。
- **P5（终止绑定）在所有方案中都不是免费的**：A/C 需要 counter+halt，B/D 需要 verifier 固定 `T`/终值（`CONSTRUCTED`）。
- **C 是压缩器而非语义证明，D 是摘要而非完整性证明**——二者都不能单独闭合 P1–P5（`CONSTRUCTED` + `INFERRED`）。
- 唯一可能产生独立密码学新意的是 B 中的"跨证明同 witness linking relation"；其是否真正新颖，取决于相关工作排查（`related_work.md`）与能否给出可证明定理（Phase 5），当前 `UNKNOWN`。
