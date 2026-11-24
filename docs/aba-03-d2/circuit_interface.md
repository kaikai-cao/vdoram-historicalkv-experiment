# ABA-03-D2 / Phase 4+5：双电路接口构造与符号成本

> 固定上游 `10c90d35…`；起点 `b8a907b8…`。只读设计，不实现电路。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 目标：给出 VM 电路与 Fetch 电路的候选接口，说明"相同承诺为何能推出相同地址"所依赖的假设与约束，并评估固定上游能否承载。Phase 5 符号成本并入本文（本轮授权五份文档无独立 cost_model）。

---

## 1. 通用承诺接口（候选）

设承诺方案 `Commit`，`context_i = (program_id, execution_id, step_i, event_type_i)`（见 `context_and_replay.md`），`r` 为 opening randomness。

```
Commit(context_i, addr_i; r_i) -> com_i
VerifyOpen(com_i, context_i, addr_i, r_i) -> {0,1}   # 电路内重算比较
```

成立所需前提（缺一不可）：
1. **binding**：不同 `(addr,r)` 不能给出同一 `com`（MiMC `UNKNOWN`，Pedersen `INFERRED`）；
2. **hiding**：`com` 不泄露 `addr`（Pedersen 信息论条件于均匀 `r`；MiMC 条件于哈希假设）；
3. **opening 正确性**：两侧电路各自约束自己的 `(addr,r)` 重算出 `com`；
4. **context 可信**：`program_id/execution_id/step/event_type` 由 verifier 锚定或电路约束（当前多为 `UNKNOWN`）。

---

## 2. 双电路候选接口（伪代码，非真实代码）

### 2.1 VM 电路

```
VM_Circuit(public: program_id, execution_id, n,
           public_out: com_vm, event_type_vm_pub,
           private_witness: addr_vm, r_vm, context_aux, is_mem_op_vm):
    # 1) 由 opcode 派生 is_mem_op（上游骨架 ZkVmExecutor:968-976）
    constrain is_mem_op_vm == (opcode_vm == Load OR opcode_vm == Store)     # VERIFIED 骨架
    # 2) event_type 必须由 is_mem_op 派生，不能是自由 witness
    constrain event_type_vm == is_mem_op_vm                                 # CONSTRUCTED
    # 3) 真实步：地址取 reg0、范围检查（ABA-03 B1/B2）
    if is_mem_op_vm == 1:
        addr_vm == reg0_vm                                                  # VERIFIED 同源
        constrain 0 <= addr_vm < n   (bit-decomp + Boolean + int-compare)  # CONSTRUCTED
    else:
        constrain addr_vm == p-1   (dummy / step0 trace 地址)               # VERIFIED otherwise 分支
    # 4) 承诺（各电路用自身 addr/r 重算）
    com_vm = Commit((program_id, execution_id, step_vm, event_type_vm), addr_vm; r_vm)
    public_out(com_vm, event_type_vm_pub)                                   # CONSTRUCTED
```

说明：`reg0_vm` 本身是私有（`ZkVmExecutor...cs:177,227`），必须保持在见证内，不进公开输入。

### 2.2 Fetch 电路

```
Fetch_Circuit(public: program_id, execution_id, step_fetch,
              public_out: com_fetch, event_type_fetch_pub,
              private_witness: addr_fetch, r_fetch, is_mem_op_fetch, trace_row):
    # 1) 真实步：in_mem_addr 来自 reg0，与 trace 行地址 FieldEquals（上游 :52）
    constrain FieldEquals(trace_row.mem_addr, addr_fetch)                   # VERIFIED 骨架
    # 2) event_type 由 is_mem_op 派生（跨电路一致性需外部锚定）
    constrain event_type_fetch == is_mem_op_fetch                           # CONSTRUCTED
    if is_mem_op_fetch == 1:
        constrain addr_fetch == reg0_fetch                                  # VERIFIED 同源
    else:
        constrain addr_fetch == p-1   # dummy；不得要求 == reg0             # VERIFIED/INFERRED
    # 3) 承诺
    com_fetch = Commit((program_id, execution_id, step_fetch, event_type_fetch), addr_fetch; r_fetch)
    public_out(com_fetch, event_type_fetch_pub)                             # CONSTRUCTED
```

注意：Fetch 电路当前**不接收** `is_mem_op`/opcode（`MemoryTraceFetch...cs` 只处理 trace 列），要按 event_type 分支需新增输入与约束 → `CONSTRUCTED`。

### 2.3 Verifier 比较

```
Verifier(proof_vm, proof_fetch):
    require proof_vm.com_vm == proof_fetch.com_fetch                       # 核心相等
    require proof_vm.event_type_vm_pub == proof_fetch.event_type_fetch_pub  # 类型一致
    require step_vm == step_fetch  (若 step 为公开，逐事件对应)             # CONSTRUCTED
    require program_id/execution_id == verifier 固定期望值                  # 需外部锚定 UNKNOWN
    accept
```

**相同承诺为何推出相同地址**：在 binding 成立且两电路各自正确开承诺的前提下，`com_vm = com_fetch` ⇒ `(addr_vm,r_vm) = (addr_fetch,r_fetch)` ⇒ `addr_vm = addr_fetch`（见 `opening_and_randomness.md` Q3）。这不是自动成立：MiMC binding 未证（`UNKNOWN`），Pedersen DL binding `INFERRED` 且需可信生成器；context 若不一致则即使地址相同也不应视为同一事件。

---

## 3. 两种比较模式

| 模式 | 公开输入内容 | verifier 比较 | 前提 | 评价 |
| --- | --- | --- | --- | --- |
| **模式 A**：两 proof 公开完全相同的 `com` | 每 proof 的 public 含 `com_i`（+event_type/step） | 直接比较两份 public 中的 `com_i` 相等 | 两电路导出同一 `com`（context/addr/r 一致） | 简单；但需保证 context 一致，`r` 不同不影响（binding 保证） |
| **模式 B**：两 proof 公开不同承诺，由更高层比较 | 每 proof public 含各自 `com_vm/com_fetch` 的承诺（如哈希） | 顶层 verifier/组合电路比较 | 需要顶层 statement 与 binding | 更复杂；接近 C3 递归方向（本轮不扩展 C3） |

本轮聚焦**模式 A**（共享同一 `com`），这也是 D1 中 C2 的原意。模式 B 需要顶层 statement，超出本轮承诺可行性审查范围（且不自动解决 C2 的 binding/hiding/随机性问题）。

---

## 4. 固定上游接口承载性（逐项）

| 需求 | 固定上游是否支持 | 证据 | 标签 |
| --- | --- | --- | --- |
| 公开输入通道 | 部分支持 | opcode 四列已公开（`InstructionFetch...cs:126-156`、`plonk.rs:143-161`）；但无 `com`/event_type 字段，需新增 | `VERIFIED`（通道在）+ `INFERRED`（字段需增） |
| 电路内承诺重算 | 不支持（作为承诺） | MiMC gadget 已用但作为哈希摘要（`ZkVmExecutor...cs:1009-1017`）；Pedersen gadget 存在但未接入（`plonk.rs` 无引用） | `VERIFIED`（现状）+ `CONSTRUCTED`（承诺用法） |
| `is_mem_op`/event_type 进入公开承诺 | 不支持 | `is_mem_op` 是私有输出（`:968-981`），Prove 忽略（原始 L164-165） | `VERIFIED`（缺失） |
| verifier 固定 vk | 不支持 | `test_rng()` 现场生成（`plonk.rs:302-304`）；无独立 verifier（ABA-03-C2 §A8） | `VERIFIED`（缺失） |
| P1-A 固定程序表 | 独立前置 | opcode 表已公开，但需 verifier 固定表/固定 vk（ABA-03-C2 §2） | `CONSTRUCTED`（前置） |
| B4 轨迹完整性 | 不支持 | 无事件计数/顺序/halt 约束（`p2_binding_semantics.md` B4） | `BLOCKED`（C2 不覆盖） |
| 宿主 throw / 哈希多重集代替约束 | 不可替代 | `ZkProgramExecutor.cs:302-332,551-583` 是宿主检查，不进 proof/verifier（ABA-03-C2 §3） | `VERIFIED`（区分） |

**结论**：固定上游的公开输入通道和 MiMC gadget 可复用，但"承诺作为共享隐藏承诺""event_type 进公开承诺""verifier 固定 vk""B4 完整性"都不具备；P2 地址绑定不自动闭合 P1，C2 不闭合 B4。

---

## 5. Phase 5：符号成本模型（不填数值）

**表达式**（T=总步数，含 step0；真实步 M，dummy 步 D=T−1−M）：

```
C_total(T) = T · (C_VM_commit + C_Fetch_commit + C_context + C_randomness)
             + M · C_real + D · C_dummy + C_verifier
```

各项定义与可得性：

| 成本项 | 含义 | 可得性 |
| --- | --- | --- |
| `C_VM_commit` / `C_Fetch_commit` | 每电路一次承诺重算（MiMC：65 轮 ×(add+pow7)，或 Pedersen 群运算） | 类型 `VERIFIED`（`MimcEncryptGadget.cs:38-55`）；门数 `UNKNOWN` |
| `C_context` | context 四字段编码进承诺 preimage | `UNKNOWN`（编码未定） |
| `C_randomness` | 随机数生成/认证/绑定约束 | `UNKNOWN`（机制未定；MPC 认证 `BLOCKED`） |
| `C_real` | 真实步范围检查（bit-decomp+Boolean+int-compare） | 类型 `VERIFIED`（ABA-03 B2）；门数 `UNKNOWN` |
| `C_dummy` | dummy 步 p−1 哨兵 + 分类约束 | `UNKNOWN` |
| `C_verifier` | verifier 比较 com/event_type/step + verify_proof | `UNKNOWN`（公开输入增长未测） |

必须区分且**不得等同**：

- R1CS/PLONK 约束数量 `≠` MPC 乘法数 `≠` 通信轮次 `≠` prove 时间 `≠` verifier 成本；
- 双电路重复计算：MiMC 两电路各算一次承诺 → 约 `2T` 次承诺调用（符号）；Pedersen 群运算成本 `UNKNOWN`；
- MPC 通信轮次增加位置：若随机数需 MPC 联合生成/认证（当前 `BLOCKED`）、或 Pedersen 群元素需 MPC share（当前不支持）；
- 非原生域运算：Pedersen 群运算非 Fr 原生（`UNKNOWN`/`BLOCKED`），MiMC 全 Fr 原生（`VERIFIED`）；
- 多步总成本随 T 线性增长，具体系数全部 `UNKNOWN`。

本阶段**不提供任何具体门数、时间、字节数**。
