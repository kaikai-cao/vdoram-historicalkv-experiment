# ABA-03-D2 / Phase 2：Opening 与随机数生命周期

> 固定上游 `10c90d35…`；起点 `b8a907b8…`。只读评估，不实现。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`（定义见 `commitment_candidates.md`）。
>
> 核心纪律：**承诺方案的密码学 binding ≠ 随机数的不可预测性 ≠ 随机数的认证性 ≠ 随机数的防重放 ≠ prover 能否选择承诺参数/setup**。以下逐项拆开。

---

## 0. 必须区分的五类性质

| 性质 | 含义 | 当前状态 |
| --- | --- | --- |
| 密码学 binding | 不同 `(addr,r)` 难以给出同一 `com`（或反之） | MiMC `UNKNOWN`（无归约）；Pedersen `INFERRED`（DL 假设，生成器信任 `UNKNOWN`） |
| 随机数不可预测性 | `r` 在承诺前不可被 verifier 之外预测（hiding 所需） | 取决于产生者；现状 `UNKNOWN`（见 §3） |
| 随机数认证性 | 参与方不能篡改 `r` 而不被发现（MAC / SPDZ） | 当前 CompatCircuit 路径 additive-only 无 MAC → `BLOCKED`（`exp-doram-06` B.1/B.4） |
| 随机数防重放 | `r` 一次一用、绑定实例，不能跨步/跨执行复用 | 无机制 → `UNKNOWN` |
| prover 选择参数/setup | prover 能否自行选生成器或重新 setup | 现场 `test_rng()` 生成 vk（`plonk.rs:302-304`）`VERIFIED`；承诺生成器固定机制 `UNKNOWN` |

---

## 1. 两个子电路的 opening randomness 关系（问题 1-4）

设 VM 侧 `(addr_vm, r_vm)`、Fetch 侧 `(addr_fetch, r_fetch)`，公开承诺 `com_vm`、`com_fetch`，verifier 要求 `com_vm = com_fetch`。

### Q1. `r_vm` 与 `r_fetch` 是否需要相等？

- **不需要相等**，前提是承诺具备 binding：若 `com_vm = com_fetch`，且两侧各自**正确开承诺**（即各自电路内约束 `Commit(context, addr_side; r_side) = com_side`），则 binding 保证 `(addr_vm, r_vm) = (addr_fetch, r_fetch)`，从而 `addr_vm = addr_fetch`。
- 这是 binding 的定义性推论，与 `r` 是否相同无关。**MiMC 路径此推论依赖未证明的 binding → `UNKNOWN`；Pedersen 路径在 DL 假设成立时可推出 → `INFERRED`。**

### Q2. 两边能否分别持有不同 opening randomness？

- 可以，只要 binding 成立且两侧各自证明自己开的是同一个 `com`。不同 `r` 反而避免「同一随机数跨电路复用」带来的链接风险。**`CONSTRUCTED`（设计候选）**。
- 但实现上：两个电路的 `r` 都必须是各自可约束的 witness，且都不能被 prover 事后重采样（见 §2）。

### Q3. 在什么 binding 假设下，相同承诺推出相同地址（即使 r 不同）？

- **Pedersen**：DL 假设 + `G/H` 无已知关系 → 完美 binding → 相同 `C` 唯一确定 `(addr, r)` → `addr_vm = addr_fetch`。`INFERRED`。
- **MiMC 哈希**：需把 `H` 建模为抗碰撞/随机预言机，且 `com = H(context‖addr‖r)` 的编码无歧义；抗碰撞意味着不能找到两个不同 `(addr,r)` 同像。源码无此归约 → `UNKNOWN`。
- 关键：**相同承诺 + 弱/无 binding 不能推出相同地址**。若 `H` 可被构造碰撞，攻击者可令 `(addr_vm,r_vm) ≠ (addr_fetch,r_fetch)` 但 `com` 相同，verifier 的相等检查通过而地址不等。

### Q4. 如果随机数必须相同，如何证明两边用的是同一个 r？

- 若设计改为强制 `r_vm = r_fetch = r`（例如为简化 opening），则必须让 verifier 能核对这一点：把 `r` 作为**公开承诺的一部分**（例如 `com_r = Commit(r; r′)` 公开、两电路都绑定 `com_r`），或把 `r` 提升为公开输入（牺牲 `r` 的隐私，进而牺牲 hiding）。
- 当前上游无任何跨电路共享随机值机制；`enc_key` 只在单执行内部逐电路宿主比对（`ZkProgramExecutor.cs:176-181,302-308,551-554`），不是共享公开承诺。`CONSTRUCTED` + `UNKNOWN`。

**结论**：推荐设计应让 `r_vm ≠ r_fetch`（各自持有），依赖 binding 推出地址相等；但这把全部安全性压在 binding 上，而 MiMC binding 未证、Pedersen 接口不兼容（见 `commitment_candidates.md`）。

---

## 2. 随机数攻击面（问题 5-7）

### Q5. 随机数由谁产生？

候选产生者及现状：

| 产生者 | 性质 | 当前证据 |
| --- | --- | --- |
| prover 本地 | 可自由选/重采样 → hiding 与防重放失效，可枚举 `addr` 后重选 `r` 命中目标 `com` | 现状若无约束即等同此类，`UNKNOWN` |
| verifier 提供 | 不可预测性由 verifier 保证；但需把 `r` 交给 prover 做 witness，泄露 `r` 给 prover 不破坏 hiding（prover 本就知道地址） | 当前无此接口，`UNKNOWN` |
| MPC 协议联合生成 | 理想：参与方共同产生不可预测、认证、不可重放的 `r`；需 MAC + 一次性 ID | 当前 additive-only 无 MAC、无 Beaver/preprocessing、`DummyFieldTripleSource` 常量三元组（`exp-doram-06` B.1/B.3）→ `BLOCKED` |
| 宿主 `FieldFactory.Random()` | 当前 `enc_key` 的做法（`ZkProgramExecutor.cs:61`）：进程内伪随机，作为私有输入注入 | `VERIFIED`（做法）；用于承诺 openings 的适配 `UNKNOWN` |

### Q6. prover 可自由选择/重采样随机数会造成什么攻击？

- **枚举 + 重采样**：小地址域下 prover 枚举 `addr`，对每个候选计算所需 `r` 使承诺匹配目标 — 若 `r` 可由 prover 选且 binding 弱，等价于伪造 opening。
- **事后拟合**：prover 先看到 `com` 再选 `r`，破坏 hiding 的不可预测前提。
- **重放**：同一 `r`+`addr` 复用产生相同 `com`，可跨 step/程序/执行拼接。
- 现状：无机制阻止这些；`CONSTRUCTED`（攻击面分析）+ `UNKNOWN`（是否实际可利用在本轮不验证）。

### Q7. 随机数是否需要 MPC MAC 认证？

- **需要**：若承诺安全性要求 prover 不能篡改/重采样 `r`，且证明生成在多 MPC 参与方间进行，则 `r` 必须是认证共享（SPDZ MAC）或由可信方固定。
- **当前不具备**：CompatCircuit → PLONK 静态使用 `honest_but_curious::MpcField`（additive），`SpdzFieldShare` 走 `mac()` cheat、`ALLOW_CHEATING=true`、序列化 `unimplemented!()`（`exp-doram-06` B.1-B.3）→ `BLOCKED`。
- 若改用 verifier 固定 `r`（不经 MPC 认证），可绕开此阻断，但引入 verifier 与 prover 的 `r` 传递/隐私设计问题（`UNKNOWN`）。

**结论**：随机数认证性在现有 MPC 路径下是**明确阻断项**；这是 C2 能否落地的关键分歧点。

---

## 3. 生命周期其余问题（问题 8-10）

### Q8. 一次性使用 / 防跨执行复用

- 需求：`r` 必须一次一用，并绑定 `execution_id`（见 `context_and_replay.md`）；否则同一承诺可跨执行重放。
- 现状：`enc_key` 是**每次执行**生成（`ZkProgramExecutor.cs:61`，一次执行一个值），但未证明其作为 opening `r` 的域语义、唯一性保证或跨执行不可复用性。`VERIFIED`（每执行一值）+ `UNKNOWN`（承诺适配）。

### Q9. 生成失败、中止、重启与重新初始化

- 若 `r` 生成后执行中止，重启时必须换全新 `r`，否则重放；需要明确状态机。
- 当前 `enc_key` 随执行实例产生，重启会重新 `Random()`（推测），但**无文档化的承诺随机数重置协议**；且 threat model 中「prover 重新 setup」是条件性推论（`leakage_and_security.md` D6 勘误 C1），不能假设 prover 被绑定于固定 `r` 来源 → `UNKNOWN`。

### Q10. 随机数泄露通道

| 通道 | 是否会泄露 `r` | 证据 |
| --- | --- | --- |
| 日志/调试输出 | 未发现记录 `in_enc_key` 明文的日志；但需审计全量日志配置 | `UNKNOWN`（未穷尽） |
| 宿主检查 | `out_hash_enc_key` 是哈希摘要（`ZkProgramExecutor.cs:176-181`），不直接泄露明值 | `INFERRED` |
| JSON witness | `in_enc_key` 作为 `AddPrivate` 注入（`ZkProgramExecutor.cs:159,288,540`）；`is_secret_share=true` 时 JSON 存 share 字符串（`plonk.rs:97-110,203-218`），非明文但 share 持有方可见 | `VERIFIED` |
| `com` 本身 | 若 hiding 成立，`com` 不应泄露 `r`（Pedersen 信息论；MiMC 条件于哈希假设） | `INFERRED` |

随机数若通过任一通道泄露给 verifier/观察者，小地址域下 hiding 立即失效。

---

## 4. 生命周期状态机（候选，非已实现）

```
生成（verifier 或 MPC 联合，非 prover 自由选）
  → 绑定（写进 context：execution_id、step、program_id）
  → 一次性使用（每承诺新 r，跨执行不复用）
  → 认证（若经 MPC：需 MAC/SPDZ；当前 BLOCKED）
  → 销毁/不复用（中止重启必须重新生成）
```

每一步在固定 commit 中的可用性：

| 步骤 | 当前可用性 | 标签 |
| --- | --- | --- |
| 生成 | 宿主 `Random()` 存在但非认证随机；MPC 认证随机不可用 | `VERIFIED`/`BLOCKED` |
| 绑定 context | 无现成机制 | `UNKNOWN` |
| 一次性使用 | 无机制保证 | `UNKNOWN` |
| 认证 | additive-only 无 MAC | `BLOCKED` |
| 中止重启处理 | 无协议 | `UNKNOWN` |

---

## 5. 本阶段结论

1. **`r_vm` 与 `r_fetch` 不必相等**，相同承诺推出相同地址依赖**承诺 binding**，与 `r` 是否相同无关；MiMC binding 未证 → `UNKNOWN`，Pedersen binding `INFERRED`（DL + 生成器信任）。
2. **随机数认证性是硬阻断**：现有 CompatCircuit → PLONK 是 additive-only、无 MAC、无真实 Beaver/SPDZ 通路（`exp-doram-06` B.1-B.3），无法保证 prover 不重采样/篡改 `r`。
3. **随机数不可预测性、防重放、中止重启处理均未闭合**；当前 `enc_key` 做法只覆盖"每执行一值"，不足以充当安全 opening randomness。
4. 若选择 Pedersen（信息论 hiding 优势），随机数走群标量域且需新 share/群运算支持，`BLOCKED`；若选择 MiMC（域兼容），binding 与 hiding 都系于未证假设与随机数质量。
5. 这是阻止进入原型的核心未知项之一（见 `decision.md`）。
