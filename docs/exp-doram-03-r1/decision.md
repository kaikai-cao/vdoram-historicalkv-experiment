# decision.md — EXP-DORAM-03-R1 最终判定

> 2026-11-23 · 起点 commit `b88f3db` · 判定对象：**Merkle 增量状态承诺能否把 ORAM 状态承诺 / R1CS 转换证明 / verifier 跨步串联同时做到 sublinear，且不牺牲 MPC 访问隐私**。
> 标记：**VERIFIED** 源码/论文证据 · **CONSTRUCTED** 本轮完整规则 · **INFERRED** 有依据推导 · **UNKNOWN / BLOCKED** 未闭合。

---

## 0. 最终结论

**HOLD。**

不是 `GO_TO_MINIMAL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：本轮给出了完整的 Merkle-Path ORAM 状态构造（`merkle-oram-construction.md`）、单步转换（`state-transition.md`）、九族 R1CS 约束（`r1cs-constraints.md`）和两条绑定路线（`mpc-snark-binding.md`）。关键反证成立：**存在逐路径增量更新，未发现“承诺必然 O(N) 全量更新”的协议矛盾**；R1CS 中叶子/路径/操作类型保持为秘密 witness，不要求公开秘密地址才能验证。Keller–Scholl（VERIFIED L2）仍提供任意方、dishonest-majority、active-secure 秘密索引的存在性依据。因此任务包 §11 的 NO_GO 条件均不满足。
- **不 GO**：GO 的 8 条中，第 4（MPC 输出与 SNARK witness 的密码学绑定）、第 5（verifier 跨步串联在当前执行链路上）、第 6（执行轨迹隐私在恶意 abort 场景）未闭合。给出规则 ≠ 已绑定/已实现/已证明无泄露。
- **具体 NO_GO 对象不变**：EXP-DORAM-02-R1 的 narrower NO_GO（直接移植现有 2–3 方 DORAM 且不改 VDORAM 执行/证明契约）继续有效；它**不是**整体研究问题的 NO_GO，核心问题仍 HOLD。

---

## 1. GO 判据逐条核对

| # | GO 条件 | 本轮状态 | 判定 |
| --- | --- | --- | --- |
| 1 | Tree / PositionMap / Stash 状态表示完整 | A1–A4 给出 bucket/slot/递归层/occupancy/元数据编码（CONSTRUCTED） | ✅ |
| 2 | 单步状态转换完整 | B0–B4 给出 11 步伪代码，逐步标注秘密/公开与成本（CONSTRUCTED） | ✅ |
| 3 | Merkle 更新与 R1CS 验证关系完整 | 九族约束 C1.1–C1.9 + sibling 相等 + 具体 MiMC 参数（CONSTRUCTED/INFERRED） | ✅ |
| 4 | MPC 输出与 SNARK witness 有明确密码学绑定 | D1 协议层 CONSTRUCTED；当前 artifact 只落盘 JSON、外部逐电路证明、无 verifier 串联（BLOCKED）；D2 具体机制 UNKNOWN | ❌ |
| 5 | Verifier 跨步状态链完整 | V0–V6 规则 CONSTRUCTED；固定 artifact 未提供（BLOCKED，沿用 VERIFIED 核查） | ❌（工程层） |
| 6 | `<t` 合谋访问模式隐私有明确协议依据 | 地址/叶子/路径/dummy 在协议层 HIDDEN；但恶意 prover 选择性 abort、MPC transcript 与 co-SNARK t-zero-knowledge 实例未闭合（UNKNOWN） | ⚠️ 未闭合 |
| 7 | 每步端到端 sublinear/polylog 估算可信 | `ΣL_j=O(log²N/logχ)`；示例 ≈2.80M 乘法约束/步，无 O(N) 项（CONSTRUCTED） | ✅（但常数大，非实用结论） |
| 8 | 没有遗漏全量扫描或隐藏 O(N) | G4 显式检查：线性 pos 索引/全树重算/整状态 hash 均已排除；终态排序是 O(T log²T) 非 O(N) | ✅（以实现遵守为前提） |

**GO 阻塞项 = 4、5、6。**

---

## 2. 方案构造结论

| 方案 | 结论 | 说明 |
| --- | --- | --- |
| **A：秘密分享 Path ORAM 状态** | CONSTRUCTED（协议层）/ BLOCKED（当前 artifact） | 状态覆盖 Tree+递归 pos+Stash+Meta；秘密索引必须走递归 oblivious array；任意方安全依赖 Keller–Scholl（VERIFIED 存在性） |
| **B：任意方 MPC-ORAM 子协议 + 公开证明层** | CONSTRUCTED（同构接口）/ BLOCKED（绑定与 verifier） | 与 A 在 `R_i`+V1–V6 层同构；差异在 witness 生成/绑定，D1 仍有工程缺口 |
| **Merkle 作为承诺工具** | 候选成立（未否决） | 每步只重算 `Σ_j(2L_j+1)` 节点；R1CS 用 auth path + sibling 相等；不计算整棵树 |

---

## 3. Stash 参数修正（必须显式记录）

任务给定解析界 `Pr[|S|>R] ≤ 14·0.6002^R`：

```
log₂(14·0.6002^R) ≈ 3.807355 − 0.736485 R
2⁻⁸⁰  ⇒ R ≥ 113.794 ⇒ R = 114
2⁻¹²⁸ ⇒ R ≥ 178.968 ⇒ R = 179
```

EXP-DORAM-03 中的 `R=89（2⁻⁸⁰）/≈100（128-bit）` **错误**，本轮修正。另记来源冲突：`docs.rs/oram` 写明 `Z=4, SO=89 suffices for 2^{-80}`（来自原论文 Figure 3 的实验/保守估计），但不是该解析界的推论。理论界不得直接当实现安全参数。

---

## 4. Merkle / R1CS 估算摘要

- 默认哈希：VDORAM artifact 的 MiMC（65 rounds，SBox=7，VERIFIED 源码）；`H(k)=260k` 乘法约束（1 次 encrypt = 260；x⁷ 需 4 乘）。
- 参数示例：`N=2²⁰, χ=4, Z=4, R=179` → `D=10`，`ΣL_j=110`；Merkle 父 hash 220 次、bucket hash 120 次、stash root 10 次。
- 乘法约束：hash 部分 `2,475,200`，ORAM 算术部分 `323,080`，合计 **≈2,798,280/步**。
- 递归 PositionMap 成本已计入：`Σ_j L_j = O((log₂N)²/(2log₂χ))`；**没有 O(N)/步项**。若有实现要求全局一致性重算，真实成本 O(N·Z)/步，GO 失效。
- Poseidon/P128Pow5T3 未被选作默认；固定证据内无完整参数集，写“使用 Poseidon”只能标 UNKNOWN。

---

## 5. MPC–SNARK 绑定结论

- **D1（同执行 witness）**：在 compatible collaborative-SNARK 前端 + 主动安全任意方 MPC + 根/步/R1CS 三重约束下，可构造“转换输出 shares = witness shares = 下一步状态 shares”；恶意替换、重放、旧状态提交由公开根、step 与 knowledge soundness 拦截（CONSTRUCTED）。
- **当前 artifact**：回调只落盘 JSON、外部逐电路手动证明、`SelfVerify()` 是单电路调试、verifier 无跨电路串联（VERIFIED）。故 D1 工程层 BLOCKED。
- **D2（独立证明阶段）**：必须额外具备份额认证/MAC + commitment 开启绑定 + anti-replay + anti-fork；固定集合内无直接机制，标 UNKNOWN，不写成既成事实。
- **硬规则执行**：本轮未用“同源 witness”替代密码学绑定，也未把宿主 hash 检查写成 verifier enforcement。

---

## 6. 隐私泄露矩阵摘要

完整 11×4 矩阵见 `privacy-analysis.md`。要点：

- `<t` 合谋下：逻辑地址、leaf、路径、操作类型、dummy/real、PositionMap 更新、stash occupancy/overflow、历史内容均为 HIDDEN（部分为条件性）；
- 全体 prover 合谋：上述多为 LEAKED——这是 VDORAM 威胁模型预期，不是缺陷，也不声称全体合谋仍隐私；
- 公开 verifier：操作类型、overflow、MPC transcript、HistoricalLog 为 CONDITIONALLY HIDDEN；Merkle root 值与 step/accessCount 为 LEAKED；
- 明确结论：**secret-shared ≠ 访问模式自动隐藏；root 公开 + proof 固定大小 ≠ 执行轨迹无泄露**。

---

## 7. 复杂度表摘要

详见 `complexity-accounting.md`。每步成本：MPC 计算/通信 `O(polylog N)`（常数大）；R1CS ≈2.80M 乘法约束（示例）；witness 只含路径/stash/auth；验证 `O(D)` 公开输入 + 单 proof；承诺更新 `Σ_j[(L_j+1)H(4Z_j)+L_jH(2)+H(4R_j)]`；历史日志每步 1 次 hash。基线为 `O(T²)` 在线查询 + `O(T log²T)` 排序；本构造保留终态排序，只消除在线线性扫描。`9.4–51.8×` 是旧的双结构参考数据结果，不是 ORAM 数据。

---

## 8. 最关键 blocker（只留两个）

### B1 — 真实执行的绑定与 verifier 强制链未闭合（BLOCKED / UNKNOWN）

D1 协议规则已给出，但在固定威胁模型下，还需要证明/实现：**任意方 active-secure compatible collaborative-SNARK** 的消费 witness 确实是 ORAM 转换同执行的线值，且 verifier 强制 `(C_i,C_{i+1},step_i,H_i,H_{i+1})` 串联。当前 artifact 只落盘 JSON、外部逐电路证明、无跨电路 verifier 检查；固定文献集合没有该 ORAM 状态转换实例。没有它，即使每步 R1CS 正确，也无法证明“证明的状态机就是 VM 实际使用的状态机”。

### B2 — 执行轨迹隐私在恶意 abort / 通信模式下未闭合（UNKNOWN）

固定形状电路与 t-zero-knowledge 的协议依据已有，但恶意 prover 的选择性 abort、stash overflow 可观察性、MPC transcript 的轮次/长度与 co-SNARK 实例级 t-zero-knowledge 尚未被一份完整协议同时证明。不能用“数据是 secret-shared”或“proof size 固定”跳过这一项。

> 这两个 blocker 正好对应负责人验收重点 2 与 3；验收重点 1（Merkle 增量与隐藏 O(N)）本轮已闭合。

---

## 9. 停止条件与下一步（不执行）

- **本轮到此停止**：不启动最小原型、不写 ORAM 电路、不跑 benchmark、不扩展下一轮文献调研。
- 若继续，只允许一个**有边界的理论任务**：在任意方 compatible collaborative-SNARK 中实例化 D1（公开输入格式、witness 分片映射、份额认证与 verifier 根链规则），同时给出无数据相关 abort 的 stash overflow 处理；两点闭合后才重新判定 GO。
- 若该任务仍无法证明，则按真实 blocker 决定停止或收窄目标，不无限扩展检查项。
