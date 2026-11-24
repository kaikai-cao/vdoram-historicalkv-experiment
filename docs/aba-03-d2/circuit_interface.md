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
1. **binding**：不同消息 `(addr,r)` 不能给出同一 `com`；Pedersen 是 DL 假设下的**计算 binding**（若 `mG+rH = m'G+r'H` 且 `m != m'`，两份 opening 可导出生成元间的 DL 关系），不是 perfect binding（MiMC `UNKNOWN`，Pedersen `INFERRED` + 生成器信任 `UNKNOWN`）；
2. **hiding**：`com` 不泄露 `addr`（Pedersen perfect hiding，条件于 `r` 均匀且保密；MiMC 条件于哈希假设）；
3. **opening 正确性**：两侧电路各自约束自己的 `(addr,r)` 重算出 `com`；
4. **context 可信**：`program_id/execution_id/step/event_type` 由 verifier 锚定或电路约束（当前多为 `UNKNOWN`）。

**Pedersen 特例**：两侧虽各自持有 opening witness，但若使用同一 `C` 且消息相同，则 `(r_vm − r_fetch)H = 0`，在素数阶群、`H` 非单位元下 `r_vm = r_fetch mod q`；不能把“独立 `r` 指向同一承诺”当作可选设计。若消息不同却 `C` 相同，则两份 opening 给出 `G/H` 的 DL 关系，由计算 binding 排除。

---

## 2. 双电路候选接口（伪代码，非真实代码）

### 2.1 VM 电路

```
VM_Circuit(public: program_id, execution_id, n,
           public_out: com_vm, event_type_vm_pub,
           private_witness: trace_addr_vm, r_vm, context_aux, is_mem_op_vm, reg0_vm):
    # r_vm 是 VM 侧 opening witness；同一 Pedersen C + 同一消息 ⇒ r_vm = r_fetch mod q（代数结果）
    # 1) 由 opcode 派生 is_mem_op（上游骨架 ZkVmExecutor:968-976）
    constrain is_mem_op_vm == (opcode_vm == Load OR opcode_vm == Store)     # VERIFIED 骨架
    # 2) event_type 必须由 is_mem_op 派生，不能是 prover 自由声明
    constrain event_type_vm == is_mem_op_vm                                 # CONSTRUCTED
    # 3) 地址：trace_addr_vm 是写进 trace/承诺的地址；reg0_vm 保持私有
    if is_mem_op_vm == 1:   # 真实 Load/Store
        constrain trace_addr_vm == reg0_vm                                  # VERIFIED 同源
        constrain 0 <= trace_addr_vm < n   (bit-decomp + Boolean + int-compare)  # CONSTRUCTED
    else:                   # dummy Fetch（step >= 1）；step0 单独排除
        constrain trace_addr_vm == p-1   (trace 哨兵)                        # VERIFIED otherwise 分支
    # 4) 承诺（各电路用自身 trace 地址与自身 r 重算）
    com_vm = Commit((program_id, execution_id, step_vm, event_type_vm), trace_addr_vm; r_vm)
    public_out(com_vm, event_type_vm_pub)                                   # CONSTRUCTED
```

说明：`reg0_vm` 本身是私有（`ZkVmExecutor...cs:177,227`），必须保持在见证内，**不得作为公开输入**。dummy 步的承诺覆盖 `p−1` 哨兵或显式不承诺地址（见 `context_and_replay.md` §2.2），不得承诺 `reg0`。step0 不执行 Fetch、不产生 Fetch 承诺事件（见 `context_and_replay.md` §2.3）；承诺序列/event_count 不含 step0，不得虚构 step0 Fetch proof。

### 2.2 Fetch 电路

```
Fetch_Circuit(public: program_id, execution_id, step_fetch,
              public_out: com_fetch, event_type_fetch_pub,
              private_witness: fetch_lookup_addr, trace_addr_fetch, r_fetch,
                               is_mem_op_fetch, reg0_fetch, trace_row):
    # r_fetch 是 Fetch 侧 opening witness；同一 Pedersen C + 同一消息 ⇒ r_fetch = r_vm mod q（代数结果）
    # 1) real/dummy 类型由电路内 opcode 派生，不能由 prover 声明
    constrain is_mem_op_fetch == (opcode_fetch == Load OR opcode_fetch == Store)  # CONSTRUCTED 接口
    constrain event_type_fetch == is_mem_op_fetch                          # CONSTRUCTED
    # 2) 按类型显式分支：lookup key 与 trace 地址是两个不同字段
    if is_mem_op_fetch == 1:   # 真实 Load/Store
        constrain fetch_lookup_addr == reg0_fetch                          # VERIFIED 同源
        constrain trace_addr_fetch == reg0_fetch                           # VERIFIED 同源
        constrain FieldEquals(trace_row.mem_addr, trace_addr_fetch)        # 仅真实步
        constrain 0 <= trace_addr_fetch < n                                # CONSTRUCTED（ABA-03 B2）
    else:                      # dummy Fetch（step >= 1）
        constrain fetch_lookup_addr == reg0_fetch                          # lookup key 仍是 reg0，不强设为 p-1
        constrain trace_addr_fetch == p-1                                  # trace 哨兵
        constrain FieldEquals(trace_row.mem_addr, p-1)                     # dummy trace row 必须是 p-1（CONSTRUCTED）
        # 不约束 fetch_lookup_addr == trace_addr_fetch；reg0 不进公开输入
    # 3) 承诺
    com_fetch = Commit((program_id, execution_id, step_fetch, event_type_fetch), trace_addr_fetch; r_fetch)
    public_out(com_fetch, event_type_fetch_pub)                             # CONSTRUCTED
```

注意：Fetch 电路当前**不接收** `is_mem_op`/opcode（`MemoryTraceFetch...cs` 只处理 trace 列），要按 event_type 分支需新增输入与约束 → `CONSTRUCTED`。`trace_row` 指当前 `step_fetch` 对应的 VM trace 行（`out_trace_mem_addr` 列）：真实步该列为 `reg0`，dummy 步为 `p−1`（`../aba-03-d1/p2_binding_semantics.md` §0 的 `VERIFIED_SOURCE` 来源）。现有 Fetch 电路接收 `in_mem_addr` 并输出 `out_trace_mem_val`，未接收/强制 `trace_row.mem_addr`；把该行按 step 对应到当前 Fetch step 并加入 `FieldEquals(trace_row.mem_addr, p−1)` 是需要新增的 `CONSTRUCTED` 约束，**不是上游已实现事实**。若 step↔trace_row 对应关系无法证明，dummy 承诺语义不能闭合。冻结语义是 `fetch_lookup_addr = reg0`（Fetch 用 `reg0` 作 lookup key）、`trace_addr = p−1`（dummy 步的 trace 哨兵），二者在 dummy 步本就不相等；**不得**强制 `fetch_lookup_addr == trace_addr`，也**不得**把 dummy 的 lookup address 强设为 `p−1`。real/dummy 必须由电路内 opcode 派生并绑定到对应公开 statement，不能由 prover 自由声明。step0 不在本伪代码的 Fetch 事件内。

### 2.3 Verifier 比较

```
Verifier(proof_vm, proof_fetch):
    require proof_vm.com_vm == proof_fetch.com_fetch                       # 核心相等
    require proof_vm.event_type_vm_pub == proof_fetch.event_type_fetch_pub  # 类型一致
    require step_vm == step_fetch  (若 step 为公开，逐事件对应)             # CONSTRUCTED
    require program_id/execution_id == verifier 固定期望值                  # 需外部锚定 UNKNOWN
    accept
```

**相同承诺为何推出相同地址**：这不是无条件数学等式。只有在两电路各自正确约束自己的 opening（real 步 lookup key 与 trace 地址一致；dummy 步承诺 trace 哨兵、绑定实际 trace row、不强加 lookup key 相等）、使用同一个 `com`，且承诺 binding 成立时，才有 `com_vm = com_fetch` ⇒ 两侧承诺消息相同 ⇒ `trace_addr_vm = trace_addr_fetch`（见 `opening_and_randomness.md` Q3）。Pedersen 特例：若 `m_vm = m_fetch` 且 `C_vm = C_fetch`，则 `(r_vm − r_fetch)H = 0`，素数阶群且 `H` 非单位元 ⇒ `r_vm = r_fetch mod q`；这是代数结果，不能把“两侧独立 `r`”当作可选设计。若消息不同却 `C` 相同，则两份 opening 导出 `G/H` 的 DL 关系，DL 困难下由计算 binding 排除，不是 perfect binding。MiMC binding 未证 → `UNKNOWN`；Pedersen `INFERRED` 且生成器信任 `UNKNOWN`；context 若不一致则即使地址相同也不应视为同一事件。

---

## 3. 两种比较模式

| 模式 | 公开输入内容 | verifier 比较 | 前提 | 评价 |
| --- | --- | --- | --- | --- |
| **模式 A**：两 proof 公开完全相同的 `com` | 每 proof 的 public 含 `com_i`（+event_type/step） | 直接比较两份 public 中的 `com_i` 相等 | 两电路导出同一 `com`（context 一致；两侧各自正确约束 opening；Pedersen 同一 `C` + 同一消息下 `r` 代数相同） | 简单；但需保证 context 一致与 binding 成立，不能把“不同 `r`”当作推荐设计或成本节省 |
| **模式 B**：两 proof 公开不同承诺，由更高层比较 | 每 proof public 含各自 `com_vm/com_fetch` 的承诺（如哈希） | 顶层 verifier/组合电路比较 | 需要顶层 statement 与 binding | 更复杂；接近 C3 递归方向（本轮不扩展 C3） |

本轮聚焦**模式 A**（共享同一 `com`），这也是 D1 中 C2 的原意。模式 B 需要顶层 statement，超出本轮承诺可行性审查范围（且不自动解决 C2 的 binding/hiding/随机性问题）。

---

## 4. 固定上游接口承载性（逐项）

| 需求 | 固定上游是否支持 | 证据 | 标签 |
| --- | --- | --- | --- |
| 公开输入通道 | 部分支持 | opcode 四列已公开（`InstructionFetch...cs:126-156`、`plonk.rs:143-161`）；但无 `com`/event_type 字段，需新增 | `VERIFIED`（通道在）+ `INFERRED`（字段需增） |
| 电路内承诺重算 | 不支持（作为承诺） | MiMC gadget 已用但作为哈希摘要（`ZkVmExecutor...cs:1009-1017`）；Pedersen gadget 存在但未接入（`plonk.rs` 无引用） | `VERIFIED`（现状）+ `CONSTRUCTED`（承诺用法） |
| `is_mem_op`/event_type 进入公开承诺 | 不支持 | `is_mem_op` 是私有输出（`:968-981`），Prove 忽略（原始 L164-165） | `VERIFIED`（缺失） |
| verifier 固定 vk | 当前 compat 路径未展示固定 VK；外部能力 `UNKNOWN` | `test_rng()` 现场 setup、setup/prove/verify 同函数（`plonk.rs:293-315`）为 `VERIFIED`；外部 verifier 是否持有固定 VK / 是否接受 prover 提供 VK 均无证据（`../aba-03-d1/leakage_and_security.md` D6 勘误）；“接受 prover 自提 VK 且无可信锚定 → 可能重选 setup”仅为 `CONDITIONAL INFERENCE` | `VERIFIED`（本地流程）+ `UNKNOWN`（外部）+ `CONDITIONAL INFERENCE`（条件风险） |
| P1-A 固定程序表 | 独立前置 | opcode 表已公开，但需 verifier 固定表/固定 vk（ABA-03-C2 §2）；P1-A 与 P2 承诺地址绑定互不替代 | `CONSTRUCTED`（前置） |
| B4 轨迹完整性 | 不支持 | 无事件计数/顺序/halt 约束（`p2_binding_semantics.md` B4） | `BLOCKED`（C2 不覆盖） |
| 宿主 throw / 哈希多重集代替约束 | 不可替代 | `ZkProgramExecutor.cs:302-332,551-583` 是宿主检查，不进 proof/verifier（ABA-03-C2 §3） | `VERIFIED`（区分） |

**结论**：固定上游的公开输入通道和 MiMC gadget 可复用，但"承诺作为共享隐藏承诺""event_type 进公开承诺""B4 完整性"都不具备。VK 项须按证据等级表述：当前 compat 路径展示的是本地 setup/prove/verify 流程；外部 verifier 的 VK 锚定方式未由现有证据确定，因此不能据此判断外部固定 VK 能力。P2 地址绑定不自动闭合 P1（P1-A 仍是独立前置），C2 不闭合 B4。

---

## 5. Phase 5：符号成本模型（不填数值）

**表达式**（T=总步数，含 step0；真实步 M，dummy 步 D=T−1−M）：

```
C_total(T) = T · (C_VM_commit + C_Fetch_commit + C_context + C_randomness)
             + M · C_real + D · C_dummy + C_verifier
```

口径：`T` 含 step0，但 step0 不执行 Fetch、不产生 Fetch 承诺事件；上式中的 `T·C_Fetch_commit` 是保守符号上界，实际 Fetch 承诺调用只对应 `step ≥ 1`。不得为 step0 虚构 Fetch proof。

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
- 共享承诺（模式 A）下不要把“两侧独立 `r`”当成推荐设计或成本节省：标准 Pedersen 同消息 + 同 `C` 强制 `r` 相同；若采用独立 `r`，必须改为独立承诺 + 额外关联证明，属 `FUTURE CANDIDATE` / `UNKNOWN`，成本未估；
- 双电路重复计算：MiMC 两电路各算一次承诺 → 约 `2T` 次承诺调用（符号）；Pedersen 群运算成本 `UNKNOWN`；
- MPC 通信轮次增加位置：若随机数需 MPC 联合生成/认证（当前 `BLOCKED`）、或 Pedersen 群元素需 MPC share（当前不支持）；
- 非原生域运算：Pedersen 群运算非 Fr 原生（`UNKNOWN`/`BLOCKED`），MiMC 全 Fr 原生（`VERIFIED`）；
- 多步总成本随 T 线性增长，具体系数全部 `UNKNOWN`。

本阶段**不提供任何具体门数、时间、字节数**。
