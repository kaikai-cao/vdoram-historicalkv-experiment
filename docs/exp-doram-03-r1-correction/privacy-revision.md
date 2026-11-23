# privacy-revision.md — 任务 E：隐私与选择性 abort 重新审查

> 2026-11-23 · 起点 `b1bfe29` · 结合 `stash-soundness.md`、`commitment-hiding.md`、`mpc-witness-binding.md` 修正原隐私矩阵。
> 状态：`HIDDEN` / `LEAKED` / `CONDITIONALLY HIDDEN` / `UNKNOWN`。
> 硬规则：不能仅凭 SPDZ active security 推断整个应用的通信长度和终止行为无泄露。

---

## E0. 四类泄露必须分开

| 类别 | 含义 | 本轮处理 |
| --- | --- | --- |
| 协议层泄露 | 由协议消息/公开输入直接可见 | 由电路形状、root 公开与 witness ZK 决定 |
| 实现层 timing 泄露 | 网络延迟、线程调度、重传、缓存 | proof 语义外，CONDITIONALLY HIDDEN |
| 公开日志泄露 | verifier 看到的 step、root、proof、abort 记录 | 公开输入固定但 abort 行为未闭合 |
| 选择性 abort 泄露 | 恶意方在看到秘密相关条件后拒绝继续 | **未解决**，BLOCKED/UNKNOWN |

---

## E1. 修正矩阵（12 项 × 4 观察者）

| 信息 | 单诚实参与方 | <t 合谋 | 全体 prover 合谋 | 公开 verifier |
| --- | --- | --- | --- | --- |
| 1. 逻辑地址 `fetch_address` | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| 2. 物理 leaf / leaf′ | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| 3. Merkle 路径 | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| 4. Load/Store/NOOP 类型 | HIDDEN | HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| 5. dummy / real Fetch | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| 6. stash occupancy | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| 7. stash overflow | HIDDEN | CONDITIONALLY HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| 8. MPC transcript | CONDITIONALLY HIDDEN | CONDITIONALLY HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| 9. Merkle roots（公开值） | LEAKED | LEAKED | LEAKED | LEAKED |
| 10. 历史记录内容 | HIDDEN | HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| 11. proof 数量 / 长度 / 时间 | LEAKED | LEAKED | LEAKED | LEAKED |
| 12. abort / 掉线行为 | UNKNOWN | UNKNOWN | LEAKED | CONDITIONALLY HIDDEN |

---

## E2. 与上一版矩阵的差异

1. **新增 proof 数量/长度/时间**：固定 proof size 不等于固定证明时间；时间是实现层泄露，不能写 HIDDEN。
2. **新增 abort / 掉线行为**：上一版只在 stash overflow 行隐含；本轮单列并标 UNKNOWN。
3. **stash overflow 在 `<t` 合谋下降级为 CONDITIONALLY HIDDEN**：若恶意合谋方触发选择性 abort，即使隐私阈值未达也可能产生公开终止差异。
4. **Merkle roots 仍为 LEAKED（公开值）**：C3 的秘密 nonce 只降低从 root 反推内容的能力，不改变“root 值公开”这一事实。
5. **历史记录内容 verifier 仍 CONDITIONALLY HIDDEN**：取决于 `Export()` 是否公开；本轮假设只公开承诺。

---

## E3. 逐项说明

### E3.1 地址 / leaf / 路径（1–3）

- 协议层：MPC 秘密索引 + 固定路径读 + one-hot 选择；witness 秘密由 co-SNARK t-zero-knowledge 保护。
- 公开层：D1 的显式路径约束只把路径关系写入 witness，不写公开输入。
- 若 D2 绑定 BLOCKED，则“witness 对应真实执行”无法证明；这影响**完整性**，但对本表“witness 内容是否可见”不直接改标。

### E3.2 操作类型与 dummy Fetch（4–5）

- `[op]` one-hot 秘密，所有操作统一跑完整电路；dummy Fetch append NegOne 行。
- verifier 侧 CONDITIONALLY HIDDEN：若程序公开输出包含明文 op，则升级 LEAKED。

### E3.3 stash occupancy / overflow / transcript（6–8）

- occupancy 固定槽位扫描，HIDDEN。
- overflow：R≥179 只在诚实执行下给出解析界；B1/B2 挑战后恶意方仍可 abort，所以 `<t` 合谋降为 CONDITIONALLY HIDDEN。
- transcript：SPDZ active security 只保证协议消息不泄露秘密；消息长度/轮次固定是**实现约束**，timing 在语义外。

### E3.4 Merkle roots（9）

- C1 确定性 root 可对低熵 bucket 字典猜测；C3 秘密 nonce 条件性缓解。
- 但 root 值公开、每步变化，因此“状态变化发生”公开可见；该事实与秘密无关（每步都变化），但 root 的伪随机性依赖 nonce 与 H，未证明严格隐藏。

### E3.5 历史记录（10）

- 每步 append 一行，dummy 也 append；历史内容在 witness，承诺公开。
- 若 `HistoricalKV.Export()` 被公开给 verifier，则内容 LEAKED；本轮保持上一版假设。

### E3.6 proof 数量/长度/时间（11）

- proof 数量 = T 固定；proof size 由 SNARK 固定。
- proof generation time 随 witness/硬件/负载变化，属于实现层泄露；标 LEAKED 对四类观察者都成立（公开可观察）。

### E3.7 abort / 掉线（12）

- B1 FS 挑战后、B2 coin-toss 后、D2 prove 失败或掉线都可能形成公开中止事件。
- 若中止概率或时点与秘密相关，则构成选择性 abort 泄露。
- 固定 artifact 没有规范 abort 事件；外部证明脚本遇错退出，无法证明恒定 → UNKNOWN / CONDITIONALLY HIDDEN。

---

## E4. 本轮结论

- 协议层的地址/leaf/路径/op/dummy/occupancy 隐私仍然可构造；
- **执行轨迹层未闭合**：挑战后 abort、MPC transcript 长度与 timing、proof 时间、nonce 随机带绑定均未在一处完整证明；
- 因此 GO 条件“隐私模型没有未处理的关键访问模式泄露”**不满足**；但这是 BLOCKED/UNKNOWN，不是 NO_GO 矛盾。
