# EXP-DORAM-03-R1 — Merkle 增量状态承诺可构造性验证

> 日期：2026-11-23 · 起点 commit `b88f3db`（EXP-DORAM-03）· 基线 VDORAM artifact `10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 范围：**纸面协议构造 + 符号化复杂度核算**。不写代码、不跑 benchmark、不改 E0/E1/R1 历史数据、不改 EXP-DORAM-02/03 原报告、不改上游源码。
> 标记口径：**VERIFIED** 一手源码/论文直接证据 · **CONSTRUCTED** 已给出可检查的协议构造 · **INFERRED** 有依据的推导 · **UNKNOWN** 无法从固定证据判断 · **BLOCKED** 明确工程/协议缺口。

---

## 0. 一句话结论

**最终判定：HOLD**（详见 `decision.md`）。

Merkle 增量承诺本身可以把“整状态承诺每步 O(N)”降为“每步只重算被访问路径”，且递归 PositionMap 的总路径长度是 `O(log²N / log χ)`，故**没有发现 O(N) 全量更新必然性**，不能 NO_GO。但端到端 GO 仍被两点挡住：

1. **绑定 BLOCKED/UNKNOWN**：要让协作 SNARK 的 witness 与真实 MPC 转换输出是同一次执行，必须有任意方、主动安全、支持线性份额 witness 的 compatible collaborative-SNARK 前端，并让 verifier 强制公开根链。固定 artifact 中回调只落盘 JSON、协作证明外部逐电路手动、verifier 无跨电路串联（沿用 `../exp-doram-02-r1/verifier-chain-check.md` VERIFIED 结论）；固定文献集合内没有 ORAM 状态转换的公开可验证构造实例。
2. **隐私闭合 UNKNOWN**：即使 Merkle 根和 proof size 固定，恶意 prover 的选择性 abort、stash overflow 可观察性、MPC 通信模式与公开 step/access 计数仍未被一份完整协议同时证明为不泄露。给定解析界 `14·0.6002^R` 下，2⁻⁸⁰ 需 `R≥114`，2⁻¹²⁸ 需 `R≥179`，EXP-DORAM-03 中的 `R=89/≈100` 数值不成立（见 `merkle-oram-construction.md` §A3.1）。

---

## 1. 本轮唯一核心问题

> 能否为 Path ORAM 的 Tree、递归 PositionMap、固定容量 Stash 构造增量式状态承诺，使承诺更新、R1CS 状态转换验证和 verifier 跨步串联同时达到 sublinear/polylog，且不向少于阈值的合谋方泄露地址、路径、叶子和操作类型？

必须分开：

- **Correctness**：所有 prover 合谋时，非法状态转换仍被公开验证拒绝；
- **Privacy**：仅 `< t` 方合谋时隐藏访问模式；全体合谋隐私不适用（VDORAM 原威胁模型）。

---

## 2. 文档导航

| 文件 | 内容 |
| --- | --- |
| `README.md` | 本文：范围、结论、导航、硬边界 |
| `merkle-oram-construction.md` | 任务 A：Tree / 递归 PositionMap / Stash / Metadata 的显式状态表示；stash 参数修正 |
| `state-transition.md` | 任务 B：一次完整 `(S_i,address_i,op_i)→(S_{i+1},result_i)` 伪代码与逐步秘密/公开属性 |
| `r1cs-constraints.md` | 任务 C：九族 R1CS 约束、具体哈希参数、参数化约束数估算 |
| `mpc-snark-binding.md` | 任务 D：D1 同执行 witness / D2 独立证明阶段，两条绑定路线对比 |
| `verifier-chain.md` | 任务 E：初始锚点、跨步根串联、历史日志串联、跳步/重放/回滚/分叉防护边界 |
| `privacy-analysis.md` | 任务 F：11×4 隐私泄露矩阵与剩余泄露面 |
| `complexity-accounting.md` | 任务 G：MPC/通信/R1CS/witness/证明/验证/承诺/日志八项成本与基线对比 |
| `literature-evidence.md` | 任务 H：仅围绕点名文献的定向核查（VERIFIED/INFERRED/UNKNOWN） |
| `decision.md` | GO/HOLD/NO-GO 判定、blocker 与停止条件 |

---

## 3. 固定前提（不修改）

沿用 EXP-DORAM-03 §1.2：step 0 不 Fetch；每个非初始 step 恰好一次 Fetch，输入为 `thisRegisters[0]`；`fetch_address` 与 `trace_address` 分离；非内存操作 `trace_address=NegOne`；初始 map 为空、未写地址 Load 返回 0；每步保留 history event；地址域固定 `[0,n−1]`。威胁模型：correctness 下 0 honest、privacy 下 `<t` 合谋；不把客户端—服务器 Path ORAM 安全称作多方 MPC 安全，不把 secret sharing 称作公开可验证性。

---

## 4. 硬边界

- 本目录是**纸面构造**；任何“CONSTRUCTED”都只表示给出了可检查的协议规则，不表示已实现、已实测或已有代码证据。
- MiMC/Merkle 是候选工具，不是结论；Poseidon 未被选为本轮默认哈希，避免把未经固定参数的 `P128Pow5T3` 写成既成事实。
- 不把 Python 参考模型称为 MPC-ORAM；不把普通哈希承诺称为零知识证明；不把宿主层 hash 检查称为 verifier enforcement；不把“同源 witness”称为密码学绑定。
- 不启动原型、不扩展下一轮研究；最终判定后停止。
