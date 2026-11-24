# ABA-03-D2 / Phase 6：C2 共享隐藏承诺最小可行性 — 决策

> 固定上游 `10c90d35…`；起点 `b8a907b8…`。只读评估，不实现、不改既有状态标签、不启动 D3。
>
> 三选一：`GO_TO_MINIMAL_PROTOTYPE` / `GO_WITH_ADDED_ASSUMPTIONS` / `HOLD_INSUFFICIENT_EVIDENCE`。

---

## 1. 决策：`HOLD_INSUFFICIENT_EVIDENCE`

**理由**：共享隐藏承诺的四个核心环节——**承诺 binding、地址 hiding、随机数可信性、上下文锚定**——没有任何一条在固定 commit 上形成完整、可验证的链。虽然 MiMC/Pedersen 的 gadget 实现都在固定 commit 内（Pedersen 甚至未被证明路径引用），但：
- binding：MiMC 无公开归约（`UNKNOWN`），Pedersen 依赖 DL + 生成器信任（`INFERRED`/`UNKNOWN`）；
- hiding：均系于随机数质量，而随机数认证在当前 additive-only 路径下 `BLOCKED`；
- context：四字段无 verifier 可信锚定完整路径；
- 双电路接口：event_type 进公开承诺、固定 vk、B4 完整性均缺失。

既不足以支撑 `GO_TO_MINIMAL_PROTOTYPE`（无可验证最小路径），也不足以支撑 `GO_WITH_ADDED_ASSUMPTIONS`（后者需明确"加哪些假设即可实现"，而当前连承诺方案与随机数机制都未选定，假设清单无法闭合）。按"关键承诺/随机性/接口问题无法判断"的定义，选 `HOLD_INSUFFICIENT_EVIDENCE`。

**既有状态标签不变**：ABA-03 `HOLD`、ABA-03-D1 `HOLD_INSUFFICIENT_EVIDENCE`、ABA-03-C2 `REQUIRES_CIRCUIT_INTERFACE_CHANGE` 均原样保留；本轮不修改这些文档。

---

## 2. 逐项回答九个决策问题

### Q1. 是否有可信的 binding 论证？

**否。** MiMC 哈希承诺：固定 commit 使用 65 轮 MiMC（`MimcEncryptGadget.cs:12-14`）链式结构，源码无安全归约，无公开可验证 binding 证明 → `UNKNOWN`。Pedersen：标准 DL binding 成立，但生成器由 `setup(rng)` 产生（`pedersen/mod.rs:50-65`），是否被 verifier 固定、是否有可验证生成过程，源码未给出 → binding 论证 `INFERRED` + 生成器信任 `UNKNOWN`。**相同承诺推出相同地址的推理对战 prover 的前提不成立。**

### Q2. 是否有适用于小地址域的 hiding 论证？

**部分（仅 Pedersen 理论上），但不可落地。** Pedersen 在均匀 `r` 下信息论 hiding，天然适合小地址域 → `INFERRED`。MiMC 的 hiding 完全系于 `r` 的高熵；小地址域下若 `r` 弱/复用，可枚举 `addr` 命中承诺 → `INFERRED`（条件性）。两者都要求 `r` 均匀不可预测，而这正是 Q3 的阻断项。因此"适用于小地址域且可实现"的 hiding 论证**不存在**。

### Q3. 随机数生命周期是否可实现？

**当前不可实现。** 随机数认证性在 CompatCircuit → PLONK 路径下 `BLOCKED`：additive-only 无 MAC、`SpdzFieldShare` 走 `mac()` cheat、`DummyFieldTripleSource` 常量三元组、无 Beaver/preprocessing（`exp-doram-06` B.1-B.3）。宿主 `enc_key = FieldFactory.Random()`（`ZkProgramExecutor.cs:61`）只覆盖"每执行一值"，不满足不可预测认证、一次性、防重放、中止重启处理（`opening_and_randomness.md` §3-4）。这是**阻止原型的第一核心未知项**。

### Q4. Context 与执行实例是否能被可信锚定？

**不能。** `program_id` 无整程序承诺（P1-A 是独立候选前置）；`execution_id` 无唯一/不可预测且 verifier 锚定的机制；`step_i` 是宿主公开注入（`ZkProgramExecutor.cs:393-395`），顺序真实性未证；`event_type_i` 若由 prover 声明可伪造（Prove 电路忽略 `is_mem_op`，原始 L164-165）。四字段均 `UNKNOWN` 或缺失（`context_and_replay.md` §1）。这是**第二核心未知项**。

### Q5. Dummy/real/step0 语义是否闭合？

**语义定义已闭合，但 verifier 在证明层面的区分未闭合。** 三语义已按冻结文档固定（真实三者相等、dummy `trace_addr=p−1` 不强加相等、step0 无 Fetch/无承诺事件）；但 verifier 要区分 real/dummy 依赖 `is_mem_op` 被绑定到公开承诺，而当前它是私有输出且 Prove 忽略 → `UNKNOWN`（`context_and_replay.md` §2）。

### Q6. 两个电路是否能分别约束自己的 opening？

**部分。** 电路内重算承诺在技术上可构造（`CONSTRUCTED`）：VM 侧已有 reg0 派生与范围骨架，Fetch 侧已有 `FieldEquals(trace_addr, in_mem_addr)`（`:52`）。但 Fetch 电路当前不接收 `is_mem_op`/opcode，要按 event_type 分支需新增输入与约束（`CONSTRUCTED`）；且 binding 缺失使"相同 com⇒相同 addr"无法成立（Q1）。因此"分别约束 opening"的实现骨架在，**安全性未闭合**。

### Q7. 固定 PLONK/MPC 接口是否支持？

**不支持完整设计。** 公开输入通道与 MiMC gadget 可复用；但承诺作为共享隐藏承诺、`event_type` 进公开承诺、verifier 固定 vk（`test_rng()` 现场生成，`plonk.rs:302-304`）、Pedersen 群 share 接入（`BLOCKED`）均缺失（`circuit_interface.md` §4）。P2 地址绑定不自动闭合 P1，C2 不闭合 B4。

### Q8. P1-A 和 B4 是否仍是独立未决问题？

**是。** P1-A（固定完整 opcode table 比较）是独立前置，可缓解 program 身份/跨程序替换，但不解决 P2 承诺 binding/hiding/随机性，也不解决 C2 承诺重放（`context_and_replay.md` §3.2）。B4（事件计数/顺序/halt 边界）在 C2 中明确不覆盖 → `BLOCKED`（`context_and_replay.md` §4）。两者都仍是独立未决。

### Q9. 哪些未知项足以阻止原型？

四个**阻断级**未知项：

1. **承诺 binding 论证**（MiMC 无归约 / Pedersen 生成器信任）——直接决定"相同承诺⇒相同地址"是否成立；
2. **随机数认证与生命周期**（当前 additive-only `BLOCKED`）——决定 hiding 与小地址域安全；
3. **context 可信锚定**（execution_id/step 顺序/event_type 来源 `UNKNOWN`）——决定防重放与 event 类型真实；
4. **event_type 进公开承诺的接口**（Prove 电路忽略 `is_mem_op`）——决定 verifier 能否区分 real/dummy。

任一项未闭合，原型都无法验证"安全语义完整"这一前提。因此不发 GO。

---

## 3. 若解除 HOLD 的最小补证任务（本轮不执行）

按阻断优先级，最小补证顺序：

1. **承诺方案定型 + binding 论证**：选定 MiMC 或 Pedersen；若为 MiMC，给出可引用的碰撞/绑定安全分析或改用有标准的哈希承诺；若为 Pedersen，给出生成器的可验证固定方案（防 toxic waste）与域适配方案。
2. **随机数机制**：明确 verifier 固定或 MPC 联合生成的 `r`，给出认证/一次性/防重放/中止重启协议；若继续 additive-only，论证 prover 不可重采样的替代机制（否则 `BLOCKED` 不解除）。
3. **context 锚定**：定义 verifier 固定的 program_id（P1-A）、execution_id 唯一性来源、step 顺序的电路约束、event_type 由 opcode 派生进公开承诺。
4. **接口验证**：在上述闭合后，再评估最小电路原型（双电路各自开承诺 + verifier 比较 com），并单独处理 B4。

以上仅为补证清单，本轮不启动。

---

## 4. 本轮结论与停止声明

- 决策：`HOLD_INSUFFICIENT_EVIDENCE`。
- **本轮最重要的结论**：承诺 binding、地址 hiding、随机数可信性、上下文锚定四件事必须拆开证明；当前没有一项形成完整可验证链。即使 Pedersen 理论性质最优、MiMC 域内最易实现，也不能据此提前宣布可行性或创新性。
- 未实现任何承诺 gadget、未改源码、未跑 benchmark、未扩展到 C3 递归、未解除任何 HOLD。
- 本轮完成后等待独立审查，不自动启动 ABA-03-D3。
