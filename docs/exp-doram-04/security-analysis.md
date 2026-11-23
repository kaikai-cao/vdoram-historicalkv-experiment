# security-analysis.md — L2 承诺构造的安全边界

> 2026-11-23 · 起点 `2556ece` · 冻结接口见 `README.md`，候选定义见 `candidate-analysis.md`。
> 标记：**VERIFIED** 一手证据 · **CONSTRUCTED** 本轮规则 · **INFERRED** 推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 接口缺失。
> 本轮只分析**承诺构造**；不重做 D2、跨步 verifier chain、选择性 abort、MPC 隐私证明。

---

## 0. 冻结接口（逐字沿用 Correction-4，不重定义）

```
ictx_i   = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)
W_pre,i  = (old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i)   // 8 字段
s_i      = commitment_blinding_randomness        // ∉ W_pre,i
com_i    = Com(Encode(ictx_i ‖ W_pre,i); s_i)
rho_k    = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)
```

七阶段顺序不变；`s_i` 不公开、不进 ORAM 状态、不作 ρ 种子；`r_tape,i ∈ W_pre,i` 被 `com_i` 覆盖。

---

## 1. 用户点名的七个安全边界问题

### 1.1 恶意 prover 能否生成两个不同消息、同一个承诺？（binding）

- ** Pedersen（B1）**：在 DL（`log_g h` 未知）/ DDH 假设下**不能**；这是标准 computational binding（Pedersen 1991；Liskov LNCS 3788 §4.3；Jokumsen 2023 Def.1，均 VERIFIED）。但 `x=Encode(...)` 需先经 `d=CRH(x)` 压缩，binding 实为 `DL ∧ CRH` 的合取假设；`CRH` 碰撞会破坏 → 只要 `CRH` 覆盖 8 字段且抗碰撞则成立（CONSTRUCTED 规则）。
- **Hash 承诺（B2）**：binding 来自 MiMC 抗碰撞；单挑战 birthday bound `≤q²/2^{2κ}`（ePrint 2021/478 §2）。但 MiMC 安全裕度 UNKNOWN（backend-facts §3），故 binding 的**具体安全位** UNKNOWN，只有“依赖 CRH”的形式保证。
- **状态**：B1 = **CONDITIONAL（假设清晰）**；B2 = **UNKNOWN（裕度未证）**。

### 1.2 恶意 prover 能否通过重采样 `s_i` 影响挑战？（grinding）

- 依赖链（Correction-4 §5）：`s_i` 可重采样 ⇒ 改 `com_i` ⇒ 改 `ρ_k` ⇒ 筛选有利挑战。
- 本轮域修正后：`enc<2^169`、`|F|≈2^253`，单挑战 `≈2^-84`、双挑战 `≈2^-168`；若 `q_H` 次 grind，`q_H·2^-168`（`q_H=2^128` ⇒ `≈2^-40`）**不满足 128-bit** → 需 `k≥4` 或不可 grind 的认证随机带。
- 防护规则（CONSTRUCTED）：`s_i` MPC 联合生成 + MAC + 不可重采样 + 每步独立 + `attempt_i` 域分离 + 失败作废。
- 执行层：artifact 无认证随机带接口（Correction-2 §E5 继承）→ **BLOCKED**。
- **状态**：规则 CONSTRUCTED，执行 **BLOCKED**； grinding 在固定 artifact 上**未被消除**。

### 1.3 承诺是否泄露低熵 ORAM witness？（hiding）

- **B1 Pedersen**：`s_i` 域均匀 ⇒ commitment 与消息**统计独立**（perfect hiding，VERIFIED）；低熵 `W_pre` 被完美遮蔽。唯一泄露来自 `d=CRH(x)` 若为公开输入——但 `d` 只是一个压缩摘要，其本身是否泄露 `x` 取决于 `CRH` 单向性；标准做法是把 `d` 作为承诺消息的一部分而非公开。**正确构造下不泄露**。
- **B2 hash**：`H(x‖s_i)` 在 ROM 下 hiding，但**需 `s_i` 熵足够**。本轮计算：`|Y|≈2^253` 套 Lemma 17 ⇒ `ℓ_u ≥ 2024 bit ≈ 8 个 Fr 元素`（INFERRED，ePrint 2015/361 Lemma 17）。若只用单个 253-bit `s_i`，canonical commitment 的统计 hiding **无保证**；MiMC 当 RO 是启发式假设（ePrint 2024/1074 明示）。
- **状态**：B1 hiding 依据强（VERIFIED 假设）；B2 hiding **CONDITIONAL**（ROM + 熵长度 + 启发式）。

### 1.4 承诺消息是否绑定 `attempt_i`？

- 冻结 `ictx_i` 含 `attempt_i`，且 `com_i = Com(Encode(ictx_i ‖ W_pre,i); s_i)` ⇒ `attempt_i` **在消息编码内**（CONSTRUCTED，沿用 Correction-4）。
- 作用：abort 后同一步重试会用新 `attempt_i` → 新 `ictx_i` → 新 `com_i` → 新 ρ，防止“同一公开实例静默重采样”。
- 实现前提：`Encode` 必须真的把 `ictx_i` 全部 6 个字段（含 `attempt_i` 与 `C_i`）纳入 hash 输入；否则绑定失效 → 实现 **UNKNOWN/BLOCKED**。
- **状态**：规则 CONSTRUCTED，实现 UNKNOWN。

### 1.5 承诺是否绑定旧状态根 `C_i`？

- `C_i ∈ ictx_i`（冻结定义），故同上：规则层绑定（CONSTRUCTED）。
- 但 `C_i` 是 `Fr` 域元素（Merkle root 编码为一个 hash 输出）；`Encode` 需把它纳入 CRH/MiMC 输入。**后端支持**：`C_i` 已作公开输入（`AddPublic(in_global_step_counter,...)` 类同），可暴露（VERIFIED 接口）。
- **状态**：规则 CONSTRUCTED，实现 UNKNOWN。

### 1.6 承诺是否覆盖全部 8 个 `W_pre,i` 字段？

- 冻结要求：`com_i` 覆盖 8 字段（CONSTRUCTED 规则）。
- 落地风险（两类承诺共有）：
  - **B2**：`x=Encode(...)` 是一次（或多次）MiMC 链式 hash；只要 `Encode` 吸收全部 8 字段即可。若 `Encode` 分块 hash 时遗漏某字段（尤其 `eviction_aux`、`r_tape,i`、`nonce`），承诺出现“承诺后换字段”漏洞 → 必须固定编码并审计。
  - **B1**：先 `d=CRH(x)`；`CRH` 同样必须吸收全部 8 字段；否则 binding 只覆盖 `d` 而不覆盖被省略字段。
- `r_tape,i` 作为第 8 字段尤其关键：它决定 `nonce'=nonce+r_t`，若不进承诺，prover 可在承诺后换随机带 → 状态更新被篡改而 `com_i` 不变。
- **状态**：规则 CONSTRUCTED，实现审计 **UNKNOWN**。

### 1.7 外部承诺验证与 SNARK witness 是否存在替换空间？

- **存在**，除非满足以下之一（B4 §4.1 逐条）：
  1. SNARK 内用同一 `W_pre,i` 线值重算 `com_i`（原生 hash → B2），或
  2. 外部 verifier 验证一个 equality/opening proof 把 `com_i` 绑定到 SNARK 公开输入中的同一 `d=CRH(witness)`。
- 单纯“外部承诺验证通过”**不证明** witness 一致；verifier 只看公开输入，看不到秘密 `x`（B4 问题 1/4）。
- 若走 (2)，外部 opening proof 需新增 proof 系统接口，且验证了 `d` 后仍需 SNARK 约束 `d=CRH(W_pre)` 防止 `d` 与 witness 脱钩 → 形成 B1(ii)+B4 组合，成本更高。
- **状态**：无环的无替换空间方案 = B2 电路内重算（**CONDITIONAL**）；纯外部桥接 **BLOCKED**。

---

## 2. 绑定关系总表

| 绑定项 | 规则层 | 实现层 | 依据 |
| --- | --- | --- | --- |
| `com_i` ↔ `W_pre,i`（8 字段全覆盖） | CONSTRUCTED | UNKNOWN（`Encode` 未定） | 冻结接口 + Correction-4 I6 |
| `com_i` ↔ `ictx_i`（含 step/C_i/attempt/version/program/circuit） | CONSTRUCTED | UNKNOWN | 冻结接口 |
| `com_i` ↔ `s_i`（opening 关系） | CONSTRUCTED | B1: BLOCKED；B2: CONDITIONAL | 承诺方案未选定 |
| `com_i` ↔ ρ（挑战派生输入） | CONSTRUCTED | CONSTRUCTED（Correction-3 去循环） | `ρ=H(ictx‖com‖ctx)` |
| 同份 witness（承诺重算 ↔ ORAM 约束） | CONSTRUCTED | B2: CONDITIONAL；B1: BLOCKED | 电路内同线值 |
| 外部承诺 ↔ SNARK witness | BLOCKED | BLOCKED | B4 无环形态退化为 B2 |

---

## 3. 承诺随机的安全假设清单

| 假设 | 用于 | 状态 |
| --- | --- | --- |
| DL / DDH（`log_g h` 未知） | B1 binding | VERIFIED 假设陈述 / 对 BLS12-377 G1 实例化 UNKNOWN |
| MiMC 抗碰撞（安全裕度） | B2 binding | UNKNOWN 裕度 |
| MiMC 作为随机预言机（启发式） | B2 hiding | CONDITIONAL（无严格归约） |
| `s_i ≥ ~8 Fr` 域元素熵 | B2 满足 Lemma 17 | INFERRED 条件 / artifact 无接口 |
| `s_i` MPC 联合生成 + MAC + 不可重采样 | grinding 防护 | CONSTRUCTED 规则 / 执行 BLOCKED |
| `Com` 覆盖全部 8 字段 + `ictx` | 绑定完整性 | CONSTRUCTED 规则 / 实现 UNKNOWN |

---

## 4. 本轮安全结论

1. **binding**：B1 有清晰假设（DL∧CRH），B2 只有 CRH 且裕度 UNKNOWN。
2. **hiding**：B1 perfect（强），B2 仅 ROM + 熵长度 + 启发式（弱）。
3. **opening**：B1 需非原生验证或外部桥接；B2 可原生重算。
4. **witness binding**：B2 电路内同线值在规则层闭合；B1/外部桥接均 BLOCKED。
5. **grinding**：两方案都依赖 `s_i` 不可重采样，执行层 BLOCKED；`k≥4` 或不可 grind 随机带未落地。
6. **覆盖完整性**：8 字段全覆盖是规则要求，`Encode`/`CRH` 的具体编码尚未定义 → UNKNOWN。

**不存在**一个候选在本轮同时满足：清晰 hiding+binding 假设、原生 opening、闭合 witness binding、可执行随机源。安全依据最强的 B1 后端阻塞，工程最近的 B2 hiding 只有条件依据。
