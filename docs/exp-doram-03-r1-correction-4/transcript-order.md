# transcript-order.md — 随机量角色分离后的七阶段 Transcript

> 2026-11-23 · 起点 `6586dd2` · 仅纸面接口定义；不重做 D1/Eviction，不重算成本。
> 标记：**VERIFIED** 固定源码/可复现算术 · **CONSTRUCTED** 本轮规则 · **INFERRED** 标准推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 接口缺失。
> 硬规则：阶段 3 锁定 `com_i`，阶段 4 才派生 ρ，阶段 7 才推进状态。

---

## 0. 与 Correction-3 的接口差异

| 对象 | Correction-3 | 本轮 |
| --- | --- | --- |
| 承诺消息 | `W_pre,i` 内含 `r_i`（同时充当盲化随机数） | `W_pre,i`（8 字段，含 `r_tape,i`），**不含** `s_i` |
| 盲化随机量 | `r_i ∈ W_pre,i` | `s_i ∉ W_pre,i`，独立 MPC 内部随机量 |
| `com_i` | `Com(Encode(ictx‖W_pre); r_i)` | `Com(Encode(ictx‖W_pre); s_i)` |
| ρ 种子 | `ictx‖com‖ctx` | 不变；**明确排除** `s_i` 与 `r_tape,i` 直接入哈希 |
| `ictx_i` | 5 元组 | 6 元组，新增公开 `attempt_i` |

---

## 1. 阶段 1：Instance binding

- **输入**：`protocol_version`、`program_id`、`circuit_id`（约束系统哈希）、`step_i`、`attempt_i`、`C_i`、上一步已接受锚点。
- **输出**：`ictx_i = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)` 与公开实例 `x_i`。
- **可见 / 可改**：全体可见；锁定后无人可改；verifier 与上一步锚点交叉核对。
- **失败**：锚点不符 → 拒绝本步，不进入阶段 2。
- **传递**：`ictx_i`, `x_i`。

`attempt_i` 从 0 起，每次公开 abort 后加一，防止同一公开实例被静默重采样。

**`C_{i+1}` 前提**（沿用 Correction-3）：只有在同一 MPC 执行中、承诺锁定前 authenticated open 时，才可进入 ρ 的 transcript；当前 artifact 无此接口（BLOCKED），默认将 `C_{i+1}` 作为证明输出，由 R1CS 绑定到 `W_pre,i.new_state`。

---

## 2. 七阶段表

| # | 阶段 | 输入 | 输出 | 谁能看到 | 谁能修改 | 失败行为 | 进入下一步 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Instance binding | 版本/程序/电路 ID、`step_i`、`attempt_i`、`C_i`、上一步锚点 | `ictx_i`, `x_i` | 全体 + verifier | 锁定后无人 | 锚点不符 → 拒绝 | `ictx_i`, `x_i` |
| 2 | Witness preparation | 上一步 `new_state` shares、VM 输入、**MPC 认证随机源** | `W_pre,i`（8 字段，含 `r_tape,i`）+ **独立生成 `s_i`** | 仅 MPC 参与方（份额级） | 承诺锁定前可形成；锁定后不可 | 参与方拒绝 → 固定格式 abort，`attempt_i+1` 重来 | `W_pre,i`, `s_i` |
| 3 | Commitment | `ictx_i`, `W_pre,i`, `s_i` | `com_i = Com(Encode(ictx_i‖W_pre,i); s_i)`，锁定 | `com_i` 公开；`W_pre,i`、`s_i` 不公开 | 锁定后无人可改 | 承诺失败 → `attempt_i+1`，随机量作废 | 已固定的 `com_i` 字节串 |
| 4 | Challenge derivation | `domain_k`, `ictx_i`, `com_i`, `transcript_context` | `ρ₁,ρ₂ ∈ F*` | ρ 公开；verifier 可重算 | 无人（哈希确定） | `ρ=0` → 域分离计数器加一重哈希 | `ρ₁,ρ₂` |
| 5 | Proof generation | `pp`, `x_i`, 公开 `ictx_i/com_i/ρ`, 私有 `W_pre,i/s_i/W_post,i` | `π_i` | `π_i` 公开 | prover 计算；不得改 `x_i/com_i/ρ` | 证明失败 → `attempt_i+1`，随机量作废 | `π_i` |
| 6 | Verification | `x_i`, `ictx_i`, `com_i`, `ρ`, `π_i`, 锚点 | accept / reject | 全体（公开可验证） | 无人 | 任一检查失败 → reject | accept 标志 |
| 7 | State advancement | accept, `C_{i+1}`, `Hist_{i+1}` | 新锚点 `(step_{i+1}, C_{i+1}, Hist_{i+1})` | 公开 | 无人（accept 后确定） | reject → 保留旧锚点，记录固定格式事件 | 下一步 `ictx_{i+1}` |

阶段 6 必做检查：

1. 重算 `ρ_k = H(domain_k‖ictx_i‖com_i‖transcript_context)`，与证明所用 ρ 逐字节一致；
2. 检查 `com_i` 的打开关系：存在 `s_i` 使 `com_i = Com(Encode(ictx_i‖W_pre,i); s_i)`，且该 `W_pre,i` 与 SNARK witness 是同一组线值；
3. 验证 SNARK 约束（Merkle 路径、stash 指纹 `A_k=B_k`、`r_t` 绑定 nonce 更新、VM/History 绑定）；
4. 检查 `step_i / attempt_i / C_i → C_{i+1} / Hist` 与锚点连续（跨步 verifier chain 仍 **BLOCKED**）；
5. verifier 不接触 `W_pre,i`、`s_i`、`r_tape,i` 明文。

**阶段 7 之前不得接受新状态根。** 阶段 2–5 的随机量在 reject/abort 后全部作废，见 `randomness-lifecycle.md`。

---

## 3. 五个必答问题

### Q1. `s_i` 是证明 witness 的一部分，还是 MPC 内部的承诺随机量？

两者取决于承诺打开在何处验证，但**公开性不变**：

- **电路内验证**（推荐接口形态）：`s_i` 作为 SNARK 的**私有 witness 线**出现，与 `W_pre,i` 一起被约束；verifier 只看到 `com_i`。此时 `s_i` 是“MPC 内部随机量 + 电路私有 witness 线”，两者是同一份份额的不同称呼。
- **电路外验证**：`s_i` 留在 MPC 内部用于对外打开承诺，不进入 SNARK witness；此时必须用额外接口证明“外部承诺对象使用的 `W_pre,i` 与 SNARK witness 相同”（见 Q3）。

无论哪种，`s_i` 都**不公开**（除非具体承诺方案的打开规范明确要求，且该要求不与 hiding 冲突）。（CONSTRUCTED 规则 / CONDITIONAL 实现）

### Q2. 若 SNARK 需要验证 `com_i`，如何把 `s_i` 与同一份 `W_pre,i` 绑定？

在电路中同时以公开输入 `(ictx_i, com_i)` 和私有 witness `(W_pre,i, s_i)` 约束：

```
com_i − Com(Encode(ictx_i‖W_pre,i); s_i) = 0
```

且 ORAM 状态转换、Merkle 路径、`A_k/B_k` 指纹、`r_t`→nonce 更新**全部使用同一组 `W_pre,i` 线值**，不是重新拷贝的第二份输入。这样 `s_i` 只打开这一份消息的承诺，无法打开另一组 witness。（CONSTRUCTED 规则）

- MiMC 类承诺可用现有 hash gadget 表达该约束（**VERIFIED** gadget 存在，**INFERRED** 约束可写出）；
- 但 MiMC 随机化承诺的 hiding 无标准规约 → L2 安全性仍 **BLOCKED**；
- Pedersen 类承诺需在 `Fr` 电路中验证 G1 方程，需非原生 `Fq` 算术且 artifact 无 gadget → **BLOCKED**。

### Q3. 若承诺验证在 SNARK 外部，如何防止外部承诺对象与 SNARK witness 不一致？

**当前无法给出一致接口，保持 BLOCKED。** 可选路径及状态：

| 路径 | 做法 | 状态 |
| --- | --- | --- |
| (a) 取消外部验证 | 把承诺打开放进电路（Q2） | CONSTRUCTED 规则；L2 方案仍 BLOCKED |
| (b) 同参数 Pedersen 外部验证 | verifier 验 `com=g^x h^{s_i}`，电路验同一 `x` 的 ORAM 约束 | 需非原生 `Fq` 与曲线 gadget；artifact 无 → BLOCKED |
| (c) 外部打开证明绑定到 SNARK 公开输入 | 外部证明 `π_open` 绑定 `(ictx_i, com_i, x_i)` | artifact 无该接口 → BLOCKED |

**禁止推断**：外部承诺被验证成功，不自动意味着其消息与 SNARK witness 一致；必须有 Q2 的电路内同线值约束或 Q3(b)(c) 的显式桥接。

### Q4. `com_i` 的绑定关系是否覆盖全部 `W_pre,i` 字段？

必须覆盖 8 个字段，缺一即产生“承诺后换字段”的漏洞：

| 字段 | 必须进 `Encode` | 理由 |
| --- | --- | --- |
| `old_state` | 是 | 绑定旧根 `C_i` |
| `new_state` | 是 | 绑定新根 `C_{i+1}` |
| `path` | 是 | 防止换访问路径 |
| `siblings` | 是 | 防止换认证路径 |
| `stash` | 是 | 指纹与 occupancy 绑定 |
| `eviction_aux` | 是 | 防止换 eviction 辅助线 |
| `nonce` | 是 | 防止换 nonce 重放旧根 |
| `r_tape,i` | 是 | 防止看到 ρ 后改 nonce 刷新量 |

`Encode` 必须长度前缀、定长域元素、顺序固定。（CONSTRUCTED 规则）

- 若承诺只接受单个域元素（Pedersen 型），需先 `d = CRH(Encode(ictx‖W_pre))` 再承诺 `d`；此时 binding 同时依赖 CRH 与底层承诺，hiding 仍需论证 → **CONDITIONAL**，不能省略该假设。
- 若实现省略任一字段，则 I6 不通过 → **BLOCKED**。

### Q5. `ictx_i` 是否同时绑定 step、program、circuit、protocol version、旧状态根？

是，按 §1 定义 6 元组：`protocol_version`、`program_id`、`circuit_id`、`step_i`、`C_i`、`attempt_i`，并作为 `Encode` 前缀与 ρ 输入同时出现。因此同一 `W_pre,i` 在不同 step/程序/电路/版本/旧根/重试次数下产生不同 `com_i` 与不同 ρ，不能跨实例移植。（CONSTRUCTED 规则）

---

## 4. Fiat–Shamir 与 grinding 的角色说明

- ρ 只由 `ictx_i‖com_i‖transcript_context` 派生；`s_i` 与 `r_tape,i` 都**不直接**作为 ρ 种子，仅通过 `com_i` 间接绑定。
- 但 `s_i` 参与 `com_i` 计算，因此若 `s_i` 可由 prover 重采样，则 `com_i` 与 ρ 同时改变 → grinding 依旧可能。故 `s_i` 必须不可重采样（MPC 联合生成 + 认证），这是 Correction-3 `q_H·2^-170` 结论在角色分离后的具体落点。
- `r_tape,i` 在 `W_pre,i` 内，承诺锁定后不可改；其改变必须改 `com_i`，同样受 binding 与不可重采样约束。
- FS 需 ROM、无歧义编码、域分离、两次独立哈希与拒绝采样（沿用 Correction-3 §3/§4，本轮不重做）。

---

## 5. 结论

七阶段顺序与可见性在角色分离后自洽（**CONSTRUCTED**）；Q1/Q2/Q4/Q5 在规则层闭合，Q3（外部承诺与 SNARK witness 的桥接）与 L2 具体承诺实现保持 **BLOCKED**。D2 与跨步 verifier chain 本轮未触碰，保持 BLOCKED。
