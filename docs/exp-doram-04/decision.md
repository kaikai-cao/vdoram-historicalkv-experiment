# decision.md — EXP-DORAM-04 最终判定

> 2026-11-23 · 起点 `2556ece2fd040978ad89fd9ed61bd1bc15243947` · 仅就本轮六份文件作判定。
> 本轮只研究 L2 承诺；D2、跨步 verifier chain、选择性 abort 按任务包允许继续 **BLOCKED**，影响在 §5 列明。

---

## 0. 唯一最终决策：**HOLD**

不是 `GO_TO_MINIMAL_PROTOCOL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：没有发现协议级矛盾或威胁模型不可兼容。Pedersen 与 hash 承诺的安全定义本身成立；公开验证仍不需要公开秘密地址/路径；固定 artifact 缺少 gadget **不是** NO_GO 理由（任务包明确禁止据此判 NO_GO）。非原生算术有成熟文献路径（10×–600× 有界），不是不可消除的障碍。
- **不 GO**：GO 六条件无任一候选同时满足。最好的 B2 满足“具体构造”“局部改造”，但 hiding 只有 ROM 启发式依据、`s_i` 随机源执行层 BLOCKED；安全最强的 B1 opening 需非原生 gadget（artifact 无）且成本 UNKNOWN。

---

## 1. GO 门槛逐条核对（取各候选最优表现）

| GO 条件 | 结论 | 依据 |
| --- | --- | --- |
| ① 至少一个具体承诺构造 | **满足** | B1 `g^d h^{s_i}`（Pedersen+CRH）；B2 `H(x‖s_i)`（MiMC），均有完整定义 |
| ② Hiding + binding 明确依据 | **部分** | B1 两者清晰（perfect + DL，VERIFIED）；但需在 BLS12-377 上实例化且 `d=CRH(x)`；B2 hiding 仅 ROM 启发式 |
| ③ Opening verification 完整 | **不满足** | B1 电路内验需非原生（无 gadget）+ `CRH` 未定义；B2 需定义 `Encode`/`H(x‖s)` 封装并扩 `s_i`，本轮未实现 |
| ④ 同份 SNARK witness 绑定接口闭合 | **部分** | B2 电路内同线值在规则层闭合（CONSTRUCTED）；实现 CONDITIONAL；B1/外部桥接 BLOCKED |
| ⑤ 当前后端可实现或改造有界 | **部分** | B2 局部改造（`H(x‖s)` + 8×域元素随机带），有量级成本界；B1/系统级改造 UNKNOWN |
| ⑥ `s_i` 随机源 + grinding 处理 | **不满足** | 联合生成/MAC/不可重采样/失败作废均为 CONSTRUCTED 规则，artifact 无认证随机带接口 → BLOCKED；`q_H·2^-168`（域修正后）未消除 |

**结论：①②③④⑤⑥ 中，完全满足 1 项，部分满足 3 项，未满足 2 项 → HOLD。**

---

## 2. 最优候选

| 标准 | 最优候选 | 理由 |
| --- | --- | --- |
| **安全依据最强** | **B1 — Pedersen `g^d h^{s_i}`（G1/BLS12-377，`d=CRH(Encode(ictx‖W_pre))`）** | 唯一 perfect hiding + 标准 DL binding（Pedersen 1991 VERIFIED）；不依赖 hash 的 RO 假设 |
| **当前后端最接近落地** | **B2 — `com_i = H(Encode(ictx‖W_pre) ‖ s_i)`，`s_i` 扩至约 8 个 `Fr` 元素（≈2024 bit）** | 完全原生 MiMC、局部改造、witness 绑定规则层闭合；代价是 hiding 仅 ROM 启发式 |

**本轮不强行二选一**：B1 与 B2 卡在不同环节（B1 卡非原生 gadget 与成本未知，B2 卡 hiding 归约），二者都共同卡在 `s_i` 随机源。选定哪一个取决于下轮把哪个条件先闭合（见 §6）。

---

## 3. 最大的三个未解决问题

1. **`s_i` 认证随机源（两方案共同、最高优先）**：`s_i` 须由同一 MPC 执行联合生成、带 MAC、任何单方不可重采样、每步独立、失败作废；artifact 只有落盘 R1CS+witness + 外部逐电路证明（Correction-2 §E5 VERIFIED），无此接口。 Closing 此项前，grinding（`q_H·2^-168`）无法处理，任何承诺的 hiding/binding 在协议层都无执行保证。**这是承诺构造之外但决定承诺能否安全使用的必要条件。**

2. **B1 的电路内 opening 验证非原生化（安全优先路线）**：G1(BLS12-377) 标量原生但坐标在 `Fq`(377 bit)，电路内验 `g^d h^{s_i}=C` 需非原生域算术；文献界 10×–600×（ePrint 2025/695 / 2024/265），artifact 无 gadget，具体约束数 UNKNOWN。另需先定义 `d=CRH(Encode(...))` 且证明 CRH 覆盖 8 字段。

3. **B2 的 hiding 严格依据（工程优先路线）**：`H(x‖s_i)` 的 hiding 只在 ROM 下成立（ePrint 2015/361 Lemma 17，需 `s_i ≥ ~2024 bit`），MiMC 当 RO 是启发式假设（ePrint 2024/1074 明示），安全裕度 UNKNOWN。需一个标准模型或有明确归约的、且 `Fr` 原生 cheap 的 hiding 承诺——文献中 KZG/ Pedersen 类有归约但非原生，Poseidon/MiMC 原生但无严格 hiding 归约，这个张力本轮未解开。

---

## 4. 本轮最重要的新发现（影响后续所有工作）

**电路域是 `Fr(BLS12-377)`（253 bit），不是既有报告继承的 BN254 `Fr`（254 bit）。**

- 一手证据：`ArithConfig.cs` 的模数十六进制串精确等于 BLS12-377 标量域 `r`，源码注释 `// BLS12-377`、位宽 `// 253`；ePrint 2022/1396 §2.1 给出同一 `r`；本轮 Python 复算 `(r−1).bit_length()=253`。
- 连带修正：B1 单挑战 soundness `2^-85 → ≈2^-84`，双挑战 `2^-170 → ≈2^-168`（`enc<2^169` 不变）；grinding `q_H·2^-168`（`q_H=2^128` ⇒ `≈2^-40`）。
- 证明系统为 **Plonk + BLS12-377**（论文 ePrint 2025/039 §Implementation + prove 脚本 `-d PlonkCompatCircuitMultiParty`），仓库中的 `groth16/verifier.rs` 是泛型单 proof 快照，与 Plonk 主路径关系 UNKNOWN。
- 后续任何承诺/非原生成本估算都必须用 253-bit 域重算，不得沿用 BN254 的 254-bit 假设。

---

## 5. 遗留 BLOCKED / UNKNOWN（影响端到端，但本轮未触碰）

- **D2** 同执行 MPC–SNARK witness 绑定：BLOCKED（影响承诺所用的“同一份 witness”能否成立）。
- **跨步 verifier chain**：BLOCKED（影响 `com_i`/`C_i` 能否跨步串联）。
- **选择性 abort**：UNKNOWN / BLOCKED；`attempt_i` 只解决“同实例静默重采样”，不解决 abort 泄露。
- **B1 在 BLS12-377 G1 上的实例化细节**、**MiMC 安全裕度**、**`Encode`/`CRH` 具体分块**、**非原生 gadget 实测约束**：均 UNKNOWN。

---

## 6. 下一项最小证据任务（只一件）

**在固定 artifact 上给出 `s_i` 的认证联合生成接口与不可重采样规则，并把 B2 的 `s_i` 扩到 ≥8 个 `Fr` 域元素后，重新计算 `H(x‖s_i)` 的精确 MiMC 约束数。**

- 理由：这是唯一同时卡住 GO 条件 ⑥（grinding）和 ③（opening 实现）的公共项；B2 是局部改造、有量级成本界，先把它的随机源与约束数算清，人才可判断 B2 的 ROM hiding 是否值得接受，或是否必须转 B1。
- 不包含：原型实现、ORAM 扩展、Merkle/Eviction 重算、D2 与 verifier chain 审查、新一轮 ORAM 文献。

---

## 7. 相对 Correction-4 的保留 / 修正 / 撤回

### 保留
- 冻结的 `ictx_i`/`W_pre,i`/`s_i`/`com_i`/`ρ` 定义与七阶段顺序；
- 三随机量（`W_pre`/`s_i`/`r_tape`）角色分离；
- `Encode` 覆盖 8 字段、`s_i` 不公开、不作 ρ 种子、不可重采样的规则；
- 承诺 gadget 缺失、co-SNARK 只落盘单 proof 的既核证据；
- D2 / verifier chain / 选择性 abort 的 BLOCKED 状态与整体 HOLD。

### 修正
- **电路域**：BN254 `Fr` → **BLS12-377 `Fr`（253 bit）**（一手源码纠正）；
- soundness 数字：`2^-85/2^-170` → `≈2^-84/≈2^-168`；grinding `q_H·2^-168`；
- 证明系统标注：主路径 Plonk（非 Groth16），Groth16 verifier 为另存泛型快照；
- 把 Correction-4「Pedersen 因域不匹配不可用」细化为**三形态**（标量原生/坐标非原生/外部桥接）与 10×–600× 有界代价；
- 把「hash 承诺启发式 hiding」细化为**ROM Lemma 17 + `s_i≈8 Fr` 熵长度**的精确条件。

### 撤回
- 「电路域为 BN254、`|F|≈2^254`」及其派生的一切 254-bit 单位假设；
- 「Pedersen 与当前后端绝对不兼容」的一刀切结论（改为有界改造分析）；
- 「`H(x‖s)` 有标准 hiding」的任何暗示（明确为 ROM + 启发式）。

---

## 8. 停止条件

六份文件完成；不写代码、不跑 benchmark、不重算 Merkle/Eviction/stash 成本、不重开 D2/verifier chain/选择性 abort、不启动原型；提交推送并核对本地/远端 SHA 后立即停止。
