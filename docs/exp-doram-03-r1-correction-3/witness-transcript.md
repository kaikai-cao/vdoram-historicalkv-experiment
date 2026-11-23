# witness-transcript.md — 挑战前 Witness 与挑战后变量的去循环拆分

> 2026-11-23 · 起点 `ee75b79ae66f6e69377bbc2b8490c57d40885b17` · 仅纸面协议定义。
> 标记：**VERIFIED** 固定源码/可复现算术 · **CONSTRUCTED** 本轮规则 · **INFERRED** 推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 未闭合。
> 硬规则：挑战必须由一个**已经固定、且不包含该挑战本身**的承诺对象派生出来。

---

## 0. 要撤回的旧定义（循环所在）

Correction-2 `commitment-security-model.md` §C1 定义：

```
challenge_aux = com(W_i) opening randomness、FS transcript 原料、ρ₁,ρ₂
W_i = (..., nonce, challenge_aux)
```

而 §C3 第 4 步又规定 `ρ₁,ρ₂ = FS(... || com(W_i) || ...)`。

于是存在依赖环：

```
ρ₁,ρ₂ ∈ W_i ──> com(W_i) ──> ρ₁,ρ₂
```

**撤回该定义。** `ρ₁,ρ₂` 与本轮挑战派生的任何辅助变量都不属于承诺对象；它们只能在承诺固定之后出现。旧的 `W_i` 记号整体保留为 `W_pre,i ∪ W_post,i`，但 `com_i` 只承诺 `W_pre,i`。

---

## 1. 去循环不变量（本轮唯一核心）

```
ictx_i = (protocol_version, program_id, circuit_id, step_i, C_i)     ① 挑战前
W_pre,i = (old_state, new_state, path, siblings, stash, eviction_aux,
           nonce, commitment_opening_randomness, pre_challenge_random_tape)  ② 挑战前
com_i   = Com(Encode(ictx_i || W_pre,i); r_i)                        ③ 挑战前固定
ρ_k     = H(domain_k || ictx_i || com_i || transcript_context), k=1,2 ④ 挑战后派生
W_post,i= F(W_pre,i, ρ₁, ρ₂)                                          ⑤ 挑战后派生
π_i     = Prove(pp, x_i, W_pre,i, W_post,i; ρ₁, ρ₂)                   ⑥ 挑战后生成
```

**依赖方向单向**：`② → ③ → ④ → ⑤ → ⑥`。不存在 `④/⑤/⑥ → ②/③` 的边。
`r_i` 是 `W_pre,i` 中的 `commitment_opening_randomness`，不是 ρ 的函数；`pre_challenge_random_tape` 同理。任何在看到 ρ 之后才确定的量都不得回填 `com_i`。（CONSTRUCTED）

形式化检查条件（verifier 或协议审查者可逐条核对）：

- **I1**：`com_i` 的输入编码中不含符号 `ρ₁,ρ₂`，也不含任何以 ρ 为自变量定义的变量。
- **I2**：`ρ` 的哈希输入中含 `com_i` 的完整字节编码（不是只含其哈希或截断）。
- **I3**：`com_i` 在 ρ 计算之前已锁定；锁定后 `W_pre,i` 与 `r_i` 不可改动。
- **I4**：`W_post,i` 必须由 `(W_pre,i, ρ)` 经确定性约束唯一确定；若存在自由变量，必须另开挑战后承诺轮，不得复用 `com_i`（本轮未定义该轮 → BLOCKED）。

---

## 2. A1：挑战前承诺对象 `W_pre,i`

```
W_pre,i = (
  old_state,                       // 旧 bucket slots / 旧 pos-map block / 旧 stash slots / 旧 meta
  new_state,                       // 新 bucket slots / 新 pos-map block / 新 stash slots / 新 meta
  path,                            // 每层 leaf bits d_t、child hash、被访问 bucket 的 4Z 字段
  siblings,                        // 每层 sib_{t+1}（旧/新路径共用同一变量）
  stash,                           // R 个槽的 (addr,val,leaf,valid) + occupancy bits
  eviction_aux,                    // P_{s,t}, ok_{s,t}, u_{t,q,s}, elig_{t,q,s}, sel, no_cand, dummy
  nonce,                           // 旧/新 bucket nonce；触碰刷新、未触碰保留
  commitment_opening_randomness,   // r_i：仅用于 com_i 的 opening randomness
  pre_challenge_random_tape        // r_tape：本步 nonce 刷新随机带（r_t 来源）
)
```

> 注意：`commitment_opening_randomness` 在前序文档记作 `r_com`，本轮统一改名 `r_i`，避免与状态根 `C_i` 混淆。`pre_challenge_random_tape` 不是 ρ，也不是 ρ 的种子替代物；它由 MPC 认证随机带产生（接口 BLOCKED，见 `commitment-interface.md`）。

### 2.1 逐字段分类

| 字段 | 类别 | 秘密 / 随机 / 公开 | 跨步保持 | 绑定到 ictx 的哪一部分 | 是否进入 ORAM 状态 |
| --- | --- | --- | --- | --- | --- |
| `old_state` | 秘密 witness（份额） | 秘密 | **是**：必须等于上一步已接受的 `new_state` | `C_i`（旧根）、`step_i` | 是 |
| `new_state` | 秘密 witness（份额） | 秘密 | **是**：成为下一步 `old_state` | `C_{i+1}`（新根）、`step_i` | 是 |
| `path` | 秘密 witness（份额） | 秘密 | 否（每步重算） | `circuit_id`、`C_i` | 是（访问路径本身） |
| `siblings` | 秘密 witness（份额） | 秘密 | 否 | `C_i`、`C_{i+1}`（新旧根共用） | 是（Merkle 认证线） |
| `stash` | 秘密 witness（份额） | 秘密 | **是**：stash 内容跨步延续 | `C_i^{Stash}`、`C_{i+1}^{Stash}` | 是 |
| `eviction_aux` | 秘密辅助 witness（份额） | 秘密 | 否 | `C_i`、`C_{i+1}`（由 R1CS 间接绑定） | 仅证明辅助线，非状态 |
| `nonce` | 秘密随机量（份额） | 秘密 | **是**：未触碰 bucket 保留旧 nonce | 旧根 `C_i` / 新根 `C_{i+1}` 的 preimage | 是（bucket hash 的一部分） |
| `commitment_opening_randomness` `r_i` | 纯随机量（份额） | 秘密 | 否：**每步独立** | `ictx_i` 全量（编码前缀） | **否**：只用于 `com_i` |
| `pre_challenge_random_tape` `r_tape` | 纯随机量（份额） | 秘密 | 否：**每步独立** | `step_i` 域分离 | 间接：`r_t` 进入 `nonce' = nonce + r_t` |

**明确禁止放入 `W_pre,i` 的字段**：

- `ρ₁, ρ₂`；
- 以 ρ 为系数的累加器 `A_k, B_k`（见 §3）；
- 任何“看到 ρ 后才选定”的匹配位、重排位、分支位；
- `π_i`、`verify_i` 的结果或证明随机数。

以上约束为 **CONSTRUCTED**；“这些字段在固定 artifact 中能以认证份额形式产生”为 **BLOCKED**（D2）。

### 2.2 哪些字段只用于承诺、不直接进入 ORAM 状态

- `r_i`：只作为 `com_i` 的 opening randomness。它不进入任何 Merkle leaf、bucket、stash 或 state root。若 `r_i` 进入状态，则状态根会随承诺随机性漂移，破坏跨步根链。
- `r_tape`：其派生的 `r_t` 进入 nonce 刷新（因而间接影响新根），但 `r_tape` 本身不是状态字段；它必须以 `step_i` 域分离，防止跨步复用。
- `eviction_aux`：证明辅助线，受 R1CS 约束但与状态根无直接 preimage 关系。

### 2.3 绑定到 step / 程序 / 根 / 版本的方式

绑定分两层，**缺一不可**：

1. **承诺层**：`com_i = Com(Encode(ictx_i || W_pre,i); r_i)`，`ictx_i` 作为编码前缀进入承诺输入。因此同一份 `W_pre,i` 在不同 `step_i` 或不同 `C_i` 下产生不同的 `com_i`，无法跨步移植。
2. **挑战层**：`ρ_k = H(domain_k || ictx_i || com_i || transcript_context)`，`domain_k` 带用途域分离，`transcript_context` 含协议版本与电路标识。因此 ρ 不能跨电路、跨用途、跨步骤复用。

`C_{i+1}` 的处理见 `transcript-order.md` §1：只有当它在挑战前已由同一 MPC 执行认证 opened 时，才可作为挑战前量进入 transcript；否则它是证明输出，**不得**进入 ρ 的输入。

---

## 3. A2：挑战后变量 `W_post,i`

```
W_post,i = (
  A_k = Σ_{u ∈ Old} ρ_k^{enc(u)},    k = 1,2
  B_k = Σ_{v ∈ New} ρ_k^{enc(v)},    k = 1,2
  // 以及任何被明确定义为 ρ 函数的辅助线；本轮只列出累加器
)
```

约束关系（必须写成 R1CS 线值等式，不是黑箱）：

```
A_k − Σ_{u ∈ Old} ρ_k^{enc(u)} = 0
B_k − Σ_{v ∈ New} ρ_k^{enc(v)} = 0
A_k − B_k = 0        （stash 多重集守恒）
```

`enc(u) = addr + 2^L·val + 2^{L+B}·leaf + 2^{2L+B}·valid`，`L=20, B=128`，故 `enc < 2^169`（**VERIFIED** 算术，沿用 `stash-soundness.md` §B6）。

**关键性质**（CONSTRUCTED）：给定 `(W_pre,i, ρ₁, ρ₂)`，`A_k,B_k` 由上式**唯一确定**， prover 无自由选择空间。因此它们不需要在 ρ 之前被承诺，也不会反向污染 `com_i`。

**若引入任何非唯一确定的 `W_post` 变量**（例如按 ρ 值挑选的匹配位）：必须新增一次挑战后承诺并重新派生第二轮挑战；本轮未定义该机制，标 **BLOCKED**，不得暗示已存在。

---

## 4. 依赖图与检查清单

```
        ictx_i ──────────────┬─────────────────────────────┐
                             │                             │
        W_pre,i ──(r_i)──> com_i                           │
                             │                             │
                             └──> H(domain || ictx || com)─┘
                                          │
                                       ρ₁, ρ₂
                                          │
                                    W_post,i (A_k,B_k)
                                          │
                                        π_i
                                          │
                                       verify
                                          │
                                    C_{i+1} accepted
```

交付前逐项核对（本轮已完成 1–4，5–7 见 `commitment-interface.md`）：

1. ☑ `W_pre,i` 中无 ρ、无 ρ 函数；
2. ☑ `com_i` 输入含 `ictx_i` 与全部 `W_pre,i`；
3. ☑ ρ 输入含 `com_i` 完整编码与域分离；
4. ☑ `W_post,i` 由 `(W_pre,i, ρ)` 唯一确定；
5. ☐ `com_i` 的 hiding + binding 有可实现依据 → BLOCKED；
6. ☐ `r_i`/`r_tape` 认证生成与防 grinding → BLOCKED（D2）；
7. ☐ 跨步 verifier chain → BLOCKED（本轮不解）。
