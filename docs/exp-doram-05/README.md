# EXP-DORAM-05 — B2 私有盐承诺安全模型修正与认证随机源设计

> 2026-11-23 · 起点 `ca26127f156d43c7f09c19435e34a627e1bf3f80` · 固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52` · 最终决策 **HOLD**。

---

## 1. 本轮目标与范围

只回答两个问题，不扩展：

1. 冻结接口 `com_i = H(x_i‖s_i)`、`s_i` 不公开 —— **究竟能给出什么 hiding 保证**？EXP-DORAM-04 引用的 Lemma 17 是否适用？
2. 能否为 `s_i` 设计**与现有 MPC 执行模型相容的认证随机源接口**，使恶意参与方不能单方面选择、重采样或偏置？

**不做**：不重调研四条承诺路线；不重算 ORAM/Merkle/Eviction/Stash 成本；不做原型；不跑 benchmark；不重开 D2、跨步 verifier chain、完整选择性 abort；不修改历史文档或上游。

**两个不预设**（任务硬约束，已遵守）：不预设 `s_i` 必须 8 个 Fr；不预设私有盐构造已满足 hiding。两者都在下面被独立推导，而非继承。

---

## 2. 冻结接口（逐字沿用 Correction-4，不得改）

```
ictx_i   = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)
W_pre,i  = (old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i)  // 8 字段
s_i      = commitment_blinding_randomness     // ∉ W_pre,i；秘密；不作 ρ 种子
x_i      = Encode(ictx_i ‖ W_pre,i)
com_i    = MiMCCommit(x_i, s_i)               // B2 候选：H(x_i‖s_i)
rho_k    = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)
```

约束：`s_i` 与 `r_tape,i` 独立、不得复用；`s_i` 不进 ORAM 状态、不公开；`attempt_i` 仍是公开上下文的一部分，但**不**被当作防选择性 abort 的完整机制。

---

## 3. 文件导航

| 文件 | 任务 | 一句话结论 |
| --- | --- | --- |
| `hiding-model.md` | A | 公开盐/私有盐/标准承诺三类严格区分；Lemma 17 具体引用 UNKNOWN、"8 Fr"撤回；给出显式 ROM 游戏 `Adv≤q·2^{-ℓ_s}` |
| `rom-analysis.md` | B | MiMC 65 轮 d=7 低于设计推荐 91 轮、次数 `2^182.5<p`；RO 仅启发式；CRH 与 RO 是两种不同要求 |
| `randomness-protocol.md` | C | R1 不合格 / R2 有 abort 偏置 / **R3（SPDZ F_PREP）推荐**；四概念分离 + 伪代码接口；artifact 层 BLOCKED |
| `cost-model.md` | D | `μ_com(k)≈260·(L_x+k+C_tag)+C_enc`；`Δμ=260·k`，`k=2` 已足（+520 µ）；不编造精确总数 |
| `decision.md` | E | **HOLD**；GO 六条件 1 满足 / 2 部分 / 1 规则满足 / 2 BLOCKED；三大阻塞按优先级列出 |

---

## 4. 主要结论速览

- **Lemma 17 是否适用其"8 Fr"结论**：**否，已撤回**。Unruh 2015/361 的 canonical commitment 承诺值是 `c=H(m‖u)`、`u` 在承诺阶段保密（与私有盐相符）；Exact lemma 与 `|Y|≤2^{ℓ_u/8}` 未从一手 PDF 核实（Cloudflare），且"返回 `(c,u)`"表述与 hiding 断言内部矛盾。结果：不预设 8 个 Fr，改为可复算 ROM 界。
- **私有盐 hiding 最终结论**：抽象 RO 层为**受限但可证明的计算 hiding**，`Adv≤q·2^{-ℓ_s}`；`k=2`（506 bit）给 `2^{-378}`，`k=1`（253 bit）约 `2^{-125}` 略低于 128-bit；统计 hiding 需 `κ+2λ≈509 bit`（约 2 Fr）；低熵消息在私有盐下**不致命**。落到 MiMC 实例化后退化为**启发式 hiding**。
- **MiMC 安全边界**：一手源码 65 轮 / SBox=7 / 输出 1 个 `Fr`；素数域设计准则 `ceil(253/log2 7)=91` 轮 > 65，达成次数 `2^182.5 < 2^253`；GF(2^n) 攻击不迁移到素数域；具体 128-bit 抗碰撞 **UNKNOWN**，不得凭 253-bit 输出宣称。
- **认证随机源**：协议层 R3（SPDZ `F_PREP.Rand` + IT-MAC + 一次性 `randomness_id` + `attempt_i` 作废）CONSTRUCTED；artifact 层无 `F_PREP.Rand` 接口、无台账、无 MAC→witness 通道 → **BLOCKED**。`attempt_i` 不消除选择性 abort。
- **B2 成本**：承诺增量 `Δμ=260·k`；`k=2` 增量 +520 µ 已足够；`k=8` 多花 1560 µ 无 RO 层安全收益。`L_x/C_enc/C_tag` 未冻结 → 只给符号公式。

---

## 5. 证据与标记纪律

- 标记：`VERIFIED` 一手论文/源码 · `CONSTRUCTED` 本轮设计 · `INFERRED` 明确前提推导 · `CONDITIONAL` 依赖未实例化假设 · `UNKNOWN` 证据不足 · `BLOCKED` 接口缺失。
- 一手来源优先级：原始论文（Unruh 2015/361；Albrecht 等 MiMC ePrint 2016/492；SPDZ ePrint 2011/535；ePrint 2022/1302、2025/789、2019/426、2020/182、2019/812、2024/1074）→ 固定 artifact 源码 → 必要教材/标准。
- **未核实的一律不写 VERIFIED**：Lemma 17 的 Exact 文本、`|Y|≤2^{ℓ_u/8}` 不等式、MiMC 具体安全位 —— 均 UNKNOWN。

---

## 6. 未解决问题（最多三个，详见 `decision.md` §4）

1. 认证随机源的 artifact 接口（BLOCKED，最高优先）。
2. MiMC 作为 `H(x‖s)` 的实例化安全裕度（UNKNOWN）。
3. 同一份 `W_pre,i` 在承诺与 ORAM 约束中的实现级一致性（UNKNOWN，属 D2；`Encode`/chaining 未冻结）。

---

## 7. 停止条件

只新增本目录六份文件；提交推送并核对本地/远端 SHA 与工作区 clean 后立即停止。不启动原型、不追加任务、不重开已冻结审查分支。
