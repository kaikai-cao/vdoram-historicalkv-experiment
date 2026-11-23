# README — EXP-DORAM-03-R1-Correction-3

> 2026-11-23 · 起点 `ee75b79ae66f6e69377bbc2b8490c57d40885b17`
> 固定 VDORAM 上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 范围：**只修 B1 transcript 的循环定义、明确挑战与证明电路的接口**。不重做 Merkle 路径、不重算 Eviction、不写代码、不跑 benchmark、不扩展文献、D2 保持 BLOCKED。

---

## 1. 本轮目标与唯一验收点

> **挑战必须由一个已经固定、且不包含该挑战本身的承诺对象派生出来。**

Correction-2 把 `ρ₁,ρ₂` 放进 `W_i.challenge_aux`，同时又令 `ρ = FS(... || com(W_i))`，形成 `ρ ∈ W_i → com(W_i) → ρ` 的循环。本轮把承诺对象拆成挑战前 `W_pre,i` 与挑战后 `W_post,i`，并给出完整、可审查的 commitment–challenge–proof transcript。

---

## 2. 文件导航

| 文件 | 内容 |
| --- | --- |
| `witness-transcript.md` | §0 撤回旧循环定义；§1 去循环不变量 I1–I4；§2 `W_pre,i` 九字段分类与 ictx 绑定；§3 `W_post,i=(A_k,B_k)` 唯一确定性；§4 依赖图与检查清单 |
| `transcript-order.md` | §1 实例绑定与 `C_{i+1}` 前提；§2 七阶段（输入/输出/可见者/可修改者/失败行为/传递信息）；§3 FS 与交互式挑战；§4 B1 指纹 soundness、次数上界、`2^-170` 条件化、独立性与 grinding |
| `commitment-interface.md` | §1 L1/L2/L3 三层承诺；§2 三类承诺方案对照；§3 nonce/随机带生命周期表与五个攻击面；§4 接口判定 |
| `decision.md` | 门槛逐条判定、唯一最终决策、相对 Correction-2 的保留/修正/撤回、两条最小阻塞项 |

---

## 3. 主要结论

- **去循环**：`W_pre,i → com_i → ρ₁,ρ₂ → W_post,i → π_i → verify → C_{i+1}` 单向依赖；`com_i` 不含 ρ，`W_post,i` 由 `(W_pre,i,ρ)` 唯一确定。状态 **CONSTRUCTED**，通过门槛。
- **Transcript**：七阶段完整；FS 需 ROM、无歧义编码、域分离、两次独立哈希与拒绝采样；先承诺后挑战不等于完整 soundness。状态 **CONSTRUCTED**，通过门槛。
- **`2^-170`**：限定为代数层、两独立均匀挑战、`enc<2^169`、`com` binding 条件下的上界；prover 可重采样 `r_i` 时有效界为 `q_H·2^-170`，`q_H=2^128` 下不满足 128-bit，需 `k≥4` 或不可 grind 随机带。旧的无条件安全声明被撤回。状态 **CONDITIONAL / BLOCKED**。
- **承诺接口**：确定性 MiMC 只有 binding；随机 hash 只有启发式 hiding；Pedersen 有明确 hiding/binding 但 `Fr` 电路需非原生 `Fq` 算术且 artifact 无实现。L1 状态根可用，L2/L3 **BLOCKED**。
- **Nonce 生命周期**：未触碰保留 / 触碰刷新的算术规则 CONSTRUCTED；认证生成、防替换/重放、固定行为 abort、防 grinding 均 **BLOCKED**。
- **最终决策**：**HOLD**。阻塞项为 L2/L3 承诺与不可 grind 的认证随机源、以及前序 D2 + verifier chain。

---

## 4. 与 Correction-2 的差异

- **保留**：Merkle 路径左右顺序、Eviction 成本（`769,670`、`2,635,246`、`2,697,766`）、`R≥114/179`、`ρ=H(x_i)` 撤回、D2 BLOCKED、跨步 verifier chain BLOCKED、整体 HOLD。
- **修正**：`W_i` 拆分、七阶段顺序与可见性、`2^-170` 的条件化、`C_{i+1}` 进入 transcript 的前提。
- **撤回**：`challenge_aux` 含 ρ 的定义；把 `2^-170` 当无条件 128-bit 安全；单哈希切分出两个挑战的暗示；“先承诺后挑战即完成 soundness”的暗示。

---

## 5. 未解决问题（本轮不扩范围）

1. `com(W_pre,i)` 在 `Fr` R1CS 后端上的可实现 hiding + binding 方案；`r_i`/`r_tape` 的认证随机源与不可重采样性。
2. D2 同执行 witness 绑定、每输入份额 MAC 覆盖、固定行为 abort、跨步 verifier chain（前序遗留，保持 BLOCKED）。
3. grinding 下达到 128-bit 所需挑战数 `k` 与相应 ACC 成本重算（本轮明确不重算成本）。

---

## 6. 停止条件

五份文件完成；提交推送、核对本地/远端 SHA 与工作区 clean 后立即停止。不启动原型、不追加 benchmark、不重开 D1/Eviction 审查。
