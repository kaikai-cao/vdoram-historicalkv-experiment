# commitment-security-model.md — 任务 C：B1 witness commitment 与 C3 秘密 nonce 的统一安全模型

> 2026-11-23 · 起点 `bc6d774` · 纸面安全模型，不实现、不跑基准。
> 标记：**VERIFIED** 固定源码/数学事实 · **CONSTRUCTED** 本轮规则 · **INFERRED** 推导 · **CONDITIONAL_CONSTRUCTION** 依赖未实例化条件 · **BLOCKED** 未闭合。
> 硬规则：不把“加随机盐”写成零知识；不把“commit-then-challenge”写成已完成的安全协议；D2 保持 BLOCKED。

---

## C1. 承诺对象：完整 witness `W_i`

```
W_i = (
  old_state,      // 每层旧 bucket slots、旧 pos-map block、旧 stash slots、旧 meta
  new_state,      // 每层新 bucket slots、新 pos-map block、新 stash slots、新 meta
  path,           // 每层 leaf bits d_t、child hash、被访问 bucket 的 4Z 字段
  siblings,       // 每层 sib_{t+1}，旧/新路径共用同一变量
  stash,          // R 个槽的 (addr,val,leaf,valid) + occupancy bits
  eviction_aux,   // P_{s,t}, ok_{s,t}, u_{t,q,s}, elig_{t,q,s}, sel, no_cand, dummy
  nonce,          // 旧/新 bucket nonce、本步认证随机带 r_tape、nonce 更新辅助值
  challenge_aux   // com(W_i) opening randomness、FS transcript 原料、ρ₁,ρ₂
)
```

| 字段类 | 隐藏？ | 绑定？ | 公开？ | 理由 |
| --- | --- | --- | --- | --- |
| `old_state/new_state` 内容 | 必须隐藏 | 必须（旧→`C_i`，新→`C_{i+1}`） | 否 | 地址、leaf、value 是秘密份额 |
| `path/siblings` | 必须隐藏 | 必须（路径关系由 R1CS 检查） | 否 | 路径即访问模式 |
| `stash/eviction_aux` | 必须隐藏 | 必须 | 否 | occupancy 与选择位泄露访问模式 |
| `nonce` | **必须隐藏** | 必须（旧 nonce 开旧根、新 nonce 开新根） | 否 | 公开 nonce 使盲化失效 |
| `challenge_aux` 中的 opening randomness | 必须隐藏 | 必须 | 否 | 公开即失去 hiding |
| `ρ₁,ρ₂`、`com(W_i)`、`C_i`、`C_{i+1}`、`step_i` | 不隐藏 | 必须 | **是** | verifier 需要；其公开本身须不泄露 |
| `π_i`、proof 长度/轮数 | 不隐藏 | 必须 | 是 | 由证明系统决定 |

**禁止假设**：`com(W_i)` 天然 hiding。确定性 MiMC 向量哈希只给 binding（在 CRH 假设下），不给 hiding。若 `com(W_i)` 公开且不 hiding，低熵 witness 可直接被枚举比对。

三层承诺必须分开：

1. **状态根** `C_i^{Tree/Stash/Top/Meta/Hist}`：binding，**不要求 hiding**（但根伪随机由 nonce 提供）；
2. **见证承诺** `com(W_i)`：binding **且** hiding（供 B1 挑战派生与见证隐私）；
3. **随机带承诺** `com(r_tape)`：binding 且 hiding，供 nonce 刷新与挑战熵来源；其打开/认证必须由同一 MPC 执行提供（D2）。

---

## C2. 三种承诺方案对照

设 `W` 为 `W_i` 的域元素编码，`r` 为随机量。

### C2.1 确定性哈希承诺 `com(W)=H(W)`（MiMC 链式）

- **binding**：在 MiMC 抗碰撞假设下成立（固定 artifact 参数 VERIFIED，安全裕度未评估）。
- **hiding**：**无**。公开 `com(W)` 可对低熵 `W` 枚举比对；跨步相同 `W` 产生相同 `com` → 可关联。
- 字典攻击：可行（若 `W` 熵低于安全参数）。
- nonce 熵：不适用；nonce 公开与否：若放入 `H` 且公开，仍不隐藏。
- 本轮判定：**不可单独用于 `com(W_i)`**。可作状态根（binding 足够），配 C3 nonce 降低根的可关联性。

### C2.2 随机 nonce + MiMC `com(W)=H(W, r_com)`

- **binding**：依赖 `r_com` 被承诺且不可替换；若 prover 可自选 `r_com`，binding 崩溃。
- **hiding**：**启发式**，不是标准承诺的 hiding 定义。随机化 CRH 能稀释字典搜索（攻击者需同时猜 `r_com`），但没有从 MiMC 抗碰撞推出 hiding 的规约；本轮标 `CONDITIONAL_CONSTRUCTION`，不写“已证明 hiding”。
- `r_com` 必须秘密、进入 MPC shares、进入 R1CS（作为 hash preimage 并受 `BIT` 范围约束）；
- 跨步：若 `r_com` 每步由认证随机带刷新，则相同 `W` 不产生相同 `com`；否则仍可关联。
- 重放：旧 `W` + 旧 `r_com` 产生旧 `com`，但 verifier 会把 `com` 与 `step_i`、`C_i` 绑定，重放旧 proof 因根链失败。
- 判定：与现有 MiMC 后端相容，但 hiding 缺严格依据。

### C2.3 Pedersen-like `com(x;r)=g^x h^r`

- **binding**：离散对数假设下计算 binding；**hiding**：`r` 均匀时 perfect/statistical hiding。
- 字典攻击：不可行（hiding 由信息论保证）；`r` 必须秘密；`r` 必须进入承诺验证电路。
- 跨步/可关联：每步独立 `r` → 不可关联；重放需同时满足根链与 `r` 的认证来源。
- **域兼容性**：BN254 标量域 `Fr` 与 G1 坐标域 `Fq` 不同，在 `Fr` 上直接验证 `g^x h^r` 需非原生域算术；若改用基域为 `Fr` 的内曲线，又需要 Artifact 中不存在的曲线 gadget（见 `evidence.md` E2）。固定 gadget 目录仅 19 个文件，无任何 Commitment/Pedersen/Merkle/Poseidon 实现（GitHub API 定点核查 VERIFIED）。
- 判定：`CONDITIONAL_CONSTRUCTION`，且**当前 artifact 无可用实现**；不替换默认 MiMC。

### 对照表

| 项 | C2.1 确定性 MiMC | C2.2 nonce+MiMC | C2.3 Pedersen-like |
| --- | --- | --- | --- |
| binding | CRH（启发式） | CRH + `r_com` 绑定 | DL（明确） |
| hiding | 无 | 启发式，无规约 | perfect/statistical |
| 字典攻击 | 可行 | 需同时猜 nonce，成本↑ | 不可行 |
| nonce 熵 | — | ≥安全参数（如 128 bit） | 域均匀 |
| nonce 公开 | — | 必须秘密 | 必须秘密 |
| nonce 进 R1CS | 否 | 是（preimage + range） | 是（指数） |
| 跨步链接 | 有 | 刷新后削弱 | 无（独立 `r`） |
| 重放防护 | 靠根链 | 靠根链 + 随机带绑定 | 靠根链 + 随机带绑定 |
| 公开根可关联性 | 相同 bucket → 相同 leaf hash | 触碰后刷新；未触碰 leaf 值不变但不公开 | 可设计无关联 |
| `<t` 合谋隐私边界 | witness 由 co-SNARK ZK 保护；`com` 本身泄露 | 合谋 `<t` 不见 `r_com`；全体合谋见 | 合谋 `<t` 不见 `r`；全体合谋见 |
| 判定 | 不用于 `com(W_i)` | 条件候选 | 条件候选，无实现 |

---

## C3. B1 challenge 顺序（完整 transcript）

```
1. MPC 产生并认证 witness 份额
   - 同一 execution 内产出 ⟨W_i⟩ 与 ⟨r_tape⟩；SPDZ MAC 检查通过；
   - ★本步在当前 artifact 为 BLOCKED（D2），以下是条件性规则，不是既成事实。
2. 计算 com(W_i)（含 hiding 随机量）与 com(r_tape)
   - 两者由已认证份额计算，不重新输入外部 shares。
3. commitment 固定
   - (step_i, C_i, com(W_i), com(r_tape), circuit_id) 写入公开 transcript 并锁定；
   - 此后 witness 与随机量不得改动（binding 提供保证）。
4. 派生挑战
   - ρ₁,ρ₂ = FS("stash-multiset" || circuit_id || step_i || C_i
                 || com(W_i) || com(r_tape) || domain_separator)
   - C_{i+1} 若在挑战前已由同一执行 authenticated open 得到，可一并加入；
     不得只由公开实例派生（撤回 ρ=H(x_i)）。
5. 执行多重集指纹约束
   - Σρ_k^{enc(old)} = Σρ_k^{enc(new)}, k=1,2；误差约 2^-170（两挑战）。
6. 协作证明
   - Prove(pp, x_i, w_i) 消费第 1 步同一批线值份额。
7. 验证与状态推进
   - verifier 重算 ρ、验 π_i、检查 V1–V6 根/step/历史连续；
   - 只有全部通过才把 C_{i+1} 作为下一步锚点。
```

| 必答问题 | 回答 |
| --- | --- |
| challenge 不可预测？ | 在 ROM/FS 假设下，com 固定前 prover 不能预知 ρ；若 com 不 binding 或可事后选择随机量，则不成立 → CONDITIONAL |
| com binding？ | 必须有明确依据（CRH 或 DL）；artifact 未提供 → CONDITIONAL/BLOCKED |
| com hiding？ | B1 必须要求 hiding，否则 transcript 泄露 witness；确定性 MiMC 不满足 → BLOCKED |
| 恶意方选择性 abort？ | **未被顺序解决**：看到 ρ 后仍可中止；不破坏 knowledge soundness，但构成可用性/隐私泄露 → UNKNOWN/BLOCKED |
| FS 的 ROM 假设？ | 是；多方设定下还要求各方对 transcript 有同一视图，且无 last-party rushing → CONDITIONAL |
| challenge 重用/跨步重放？ | 由 `step_i`、`C_i`、`circuit_id`、domain separator 域分离，且 ρ 不复用；重放旧 π 因根链失配被拒；若域分离被省略 → BLOCKED |

**结论**：`commit-then-challenge` 的顺序是必要的，但**不等于**已经完成的安全协议；缺失项见上表。

---

## C4. C3 nonce 生命周期

| 问题 | 规则 | 状态 |
| --- | --- | --- |
| 如何生成 | 同一 MPC execution 的认证随机带 `r_tape`，经 MAC 检查；不由单个 prover 本地采样 | **BLOCKED**（artifact 无认证随机带→nonce 接口，D2） |
| 谁知道 | `⟨nonce⟩` 为 m 方份额；`<t` 合谋无完整值；verifier 不见 nonce | CONDITIONAL |
| 每 bucket / 每 step 独立 | 被触碰 bucket 每步刷新；未触碰 bucket 保留旧 nonce（全量刷新是 O(N)，禁止） | CONSTRUCTED |
| 更新 bucket 时旧 nonce | 旧 leaf hash 用旧 nonce 打开 `C_i`；新 leaf 用 `nonce' = nonce + r_t`（域内）并 `BIT` 范围检查 | CONSTRUCTED（算术）/ BLOCKED（`r_t` 来源） |
| 未更新 bucket | nonce 不变；其 leaf hash 不变，但该 leaf 不在公开 transcript 中，verifier 只见根 | CONSTRUCTED |
| 与公开根一起认证 | nonce 是 bucket hash 的 preimage，旧/新 nonce 分别被旧/新根绑定 | CONSTRUCTED |
| 防替换/重放/跨步复用 | 旧 nonce 必须开当前 `C_i`；新 nonce 必须等于 `old+r_t` 且 `r_t` 来自已承诺随机带；`r_t` 用 `step_i` 域分离。缺随机带承诺时 prover 可自选 `r_t` → 可替换/重放 | CONDITIONAL / **BLOCKED** |
| 掉线与 abort | 未定义固定长度、固定轮次的公开 abort 事件；无法证明 abort 与 nonce/秘密独立 | **BLOCKED** |

C3 的 hiding 强度限制：它把低熵 bucket 的字典搜索变成“同时猜 nonce”的搜索，成本约 `2^λ`（λ=nonce 位宽），**不是**信息论隐藏，也不是零知识。

---

## C5. 统一方案与结论

**没有足够依据选定一个在固定 artifact 上可直接落地的完整方案。** 可论证的条件性方案如下：

- **commitment 算法**：`com(W_i) = PedersenLike(W_i; r_com)`（需基域与 `Fr` 相容的内曲线）；暂定替代为 `H(W_i, r_com)`（MiMC，仅启发式 hiding）。
- **输入**：§C1 的 `W_i` 全部域元素；`r_com`、`r_tape` 来自同一 MPC 认证随机带。
- **随机量**：每步独立；`nonce' = nonce + r_t`，`r_t` 域分离于 `step_i`。
- **transcript**：§C3 七步；ρ 由 `com(W_i)` 与 `com(r_tape)` 派生，不从公开实例单独派生。
- **verifier 检查**：重算 ρ；验 π；检查 `C_i→C_{i+1}`、`step_i→step_{i+1}`、`C^{Hist}` 连续；不接触 nonce/witness 明文。
- **安全假设**：`<t` 合谋下 MPC 隐私；com 的 binding+hiding；FS/ROM；nonce 随机带已认证；固定行为 abort。
- **暴露信息**：`C_i/C_{i+1}`、`com`、`ρ`、π、固定形状、step；**不暴露** witness、nonce、路径、stash occupancy。
- **未解决**：com(W) 的 hiding 依据；认证随机带接口；nonce 防重放的形式化；选择性 abort；D2 端到端绑定（保持 BLOCKED）。

**判定**：`CONDITIONAL_CONSTRUCTION`，不能进入 GO；这与 `decision.md` 的 HOLD 一致。
