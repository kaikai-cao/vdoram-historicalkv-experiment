# ABA-03-D3-03-01 / Phase 3：R6 / R7 — Event Type 与 Trace Binding 可实现性

> 实验仓起点：`9788d5c1888ac28ee936892d36086cac32423115`；固定上游 `10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 目标：评估事件类型（real/dummy）与 trace row 能否由 verifier 检查地绑定到可信 VM 执行，而非 prover 自报。
>
> 证据来源：`interface_evidence_inventory.md` §1 组件 2/3/4；`../aba-03/source_trace_audit.md` A1/A2；`../aba-03-d1/p2_binding_semantics.md` §0；`../aba-03-d3-02/event_sequence_relation.md` R6/R7。
>
> 冻结语义（本轮严格保持，不得改变）：
> ```
> Real  : fetch_lookup_addr = reg0 ; trace_addr = reg0
> Dummy : fetch_lookup_addr = reg0 ; trace_addr = p−1
> ```
> dummy lookup address 不得被约束为 `p−1`，不得因此公开或承诺 dummy 的 `reg0`。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。

---

## 1. R6 — Event Type Binding

### 1.1 现有接口证据（VERIFIED）

| 事实 | 源码证据 | 标签 |
| --- | --- | --- |
| `out_trace_is_mem_op = BoolOr(op==Load, op==Store)`，私有 output | `ZkVmExecutorCircuitBoardGenerator.cs:972-978` 原始 | VERIFIED |
| `is_mem_write = (op==Store)`，私有 output | `ZkVmExecutorCircuitBoardGenerator.cs:982-984` 原始 | VERIFIED |
| opcode 整表为 public input（可比对程序语义） | `InstructionFetchCircuitBoardGenerator.cs:126-156`；`ZkProgramExecutor.cs:147-157` | VERIFIED（既有证据） |
| Prove 电路不接收 opcode/is_mem_op 作为输入，只收 trace 5 列 + enc_key | Prove 快照 L47/53 → 原始 L43/49；`source_trace_audit.md` A2 | VERIFIED |
| Prove 电路明确忽略 is_mem_op | Prove 快照 L119 → 原始 L115（"不需要确保 is_mem_op 在 [0,1]，哈希已保证"）；L169 → 原始 L165（"safely ignore is_mem_op"） | VERIFIED |
| step0 归零分支影响 is_mem_op 哈希链 | `ZkVmExecutorCircuitBoardGenerator.cs:133-217` 原始 | VERIFIED |
| opcode 表作 public input 但无 verifier 固定预期（P1-A 未决） | `../aba-03-c2/verifier_interface_audit.md` §2 | 既有结论 |

**直接结论（VERIFIED + INFERRED）**：real/dummy 类型在 VM 电路中由 opcode 私有派生（`is_mem_op`），这是"类型来自执行语义"的**派生路径存在**；但 `is_mem_op` 是私有 witness，Prove 电路不接收它且明确忽略类型语义，prover 可以在事件层面自行声明类型而不被证明拒绝。opcode 表虽是 public input，但无 verifier 固定预期表（P1-A 未决），且"opcode 表正确"不自动等于"这个事件的 type 绑定到了该 opcode"。

### 1.2 verifier 可检查关系与候选最小接口

- **当前可检查**：verifier 只见 public input（opcode 表、step）与 public output 哈希；`is_mem_op` 私有，不可直接检查类型。
- **候选最小接口（`CONSTRUCTED`）**：让 `is_mem_op` 以受约束方式进入证明关系：
  ```
  is_mem_op_j ∈ {0,1}                          # 电路中布尔约束
  type_j = real ⇔ is_mem_op_j = 1              # Bind 到执行语义
  opcode_j ∈ {Load,Store} ⇔ is_mem_op_j = 1    # 已在 VM 电路派生（L972-978）
  dummy : trace_addr_j = p−1, lookup=reg0(私有)，不承诺 reg0
  real  : trace_addr_j = reg0_j, 0≤addr<n（地址范围另属 P2/范围未决）
  ```
  两种落点：① 把 `is_mem_op` 作为受约束 public input/output 暴露给 verifier（泄露类型位，是否可接受 `UNKNOWN`）；② 把 type 隐藏在承诺里，verifier 通过类型承诺的 opening 约束检查（承诺层 binding/hiding 未决）。
- **所需电路修改**：VM 电路需把 `is_mem_op` 或类型承诺纳入 public statement；Fetch/事件电路需按类型分支约束 trace 地址（当前 Fetch 电路无 is_mem_op 输入）。
- **隐私影响**：直接公开 type 暴露"该步是否为访存"，可能泄露控制流（`UNKNOWN` 可接受性）；隐藏承诺路径保护类型但依赖未决承诺层。
- **未解决问题**：is_mem_op 证明层绑定、P1-A 固定预期 opcode 表、类型承诺方案、dummy 分支与真实执行类型的同电路绑定。
- **证据等级**：候选 `CONSTRUCTED`；绑定缺失 `VERIFIED`；隐私可接受性 `UNKNOWN`。

---

## 2. R7 — Trace Row Binding

### 2.1 三层绑定的严格区分（本轮核心）

"trace row 绑定"必须拆成三个强度不同的性质，不能混为一谈：

| 层 | 性质 | 当前状态 | 标签 |
| --- | --- | --- | --- |
| (1) | 证明某个 trace row **内部一致**（哈希正确、同址值不变、排序合法） | Prove 电路实现：行哈希 public output（L65-80 快照）、排序检查（原始 L80-158）、值完整性（原始 L167-193）、out_is_satisfied（L209-214） | `VERIFIED`（存在） |
| (2) | 证明该 trace row **属于某个 VM step**（step↔row 对应） | step 列由 host 注入（L397-398），row 按执行顺序 append（L100），无电路内 step↔row 位置约束 | `CONSTRUCTED`/`UNKNOWN`（无电路约束） |
| (3) | 证明它就是**同一步实际执行产生**的 trace row（内容来自该步 VM 私有输出且未被替换） | `out_trace_mem_addr/mem_val` 是 VM 私有输出（L990-1007），跨电路无 in-circuit 等式；host 哈希多重集比对（L571-587）在 MPC 执行器代码内，非电路/verifier 检查 | `UNKNOWN`/`BLOCKED` |

**关键结论（VERIFIED + INFERRED）**：当前只实现第 (1) 层（trace 内部一致）；第 (2)(3) 层依赖 host 注入与 host 哈希比对，不是 proof soundness 的一部分。把这三层等同，就是把"trace 自洽"误当"trace 属于本次执行"。

### 2.2 现有接口证据（VERIFIED）

| 事实 | 源码证据 | 标签 |
| --- | --- | --- |
| `out_trace_mem_addr`：real(Store/Load) 取 reg0/addr，dummy 取 NegOne(=p−1) | `ZkVmExecutorCircuitBoardGenerator.cs:990-999` 原始 | VERIFIED |
| Fetch 侧 `in_mem_addr = thisRegisters[0]`（reg0，私有） | `ZkProgramExecutor.cs:226-230`；`MemoryTraceFetchCircuitBoardGenerator.cs:45-46` | VERIFIED |
| Fetch 电路逐行 `FieldEquals(in_trace_mem_addr[row], in_mem_addr)` | `MemoryTraceFetchCircuitBoardGenerator.cs:56` | VERIFIED |
| Fetch 侧地址与 executor 侧 out_trace_mem_addr 构造同源，但分属不同电路，无 in-circuit 等式 | `source_trace_audit.md` A2 | VERIFIED（同源）+ INFERRED（无等式） |
| Prove 电路每行公开输出 `out_{i}_hash_mem_trace = H(magic, step, is_mem_op, is_mem_write, addr, val, enc_key)` | Prove 快照 L65-82 → 原始 L61-78 | VERIFIED |
| host 对 trace 行哈希做多重集计数比对（防丢行/重排） | `ZkProgramExecutor.cs:408-412,571-587` | VERIFIED（代码）+ INFERRED（安全边界：host 检查非 verifier 检查） |
| trace 字段 content（addr/val）私有输出，外部只见哈希 | `ZkProgramExecutor.cs:397-405`；`source_trace_audit.md` A2 | VERIFIED |

### 2.3 verifier 可检查关系与候选最小接口

- **当前可检查**：verifier 只见 Prove 电路公开的行哈希多重集；无法检查某一行属于某 step，或该行来自同一步实际执行。
- **host 比较 hash 能否替代证明内绑定？答：不能**（`INFERRED`）。host 多重集比对是 C# 执行器代码内的 `if (...) throw`，不进 R1CS、不进 public inputs，对 verifier 不可见（沿用 `verifier_interface_audit.md` §A9 结论）。它只能保证执行器自身两阶段数据一致，不能向独立 verifier 证明 trace 归属。
- **候选最小接口（`CONSTRUCTED`）**：
  ```
  （路径一：同电路）在 VM 电路内直接输出该步 trace row 的承诺，
      同一步的 Fetch/事件证明绑定到该承诺的 opening（step↔row 电路内连接）；
  （路径二：跨电路）Prove 电路把 row↔step 映射纳入 public statement，
      verifier 固定 step 域 [1,T−1] 并逐行核对承诺 opening；
  dummy 行约束 FieldEquals(row.mem_addr, p−1)，不约束 lookup，不承诺 reg0。
  ```
- **所需电路修改**：新增 step↔row 映射约束（当前无）；Fetch/事件电路接收并约束 trace row 引用；或将 row↔step 承诺纳入 public statement。
- **隐私影响**：行哈希/承诺可保持地址隐私（若基元隐藏）；但承诺层 binding/hiding 未决（`../aba-03-d2/decision.md`）；dummy 语义保持。
- **未解决问题**：step↔row 电路映射、内容绑定、承诺方案与 opening、dummy 分支电路约束。
- **证据等级**：候选 `CONSTRUCTED`；第 (2)(3) 层缺失 `VERIFIED`/`UNKNOWN`；host 不可替代 `INFERRED`。

---

## 3. 状态小结

| 关系 | 当前源码支持 | 候选接口 | 必要电路修改 | verifier 可检查性 | 状态 |
| --- | --- | --- | --- | --- | --- |
| R6 事件类型 | is_mem_op 私有派生；Prove 忽略 | type 位 public 或类型承诺 opening | VM 电路暴露 is_mem_op/承诺 + Fetch 按类型分支 | 当前否（私有）；候选视接口 | `BLOCKED_BY_CURRENT_INTERFACE` |
| R7 trace 行内部一致 | Prove 电路实现（第 1 层） | 沿用 + 公开行哈希 | 已有（第 1 层） | 行哈希 public | `VERIFIED`（第 1 层） |
| R7 step↔row 对应 | host 注入 step + append | 电路内 row↔step 映射或承诺 | 新增映射约束 | 当前否 | `BLOCKED_BY_CURRENT_INTERFACE` |
| R7 行内容来自同一步执行 | 私有输出 + host 哈希比对 | 同电路承诺 / 受约束公共承诺 | 新增内容绑定 | 当前否 | `UNKNOWN`/`BLOCKED` |

**R6/R7 当前状态**：第 (1) 层 trace 内部一致为 `VERIFIED`；R6 类型绑定与 R7 第 (2)(3) 层为 `BLOCKED_BY_CURRENT_INTERFACE` —— 固定架构缺少把类型/行归属纳入 verifier 可检查 statement 的接口，host 哈希比对不能替代证明内绑定。所有候选接口均为 `CONSTRUCTED`，未实现、未测量；地址隐私与 dummy 冻结语义在候选中严格保持。
