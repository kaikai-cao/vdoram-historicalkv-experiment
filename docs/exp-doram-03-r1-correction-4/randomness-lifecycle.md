# randomness-lifecycle.md — `s_i` 与 `r_tape,i` 的独立生命周期

> 2026-11-23 · 起点 `6586dd2` · 只分析随机源，不重算 ORAM 成本、不重做路径/Eviction。
> 标记：**VERIFIED** 固定源码/可复现事实 · **CONSTRUCTED** 本轮规则 · **INFERRED** 标准推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 接口缺失。

---

## 0. 两个随机源的角色

| 项目 | `s_i` | `r_tape,i` |
| --- | --- | --- |
| 作用 | 承诺盲化（opening randomness） | 状态更新随机带（派生 `r_t` 刷新 nonce） |
| 是否进入 `W_pre,i` | **否** | **是**（第 8 字段） |
| 是否进入 ORAM 状态 | 否 | 间接：`r_t` 进入 `nonce'` |
| 是否公开 | 否（除非方案打开规范明确要求且不与 hiding 冲突） | 否 |
| 是否参与 ρ 派生种子 | 否（仅经 `com_i` 间接影响） | 否（仅经 `com_i` 间接影响） |
| 是否需要秘密分享 | **需要**：不能让单个参与方单独知道或选定 | **需要**：nonce 刷新不得被单方偏置 |
| 是否需要 MAC | **需要**：SPDZ authenticated share；artifact 未证 | **需要**：同上 |
| 是否允许重采样 | **不允许**；承诺锁定后不可改，执行层防重采样 BLOCKED | **不允许**；已在 `W_pre,i` 中被承诺，改则须改 `com_i` |
| 是否跨步复用 | 原则上否，每步独立 + `attempt_i` 域分离 | 原则上否，每步独立 + `ictx_i` 域分离 |
| abort 后处理 | 立即作废，新 `attempt_i` 重新联合生成 | 立即作废，新 `attempt_i` 重新联合生成 |
| 生成来源 | MPC 联合认证随机带（**BLOCKED**） | MPC 联合认证随机带（**BLOCKED**） |
| 状态 | CONSTRUCTED 规则 / BLOCKED 实现 | CONSTRUCTED 规则 / BLOCKED 实现 |

**关键区分**：`s_i` 不属于消息，所以改动 `s_i` 不需要改 `W_pre,i` 的语义内容；`r_tape,i` 属于消息，改动它就是改动 witness。两者对 grinding 的影响因此不同，但防重采样要求相同。

---

## 1. 独立性是否必要

- **必要**（CONSTRUCTED 要求）：`s_i` 与 `r_tape,i` 必须由**互不相同、域分离**的随机来源产生。
  - 若 `s_i` 可由 `r_tape,i` 推导，则知道 nonce 刷新量的一方可能推断盲化因子，削弱 L2 hiding；
  - 若两者来自同一可rese ed 的本地种子，恶意参与方可同时重采样，恢复 `q_H` grinding。
- 实现方式（条件性）：在同一 MPC 执行内从认证随机带取两段，分别以 `"commit-blinding"` 与 `"state-tape"` 域标签展开：
  ```
  s_i       = Expand("commit-blinding" ‖ ictx_i ‖ seed_i)
  r_tape,i  = Expand("state-tape"      ‖ ictx_i ‖ seed_i)
  ```
  即使底层 `seed_i` 共享，域分离在 RO 模型下给出计算独立的两段（**INFERRED**）；若要严格独立应取两段物理独立随机源（**CONDITIONAL**）。
- artifact 无认证随机带接口 → 上述展开**无法落地，BLOCKED**（Correction-2 §E5）。

---

## 2. 联合生成与偏置

- **要求**：`s_i` 与 `r_tape,i` 都不能由单一参与方本地采样；必须由 m 方联合随机生成（如 SPDZ 预处理产生的随机带），且每方份额带 MAC。
- **防偏置**：若最后一方可在看到他人份额后决定是否继续，可偏置随机带（last-party rushing）。MPC coin-toss 在无偏置与无选择性 abort 方面于 dishonest majority 下需额外假设（**UNKNOWN**，沿用 Correction-1/2 结论）。
- **恶意参与方拒绝打开随机份额**：
  1. 在承诺锁定前拒绝 → 本步 abort，`attempt_i+1`，随机量全部作废，重新联合生成（CONSTRUCTED 规则）；
  2. 在承诺锁定后、ρ 派生后拒绝 → 同样作废并重来，但**重来必须换 `attempt_i`**，否则同一公开实例可被反复尝试以筛选有利 ρ（CONSTRUCTED 规则）；
  3. 固定行为 abort 是否足以阻断“基于秘密的选择性中止”仍 **UNKNOWN / BLOCKED**，不能假设足够。
- artifact 无对应接口 → 执行层 **BLOCKED**。

---

## 3. 承诺失败 / 证明失败后的作废规则

| 事件 | 随机量处理 | 公开记录 | 状态 |
| --- | --- | --- | --- |
| 阶段 1 锚点不符 | 尚未生成，不涉作废 | 拒绝事件 | CONSTRUCTED |
| 阶段 2 参与方拒绝 | `s_i`、`r_tape,i` 作废 | 固定格式 abort + `attempt_i+1` | CONSTRUCTED 规则 / BLOCKED 执行 |
| 阶段 3 承诺失败 | 两者作废 | 同上 | CONSTRUCTED 规则 |
| 阶段 4 ρ=0 重哈希 | 随机量**不作废**，仅换域分离计数器重派生 | 重哈希计数器公开 | CONSTRUCTED |
| 阶段 5 证明失败 | 两者作废，禁止用同一实例重试 | 公开失败事件 + `attempt_i+1` | CONSTRUCTED 规则 / BLOCKED 执行 |
| 阶段 6 验证失败 | 两者作废；状态锚点不变 | reject 事件 | CONSTRUCTED 规则 |
| 阶段 7 成功 | 两者完成使命；不复用 | 新锚点 | CONSTRUCTED |

**禁止**：失败后保留 `s_i` 或 `r_tape,i` 并在同 `attempt_i` 下再次尝试。该行为等价于 grinding。

---

## 4. 跨步复用、关联与 grinding

- **`s_i` 跨步复用**：同一个盲化因子用于不同 `W_pre` 时，在 Pedersen 型承诺下会使 `com_i/com_j` 的比值泄露消息差；在 hash 型下增加可关联性。必须每步独立（**INFERRED** / CONDITIONAL）。
- **`r_tape,i` 跨步复用**：`r_t` 重复会形成 nonce 刷新序列的可关联结构，可能被用作访问模式旁路；必须以 `ictx_i` 域分离（**INFERRED**）。
- **grinding 落点**：
  - `s_i` 若可重采样 → 改 `com_i` → 改 ρ，重演 Correction-3 的 `q_H·2^-170` 问题；
  - `r_tape,i` 在 `W_pre,i` 内，改它必须改 `com_i`，同样改变 ρ；
  - 两者都要求“不可由单方重采样 + 认证随机源 + 失败后新 `attempt_i`”。
- 由于 artifact 无认证随机源，上述防护目前全部 **BLOCKED**。

---

## 5. 固定长度 abort 是否足够

**不足够，不能直接假设。** 固定长度 abort 只限制公开事件的长度一致，不保证：

1. 中止决定与 witness/nonce/随机量无关（选择性中止仍可泄露“此 witness 不利”）；
2. 参与方不会通过多次 `attempt_i` 筛选有利 ρ（需公开计数与作废规则，且计数本身可能泄露重试次数）；
3. 中止后新随机源与旧随机源独立（需认证随机带，BLOCKED）；
4. 中止事件不泄露哪个参与方拒绝以及拒绝发生在哪个阶段（当前未定义）。

固定长度 abort 是**必要但非充分**条件；完整处理保持 **UNKNOWN / BLOCKED**，与 D2、跨步 verifier chain 一起列为遗留阻塞。

---

## 6. 小结

| 结论 | 状态 |
| --- | --- |
| `s_i` 与 `r_tape,i` 角色、可见性、是否进消息的定义 | CONSTRUCTED |
| 两者必须 MPC 联合生成、MAC 认证、不可重采样、每步独立 | CONSTRUCTED 要求 |
| 上述要求在固定 artifact 上可执行 | **BLOCKED**（无认证随机带接口） |
| 两者独立的域分离展开 | INFERRED / CONDITIONAL |
| 失败后作废 + `attempt_i` 防静默重试 | CONSTRUCTED 规则 / BLOCKED 执行 |
| 固定长度 abort 足以解决选择性 abort | **UNKNOWN / BLOCKED**（明确否定该假设） |
