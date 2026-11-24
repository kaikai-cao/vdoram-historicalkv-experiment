# ABA-03-D2 / Phase 6：C2 共享隐藏承诺最小可行性 — 决策

> 固定上游 `10c90d35…`；起点 `b8a907b8…`。只读评估，不实现、不改既有状态标签、不启动 D3。
>
> 三选一：`GO_TO_MINIMAL_PROTOTYPE` / `GO_WITH_ADDED_ASSUMPTIONS` / `HOLD_INSUFFICIENT_EVIDENCE`。

---

## 1. 决策：`HOLD_INSUFFICIENT_EVIDENCE`

**理由**：共享隐藏承诺的四个核心环节——**承诺 binding、地址 hiding、随机数可信性、上下文锚定**——没有任何一条在固定 commit 上形成完整、可验证的链。虽然 MiMC/Pedersen 的 gadget 实现都在固定 commit 内（Pedersen 甚至未被证明路径引用），但：
- binding：MiMC 无公开归约（`UNKNOWN`），Pedersen 依赖 DL + 生成器信任（`INFERRED`/`UNKNOWN`）；
- hiding：两侧 hiding 均系于 `r` 的分布/保密条件（Pedersen 理论 perfect hiding 不等于接口已落地）；当前 additive-only 路径阻断的是主动安全 MPC 随机数认证，二者是不同的未决问题；
- context：四字段无 verifier 可信锚定完整路径；
- 双电路接口：event_type 进公开承诺、B4 完整性均缺失；VK 锚定在外部部署中为 `UNKNOWN`（当前仅见本地现场 setup/prove/verify），不能据此断言外部固定 VK 能力。

既不足以支撑 `GO_TO_MINIMAL_PROTOTYPE`（无可验证最小路径），也不足以支撑 `GO_WITH_ADDED_ASSUMPTIONS`（后者需明确"加哪些假设即可实现"，而当前连承诺方案与随机数机制都未选定，假设清单无法闭合）。按"关键承诺/随机性/接口问题无法判断"的定义，选 `HOLD_INSUFFICIENT_EVIDENCE`。

**既有状态标签不变**：ABA-03 `HOLD`、ABA-03-D1 `HOLD_INSUFFICIENT_EVIDENCE`、ABA-03-C2 `REQUIRES_CIRCUIT_INTERFACE_CHANGE` 均原样保留；本轮不修改这些文档。

---

## 2. 逐项回答九个决策问题

### Q1. 是否有可信的 binding 论证？

**否，尚无可直接落地的 binding 论证。** MiMC 哈希承诺：固定 commit 使用 65 轮 MiMC（`MimcEncryptGadget.cs:12-14`）链式结构，源码无安全归约，无公开可验证 binding 证明 → `UNKNOWN`。Pedersen：在 DL 困难且生成元关系未知时有**计算 binding**（不是 perfect binding；若 `mG + rH = m'G + r'H` 且 `m != m'`，两份 opening 即导出 `G/H` 的 DL 关系）；同一 Pedersen 承诺下若 `m_vm = m_fetch = m` 且 `C_vm = C_fetch`，则 `(r_vm − r_fetch)H = 0`，素数阶群且 `H` 非单位元 ⇒ `r_vm = r_fetch mod q`，这是代数结果而非额外假设，不能推荐两侧使用独立随机数指向同一承诺；但生成器由 `setup(rng)` 产生（`pedersen/mod.rs:50-65`），是否被 verifier 固定、是否有可验证生成过程，源码未给出 → binding 论证 `INFERRED` + 生成器信任 `UNKNOWN`。**“相同承诺 ⇒ 相同地址”不是无条件数学等式：需两电路各自正确约束 opening、使用同一承诺、且 binding 成立；这些前提当前未闭合。**

### Q2. 是否有适用于小地址域的 hiding 论证？

**部分（仅 Pedersen 理论上），但不可落地。** Pedersen 在 `r` 均匀且保密（观察者不可获得）时是 **perfect hiding**，天然适合小地址域 → `INFERRED`；这是理论性质，不等于已接入当前 PLONK/MPC 路径。MiMC 的 hiding 完全系于 `r` 的高熵；小地址域下若 `r` 弱/复用，可枚举 `addr` 命中承诺 → `INFERRED`（条件性）。Pedersen 要求 `r` 均匀且保密，MiMC 还要求不可预测性，而这些条件没有被当前路径证明（见 Q3）。因此"适用于小地址域且可实现"的 hiding 论证**不存在**。

### Q3. 随机数生命周期是否可实现？

**当前不可实现完整生命周期。** 当前 MPC 路径中的主动安全随机数认证 `BLOCKED`：additive-only 无 MAC、`SpdzFieldShare` 走 `mac()` cheat、`DummyFieldTripleSource` 常量三元组、无 Beaver/preprocessing（`exp-doram-06` B.1-B.3）；这阻断的是“现有 MPC 路径中参与方不能篡改 share/r”，**不等于**所有 prover 本地随机数生成都不安全。prover/宿主本地生成 `r` 是承诺者的正常做法，不自动破坏 hiding，但需满足方案要求的分布且观察者不可获得 `r`；宿主 `enc_key = FieldFactory.Random()`（`ZkProgramExecutor.cs:61`）只覆盖“每执行一值”，其作为 opening `r` 的分布/保密性、一次性与中止重启处理都未闭合（`opening_and_randomness.md` §2/§4）。防重放另需可信 `execution_id`、`step`、program/context 绑定与 verifier 检查，不能靠随机数随机性解决。这是**阻止原型的第一核心未知项**。

### Q4. Context 与执行实例是否能被可信锚定？

**不能。** `program_id` 无整程序承诺（P1-A 是独立候选前置）；`execution_id` 无唯一/不可预测且 verifier 锚定的机制；`step_i` 是宿主公开注入（`ZkProgramExecutor.cs:393-395`），顺序真实性未证；`event_type_i` 若由 prover 声明可伪造（Prove 电路忽略 `is_mem_op`，原始 L164-165）。四字段均 `UNKNOWN` 或缺失（`context_and_replay.md` §1）。这是**第二核心未知项**。

### Q5. Dummy/real/step0 语义是否闭合？

**语义定义已闭合，但 verifier 在证明层面的区分未闭合。** 三语义已按冻结文档固定：真实 Load/Store 的 `fetch_lookup_addr = reg0 = trace_addr`；dummy Fetch 的 `fetch_lookup_addr = reg0`（lookup key）而 `trace_addr = p−1`（trace 哨兵），不强加二者相等、不把 lookup address 强设为 `p−1`，`reg0` 不进公开输入；step0 无 Fetch/无承诺事件（不得虚构 Fetch proof）。但 verifier 要区分 real/dummy 依赖电路内 opcode 派生的 `is_mem_op` 被绑定到对应公开 statement，而当前它是私有输出且 Prove 忽略 → `UNKNOWN`（`context_and_replay.md` §2、`../aba-03-d1/p2_binding_semantics.md` §0）。

### Q6. 两个电路是否能分别约束自己的 opening？

**部分。** 电路内重算承诺在技术上可构造（`CONSTRUCTED`）：VM 侧已有 reg0 派生与范围骨架，Fetch 侧已有 `FieldEquals(trace_addr, in_mem_addr)`（`:52`），但该相等只能用于真实步；dummy 步必须显式分支（lookup key 仍为 `reg0`，trace 哨兵 `p−1`，不强加相等；实际 trace row 还需 `FieldEquals(trace_row.mem_addr, p−1)` 绑定，需新增约束 → `CONSTRUCTED`）。标准 Pedersen 下两侧各自持有 opening witness，但同一 `C` + 同一消息代数要求 `r_vm = r_fetch mod q`，不能把独立 `r` 当作推荐设计。Fetch 电路当前不接收 `is_mem_op`/opcode，要按 event_type 分支需新增输入与约束（`CONSTRUCTED`）；且 binding 未闭合，使“相同 `com` ⇒ 相同地址”只能作为条件性推论而非无条件结论（Q1）。因此“分别约束 opening”的实现骨架在，**安全性未闭合**。

### Q7. 固定 PLONK/MPC 接口是否支持？

**不支持完整设计。** 公开输入通道与 MiMC gadget 可复用；但承诺作为共享隐藏承诺、`event_type` 进公开承诺、Pedersen 群 share 接入（`BLOCKED`）均缺失（`circuit_interface.md` §4）。VK 项严格按 D1-C1 证据等级：当前 compat 路径本地 `test_rng()` 现场 setup、setup/prove/verify 同函数为 `VERIFIED`；外部 verifier 是否持有固定 VK / 是否接受 prover 提供 VK 为 `UNKNOWN`；仅在“接受 prover 自提 VK 且无可信锚定”前提下才可能重选 setup，为 `CONDITIONAL INFERENCE`。因此不能写成“固定上游不支持固定 VK”或“现场 setup 已证明外部 verifier 不可信”。P2 地址绑定不自动闭合 P1（P1-A 仍是独立前置），C2 不闭合 B4。

### Q8. P1-A 和 B4 是否仍是独立未决问题？

**是。** P1-A（固定完整 opcode table 比较）是独立前置，可缓解 program 身份/跨程序替换，但不解决 P2 承诺 binding/hiding/随机性，也不解决 C2 承诺重放（`context_and_replay.md` §3.2）。B4（事件计数/顺序/halt 边界）在 C2 中明确不覆盖 → `BLOCKED`（`context_and_replay.md` §4）。两者都仍是独立未决。

### Q9. 哪些未知项足以阻止原型？

四个**阻断级**未知项：

1. **承诺 binding 论证**（MiMC 无归约 / Pedersen 生成器信任与 DL 假设；Pedersen 仅计算 binding、不是 perfect binding）——直接决定"相同承诺 + 两侧正确约束 opening ⇒ 相同地址"的条件性推论是否成立；
2. **随机数认证与生命周期**（当前 additive-only 路径下主动安全 MPC 认证 `BLOCKED`；本地生成的分布/保密性与一次性未证）——决定 hiding 与小地址域安全；
3. **context 可信锚定**（execution_id/step 顺序/event_type 来源 `UNKNOWN`；防重放不能只靠随机性）——决定防重放与 event 类型真实；
4. **event_type 进公开承诺的接口**（Prove 电路忽略 `is_mem_op`）——决定 verifier 能否区分 real/dummy。

任一项未闭合，原型都无法验证"安全语义完整"这一前提。因此不发 GO。

---

## 3. 若解除 HOLD 的最小补证任务（本轮不执行）

按阻断优先级，最小补证顺序：

1. **承诺方案定型 + binding 论证**：选定 MiMC 或 Pedersen；若为 MiMC，给出可引用的碰撞/绑定安全分析或改用有标准的哈希承诺；若为 Pedersen，明确 binding 是 DL 假设下的计算性质（两份不同消息 opening 会泄露生成元 DL 关系），给出生成器的可验证固定方案（防 toxic waste）与域适配方案。
2. **随机数机制**：明确 `r` 的产生者、分布与保密条件，给出认证/一次性/防重放/中止重启协议；若继续 additive-only，须论证在缺少主动安全 MPC 认证时如何满足这些条件（否则当前路径的 `BLOCKED` 不解除）。prover 本地生成本身正常，不等于该阻断已解除。
3. **context 锚定**：定义 verifier 固定的 program_id（P1-A）、execution_id 唯一性来源、step 顺序的电路约束、event_type 由 opcode 派生进公开承诺。
4. **接口验证**：在上述闭合后，再评估最小电路原型（双电路各自开承诺 + verifier 比较 com），并单独处理 B4。

以上仅为补证清单，本轮不启动。

---

## 4. 本轮结论与停止声明

- 决策：`HOLD_INSUFFICIENT_EVIDENCE`。
- **本轮最重要的结论**：承诺 binding、地址 hiding、随机数可信性、上下文锚定四件事必须拆开证明；当前没有一项形成完整可验证链。即使 Pedersen 理论性质最优（perfect hiding + DL 假设下的计算 binding）、MiMC 域内最易实现，也不能据此提前宣布可行性或创新性。**Pedersen 的理论安全性质正确，不等于它已能接入当前 PLONK/MPC 路径；prover 自己生成随机数正常，也不等于当前 MPC 随机数认证问题已经解决。**
- 本轮仅为文档勘误，不构成构造可行性证明：dummy trace row 绑定需新增电路约束（`CONSTRUCTED`），独立 `r` 的关联证明属 `FUTURE CANDIDATE` / `UNKNOWN`，均未实现或验证。
- 未实现任何承诺 gadget、未改源码、未跑 benchmark、未扩展到 C3 递归、未解除任何 HOLD。
- 本轮完成后等待独立审查，不自动启动 ABA-03-D3。
