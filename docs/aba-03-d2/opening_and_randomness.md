# ABA-03-D2 / Phase 2：Opening 与随机数生命周期

> 固定上游 `10c90d35…`；起点 `b8a907b8…`。只读评估，不实现。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`（定义见 `commitment_candidates.md`）。
>
> 核心纪律：**承诺方案的密码学 binding ≠ 随机数的不可预测性 ≠ 随机数的认证性 ≠ 随机数的防重放 ≠ prover 能否选择承诺参数/setup**。以下逐项拆开。

---

## 0. 必须区分的五类性质

| 类别 | 性质 | 含义 | 当前状态 |
| --- | --- | --- | --- |
| A | 随机数均匀性与保密性 | prover/宿主本地生成随机数是承诺者的正常做法，**不自动破坏 hiding**；条件是满足方案要求的分布，且观察者不可获得 `r` | 宿主 `FieldFactory.Random()` 生成 `enc_key` 是 `VERIFIED`（做法）；其作为 opening `r` 的分布/保密性 `UNKNOWN` |
| B | 承诺 binding | 同一承诺不应有两份不同消息的 opening；Pedersen 是 DL 假设下的**计算 binding**，不是 perfect binding | MiMC `UNKNOWN`（无归约）；Pedersen `INFERRED`（DL + 生成器信任 `UNKNOWN`）。prover 能选 `r` **不等于**能为同一承诺伪造两份不同 opening |
| C | 随机数复用 | 复用可能造成承诺链接、消息关系泄露或其他方案相关风险 | `INFERRED`（方案相关）；不得写成所有复用都直接破坏 binding |
| D | MPC 随机数认证 | 多方参与时，参与方不能篡改 share 或 `r` 而不被发现 | 当前 additive-only、无 MAC、无可用 Beaver triple 路径 → 主动安全随机数认证 `BLOCKED`；不得据此推断所有 prover 本地随机数生成都不安全 |
| E | 防重放 | 随机数本身不是防重放机制；需可信 `execution_id`、`step`、program/context 绑定与 verifier 检查 | 无机制 → `UNKNOWN` |

另有独立事项：prover 能否自行选生成器或重新 setup，与“prover 本地选 `r`”不是同一问题。当前 compat 路径现场 `test_rng()` 生成 vk（`plonk.rs:302-304`）为 `VERIFIED`；外部 verifier 的 VK 锚定方式为 `UNKNOWN`（见 `../aba-03-d1/leakage_and_security.md` D6 勘误）。

---

## 1. 两个子电路的 opening randomness 关系（问题 1-4）

设 VM 侧 `(addr_vm, r_vm)`、Fetch 侧 `(addr_fetch, r_fetch)`，公开承诺 `com_vm`、`com_fetch`，verifier 要求 `com_vm = com_fetch`。

### Q1. `r_vm` 与 `r_fetch` 是否需要相等？

- **标准 Pedersen 下，同一承诺且同一消息时必然相等（mod q）**：设 `C_vm = C_fetch = C`、`m_vm = m_fetch = m`，则 `mG + r_vm H = mG + r_fetch H`，即 `(r_vm − r_fetch)H = 0`。在群阶 `q` 为素数、生成元非零且两侧正确约束 opening 的条件下，`H` 的阶为 `q`，故 `r_vm = r_fetch mod q`。这是群上的代数结果，不是额外安全假设；因此不能再说“不同 `r` 不影响地址一致性推论”或“同一承诺下允许两侧任意使用不同随机数”。
- 若 `m_vm != m_fetch` 却 `C_vm = C_fetch`，则 `(m_vm − m_fetch)G = (r_fetch − r_vm)H`，两份 opening 给出 `G/H` 的离散对数关系；DL 困难且生成元关系未知时不可行（见 Q3）。
- 因此，“相同承诺推出相同地址”的完整前提是：两侧各自正确约束自己的 opening、使用同一个 `C`、且 binding 成立；在 Pedersen 下同一消息还会代数地强制两侧 `r` 相同。**MiMC 路径依赖未证明的 binding → `UNKNOWN`；Pedersen 计算 binding → `INFERRED`。**

### Q2. 两边能否分别持有不同 opening randomness？

- **在同一 Pedersen 承诺 + 同一消息下不能**：由 Q1 的代数关系，`r_vm = r_fetch mod q`，这不是可自由选择的选项，也不是“推荐设计”。
- 若改为两侧使用**独立随机数与独立承诺**（`C_vm = Commit(m; r_vm)`、`C_fetch = Commit(m; r_fetch)`），各自 hiding 可以使用不同 `r`，但 verifier 不能再靠 `C_vm == C_fetch` 比较；必须另行设计证明两个隐藏地址相等的关系，并单独分析其 soundness、hiding 与 verifier 接口 → `UNKNOWN` / `FUTURE CANDIDATE`，本轮不设计、不声称已解决。
- 随机数复用带来的链接风险单独在 Q8 分析，不能作为“同一 Pedersen 承诺下任意选不同 `r`”的理由。实现上，两个电路的 `r` 都必须是各自可约束的 witness，且都不能被 prover 事后重采样（见 §2）。

### Q3. 在什么 binding 假设下，相同承诺推出相同地址？

- **Pedersen，情况一（两侧地址相同、承诺相同）**：`m_vm = m_fetch = m` 且 `C_vm = C_fetch` 时，`mG + r_vm H = mG + r_fetch H` ⇒ `(r_vm − r_fetch)H = 0`。群阶 `q` 为素数、`H` 非单位元 ⇒ `r_vm = r_fetch mod q`。这是代数结果，不是独立随机数可任意选择的许可。
- **Pedersen，情况二（两侧地址不同、承诺相同）**：`C = m_vm G + r_vm H = m_fetch G + r_fetch H` 且 `m_vm != m_fetch` 时，`(m_vm − m_fetch)G = (r_fetch − r_vm)H`，由此可导出 `G/H` 的离散对数关系；DL 困难且生成元关系未知时不能有效构造。因此是 **computational binding**，不是 perfect binding。
- 综上，**在两电路各自正确约束 opening、使用同一 `C` 且 binding 成立**时推出 `addr_vm = addr_fetch`；同消息下的 `r` 相等不需要额外断言，不同消息下的双重 opening 由 binding 排除。`INFERRED`。
- **MiMC 哈希**：需把 `H` 建模为抗碰撞/随机预言机，且 `com = H(context‖addr‖r)` 的编码无歧义；抗碰撞意味着不能找到两个不同 `(addr,r)` 同像。源码无此归约 → `UNKNOWN`。
- 关键：**相同承诺 + 弱/无 binding 不能推出相同地址**。若 `H` 可被构造碰撞，攻击者可令 `(addr_vm,r_vm) ≠ (addr_fetch,r_fetch)` 但 `com` 相同，verifier 的相等检查通过而地址不等。

### Q4. 同一 Pedersen 承诺下是否需要额外公开 r 或单独添加跨电路 r 相等约束？

- **不需要**：在两侧各自正确约束 `C_side = m_side G + r_side H` 且公开 `C_vm = C_fetch` 的前提下，同消息时 `r_vm = r_fetch mod q` 是 Q1 的代数结果；不同消息时若 `C` 相同则给出 DL 关系，由计算 binding 排除。把 `r` 提升为公开输入会牺牲 hiding，额外跨电路 `r` 相等约束在同一 Pedersen 承诺方案中没有必要。
- 但这**不等于**当前接口已闭合：两侧必须分别正确约束自己的 opening；Pedersen 还需域/share 适配与可信生成器，仍为 `UNKNOWN` / `BLOCKED`（见 `commitment_candidates.md`）。
- 若选择“独立随机数 + 独立承诺 + 额外关联证明”，则属于 `FUTURE CANDIDATE` / `UNKNOWN`，需单独分析 soundness、hiding 与 verifier 接口，本轮不设计。

**结论**：在同一 Pedersen 承诺下不能把“两侧独立 `r`”当作推荐设计；同一消息时 `r` 相等是素数阶群上的代数结果。相同承诺推出相同地址仍以“两电路各自正确约束 opening + 使用同一承诺 + binding 成立”为前提，不是无条件数学等式。MiMC binding 未证，Pedersen 虽在 DL 假设下有计算 binding 但接口不兼容（见 `commitment_candidates.md`）；独立随机数方案只能作为 `FUTURE CANDIDATE`，需另行设计与分析。

---

## 2. 随机数主体、攻击面与重放（Q5-Q9）

### Q5. 谁可以产生随机数，谁能观察随机数？

- **prover/宿主本地产生**：承诺者自己选 `r` 是承诺方案的正常做法，**不自动破坏 hiding**；前提是 `r` 满足方案要求的分布（如均匀）且观察者不可获得。当前 `enc_key = FieldFactory.Random()` 是宿主进程现场生成、作为私有输入注入（`ZkProgramExecutor.cs:61,159,288,540`）：`VERIFIED`（做法）；其作为 opening `r` 的分布/保密性 `UNKNOWN`。
- **verifier 提供**：不可预测性由 verifier 保证；prover 见到 `r` 不必然破坏 hiding（prover 本就知道地址），但需定义传输与隐私语义。当前无此接口 → `UNKNOWN`。
- **MPC 联合生成**：理想情况下参与方共同产生不可预测、认证的 `r`；当前 additive-only、无 MAC、无可用 Beaver triple → `BLOCKED`。
- **观察者可见的值**：公开承诺 `com` 按设计不应泄露 `r`（Pedersen perfect hiding 条件于 `r` 均匀且保密；MiMC 条件于哈希假设）。日志、宿主摘要检查、JSON witness/share 的可见性沿用 §3 的证据等级，不在此处升级。

### Q6. 谁能篡改 MPC share？

- 若承诺生成走多方 MPC，能提交或替换 share 的一方可篡改 `r` 或 opening 值；需要 MAC/SPDZ 或可信方固定才能检测。当前 CompatCircuit → PLONK 使用 `honest_but_curious::MpcField`（additive），`SpdzFieldShare::mac()` 走 cheat、`ALLOW_CHEATING=true`、序列化 `unimplemented!()`（`exp-doram-06` B.1-B.3）→ 当前架构下主动安全随机数认证 `BLOCKED`。
- 该阻断针对**现有 MPC 路径中的认证随机数**，**不得**据此推断所有 prover 本地随机数生成都不安全；也不等于“攻击者已能伪造承诺”。
- 若改用 verifier 固定 `r`（不经 MPC 认证），可绕开此阻断，但引入 `r` 的传递/隐私设计问题 → `UNKNOWN`。

### Q7. 谁能重放承诺？

- 能重用同一 `com`（及其公开 statement）的一方即可跨 step/程序/执行重放；是否成立依赖公开 statement 是否含可信 `execution_id`、`step`、`program_id/context` 与 verifier 检查（`context_and_replay.md`）。当前四字段无 verifier 可信锚定 → `UNKNOWN`。
- 随机数是否随机**不是**防重放机制：换一个新 `r` 不阻止旧 `com` 被重放，`r` 复用也不自动等于重放成功；需 context 绑定与 verifier 检查共同闭合。
- 当前 `enc_key` 每执行生成一次（`ZkProgramExecutor.cs:61`），但未证明其作为 `r` 的实例唯一性或跨执行不可复用性 → `VERIFIED`（每执行一值）+ `UNKNOWN`（承诺适配）。

### Q8. 谁能为同一承诺找到不同 opening？

- 这是承诺 **binding** 问题，与“谁能产生/选择 `r`”分开。prover 能自行选 `r` 只说明它控制生成，**不代表**能为同一 `com` 给出两个不同消息的 opening。
- 若 `mG + rH = m'G + r'H` 且 `m != m'`，则 `(m−m')G = (r'−r)H` 直接给出生成元间的 DL 关系（非平凡，因为 `m−m' != 0`）。因此 Pedersen 的 binding 依赖离散对数困难，是 **computational binding**，不是 perfect binding；生成器可验证固定/无陷门仍 `UNKNOWN`。MiMC 侧无公开归约 → `UNKNOWN`。
- 随机数复用（不同承诺/不同上下文重复使用同一 `r`）可能造成承诺链接或消息关系泄露（`INFERRED`，方案相关），这是**复用风险**；它与“同一承诺下两份不同消息 opening”的 **binding 问题**是两类风险，**不得**混写，也**不得**写成所有复用都直接破坏 binding。Pedersen 同承诺同消息会代数强制 `r` 相同（Q1），不能把“不同 `r` 指向同一 `C`”当作独立设计自由度。
- 跨电路推出相同地址需：两电路各自正确约束 opening + 使用同一承诺 + binding 成立；不是无条件数学等式（见 Q1/Q3、`circuit_interface.md`）。

### Q9. 中止、重启与重新初始化时如何处理随机数？

- 执行中止后若沿用旧 `r`，可能造成承诺链接或重放风险；需要明确“换全新 `r`、重新绑定 `execution_id/step/context`、verifier 检查”的状态机。当前无文档化协议 → `UNKNOWN`。
- 当前 `enc_key` 随执行实例产生；重启是否重新 `Random()` 属于推测，不作为结论。threat model 中 prover 重新 setup 只是条件性推论（`../aba-03-d1/leakage_and_security.md` D6 勘误），不能假设 prover 被绑定于固定 `r` 来源 → `UNKNOWN`。

---

## 3. 随机数泄露通道（沿用原证据等级）

### Q10. 随机数泄露通道

| 通道 | 是否会泄露 `r` | 证据 |
| --- | --- | --- |
| 日志/调试输出 | 未发现记录 `in_enc_key` 明文的日志；但需审计全量日志配置 | `UNKNOWN`（未穷尽） |
| 宿主检查 | `out_hash_enc_key` 是哈希摘要（`ZkProgramExecutor.cs:176-181`），不直接泄露明值 | `INFERRED` |
| JSON witness | `in_enc_key` 作为 `AddPrivate` 注入（`ZkProgramExecutor.cs:159,288,540`）；`is_secret_share=true` 时 JSON 存 share 字符串（`plonk.rs:97-110,203-218`），非明文但 share 持有方可见 | `VERIFIED` |
| `com` 本身 | 若 hiding 成立，`com` 不应泄露 `r`（Pedersen perfect hiding 条件于均匀且保密的 `r`；MiMC 条件于哈希假设） | `INFERRED` |

随机数若通过任一通道泄露给 verifier/观察者，小地址域下 hiding 立即失效。

---

## 4. 生命周期状态机（候选，非已实现）

```
生成（prover/宿主本地生成属正常起点；需满足分布与保密性，或在可用时由 verifier/MPC 联合生成）
  → 绑定（写进 context：execution_id、step、program_id；防重放靠绑定与 verifier 检查，不靠 r 的随机性）
  → 一次性使用（每承诺新 r；复用风险按方案分别分析，不等同于 binding 失效）
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

1. **标准 Pedersen 同一承诺、同一消息下 `r_vm = r_fetch mod q`**（素数阶群 + 非单位元生成元上的代数结果）；不能推荐“两侧独立 `r` 指向同一 `C`”。相同承诺推出相同地址仍以“两电路各自正确约束 opening + 使用同一承诺 + binding 成立”为前提，不是无条件数学等式。MiMC binding 未证 → `UNKNOWN`；Pedersen 是 DL 假设下的计算 binding → `INFERRED`，且生成器信任 `UNKNOWN`。
2. **当前 MPC 路径中的主动安全随机数认证是硬阻断**：CompatCircuit → PLONK 是 additive-only、无 MAC、无真实 Beaver/SPDZ 通路（`exp-doram-06` B.1-B.3）；这只说明现有架构无法认证 share，不等于所有 prover 本地随机数生成都不安全。
3. **随机数分布/保密性、防重放、中止重启处理均未闭合**；当前 `enc_key` 只覆盖“每执行一值”，不足以充当安全 opening randomness。防重放需可信 `execution_id`、`step`、program/context 绑定与 verifier 检查，不能靠 `r` 的随机性解决。
4. 若选择 Pedersen（perfect hiding 优势），随机数走群标量域且需新 share/群运算支持，`BLOCKED`；若选择 MiMC（域兼容），binding 与 hiding 都系于未证假设与随机数质量。Pedersen 的理论性质正确不等于已接入当前 PLONK/MPC 路径；若要用独立 `r`，必须改为独立承诺 + 额外关联证明，属 `FUTURE CANDIDATE` / `UNKNOWN`，本轮不设计。
5. 这是阻止进入原型的核心未知项之一（见 `decision.md`）。
