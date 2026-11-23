# decision.md — EXP-DORAM-03-R1-Correction-3 最终决策

> 2026-11-23 · 起点 `ee75b79ae66f6e69377bbc2b8490c57d40885b17` · 仅就本轮五份文件作判定。
> D2（MPC–SNARK 同执行绑定）与跨步 verifier chain 按任务包要求**保持 BLOCKED**，本轮未尝试解决。

---

## 0. 唯一最终决策：**HOLD**

不是 `GO_TO_MINIMAL_PROTOCOL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：本轮未发现不可消除的协议级矛盾；去循环后挑战由已固定且不含挑战的承诺对象派生，公开验证仍不需要公开秘密地址或路径；成本未重算也未出现新的 O(N) 结构。
- **不 GO**：承诺 hiding+binding 接口与 nonce 认证随机源仍是 `BLOCKED`，而这两项**正是本轮验收的核心对象**，不属于可以被“原型范围隔离”的外部工程接口。把它们隔离出去后，B1 挑战的 soundness 与 witness 隐私都失去依据，不能称为一个完整的协议原型。
- **注意**：任务包允许 D2 与跨步 verifier chain 保持 BLOCKED，但本轮的 GO 条件包括「承诺 hiding+binding 有具体候选或明确 BLOCKED」「nonce 生命周期有完整方案或明确 BLOCKED」。明确 BLOCKED 这两项后，剩余协议定义不足以支撑 GO；HOLD 是唯一自洽结论。

---

## 1. 门槛逐条判定

| 门槛 | 状态 | 依据 |
| --- | --- | --- |
| W_pre 与 challenge 去循环 | **必须通过 → 通过** | `witness-transcript.md` §0–1：撤回 `ρ∈challenge_aux⊆W_i`，改为 `W_pre,i → com_i → ρ → W_post,i → π` 单向依赖；I1–I4 可逐条核对（CONSTRUCTED） |
| Transcript 顺序完整 | **必须通过 → 通过** | `transcript-order.md` §2：七阶段均写明输入/输出/可见者/可修改者/失败行为/传递信息；§3 区分 FS 与交互式挑战（CONSTRUCTED） |
| B1 soundness 假设可审查 | **通过或明确 BLOCKED → 明确条件化** | `transcript-order.md` §4：`2^-170` 被限定为代数层、两独立均匀挑战、`enc<2^169`、`com` binding 条件下的上界；`q_H=2^128` 下需 `k≥4` 或不可 grind 随机带（CONDITIONAL / BLOCKED） |
| Commitment hiding+binding | **具体候选或明确 BLOCKED → BLOCKED** | `commitment-interface.md` §2：确定性 MiMC 无 hiding；`H(x,r_i)` 仅启发式；Pedersen 域不匹配且无实现；L1 可作 binding 但 L2/L3 无已定义方案 |
| Nonce 生命周期 | **完整方案或明确 BLOCKED → BLOCKED** | `commitment-interface.md` §3：保留/刷新算术 CONSTRUCTED；生成、认证分发、防 grinding、固定行为 abort 均 BLOCKED |
| D2 同执行 MPC–SNARK witness 绑定 | **保持 BLOCKED** | 本轮未触碰；Correction-2 §E5 VERIFIED 显示只落盘 + 外部逐电路证明 |
| 跨 step verifier chain | **保持 BLOCKED** | 本轮未触碰；ρ 的域分离只为防止挑战复用，不构成 verifier 链 |

---

## 2. 本轮完成的三件事

### A — 去循环（`witness-transcript.md`）

- 撤回 Correction-2 中 `challenge_aux` 含 `ρ₁,ρ₂` 的定义。
- 定义 `W_pre,i` 九个字段及分类：秘密 witness / 纯随机量 / 跨步保持 / 绑定 ictx / 是否进入状态。
- `com_i = Com(Encode(ictx_i‖W_pre,i); r_i)`；`ρ_k = H(domain_k‖ictx_i‖com_i‖context)`。
- `W_post,i = (A_k,B_k)` 由 `(W_pre,i,ρ)` 唯一确定，不进 `com_i`，不会反向改变承诺对象；若引入自由 `W_post`，必须新增挑战后承诺轮（未定义 → BLOCKED）。
- 明确 `r_i`、`r_tape` 只用于承诺/随机源，`r_i` 不进入 ORAM 状态；`C_{i+1}` 仅在挑战前认证 open 时才进 transcript，当前 artifact 下默认作为证明输出。

### B — Transcript 与指纹（`transcript-order.md`）

- 七阶段顺序 +  FS/交互式区别；ROM、编码、域分离、拒绝采样、两次独立哈希的要求全部写明。
- 指纹检查 `A_k = B_k (k=1,2)`；`enc<2^169`；单挑战 ≤ `2^-85`；双挑战 ≤ `2^-170` **仅在独立均匀条件下成立**。
- 新增 grinding 限定：prover 可重采样 `r_i` 时 `q_H·2^-170`，`q_H=2^128` 下不满足 128-bit；需 `k≥4` 或不可 grind 随机带。
- 重申：先承诺后挑战不等于完整 soundness 证明。

### C — 承诺接口与随机量（`commitment-interface.md`）

- 区分 L1 状态根 / L2 `W_pre` 承诺 / L3 随机带承诺；Merkle root 不天然 hiding。
- 三类承诺逐项对照 binding、hiding、字典攻击、随机源、域兼容、verifier 可见信息、跨步绑定、artifact 实现。
- 生命周期表 + 五个攻击面（替换 nonce、跨 witness 复用 nonce、跨 step 复用 com、选择性 abort、多次提交 grinding）逐项给出条件防御或 BLOCKED。

---

## 3. 相对 Correction-2：保留 / 修正 / 撤回

### 保留
- Merkle 路径方向修正（`d=0` 左 / `d=1` 右、`H(h^L,h^R)`）与 eviction 成本（`769,670`、`2,635,246`、`2,697,766`）；
- `R≥114/179`、`ρ=H(x_i)` 撤回、D2 BLOCKED、跨步 verifier chain BLOCKED；
- 三层承诺区分、整体 `enc` 编码、选择性 abort 未解决、整体 HOLD。

### 修正
- `W_i` 拆为 `W_pre,i` 与 `W_post,i`，承诺对象不再含 ρ；
- 七阶段 transcript 补齐可见性/修改权/失败行为；
- `2^-170` 从无条件结论改为条件化代数界，并补充 grinding 并集界；
- `C_{i+1}` 进入 transcript 的前提被显式限定为“挑战前认证 open”。

### 撤回
- `challenge_aux` 含 `ρ₁,ρ₂` 的旧定义；
- 把 `2^-170` 当作 128-bit 安全声明的表述；
- 用单个 254-bit 哈希切成两个挑战元素的任何暗示；
- “先 commitment 后 challenge 即完成 soundness”的暗示。

---

## 4. 最小阻塞项（只留两条）

1. **L2/L3 承诺与不可 grind 的认证随机源**：给出一个在 `Fr` R1CS 后端可实现、同时具备明确 hiding 与 binding 依据的 `com(W_pre,i)`，并让 `r_i`/`r_tape` 来自单一 MPC 执行的认证随机带且不可由单方重采样；否则 B1 挑战既不可信也泄露 witness。
2. **D2 同执行绑定 + 固定行为 abort + 跨步 verifier chain**（前序遗留，BLOCKED）：ORAM 输出份额、辅助 witness 份额、公开根与证明输入使用同一批已认证线值；证明失败/掉线形成与秘密无关的固定长度事件；verifier 强制 `C_{i+1}^{out}=C_{i+1}^{in}` 与 step/History 连续。

第 1 条是本轮验收的核心未闭合项，第 2 条是前序遗留。两条闭合前不启动最小协议原型；若证明第 1 条在固定威胁模型下不可构造，才重新评估 NO_GO。

---

## 5. 证据标记小结

- **VERIFIED**：MiMC 65 轮/SBox=7 与 gadget 目录无承诺实现（沿用 Correction-2 §E1/E2）；`enc<2^169` 与域大小算术。
- **CONSTRUCTED**：`W_pre/W_post` 拆分、七阶段顺序、生命周期表、依赖图与检查项。
- **INFERRED / CONDITIONAL**：Schwartz–Zippel 单/双挑战误差、ROM 下 ρ 独立性、Pedersen 安全定义与域不匹配、`com` binding 推导。
- **UNKNOWN / BLOCKED**：`com(W_pre,i)` 的 hiding 规约、认证随机带接口、MAC 对 witness 输入的覆盖、选择性 abort、 grinding 下的有效安全位、跨步 verifier chain、D2。

---

## 6. 停止条件

五份文件完成；提交推送后停止。不写 ORAM 电路、不跑 benchmark、不扩展文献、不启动原型、不重开 D1/Eviction 审查。
