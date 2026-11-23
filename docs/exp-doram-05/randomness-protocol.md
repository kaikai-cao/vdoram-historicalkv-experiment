# randomness-protocol.md — `s_i` 认证随机源接口设计

> 2026-11-23 · 起点 `ca26127` · 冻结接口见 `README.md`。
> 标记：**VERIFIED** 原始论文/固定源码直接支持 · **CONSTRUCTED** 本轮设计的协议/接口 · **INFERRED** 由明确前提推导 · **CONDITIONAL** 依赖假设 · **UNKNOWN** 证据不足 · **BLOCKED** 现有接口不支持。
> 本轮只设计 `s_i`（承诺盲化随机量）的认证联合生成/消费/作废接口；**不重新研究 D2、跨步 verifier chain、完整 selective-abort 安全性**。

---

## 0. 冻结前提

```
s_i   = commitment_blinding_randomness   // 不属于 W_pre,i；秘密；不作 rho 种子
r_tape,i ∈ W_pre,i                       // 与 s_i 独立，不得复用
com_i = Com(Encode(ictx_i‖W_pre,i); s_i)
rho_k = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)
ictx_i = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)
```

目标：设计使恶意参与方**不能单方面选择、重采样或偏置** `s_i` 的接口；`s_i` 由协议生成而非 prover 自定。

---

## 1. C1：参与方与威胁模型（VERIFIED 基础 + CONSTRUCTED 适配）

- **生成方**：参与本次协作证明的全部 `n` 个 prover（即 MPC 参与方），**不是**单个 prover、不是外部 verifier。
- **敌手能力**：沿用 SPDZ / VDORAM 冻结模型 —— 活跃敌手可腐化至多 `n−1` 方（dishonest majority），至少 1 方诚实（VERIFIED：SPDZ ePrint 2011/535 摘要逐字「secure against an active adversary corrupting up to n−1 of the n players」）。
- **privacy 边界**：少于隐私阈值合谋时 `s_i` 对敌手隐藏；**全部参与方合谋时，`s_i` 的数值可被重构**（加法分享的必然结果），但此时 VDORAM 隐私本就不保证 —— 与冻结威胁模型一致，不额外声称。
- **randomness 边界与 privacy 边界不同**：即便全部合谋使 `s_i` 值可知，只要 MAC 检查与承诺-挑战顺序正确，仍可保证"无单方可在生成阶段单方面改写已被各方接受的随机量"这一**完整性**性质（诚实多数下由 MAC 保证）。全合谋时 MAC 完整性也失效 —— 明确记录，不外推。
- **不得混淆**："多方共同生成" ≠ "不可偏置"。是否不可偏置取决于具体机制（§2）。

---

## 2. C2：生成协议 —— 三条路线比较

### 路线 R1：XOR / 加法秘密分享随机量（每方本地采样）

```
每方 P_j 本地采样 s^(j) ← Fr；s = Σ_j s^(j)
```

- **偏置性**：最后提交的一方若知道他人贡献，可通过选择自己的 `s^(n)` 把 `s` 调到任意目标值（**偏置可行**）→ 不满足目标。
- **修复需求**：必须加"先承诺后揭示"或 MAC/预处理认证。单独 R1 **不合格**。

### 路线 R2：每方本地采样 + 对贡献承诺后再公开

```
1. P_j 采样 s^(j)，发布 Com(s^(j); r^(j))
2. 全部承诺固定后，公开 s^(j), r^(j)，s = Σ s^(j)
```

- **偏置性**：承诺固定后各方贡献已锁定，单方无法再改 —— 抗**预测性偏置**（INFERRED）。
- **剩余问题**：最后一方仍可**选择性 abort**（看到他人承诺后拒绝揭示）→ 偏置空间通过 abort 保留；这是 selective-abort 问题，本轮只标记接口关系，不扩展（见 §5）。
- **与 artifact 关系**：artifact 有 MiMC gadget，可用 `Com(v;r)=H(v‖r)` 搭承诺层，但该 hash-commitment 的 hiding 仅为启发式（`hiding-model.md` §5）→ 用于"锁定贡献"的 binding 足够，hiding 依赖启发式。CONDITIONAL。

### 路线 R3：复用 MPC 引擎已有的认证随机 share（推荐候选）

- **一手依据（VERIFIED）**：
  - SPDZ ePrint 2011/535 摘要：预处理阶段生成与函数/输入无关的随机量；online 阶段信息论安全，对抗 `n−1` 腐化。
  - ePrint 2025/789 §2.3 逐字：「SPDZ is an actively secure MPC protocol that tolerates up to n-1 out of n corrupted parties, based on **secret-shared MACs**」；预处理「generates multiplication triples and **other correlated randomness**」；MAC 检查「partial opening ... run a MAC check ... commits to σ_i ... aborts if chk ≠ 0」；批量检查用「coin-tossing protocol to obtain a random challenge」。
  - ePrint 2022/1302 逐字：SPDZ 预处理「samples `α ←$ F` as the global MAC key. The MAC of a value `x` is `γ(x) := α·x`」；「samples a uniformly random `r ←$ F` and outputs `⟨r⟩ = ([r], [γ(r)] = [α·r])`」—— 这正是**认证随机 share**原语；MAC 检查伪造成功概率「no greater than 1/p」。
  - VDORAM 协作 SNARK 实现（ePrint 2021/1530 §6 Fig.6，backend-facts §1 已核 VERIFIED）：`AuthShare { val: AddShare, mac: AddShare }`，即 artifact 类型层面**存在**认证 share 结构。
- **偏置性**：`r ←$ F` 由预处理功能 `F_PREP` 生成，不由任何一方输入决定；在至少一方诚实 + 底层预处理安全的前提下，**单方不能选择或预测 `r`**（INFERRED，基于 F_PREP  Ideal Functionality 语义）。这满足 C2 目标。
- **与 artifact 关系**：`AuthShare` 类型存在，但 **VDORAM artifact 未暴露可直接调用的 `F_PREP.Rand` / `AuthenticatedRandomShare` 接口**（backend-facts §6「认证随机源接口 无 → BLOCKED」继承）。→ 协议设计 CONSTRUCTED，执行接口 **BLOCKED**。

**三路线结论**：R1 不合格；R2 可作为无预处理时的后备（CONDITIONAL，abort 偏置残留）；**R3 为推荐候选**（协议层 CONSTRUCTED，artifact 接口 BLOCKED）。

---

## 3. C3：不可重采样、认证、失败作废、attempt 绑定

必须把四个概念分开（任务明确要求）：

| 概念 | 含义 | 由谁保证 | 本系统状态 |
| --- | --- | --- | --- |
| `s_i` 的**随机性** | 取值均匀、不可预测 | F_PREP.Rand（R3） | CONSTRUCTED / 执行 BLOCKED |
| `s_i` 的**认证** | 每方份额带 MAC，改动可被检出 | SPDZ IT-MAC `γ=α·s` | CONSTRUCTED / 执行 BLOCKED |
| `s_i` 的**不可重采样** | 生成后单方不能丢弃重取来改 `com_i`→改 `rho` | 一次性 ID + commit 固定 + MAC | CONSTRUCTED / 执行 BLOCKED |
| **失败作废** | abort / proof fail 后旧 `s_i` 不得原样再用 | `consume_once` 记录 + attempt 递增 | CONSTRUCTED / 执行 BLOCKED |
| **attempt_i 公开绑定** | 重试进入新实例域，避免同实例静默重采样 | `ictx_i` 含 `attempt_i`（冻结） | 规则 CONSTRUCTED / 实现 UNKNOWN |

**关于 abort（仅接口关系，不扩展完整研究）**：

- 参与方在看到 `rho`（依赖 `com_i`，依赖 `s_i`）后选择性 abort，再以新 `attempt_i` 重来，等价于"换一次随机量再挑战" —— **偏置空间仍然存在**。
- `attempt_i` 只保证"同实例不会被静默重采样"，**不消除**选择性 abort 泄露。固定长度 abort 也不足以消除（Correction-3/4 已记，本轮沿用）。
- grinding 定量：若 `s_i` 可重采样，`q_H` 次尝试下双挑战有效安全约 `q_H·2^{-168}`（域修正后，exp-doram-04 backend-facts §0；`q_H=2^128 ⇒ ≈2^{-40}`）。阻断此路径**必须**依赖 R3 的认证随机 + 一次性消费，而非仅靠 `attempt_i`。

---

## 4. C4：伪代码级接口（CONSTRUCTED，不要求实现）

### 4.1 生成接口

```
generate_authenticated_blinding(
    protocol_id,        // 域分离：协议标识
    circuit_id,         // 与本步电路绑定
    step_i,             // 步号
    old_root,           // C_i，绑定旧状态根
    attempt_i           // 公开尝试号
) -> AuthenticatedSharedRandomness<s_i>
```

**返回对象**（CONSTRUCTED 定义）：

```
AuthenticatedSharedRandomness<s_i> := {
    enc_s_i,             // 编码后的 s_i：k 个共享份额 [s_i]（加法/MPC share），k 由长度档位定
    auth_tag,            // 每份额的 IT-MAC 共享 [γ(s_i)]，γ = α·s_i，α 为全局秘密 MAC 键
    randomness_id,       // rid = H("BLIND"‖protocol_id‖circuit_id‖step_i‖old_root‖attempt_i‖nonce_commit)
    context_binding,     // 上述 ictx 六个字段的承诺摘要，确保 s_i 只用于本实例
    producer_set         // 生成方名单（用于审计，非秘密）
}
```

**步骤与逐项作用**（每步标明防住什么、依赖什么）：

| 步 | 动作 | 防住 | 依赖 | artifact 状态 |
| --- | --- | --- | --- | --- |
| 1 | 调 `F_PREP.Rand()` 取 `[r]` 与 `[γ(r)]`，重复 k 次得 `[s_i]` | 单方选择/预测 `s_i` | SPDZ 预处理安全 + ≥1 诚实方 | **BLOCKED**（无接口） |
| 2 | MAC 校验份额一致性 | 改动份额被检出 | IT-MAC（VERIFIED 机制） | BLOCKED（执行层） |
| 3 | 计算 `randomness_id`，写一次性台账（见消费接口） | 跨步/跨实例复用 | 台账实现 | BLOCKED |
| 4 | 用 `context_binding` 把 `s_i` 绑到 `ictx_i` | 换实例复用同一 `s_i` | 承诺层 | CONDITIONAL |
| 5 | 作为私有 witness 送入承诺电路 | — | AddPrivate 接口 VERIFIED | 规则 CONSTRUCTED |

### 4.2 一次性消费接口

```
consume_once(
    randomness_id,
    circuit_id,
    step_i,
    commitment_instance   // com_i 与 ictx_i 的摘要
) -> ok | abort
```

**语义**（CONSTRUCTED）：
- 台账中 `randomness_id` 必须**未消费**；消费后置为 spent，不可逆、不可原样重试。
- 校验 `circuit_id, step_i, commitment_instance` 与生成时 `context_binding` 一致，否则 abort。
- abort / 掉线 / proof fail：旧 `s_i` **作废**（spent），重试必须用新 `attempt_i` 重新 `generate_authenticated_blinding`。

### 4.3 MAC 与认证标签的可见性（任务明确要求）

- `[γ(s_i)]`（MAC 份额）是 **MPC 内部状态**，**不进入** SNARK 公开输入，也**不作为**电路 witness 除非协议显式需要；避免泄露全局 MAC 键信息。
- 进入电路的只有 `[s_i]` 的份额线值（且以 `AddPrivate` 私有 witness 形式）。
- **未闭合风险**：SPDZ MAC 检查是否覆盖"送进协作证明的每一个 witness 线值"，artifact 证据不足（Correction-4 / backend-facts 已记）→ **BLOCKED**。本接口只能保证 `s_i` 在**生成阶段**被认证；从认证份额到证明 witness 的传递仍是 D2 的一部分，本轮**不解决**。

---

## 5. 与现有组件的关系

| 组件 | 可复用？ | 证据 |
| --- | --- | --- |
| `AuthShare {val, mac}` 类型 | 类型可复用 | ePrint 2021/1530 §6 Fig.6 / backend-facts §1 VERIFIED |
| SPDZ IT-MAC 机制 | 协议层可复用 | ePrint 2011/535、2025/789、2022/1302 VERIFIED |
| `F_PREP.Rand` 认证随机 | 协议层可复用，**artifact 无接口** | ePrint 2022/1302 VERIFIED / artifact BLOCKED |
| MiMC `Com` 锁定贡献（R2） | 可搭，hiding 启发式 | gadget VERIFIED / hiding CONDITIONAL |
| 一次性消费台账 | 需新增 | 无现成组件 → BLOCKED |

---

## 6. 本页最终结论

| 门槛 | 状态 |
| --- | --- |
| 多方联合生成、单方不可选择/预测 `s_i` | CONSTRUCTED（R3 基于 SPDZ F_PREP）/ 执行 BLOCKED |
| MAC 认证覆盖份额 | CONSTRUCTED（IT-MAC 机制 VERIFIED）/ artifact 接口 BLOCKED |
| 不可重采样 + 一次性作废 | CONSTRUCTED（rid 台账 + attempt）/ 实现 BLOCKED |
| MAC 传到证明 witness 的覆盖 | **BLOCKED**（属 D2，本轮不解决） |
| 选择性 abort 偏置 | **UNKNOWN/BLOCKED**（仅记接口关系，`attempt_i` 不消除） |
| 全体合谋 | 隐私与 MAC 完整性均失效，符合冻结威胁模型，不外推 |

**核心判断**：认证随机源在**协议层可以正确设计**（R3），但 VDORAM artifact 既不暴露 `F_PREP.Rand` 接口，也缺一次性消费台账，更没有把认证份额衔接到协作证明 witness 的通道。因此这一项在"当前系统能否落地"的意义上是 **BLOCKED**，不是 CONSTRUCTED 已实现。这与任务令"不得把它描述成已在 artifact 中实现"一致。
