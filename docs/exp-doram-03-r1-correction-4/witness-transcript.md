# witness-transcript.md — 承诺消息、承诺盲化随机数与状态更新随机带的角色分离

> 2026-11-23 · 起点 `6586dd28d3d7f4dce8d51815c96f4ea4be7eba9c` · 仅纸面接口定义，不实现、不重算成本。
> 标记：**VERIFIED** 固定源码/可复现算术 · **CONSTRUCTED** 本轮规则 · **INFERRED** 标准推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 当前 artifact 无接口。
> 硬规则：`W_pre,i`（消息）、`s_i`（承诺盲化随机数）、`r_tape,i`（状态更新随机带）是三个不同对象。

---

## 0. 要修复的角色混淆

Correction-3 `witness-transcript.md` §2.1 把 `commitment_opening_randomness`（记作 `r_i`）同时放进 `W_pre,i` 的字段列表，又用它做 `com_i = Com(Encode(ictx_i‖W_pre,i); r_i)` 的 opening randomness。

由此产生三处混淆：

1. **消息包含自身的盲化因子**：承诺输入与盲化随机量来自同一字段，无法独立论述 hiding 与 binding；
2. **grinding 接口不清**：若 prover 可改该字段，则消息与 `com_i` 同时改变，`ρ` 随之改变，无法把“witness 固定后派生挑战”与“盲化随机性”分开审查；
3. **状态更新随机带被误归类**：`pre_challenge_random_tape` 与承诺盲化随机数并列，但其作用是刷新 nonce、进入 ORAM 新状态，性质完全不同。

**本轮撤回该记法。** 三个对象分离如下。

---

## 1. 最终定义

```
ictx_i = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)

W_pre,i = (
  old_state,      // 旧 bucket / 旧 pos-map block / 旧 stash slots / 旧 meta
  new_state,      // 新 bucket / 新 pos-map block / 新 stash slots / 新 meta
  path,           // 每层 leaf bits、child hash、被访问 bucket 字段
  siblings,       // 每层 sib（旧/新路径共用）
  stash,          // R 槽 (addr,val,leaf,valid) + occupancy
  eviction_aux,   // P, ok, u, elig, sel, no_cand, dummy
  nonce,          // 旧/新 bucket nonce
  r_tape,i        // 状态更新随机带：派生 r_t 以刷新 nonce
)

s_i      = commitment_blinding_randomness     // 仅承诺打开，不属于 W_pre,i

com_i    = Com(Encode(ictx_i ‖ W_pre,i); s_i)
rho_k    = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context),  k = 1,2
W_post,i = (A_k, B_k),  A_k = Σ_{u∈Old} ρ_k^{enc(u)},  B_k = Σ_{v∈New} ρ_k^{enc(v)}
```

- `attempt_i` 是公开重试计数，用于 abort 后重新实例绑定，防止“同一公开实例静默重采样”（**CONSTRUCTED**，见 `randomness-lifecycle.md`）。
- `W_pre,i` 现为 **8 个字段**；`s_i` **不在其中**。
- `W_post,i` 仍只包含挑战后由 `(W_pre,i, ρ)` 唯一确定的变量。

**依赖方向**：

```
ictx_i ─────────────┬──> Encode(ictx_i ‖ W_pre,i) ──> com_i ──> ρ_k ──> W_post,i ──> π_i ──> verify
W_pre,i ────────────┘                                   ↑
r_tape,i ⊂ W_pre,i ──> r_t ──> nonce' ⊂ new_state        │
s_i ────────────────────────────────────────────────────┘   （仅作为打开随机量）
```

不存在 `ρ/W_post/π → W_pre/com/s` 的边；`r_tape,i` 只通过 `com_i` 间接影响 ρ，不作为 ρ 的派生种子。（CONSTRUCTED）

---

## 2. `s_i`：承诺盲化随机数

| 属性 | 规定 | 状态 |
| --- | --- | --- |
| 是否属于 `W_pre,i` | **否**。不在消息编码中出现 | CONSTRUCTED |
| 是否进入 ORAM 状态 | **否**。不进入任何 bucket、stash、nonce、state root | CONSTRUCTED |
| 是否公开给 verifier | **否**；仅在具体方案明确要求时例外。若承诺打开在 SNARK 内验证，`s_i` 是私有 witness 线 | CONDITIONAL（取决于方案） |
| 参与承诺打开验证 | 是：`com_i = Com(Encode(ictx_i‖W_pre,i); s_i)` 必须由电路或外部接口检查 | CONSTRUCTED 规则 / BLOCKED（接口） |
| 是否作为 ρ 种子 | **否**。ρ 只由 `ictx_i‖com_i‖transcript_context` 派生 | CONSTRUCTED |
| 是否由 MPC 联合产生 | **必须**。若由单一 prover 选定，可重采样 `s_i` 改变 `com_i` 进而 grinding ρ | CONSTRUCTED 要求 / BLOCKED 实现 |
| 是否允许任一参与方重采样 | **不允许**；承诺锁定后不可改。执行层防重采样需认证随机源 | BLOCKED |
| 是否需要 MAC/authentication | 是（SPDZ 风格 authenticated share）；artifact 对 proof witness 输入的 MAC 覆盖未证 | BLOCKED |
| 是否跨 step 持久化 | **否**。每步独立；重试用新 `attempt_i` 并重新生成 | CONSTRUCTED 规则 / BLOCKED 执行 |
| 与 `r_tape,i` 的关系 | 必须独立（域分离的不同随机带）；相关性会削弱 hiding 或恢复 grinding | CONDITIONAL |

> 若 `s_i` 可被 prover 自由重采样，则 §1 中的 “witness 固定后派生挑战” 仍不成立：prover 可枚举 `s_i` 直到 ρ 有利。这是 Correction-3 grinding 结论在角色分离后的精确落点。

---

## 3. `r_tape,i`：状态更新随机带

| 属性 | 规定 | 状态 |
| --- | --- | --- |
| 是否属于 `W_pre,i` | **是**，作为第 8 个字段，被 `com_i` 承诺 | CONSTRUCTED |
| 是否作为 ρ 派生种子 | **否**；只经 `com_i` 间接绑定 | CONSTRUCTED |
| 是否进入 ORAM 状态 | **间接进入**：派生 `r_t` 刷新 nonce | CONSTRUCTED |
| 是否公开 | 否 | CONSTRUCTED |
| 是否由 MPC 联合产生 | **必须**（与 `s_i` 同样理由：防单方偏置 nonce 刷新） | BLOCKED 实现 |
| 是否需要 MAC | 是 | BLOCKED |
| 是否跨 step 持久化 | 否，每步独立并用 `ictx_i` 域分离 | CONSTRUCTED 规则 |

### 3.1 `r_t` 的显式绑定

设本步被触碰 bucket 数为 `κ`（符号量，**本轮不重算其数值或成本**），定义域分离展开：

```
r_t,q = H("nonce-refresh" ‖ q ‖ ictx_i ‖ r_tape,i) ∈ F,   q = 1..κ
nonce'_q = nonce_q + r_t,q
```

必须写成 R1CS 线值约束（不是黑箱）：

```
r_t,q − H("nonce-refresh" ‖ q ‖ ictx_i ‖ r_tape,i) = 0
nonce'_q − nonce_q − r_t,q = 0
```

`nonce'` 进入新 bucket hash → 新状态根 `C_{i+1}`。于是 `r_tape,i` 的完整性由 `com_i` 对 `W_pre,i` 的 binding 覆盖，而 `nonce'` 的合法性由上述约束覆盖。（CONSTRUCTED 算术；`r_tape,i` 的认证生成 **BLOCKED**）

---

## 4. 无循环检查清单

| 检查 | 内容 | 结果 |
| --- | --- | --- |
| I1 | `com_i` 输入不含 `ρ_k` 或任何 `W_post,i` 变量 | CONSTRUCTED 通过 |
| I2 | `ρ_k` 输入含 `com_i` 完整字节编码，`ictx_i` 含 `attempt_i` | CONSTRUCTED 通过 |
| I3 | `s_i ∉ W_pre,i`，不进入 ORAM 状态，不作为 ρ 种子 | CONSTRUCTED 通过 |
| I4 | `r_tape,i ∈ W_pre,i`，不是独立 ρ 种子；`r_t` 在电路中绑定 nonce 更新 | CONSTRUCTED 通过 |
| I5 | `W_post,i` 由 `(W_pre,i, ρ)` 唯一确定，无自由变量 | CONSTRUCTED 通过（沿用 Correction-3） |
| I6 | `com_i` 编码覆盖 `W_pre,i` **全部 8 个字段** | CONSTRUCTED 规则 / BLOCKED（承诺实现） |
| I7 | `s_i`、`r_tape,i` 不可由单方重采样，且有认证来源 | **BLOCKED** |

---

## 5. 当前 artifact 支持情况

| 项 | 事实 | 状态 |
| --- | --- | --- |
| MiMC hash gadget（65 轮、SBox=7） | 固定 artifact 中存在 | VERIFIED（Correction-2 §E1） |
| `Commitment` / `Pedersen` / `Poseidon` / `Merkle` gadget | gadget 目录 19 文件中均不存在 | VERIFIED（Correction-2 §E2） |
| 联合认证随机带 → `s_i`/`r_tape,i` 接口 | 不存在；当前只落盘 R1CS+witness、外部逐电路证明 | BLOCKED（Correction-2 §E5） |
| proof witness 每个输入份额的 MAC 覆盖 | 未证 | BLOCKED |

**结论**：角色定义在纸面上完全分离并通过 I1–I5；I6/I7 因固定 artifact 缺少承诺与认证随机源接口而保持 **BLOCKED**。本轮不得把定义写成已实现。
