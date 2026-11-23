# EXP-DORAM-03-R1-Correction — 构造与安全性修正

> 2026-11-23 · 起点 `b1bfe29e5cfee847c903f1504bacbe6fd4ec571b` · 固定上游 `BDS-SDU/vdoram-artifacts` commit `10c90d35464620a35ddb1e2c29d2e8725acedd52`。
> 范围：只修正 R1 的五个技术缺口，不推翻 R1、不扩大文献、不写代码、不跑 benchmark、不启动 Path ORAM 原型。

---

## 0. 本轮目标

验证在补齐成本、stash soundness、commitment hiding、秘密路径绑定与 MPC–SNARK witness 绑定后，是否值得进入最小原型。标记：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED` / `CONDITIONAL_CONSTRUCTION`。**不把构造草案写成已证明安全的协议。**

---

## 1. 文件导航

| 文件 | 内容 |
| --- | --- |
| `README.md` | 目标、基线、导航、结论、差异、未解决问题 |
| `r1cs-cost-revision.md` | 任务 A：12 项 R1CS 成本重算与 `N=2²⁰` 示例 |
| `stash-soundness.md` | 任务 B：随机挑战顺序与 B1/B2/B3 多重集守恒方案 |
| `commitment-hiding.md` | 任务 C：C1–C4 Merkle commitment hiding 比较 |
| `mpc-witness-binding.md` | 任务 D：显式秘密路径 R1CS + MPC→SNARK witness 绑定 |
| `privacy-revision.md` | 任务 E：12×4 修正隐私矩阵与四类泄露分层 |
| `literature-evidence.md` | 定点文献/源码证据，逐条标注“支持/不能支持” |
| `decision.md` | 任务 F：唯一决策、GO 判据、唯一后续技术问题 |

---

## 2. 主要结论

**最终决策：HOLD。**

1. **成本**：旧 `2,798,280` 撤回。按原 stash 单哈希承诺重算为 `6,144,043` µ/步；按推荐 stash-Merkle + B1 为 **`2,524,843` µ/步**；加入秘密 nonce 约 `2,587,363` µ/步。详见 `r1cs-cost-revision.md`。
2. **stash soundness**：原 `ρ=H(x_i)` 顺序错误，撤回；B1 commit-then-challenge 数学 sound 但依赖 witness commitment 接口；B3 确定性匹配无随机挑战但约 `2.60M` µ（整字段编码相等口径 `6.04M`）。
3. **commitment hiding**：确定性 Merkle 不隐藏低熵 bucket；公开盐无效；C3 秘密 nonce 为候选，但只是 `CONDITIONAL_CONSTRUCTION`。
4. **MPC–SNARK 绑定**：D1 路径约束已显式 CONSTRUCTED；D2 端到端输出 shares ↔ witness shares 绑定 **BLOCKED**（无 ORAM 线接口、无每 witness 输入 MAC 覆盖证明、无同执行 co-SNARK 接口）。
5. **隐私**：新增 proof 时间/长度与 abort/掉线两行；选择性 abort 与实现层 timing 仍未闭合。
6. **参与方模型**：仍为任意 m、dishonest majority、active security；未偷改 VDORAM 目标。

---

## 3. 与 R1 的差异

- 保留：Merkle 增量方向、四状态表示、每步无 O(N)、stash 解析界修正、V1–V6 规则、整体 HOLD。
- 修正：R1CS 总成本逐项化；stash 挑战顺序；commitment hiding 从“Merkle 默认绑定”改为条件性 nonce 构造；隐私矩阵 11→12 项。
- 撤回：`ρ=H(x_i)` soundness；“同源 witness”绑定暗示；`2,798,280` 作为可信最终值；“加盐即零知识”的任何表述。

---

## 4. 未解决问题（不允许在本轮启动）

1. 任意方 active-secure compatible co-SNARK 的同执行 witness 接口与 MAC 覆盖证明。
2. witness commitment / 挑战顺序 / nonce 随机带绑定和防重放。
3. 固定行为的 abort / 掉线公开事件，及其与秘密无关的可检查规则。
4. 跨电路 verifier 根、step、历史串联在当前 artifact 的实现。
5. 实现层 timing 与 proof generation time 的固定性。

唯一后续技术问题见 `decision.md` §5；在它闭合前不启动最小原型。
