# ABA-03-D2 / Phase 3：Context、事件语义与防重放

> 固定上游 `10c90d35…`；起点 `b8a907b8…`。只读评估，不实现。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 候选上下文：`context_i = (program_id, execution_id, step_i, event_type_i)`，进入承诺 preimage，与 `addr_i` 一同被绑定。本文逐字段判断其是否可"可信锚定"，并明确 **C2 本身不解决 B4 完整轨迹问题**。

---

## 1. Context 字段逐项锚定

| 字段 | 由谁固定/产生 | 当前源码状态 | 能否可信锚定 | 标签 |
| --- | --- | --- | --- | --- |
| `program_id` | 需 verifier 固定或可信派生 | 上游**无**整程序承诺/program id；只有逐行 opcode 哈希（含 step/随机 `enc_key`），见 `../aba-03/source_trace_audit.md` §A3、ABA-03-C2 §2 | **不能直接锚定**。P1-A（固定完整 opcode table 比较）是独立前置，可提供一个候选 program 身份来源，但需 verifier 侧固定表/固定 vk | `VERIFIED`（缺失）+ `CONSTRUCTED`（P1-A 前置） |
| `execution_id` | 需每执行唯一/不可预测 | 当前 `enc_key = FieldFactory.Random()`（`ZkProgramExecutor.cs:61`）每执行生成一次，但没有"执行实例 ID"的语义、唯一性证明或 verifier 可见锚点 | **无现成机制**；用 `enc_key` 充当 execution_id 需证明跨执行唯一且被 verifier 锚定 | `VERIFIED`（enc_key 每执行）+ `UNKNOWN`（实例 ID 语义） |
| `step_i` | 电路约束 vs 宿主注入 | `global_step_counter` 由宿主以**公开值**注入 trace（`ZkProgramExecutor.cs:393-395`），电路内有 `is_global_step_counter_non_zero` 与 step0 归零逻辑（`ZkVmExecutor...cs:101-123`），但不是"电路约束出的 step"，而是外部输入 | **部分是公开值，但未证明与执行顺序绑定**；承诺含 step 只是把宿主值写进 preimage，若宿主可伪另一方面 step 则上下文可伪造 | `VERIFIED`（注入方式）+ `UNKNOWN`（顺序绑定） |
| `event_type_i` | 需证明来自真实 opcode | `is_mem_op`/`is_mem_write` 是电路内由 opcode 派生的**私有输出**（`ZkVmExecutor...cs:968-981`），Prove 电路忽略 `is_mem_op`（原始 L164-165），verifier 不可见明文 | **不能仅凭 prover 声明**：若 event_type 只是 prover 写进承诺 preimage 的值，攻击者可把真实访问标成 dummy；必须由电路内 opcode→is_mem_op 派生并绑定到公开承诺 | `VERIFIED`（派生存在）+ `INFERRED`（绑定缺失） |

**结论**：四个 context 字段中，**没有一个**在当前固定 commit 内具备"verifier 可独立信任锚定"的完整路径。program_id 有 P1-A 候选前置；execution_id、step 顺序、event_type 的可信锚定均 `UNKNOWN` 或缺失。

---

## 2. 三种事件语义（不得混淆）

沿用 `../aba-03-d1/p2_binding_semantics.md` 已冻结语义（本轮不改），分析各自进入承诺的方式。

### 2.1 真实 Load/Store（`is_mem_op = 1`）

- 语义：`fetch_addr = reg0 = trace_addr`，`0 ≤ addr < n`（B1）。地址应进入承诺的 `addr` 字段。
- 约束位置候选：地址来自 VM 电路 `inRegisterWires[0]`（`ZkVmExecutor...cs:224-227`），Fetch 侧来自 `in_mem_addr=thisRegisters[0]`（`ZkProgramExecutor.cs:226`）。两侧各自在**自己的电路内**把该地址绑定进 `com`。
- 必须：`event_type=real` 由 opcode 派生而非声明；addr 字段受范围检查（ABA-03 B2）。
- 当前：跨电路同一性与范围约束均未实现（`UNKNOWN`）。

### 2.2 Dummy Fetch（`is_mem_op = 0`，step≥1）

- 语义：`trace_addr = p−1`，**不得**强制 `fetch_addr = trace_addr`（`p2_binding_semantics.md` §1）。
- 进入承诺的正确方式：dummy 步的承诺应承诺 `event_type=dummy` 与 `addr=p−1`（或明确不承诺 `addr`），**绝不承诺 `reg0`**——承诺 `reg0` 会在公开 `com` 的对照下意外暴露非内存寄存器信息（虽承诺隐藏，但可通过 opening 重放链接）。
- verifier 如何知道确实是 dummy：必须由电路内 `is_mem_op=0`（由 opcode 派生）绑定到承诺的 event_type 字段，而非 prover 自行声明。当前 Prove 电路忽略 `is_mem_op`（原始 L164-165）→ 无法在证明层面区分 → `UNKNOWN`。

### 2.3 Step 0

- 语义：不执行 Fetch（`ZkProgramExecutor.cs:201-203`），但仍 append 一行 trace（`:389-402`），该行 `is_mem_op=0`、地址 `p−1`、值 0（ABA-03-C1 冻结）。
- **不得**为 step0 构造 Fetch proof 或承诺事件；承诺序列/event_count 不应包含 step0。
- 当前：无"承诺事件序列"概念 → 无对应机制，`CONSTRUCTED`（设计要求）。

### 三类事件对照

| 事件 | 承诺 addr 字段 | 承诺 event_type 来源 | 是否允许 Fetch proof | 当前可验证性 |
| --- | --- | --- | --- | --- |
| 真实 Load/Store | `reg0`（受范围检查） | opcode 派生 `is_mem_op=1` | 是 | `UNKNOWN`（同一性/范围未实现） |
| Dummy Fetch | `p−1` 或不承诺 | opcode 派生 `is_mem_op=0` | 是（dummy Fetch 存在） | `UNKNOWN`（Prove 忽略 is_mem_op） |
| step0 | 不产生承诺事件 | — | **否** | `CONSTRUCTED`（须显式排除） |

---

## 3. 防重放场景分析

### 3.1 同一承诺跨 step 复用

- 风险：若 `com` 不含 `step_i`，同一 `(addr,r)` 的承诺可在不同 step 复用。
- 缓解：`step_i` 进 context（§1），但 `step_i` 当前是宿主公开注入值（`VERIFIED`），其"执行顺序真实性"未证 → 缓解不完整（`UNKNOWN`）。

### 3.2 同一承诺跨 program 复用

- 风险：换一张 opcode 表但复用承诺，verifier 无法区分。
- 缓解：`program_id` 进 context，P1-A 固定表是候选前置（`CONSTRUCTED`）；但 program_id 无现成可信锚点（`UNKNOWN`）。

### 3.3 同一承诺跨 execution 复用

- 风险：同一承诺/证明在不同执行实例重放。
- 缓解：`execution_id` 进 context 且每执行唯一不可预测；当前无此机制，`enc_key` 每执行随机但未被 verifier 锚定 → `UNKNOWN`。

### 3.4 proof 重排、删除、重复提交

- 风险：承诺逐 step 生成，但 verifier 若只见承诺集合而无顺序约束，可重排/删除/重复提交。
- 现状：C2"两电路对同一 `com`"只保证**单条承诺的地址同一性**，不保证**事件序列的完整性**。这是 B4（计数/顺序/halt 边界），`p2_binding_semantics.md` §3 B4 已明确未解决 → `BLOCKED`（C2 本身不覆盖）。

### 3.5 execution 中止后重启

- 风险：中止后重启若复用 `r`/`execution_id`，承诺重放。
- 现状：无状态机协议（`opening_and_randomness.md` §3 Q9）→ `UNKNOWN`。

### 3.6 prover 重新生成承诺与重新生成 proof

- 风险：prover 换 `r`/`com` 重新生成，配合现场 vk 尝试有利实例——威胁模型为条件性推论（`leakage_and_security.md` D6 勘误 C1），非已验证攻击。
- 缓解：固定承诺生成器 + verifier 固定 context + 认证随机；当前均缺 → `UNKNOWN`。

---

## 4. C2 与 B4 的边界（必须明确）

- **C2 能做的**：在两个电路对同一公开承诺的框架下，若 binding 成立且 opening 正确，推出**该承诺对应步**的地址同一性（B1）。
- **C2 不能做的**：
  - 证明所有应执行的 Fetch 都有承诺（无遗漏）；
  - 证明承诺按 step 顺序、无重复、无删除（顺序/完整性）；
  - 证明执行在正确 halt 处终止（halt 边界）；
  - 证明 event_type 确实来自 opcode 而非声明。
- 这些都是 B4 的范畴，需要**独立的**事件计数、顺序、halt 边界约束（见 `../aba-03-d1/p2_binding_semantics.md` B4、`../aba-03-d1/leakage_and_security.md` D8）。**不得把 C2 的"相同承诺"写成已解决 B4。**

---

## 5. 本阶段结论

1. `context_i` 四字段中 program_id（P1-A 候选前置外）、execution_id、step 顺序绑定、event_type 来源**均无 verifier 可信锚定路径**；step 只是宿主公开注入，event_type 若由 prover 声明则可伪造。
2. 三种事件语义可区分，但 verifier 在证明层面区分 real/dummy 依赖 `is_mem_op` 被绑定到公开承诺，而当前 Prove 电路忽略 `is_mem_op` → `UNKNOWN`。
3. step0 必须为"无 Fetch/无承诺事件"，需显式排除。
4. 六类重放场景中，跨 step/program/execution 可通过 context 字段缓解但字段本身未可信锚定；proof 重排/删除/重复属于 B4，C2 不覆盖 → `BLOCKED`。
5. 上下文锚定是阻止进入原型的第二个核心未知项（见 `decision.md`）。
