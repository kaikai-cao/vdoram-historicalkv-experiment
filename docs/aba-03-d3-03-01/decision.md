# ABA-03-D3-03-01 / Phase 5–6：R5–R8 证明接口可实现性决策

> 实验仓起点：`9788d5c1888ac28ee936892d36086cac32423115`；固定上游 `10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读接口评估；不实现电路/接口，不跑测试，不改既有文档，不解除任何 HOLD，不改 P1-A/VK/P2。
>
> 证据来源：`interface_evidence_inventory.md`、`r5_step_provenance.md`、`r6_r7_event_trace_binding.md`、`r8_termination_anchor.md`。
>
> 阶段结论候选：`INTERFACE_FEASIBILITY_ESTABLISHED` / `INTERFACE_FEASIBILITY_PARTIAL` / `BLOCKED_BY_CURRENT_INTERFACE`。

---

## 1. 阶段结论：`BLOCKED_BY_CURRENT_INTERFACE`

**核心判断（VERIFIED + INFERRED）**：B4 的 R5–R8 四类信息——可信 step 来源、事件类型、trace 行归属、真实终止步——在当前固定实现中**全部**停留在"VM 私有 witness / host 注入值 / prover 提供的 public input"三类；没有任何一项由 verifier 固定或经可信通道取得，也没有电路约束把它们绑定到同一次完整 VM 执行。证明接口本身（`plonk.rs:293-315`）是 prover 进程内 setup→prove→verify、vk 现场 `test_rng()` 生成、public inputs 来自 prover JSON，因此当前 verifier **无法**在不依赖 prover/host 自我声明的前提下验证这些关系。

按本轮停止标准："若 R5–R8 仍只能靠 host 自己提供的数据来声明，而没有电路约束或可信 verifier 锚点，就应判为接口阻断。" —— 现状正是如此，故阶段结论为 `BLOCKED_BY_CURRENT_INTERFACE`，而不是勉强设计一个"看似可行"的接口。

**边界**：这是**当前接口**的阻断判断，不是"架构上不可能"的证明。要解除需同时改 VM 电路、Fetch/事件电路与 prover/verifier 接口，并闭合承诺层与 execution 锚点（均未决）。

---

## 2. 跨关系依赖图（Phase 5）

任务建议的依赖图基本准确，但需补充与修正两处方向/遗漏：

```
R5: trusted step provenance
        |
        +------> R4: sequence ordering      （R4 的可信 step 依赖 R5；D3-02-C1 已确认）
        |
        +------> R6: event type binding     （类型需绑定到可信 step 的执行语义）
        |
        +------> R7: trace row binding      （step↔row 依赖可信 step）
        |
        +------> R2/R3: step 域上的覆盖/注入（step 值可信才有意义）

R8: trusted termination anchor
        |
        +------> complete step domain [1, T-1]   （T 可信才确定 step 全集）
        |
        +------> R2/R3 coverage and uniqueness
        |
        +------> R4: ordering                （补充：R4 还需 R8 确定序列长度/末项）

R5 + R8 共同 ---> R4 完整成立（顺序 + 长度 + 末项都由可信 step 域决定）
```

**修正/补充说明**：
1. **方向正确**：R4 ← R5（顺序依赖可信 step）、R2/R3 ← R8（step 域依赖可信 T）与任务建议一致。
2. **遗漏 1**：R8 也应指向 R4 —— R4 不仅要"顺序单调"，还要覆盖到正确末项（D3-02-C1 的充分条件含 R8），否则 prover 可对前缀做正确排序通过 R4。
3. **遗漏 2**：R5 还应指向 R2/R3 —— 覆盖与注入是在 step 值上定义的；若 step 可伪造（R5 缺失），R2/R3 的鸽巢论证失去意义。
4. **遗漏 3（execution 同一性）**：R5–R8 要共同成立，还隐含一个公共前提——所有关系属于**同一 execution instance**。当前无 execution_id 可信锚点（P2/context 未决，`../aba-03-d2/context_and_replay.md`），这是依赖图外的前置条件，单独列为未决缺口。

---

## 3. R5–R8 关系—接口映射表（Phase 6 必答表）

| 关系 | 当前源码支持 | 候选接口 | 必要电路修改 | verifier 可检查性 | 状态 |
| --- | --- | --- | --- | --- | --- |
| **R5 step provenance** | step 是 host 循环变量 + public input（L113-116/149/287/397）；L87 依赖 MPC 诚实 | 电路内 step counter + 绑定 public statement | VM 电路新增 counter 与初值/递增约束 | 当前否（prover public input）；候选需可信来源 | `BLOCKED_BY_CURRENT_INTERFACE` |
| **R6 event type** | is_mem_op 私有派生（L972-978）；Prove 忽略（原始 L115/L165） | type 位 public 或类型承诺 opening | VM 暴露 is_mem_op/承诺 + Fetch 按类型分支 | 当前否（私有） | `BLOCKED_BY_CURRENT_INTERFACE` |
| **R7 trace row（内部一致）** | Prove 行哈希 public + 排序/值完整性（原始 L61-78/L80-158/L167-193） | 沿用 | 已有 | 行哈希 public | `VERIFIED`（第 1 层） |
| **R7 step↔row / 内容归属** | host 注入 step + append（L397-405）+ host 哈希比对（L571-587） | 电路内 row↔step 映射或受约束承诺 | 新增映射约束 + 内容绑定 | 当前否 | `UNKNOWN`/`BLOCKED` |
| **R8 termination** | halt 是 public output（L902-906），break/T 由 host（L419-421/601），T 不进 statement | verifier 固定 T / 电路 counter / halt↔末项绑定 / 执行摘要 | step counter + halt↔事件末项绑定 + T 与 execution 锚点进 statement | 当前否 | `BLOCKED_BY_CURRENT_INTERFACE` |

---

## 4. 两种整体接口方向（Phase 5，不选择胜者）

### Option A：单一联合证明关系

VM 执行与 Fetch 事件关系在同一证明关系中约束。

- **最少新增 witness/public input**（`CONSTRUCTED`）：电路内 step counter `step_i`；每步 `is_mem_op`/type（或类型承诺）；step↔row 映射；halt 与事件序列末项绑定；T 与 execution 锚点。
- **需修改的现有电路**：VM 执行电路（step counter、type 暴露、halt 绑定）；Fetch/事件电路（接收 step 与类型依赖）；Prove 电路（step↔row 纳入 statement）。
- **能否同时绑定 R4–R8**：理论上能（`INFERRED`）——同电路内 step 可信递增（R5）、顺序自然由 step 排列（R4）、类型与 trace 同源（R6/R7）、halt 与末项同电路绑定（R8）；但这是关系层推断，未实现。
- **地址隐私**：可保持（`reg0` 与 dummy lookup 保持私有，类型/承诺走隐藏路径）；但承诺层 binding/hiding 未决。
- **成本未知项**：新增门数、证明时间、proof 字节、VK 重设成本全 `UNKNOWN`。
- **硬约束**：改 VM 电路意味着改变电路结构，固定 VK 需重设（与 VK 信任模型相关，本轮不改）。

### Option B：分离证明 + 公共承诺桥接

VM 与 Fetch 分别证明，通过公共承诺或摘要连接。

- **每个子证明必须公开什么**（`CONSTRUCTED`）：VM 子证明公开每步事件承诺/摘要、可信 step（或其承诺）、T 与 halt 边界；Fetch 子证明公开逐事件承诺/摘要与引用的 step 承诺。
- **如何证明私有 step/address 与公共承诺一致**：需每个私有量对公共承诺的 opening 约束（`CONSTRUCTED`）；承诺 binding/hiding/opening 未决（`../aba-03-d2/decision.md`）。**"有相同 commitment"不等于"已绑定"**——必须说明承诺生成、隐藏、binding 与 opening 约束，否则 prover 可声称任意私有值对应同一承诺。
- **verifier 如何确认两个子证明属于同一 execution**：需 execution 级公共锚点（execution_id 承诺 + program 绑定），当前无（P2/context 未决）→ `UNKNOWN`。
- **是否引入新信任锚点**：是（承诺方案可信生成器、execution 锚点、子证明 VK 集合）→ 扩大信任边界。
- **递归硬约束**：递归验证器不能直接读子证明 private witness；所有跨证明关系必须经受约束的公共输入或承诺（沿用 D1-C1/D3-02）→ `BLOCKED`（当前无递归接口证据，`plonk.rs:293-315` 单电路）。
- **成本未知项**：递归验证开销、子证明数量、承诺生成/opening 成本全 `UNKNOWN`。

**对比小结**：Option A 关系最直接但改 VM 电路/VK 代价大；Option B 保留电路分离但引入承诺层与 execution 锚点的新信任面，且递归接口当前 `BLOCKED`。两者都**未解决**承诺层与 execution 同一性这两个前置未决，故本轮不选胜者、不建议直接进入原型。

---

## 5. UNKNOWN / BLOCKED 清单（明确）

**UNKNOWN**：
- verifier 如何可信取得预期 T 与 execution 锚点（R8-A）；
- 公开 type / step 位置的隐私可接受性；
- 承诺方案（MiMC 无 binding 归约 / Pedersen 当前 PLONK/MPC 路径不承载）与 opening 同时闭合；
- 所有候选接口的具体成本（门数、时间、字节、轮次）；
- Option B 的递归接口与当前 additive-only MPC prove 路径能否共存。

**BLOCKED（架构缺必要接口）**：
- 固定 commit 无独立 verifier、无固定 VK、public inputs 全部来自 prover JSON（`plonk.rs:293-315`）；
- 无电路内 step counter / 递增约束（R5）；
- Prove 电路不接收 is_mem_op、明确忽略类型（R6）；
- 无 step↔row 电路映射、无 in-circuit `in_mem_addr == out_trace_mem_addr` 等式（R7）；
- T 不进 proof statement、halt break 由 host 控制（R8）；
- 无递归/组合证明接口（Option B）；
- 无 execution_id / program 可信锚点（前置缺口，属 P2/context 未决）。

---

## 6. 六个必答题

1. **哪些关系可直接复用现有接口？** —— 仅 R7 的第 (1) 层：Prove 电路的行级哈希承诺、排序与值完整性检查、out_is_satisfied 公开输出（`VERIFIED`）。此外 opcode table 作 public input 的通道可复用（P1-A，但需 verifier 固定预期表，未决）。R5/R6/R8 与 R7 第 (2)(3) 层均无可直接复用的可信接口。
2. **哪些关系需要修改 VM 电路？** —— R5（新增 step counter 与递增约束）、R6（暴露 is_mem_op/类型承诺、Fetch 按类型分支）、R8（halt↔事件末项绑定、T 进 statement）；R7 内容绑定也需 VM 侧 row↔step 映射。
3. **哪些关系需要修改 Fetch 电路？** —— R6/R7：Fetch 电路当前不接收 is_mem_op/step，需新增类型分支约束 trace 地址（real=reg0、dummy=p−1）与 step↔row 引用绑定。
4. **哪些关系需要修改 proof/verifier 接口？** —— 全部：需要独立 verifier、固定/可信 VK、verifier 固定预期 T 与 execution 锚点、把 step/type/T 纳入可核对 public statement；当前 prover 自测接口无法承担 R5–R8 的检查。
5. **是否存在保留地址隐私的候选方案？** —— 存在候选表述（`CONSTRUCTED`）：step/type 用承诺或公开非地址信息、dummy 只承诺 p−1、reg0 保持私有；但承诺层 binding/hiding 与 opening 未决，隐私目标能否成立 `UNKNOWN`。
6. **是否存在不改变当前架构信任边界的方案？** —— 否（`INFERRED`）。R5–R8 全部要求把信息从"prover/host 自我声明"提升为"verifier 可检查"，必然引入新的可信来源（固定 VK、固定 T、execution 锚点、承诺生成器）或修改电路结构（固定 VK 重设）；不存在既不改信任边界又能让 verifier 摆脱自我声明的方案。

---

## 7. 下一阶段是否值得进入接口原型？

**不建议**（本轮结论）。理由：R5–R8 的接口阻断不是单一可实现性缺口，而是同时依赖三个未决前置——① 承诺层 binding/hiding/opening（`../aba-03-d2/decision.md`）；② execution/program 可信锚点（P2/context 未决）；③ 独立 verifier + 固定 VK + 可信 T 的信任模型（P1-A/VK 未决）。在这些前置闭合前做接口原型，只会把"self-declared 数据"换个封装，无法满足 B4 的 verifier 可检查目标。若后续继续，应另行授权"前置条件闭合"工作，优先顺序建议：R5 step 可信产生（R4 依赖它）→ R8 终止锚定 → R6/R7 类型与行绑定 → 承诺层与 execution 锚点定型，再谈接口规格与原型。

---

## 8. 证据纪律与停止声明

- 本轮只新增五份 `docs/aba-03-d3-03-01/` 文档，未改任何既有文档（D3-01、D3-02、D1、D2、C2、ABA-03、EXP-DORAM），未改源码、测试、配置、数据。
- 只读打开固定 commit 源码快照核实接口行号；未重抓上游、未混入其他版本源码；plonk.rs/verifier.rs 接口沿用既有冻结证据，未重抓。
- 所有候选接口标 `CONSTRUCTED`、无证据项标 `UNKNOWN`/`BLOCKED`；未把 host 检查写成电路约束或 proof soundness；未把"public input 存在"写成"verifier 已检查"；未把"相同 commitment"写成"子证明已绑定"。
- 地址隐私与 dummy 冻结语义（real: lookup=trace=reg0；dummy: lookup=reg0、trace=p−1、不约束 lookup 为 sentinel、不承诺 reg0）在所有候选中保持。
- **阶段结论 `BLOCKED_BY_CURRENT_INTERFACE`；B4 仍为 `B4_RELATION_PARTIALLY_FORMALIZED`（旧文档不改）；总决策仍 `HOLD_INSUFFICIENT_EVIDENCE`；P1-A / VK / P2 既有结论不变。**
- **完成后停止**：不启动 D3-03-02，不实现接口/电路，不扩展到 P1-A/VK/P2，不解除任何 HOLD。等待独立审查。
