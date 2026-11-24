# ABA-03-D3-01 / Phase 1：统一验证关系模型

> 实验仓起点：`03960aa941bcd8ef88fbd06a83cf7599682a5cbd`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只复用既有证据的设计评估；不重抓上游源码、不实现电路、不解除 HOLD、不运行测试。
>
> 标签：`VERIFIED` = 既有文档中固定 commit 源码事实；`CONSTRUCTED` = 本阶段候选关系，非上游实现；`INFERRED` = 由既有证据推导；`UNKNOWN` = 缺证据；`BLOCKED` = 当前接口无法支撑结论。
>
> 证据来源（只引用，不重抓）：`../aba-03/source_trace_audit.md` A1–A4；`../aba-03-c2/verifier_interface_audit.md` §1–§3；`../aba-03-d1/p2_binding_semantics.md` §1/§3；`../aba-03-d1/design_options.md` §1–§3；`../aba-03-d1/leakage_and_security.md` §1；`../aba-03-d2/opening_and_randomness.md` Q1–Q9；`../aba-03-d2/context_and_replay.md` §1–§4；`../aba-03-d2/circuit_interface.md` §1–§5；`../aba-03-d2/decision.md` §2/§4。

---

## 0. 一句话结论

现有证据能给出一组**候选统一 statement 的字段与关系骨架**，但不能给出一条已闭合的可验证链：程序身份有 verifier 侧最小路径（P1-A-1），地址同一性需要新增电路/承诺接口，dummy 事件及其 trace row 绑定需要新增电路约束，B4 完整性与 VK/context 锚定仍是独立未决项。本文中的关系表达式均为候选模型，**不是现有实现**；是否可进入接口规格阶段由 `decision.md` 统一判断。

---

## 1. 对象定义与当前可见性

| 对象 | 定义 | 当前固定 commit 中的证据 | 当前可见性 | 本阶段要求 |
| --- | --- | --- | --- | --- |
| `Program` | 预期程序身份与其指令/操作语义，记为预期完整 opcode table `OP_exp`（或可选稳定 digest） | opcode table 四列已是 public input（`InstructionFetchCircuitBoardGenerator.cs:126-156`；`ZkProgramExecutor.cs:147-157`；`plonk.rs:143-161`）；无整程序 hash/program id（`../aba-03/source_trace_audit.md` A3；`../aba-03-c2/verifier_interface_audit.md` §2） | `OP_pub` 公开；无 verifier 预期值 | verifier 固定 `OP_exp`；program_id/digest 为可选，不与 P1-A-1 混同 |
| `Execution` | 一次执行实例及其唯一上下文，记为 `exec_id`、`n`、`T`、`prog_ref` | `enc_key = FieldFactory.Random()` 每执行生成，但不是执行实例 ID；`n` 已公开但无范围约束（`ZkProgramExecutor.cs:61,256-262`；`../aba-03/source_trace_audit.md` A3） | `n` 公开；`exec_id` 无机制 | `exec_id` 必须由可信来源产生并被 verifier 锚定；当前 `UNKNOWN` |
| `Step` | VM 执行步与顺序，记为 `step_i`、`pc_i` | `global_step_counter` 由宿主以公开值注入 trace（`ZkProgramExecutor.cs:393-395`）；`pc_i` 当前私有（`:134-136`）；电路有 step0 归零逻辑（`ZkVmExecutor...cs:101-123`） | `step_i` 公开注入但顺序真实性未证；`pc_i` 私有 | 需证明 step 单调/连续与事件对齐；当前 `UNKNOWN` |
| `Event` | step≥1 的 Fetch 事件，类型 `real`(Load/Store) 或 `dummy` | 每 step≥1 都构造 Fetch，输入为 `thisRegisters[0]`（`ZkProgramExecutor.cs:205-228`，尤其 `:226`）；`is_mem_op` 由 opcode 电路派生但私有（`:968-976`） | 类型与地址不在 proof statement | 类型必须由电路内 opcode 派生并进入公开 statement 或公开承诺；当前 `CONSTRUCTED` |
| `TraceRow` | VM 历史记录中与某 step 对应的行，关键列 `trace_addr`、`is_mem_op`、`mem_val` | trace 行由执行器 append（`:389-402`）；`step` 列是公开注入而非电路输出；`out_trace_mem_addr` 由电路派生（`:989-1007`） | 列值私有/摘要可见；step↔row 对应未证 | 必须新增 step↔row 对应的电路约束；当前 `CONSTRUCTED`/`UNKNOWN` |
| `Address` | 真实访问地址 `reg0`，或 dummy 哨兵 `p−1` | 地址源为 `inRegisterWires[0]`（`ZkVmExecutor...cs:224-227`），Fetch 输入同为 `thisRegisters[0]`（`ZkProgramExecutor.cs:226`）；dummy trace 地址为 `p−1`（`:941-943,989-997`） | 地址私有；dummy lookup 值也是私有 | 真实步三值相等 + 范围；dummy 承诺哨兵且不承诺 `reg0` |
| `Commitment` | 隐藏地址与 context 的承诺 `com_i`，候选形式 `Commit(context_i, addr_i; r_i)` | 固定 commit 存在 MiMC gadget 但无公开 binding 归约；Pedersen gadget 存在但未接入 CompatCircuit→PLONK 路径（`../aba-03-d2/commitment_candidates.md` §0/§2） | 当前无共享承诺 | binding/hiding/opening/随机数机制全部未闭合 |
| `Proof` | VM、Fetch、Trace 一致性等证明对象 | 当前 compat 路径每电路 setup→prove→verify 同函数，proof 只在进程内（`plonk.rs:293-315`）；无独立 verifier（`:A8`） | prover 自测对象 | 需明确每类 proof 的公开 statement 与 verifier 检查边界 |
| `Verifier` | 独立验证者，持有可信 VK、预期 statement 与程序期望值 | 固定源码无独立 verifier；外部部署是否固定 VK 为 `UNKNOWN`（`../aba-03-d1/leakage_and_security.md` D6 勘误） | 当前不存在独立主体 | 固定 VK + 固定 `OP_exp` + 固定 context 期望值；VK 信任模型待定 |

---

## 2. 统一关系候选（非现有实现）

### 2.1 符号约定

```
OP_exp        verifier 固定的预期完整 opcode table
OP_pub        proof public inputs 中的 opcode table
prog_ref      program 身份锚点（P1-A-1 下可由 OP_exp 承担；digest 为可选 P1-A-2）
exec_id       执行实例唯一标识（当前无机制）
step_i        第 i 个 VM 步（step 0 为例外）
is_mem_op_i   由 opcode 在电路内派生的事件类型
addr_i        承诺覆盖的地址；真实步为 reg0，dummy 步为 p−1
r_i           opening randomness
com_i         公开承诺（若选隐藏承诺路径）
row_i         与 step_i 对应的 VM trace row
```

### 2.2 候选关系集合

以下表达式均是 `CONSTRUCTED` 候选关系，**不是当前上游约束**。

```
R-Program (P1-A-1, verifier 侧):
    OP_pub == OP_exp                         # 逐项比较，复用现有 public-input 通道

R-Execution (待设计):
    exec_id 由可信来源唯一产生并被 verifier 固定
    n, T 或 step_bound 进入 verifier 固定 statement

R-Step/Event (电路内 + 公开 statement):
    step 0: 无 Fetch proof，无承诺事件
    step i≥1: event_i = (step_i, is_mem_op_i, addr_i, ...)
    is_mem_op_i == (opcode_i ∈ {Load, Store})    # 电路内派生，不能由 prover 声明

R-Real (is_mem_op_i = 1):
    fetch_lookup_addr_i == reg0_i
    trace_addr_i       == reg0_i
    fetch_lookup_addr_i == trace_addr_i
    0 <= addr_i < n                              # 完整域元素 + 位分解范围检查

R-Dummy (is_mem_op_i = 0, i≥1):
    fetch_lookup_addr_i == reg0_i                # lookup key 不改成哨兵
    trace_addr_i        == p−1
    FieldEquals(row_i.mem_addr, p−1)             # 绑定实际 trace row
    不得断言 fetch_lookup_addr_i == trace_addr_i
    event_type 承诺覆盖 dummy 与 p−1，不承诺 reg0

R-TraceRow:
    row_i 必须对应当前 step_i（需新增 step↔row 电路映射）
    step 0 的 trace 行存在但不进入 Fetch/承诺事件序列

R-Commitment (若选共享隐藏承诺路径):
    com_vm_i  = Commit(context_i, trace_addr_vm_i; r_vm_i)
    com_fetch_i = Commit(context_i, trace_addr_fetch_i; r_fetch_i)
    com_vm_i == com_fetch_i == com_i             # 公开比较
    两侧各自正确约束 opening；Pedersen 同 C + 同消息 ⇒ r_vm = r_fetch mod q

R-Completeness (B4, 未闭合):
    count(events) == T − 1 − M
    events 按 step 单调、无重复、无遗漏、无重排
    execution 在预期 halt/异常边界终止
```

### 2.3 四类关系分级

| 类别 | 关系 | 证据等级 | 说明 |
| --- | --- | --- | --- |
| 已由固定上游实现 | opcode table 进入 public inputs；每 step≥1 构造 Fetch 且 lookup key 为 reg0；VM trace 地址/sentinel 派生；step0 无 Fetch；`is_mem_op` 由 opcode 派生；宿主哈希 `throw` 检查 | `VERIFIED`（`source_trace_audit.md` A1–A2；`p2_binding_semantics.md` §1；`verifier_interface_audit.md` §1/§3） | 这些是源码事实，不等于 verifier 可验证绑定 |
| 有证据支持但未进入电路 | Fetch 与 VM 地址构造同源（都来自 reg0）；Fetch 内部存在按地址选择 trace 行的 `FieldEquals`；Prove 电路检查 trace 内部顺序/一致性 | `INFERRED` + `VERIFIED`（同源事实）；`VERIFIED`（缺失跨电路等式） | 同源 ≠ 跨 proof 同一性；宿主检查不等于证明 soundness |
| 本阶段提出的新构造 | 共享公开承诺、event_type 公开/承诺化、step↔trace row 映射、B4 计数/顺序/halt 约束、独立 verifier 固定 OP_exp/VK | `CONSTRUCTED` | 均未实现；需后续接口规格与电路约束 |
| 当前无法证明 | MiMC binding 归约；Pedersen 接入 Fr-wire/PLONK/MPC；`exec_id` 唯一性与 verifier 锚定；外部 VK 信任；B4 完整闭合；独立 `r` 关联证明 | `UNKNOWN` / `BLOCKED` | 不得用理论性质或伪代码替代证据 |

---

## 3. 字段边界：verifier 固定 / 公开 / 私有

| 字段 | verifier 固定 | proof public | private witness / 输出 | 依据与边界 |
| --- | --- | --- | --- | --- |
| opcode table `OP_exp` | 是（P1-A-1 最小路径） | `OP_pub` 已公开 | 选中 opcode 行当前私有 | `verifier_interface_audit.md` §2；固定表比较不必然新增电路 |
| program digest | 可选（P1-A-2） | 可替代整表公开 | 需新增电路承诺关系 | 不得声称 digest 必然优于完整表 |
| `n` / `Nmax` / `step_bound` | 需 verifier 固定期望 | 当前 `n` 已公开 | — | `source_trace_audit.md` A3：公开 ≠ 有界；范围约束未实现 |
| `exec_id` | 需 verifier 锚定 | 是否公开取决于防重放设计 | 不得由 prover 自由声明 | `context_and_replay.md` §1/§3.3：当前 `UNKNOWN` |
| `step_i` | 顺序真实性需约束 | 当前宿主注入为公开 | — | `ZkProgramExecutor.cs:393-395`；公开值 ≠ 被证明的顺序 |
| `pc_i` / opcode 选中行 | 否（当前） | 可选提升（C1）或保持承诺内隐藏 | 当前私有 | `source_trace_audit.md` A1；提升公开会增加暴露 |
| `is_mem_op_i` / event_type | 需绑定到公开 statement 或承诺 | 可选公开分类字段 | 当前电路派生私有输出 | Prove 忽略 `is_mem_op`（原始 L164-165）；不能由 prover 声明 |
| `reg0` / 真实地址 | 否 | 隐藏路径下不公开，承诺覆盖 | 是 | C1 公开地址路径有不可接受隐私退化（`design_options.md` §1） |
| dummy lookup 与 sentinel | sentinel 固定为 `p−1` | 可公开 event_type/承诺 | lookup `reg0` 私有 | `p2_binding_semantics.md` B2；dummy 不承诺 `reg0` |
| `r_i` | 机制未定 | 不应公开（牺牲 hiding） | 是 | `opening_and_randomness.md` Q5–Q9；MPC 认证当前 `BLOCKED` |
| `com_i` | verifier 比较两份 proof 的公开值 | 是（隐藏路径） | — | 同 C + 同消息下 Pedersen `r` 代数相同；不同消息双重 opening 导出 DL 关系 |
| VK | 必须 verifier 固定/可信分发 | 否 | — | 当前本地 `test_rng()` 现场 setup 为 `VERIFIED`；外部为 `UNKNOWN` |

---

## 4. 四个核心问题的边界回答

1. **哪些字段必须由 verifier 提供或固定？** 预期完整 opcode table（或可选的稳定 digest）、VK、`n/Nmax`/step 边界、执行实例锚点 `exec_id` 与承诺 context 期望值。当前只有 public-input 通道与标准 `verify_proof` 可复用，独立 verifier 与固定期望值缺失（`verifier_interface_audit.md` §1/§2、§4）。
2. **哪些字段可以是公开输入？** 已有 opcode table；候选公开字段包括 `step_i`、`event_type_i`、`com_i`、`n`、`exec_id`（是否公开取决于隐私/防重放设计）、可选 `pc_i/opcode_i`。真实地址公开（C1）虽有最短路径，但泄漏真实访问模式，不能作为默认方案（`design_options.md` §1）。
3. **哪些字段必须保持私有？** `reg0`/真实地址、`r_i`、选中 opcode 行/PC（除非显式选择 C1 公开化）、MPC share。`is_mem_op` 当前为私有派生输出；若 verifier 需分类，必须新增“由 opcode 派生且绑定到公开 statement/承诺”的路径，而不是让 prover 直接声明。
4. **VM、Fetch、Trace、Commitment 如何对应？** 真实步应形成 `reg0 → (fetch_lookup_addr, trace_addr) → 同一 com_i → 同一 step/event` 的闭合关系；dummy 步只能承诺 `p−1` 与类型，lookup 仍为 `reg0` 且不得公开；step↔trace_row 映射与 B4 顺序/完整性尚需新增约束（`p2_binding_semantics.md` B1–B4；`circuit_interface.md` §2/§3）。
5. **dummy 如何不泄露 reg0？** 承诺 event_type=dummy 与 `addr=p−1`（或显式不承诺地址），绝不承诺 dummy lookup 的 `reg0`；实际 trace row 只绑定哨兵 `p−1`（`context_and_replay.md` §2.2；`circuit_interface.md` §2.2）。
6. **step 0 如何进入事件序列？** step 0 有 trace 行但无 Fetch、无承诺事件；event count 为 `T−1−M`，step0 必须显式排除，不得虚构 Fetch proof（`p2_binding_semantics.md` B3；`context_and_replay.md` §2.3）。

---

## 5. 本阶段明确不声称的事

- 不声称 `OP_pub == OP_exp` 已由 verifier 执行：当前无独立 verifier，public inputs 来自 prover 自己（`verifier_interface_audit.md` §A8）。
- 不声称 fetch/trace/commitment 的统一关系已在电路内成立：它们均为 `CONSTRUCTED`。
- 不声称共享承诺可用：MiMC binding 无公开归约，Pedersen 未接入当前证明路径，随机数与 context 机制未闭合（`../aba-03-d2/commitment_candidates.md`、`opening_and_randomness.md`）。
- 不声称 B4 已闭合：承诺相等与事件序列完整性是两个不同问题（`context_and_replay.md` §4）。
- 不把宿主端 `throw` 或逐行哈希多重集检查当作 proof soundness 或 verifier 检查。
