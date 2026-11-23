# transcript-order.md — 无循环 commitment–challenge–proof 顺序与 B1 指纹 soundness

> 2026-11-23 · 起点 `ee75b79` · 仅纸面协议定义，不实现、不跑基准。
> 标记：**VERIFIED** 可复现算术/固定源码 · **CONSTRUCTED** 本轮规则 · **INFERRED** 标准结论推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 未闭合。
> 硬规则：**先 commitment、后 challenge 是必要条件，不等于完整 soundness 证明。**

---

## 0. 依赖方向

```
ictx_i, W_pre,i → com_i → ρ₁,ρ₂ → W_post,i → π_i → verify → 接受 C_{i+1}
```

任何从 `ρ/W_post/π` 指回 `W_pre/com` 的边都是循环，必须拒绝。`W_pre,i` 的严格定义见 `witness-transcript.md`。

---

## 1. 阶段 1：Instance binding（实例固定）

- **输入**：`protocol_version`、`program_id`、`circuit_id`（约束系统哈希）、`step_i`、`C_i`（旧状态根元组）、上一步已接受的 `(step_{i−1}, C_{i−1}, C_i, Hist_i)`。
- **输出**：`ictx_i = (protocol_version, program_id, circuit_id, step_i, C_i)` 与公开实例 `x_i`。
- **谁能看到**：所有参与方 + 公开 verifier。
- **谁能修改**：锁定后任何一方都不能改；verifier 用上一步锚点交叉核对。
- **失败行为**：与链上锚点不一致 → 本步直接拒绝，不进入见证准备。
- **传递给下一步**：`ictx_i`、`x_i`。

**`C_{i+1}` 的处理（必须明说，否则又是一处循环）**：

- `new_state ∈ W_pre,i` 决定 `C_{i+1}`。若 `C_{i+1}` 要在 ρ 之前进入 transcript，则它必须由**同一 MPC 执行**在承诺固定之前 authenticated open 得到（**CONDITIONAL / BLOCKED**，依赖 D2）。
- 当前 artifact 不具备该接口（Correction-2 `evidence.md` E5 VERIFIED），因此**默认实现把 `C_{i+1}` 视为证明输出**：它不进入 ρ 的输入，而在阶段 6/7 由 proof 的公开输出给出，并由 R1CS 约束绑定到 `W_pre,i.new_state`。
- 无论采用哪种，`C_{i+1}` 都不得由 prover 在看到 ρ 后自由选取。

---

## 2. 七阶段完整 Transcript

| # | 阶段 | 输入 | 输出 | 谁能看到 | 谁能修改 | 失败行为 | 进入下一步的信息 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Instance binding | 版本、程序 ID、电路 ID、`step_i`、`C_i`、上一步锚点 | `ictx_i`, `x_i` | 全体 + verifier | 锁定后无人可改 | 锚点不符 → 拒绝本步 | `ictx_i`, `x_i` |
| 2 | Witness preparation | 上一步 `new_state` shares、VM 输入、MPC 认证随机带 | `W_pre,i`（含 `r_i`、`r_tape`） | 仅 MPC 参与方（份额级）；verifier 不见 | 参与方在承诺前可形成；承诺后不可改 | 任一参与方拒绝 → abort（固定行为未定义，**BLOCKED**） | `W_pre,i` |
| 3 | Commitment | `ictx_i`, `W_pre,i`, `r_i` | `com_i = Com(Encode(ictx_i‖W_pre,i); r_i)` | `com_i` 公开；`W_pre,i` 秘密 | 锁定后无人可改 | 承诺计算失败 → abort | 已固定的 `com_i` 字节串 |
| 4 | Challenge derivation | `domain_k`, `ictx_i`, `com_i`, `transcript_context` | `ρ₁,ρ₂ ∈ F*` | `ρ` 公开；verifier 可重算 | 无人可改（哈希确定） / 交互式变体由挑战者采样 | `ρ=0` → 域分离计数器加一后重哈希 | `ρ₁,ρ₂` |
| 5 | Proof generation | `pp`, `x_i`, `W_pre,i`, `ρ`, `W_post,i` | `π_i` | `π_i` 公开 | prover 计算；不得改 `x_i`/`com_i`/`ρ` | 证明构造失败 → abort | `π_i` |
| 6 | Verification | `x_i`, `com_i`, `ρ`, `π_i`, `transcript_context`, 锚点 | accept / reject | 全体（公开可验证） | 无人 | 任一检查失败 → reject | accept 标志 |
| 7 | State advancement | accept 标志, `C_{i+1}`, `Hist_{i+1}` | 新锚点 `(step_{i+1}, C_{i+1}, Hist_{i+1})` | 公开 | 无人（accept 后确定） | reject → 保留旧锚点，记录固定格式 abort 事件（格式未定义，**BLOCKED**） | 下一步 `ictx_{i+1}` |

阶段 6 的具体检查：

1. 重算 `ρ_k = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)`，与证明所用 ρ 逐字节一致；
2. 检查 `com_i` 的承诺绑定关系（若承诺在电路内验证，则作为约束；否则需外部验证接口 → BLOCKED）；
3. 验证 `π_i` 的约束满足（含 `A_k = B_k` 指纹、Merkle 路径、stash 转换）；
4. 检查 `step_i`、`C_i → C_{i+1}`、`C^{Hist}` 与链上锚点连续（V1–V6，**跨步 verifier chain 保持 BLOCKED**）；
5. 不接触 witness / nonce / 路径明文。

---

## 3. Fiat–Shamir 与交互式挑战的区别

### 3.1 Fiat–Shamir（本轮默认）

- **挑战来源**：`ρ_k = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)`，不含任何交互式消息。
- **必须声明的假设**：Random Oracle Model（ROM）；承诺 `com_i` binding（且为 witness 隐私需 hiding）；哈希输出在 `F` 中近似均匀；transcript 编码无歧义。
- **编码与域分离**：所有输入以长度前缀 + 定长域元素编码序列化；`domain_1 = "stash-fingerprint-rho1-v1"`，`domain_2 = "stash-fingerprint-rho2-v1"`；`protocol_version` 与 `circuit_id` 必须进入哈希。
- **挑战长度**：`ρ₁,ρ₂` 必须由**两次独立的域分离哈希**产生，每次输出经拒绝采样落入 `F*`。**不得**把单个 254-bit 哈希切成两个域元素——那不是两个独立样本；见 §4.4。
- **多方视图**：所有参与方必须对 `com_i` 字节串有同一视图；`last-party rushing` 问题在纯 FS 中不存在（无交互消息），但** grinding 风险仍存在**（§4.6）。
- **状态**：CONDITIONAL（ROM + 承诺依据未闭合）。

### 3.2 交互式 / 多方 coin-tossing（对照，不采用）

- 挑战由外部 verifier 或 MPC coin-tossing 产生：`r_0…r_{m−1}` 各自 commit → 全部收齐后 open → `ρ = H(r_0‖…‖r_{m−1}‖ictx‖com)`。
- **偏置面**：最后打开者可在看到他人 `r` 后选择是否 open（rushing bias）；任何参与方看到 ρ 后可拒绝继续（选择性 abort）。
- **额外通信**：至少 commit/open 两轮 × m 方 + abort 处理轮；artifact 无此接口（Correction-2 §E5）。
- **状态**：UNKNOWN / BLOCKED（dishonest majority 下无偏置与固定行为 abort 未证明）。

> 不能把“先 commitment 后 challenge”直接写成 soundness 已成立：它只排除了“prover 在已知挑战后选 witness”这一类攻击； grinding、偏置、abort、承诺可替换都还需单独处理。

---

## 4. B1 多项式指纹挑战（任务 C）

### 4.1 被检查的关系

对 `k = 1,2`：

```
A_k = Σ_{u ∈ Old} ρ_k^{enc(u)}
B_k = Σ_{v ∈ New} ρ_k^{enc(v)}
约束 A_k − B_k = 0
```

- `Old/New` 为 stash 的两组 `Q = R + Z(L+1)` 个槽（包含 dummy/空槽，空槽 `enc = 0`）。
- `enc(u) = addr + 2^L·val + 2^{L+B}·leaf + 2^{2L+B}·valid`，`L=20, B=128`。
- 整体编码必要性沿用 `stash-soundness.md` §B6（**VERIFIED** 推导）：只编码地址会漏掉 `val/leaf/valid` 替换。

### 4.2 被承诺的 witness 集合

- `com_i` 承诺 `W_pre,i`，其中包含 `stash`（Old/New 槽）与 `eviction_aux`，因此 `enc` 的取值在 ρ 派生前已固定。
- `A_k, B_k ∈ W_post,i`，不在 `com_i` 内；由 `(W_pre,i, ρ)` 唯一确定（见 `witness-transcript.md` §3）。
- 若 prover 在看到 ρ 后改动 stash，则 `com_i` 的 binding 被破坏；binding 依据见 `commitment-interface.md`（**BLOCKED**）。

### 4.3 挑战空间与 `0^0`

- `F = BN254 scalar field Fr`，`|F| ≈ 2^254`（**VERIFIED** 标准配置，Correction-2 §E4）。
- 挑战从 `F* = F \ {0}` 采样。理由：空槽 `enc = 0`，若 `ρ = 0` 则 `0^0` 无定义；均匀采样命中 0 的概率约 `2^-254`，仍须显式拒绝。拒绝时以域分离计数器加一重哈希。

### 4.4 多项式次数上界与单/双挑战误差

- `enc < 2^169`（**VERIFIED** 算术：`2L+B+1 = 169` bit）。
- 若 `Old ≠ New`（多重集不同），差多项式 `D(z) = Σ_{u∈Old} z^{enc(u)} − Σ_{v∈New} z^{enc(v)}` 非零，且 `deg D ≤ 2^169 − 1`。
- Schwartz–Zippel（标准结论，**INFERRED**）：对均匀 `ρ ∈ F*`，
  `Pr[D(ρ)=0] ≤ deg D / (|F|−1) < 2^169 / 2^254 = 2^-85`。
- **两个独立挑战**：若 `ρ₁,ρ₂` 是独立均匀样本，则
  `Pr[D(ρ₁)=0 ∧ D(ρ₂)=0] ≤ (2^-85)² = 2^-170`。
- 上述 `2^-170` **只是代数误差上界**，且仅在 §4.5–4.6 全部条件成立时有效。旧报告把它写成无条件 128-bit 安全结论，属于**越界表述**，本轮修正为条件结论。

### 4.5 两个挑战是否独立

- **必须**用两次域分离哈希产生：`ρ_k = H("stash-fingerprint-rho"‖k‖ictx_i‖com_i‖context)`，`k∈{1,2}`，各经拒绝采样。
- **不得**用单个哈希输出切成两个 254-bit 元素：切分后的两段来自同一 RO 输出，不是独立样本，且拒绝采样会引入相关性；此时 `(2^-85)²` 的乘积界不成立。
- 若改用顺序派生 `ρ₂ = H(transcript‖ρ₁)`，在 RO 下仍可视作独立（**INFERRED**），但需把 `ρ₁` 写入 transcript，本轮不采用。
- 小阶元素：若 `ord(ρ)` 很小，`ρ^a = ρ^b` 可在 `enc` 范围内碰撞。均匀 `ρ` 落在小阶子群的概率可忽略；若要严格 128-bit 界，实现中应显式拒绝 `ord(ρ) < 2^128` 的元素（**CONDITIONAL**）。

### 4.6 挑战重用与 grinding（本轮新增的关键限定）

- **重用**：`ρ` 绑定 `ictx_i`（含 `step_i`、`C_i`、`circuit_id`、`program_id`、`version`）与 `domain_k`，不得跨步、跨电路、跨用途复用。旧 `π` 重放因根链失配被拒（**CONSTRUCTED**）。
- **grinding**：若 `r_i`（或 `r_tape`）可由 prover 自由重采样，则 prover 可离线尝试 `q_H` 个不同的 `com_i`，挑一个使 `D(ρ)=0` 的挑战。FS 并集界给出有效成功概率约 `q_H · 2^-170`。
  - 以 `q_H = 2^128` 计，`q_H·2^-170 = 2^-42`，**不满足 128-bit 安全**。
  - 因此 `2^-170` 不能无条件作为安全结论。它成立需要：`r_i`/`r_tape` 来自**不可由单方重采样**的认证随机带（→ D2，**BLOCKED**），或增加挑战数。
  - 若增加挑战数 `k`：需 `(2^-85)^k · q_H ≤ 2^-128`；在 `q_H=2^128` 下 `k≥4`。`ACC` 项随挑战数线性增加；**本轮不重算成本**（范围外）。状态 **CONDITIONAL**。
- **多次提交**：prover 提交多个 `com_i` 筛选有利 ρ，等价于 grinding，不能靠“先承诺后挑战”排除。

### 4.7 三层风险必须分开

| 层 | 无害条件 | 本轮状态 |
| --- | --- | --- |
| 代数随机挑战 soundness | `ρ` 在 `F*` 中独立均匀；`enc` 位宽受约束；`com` binding | CONDITIONAL（2^-170 仅在此层成立） |
| FS / ROM 计算安全 | RO 假设、无歧义编码、不可 grinding 的随机带 | BLOCKED（`r_i` 认证生成接口缺失） |
| 多方协议偏置 / abort | 无 rushing bias、无选择性 abort、视图一致 | UNKNOWN / BLOCKED |

---

## 5. 本轮结论

- 去循环顺序本身：**CONSTRUCTED**（七阶段、I1–I4 可审查）。
- `2^-170`：从“无条件结论”修正为“代数层、两独立均匀挑战、且 `com` binding 且随机不可 grinding 条件下的上界”；`q_H=2^128` 下需 `k≥4` 或非可 grind 随机带。旧数字不撤回但**不再作为 128-bit 安全声明**。
- 顺序不等于完整协议：承诺 hiding/binding（BLOCKED）、`r_i`/`r_tape` 认证生成（BLOCKED）、选择性 abort（UNKNOWN）、跨步 verifier chain（BLOCKED）均需另行处理。
