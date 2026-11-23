# mpc-snark-binding.md — 任务 D：MPC 输出与协作 SNARK witness 的绑定

> 2026-11-23 · 起点 `b88f3db` · 本轮重点。
> 硬规则：**“来自同一程序 / 同源 witness / 同一份份额”本身不是密码学绑定**。必须说明恶意参与方为何不能替换 shares、重放旧状态或提交不一致 witness。
> 标记：**VERIFIED** 一手源码/论文证据 · **CONSTRUCTED** 设计规则 · **INFERRED** 有依据推导 · **UNKNOWN** 固定证据无法判断 · **BLOCKED** 当前工程缺口。

---

## D0. 要绑定的三个对象

```
(1) MPC 实际执行 ORAM 状态转换后的输出 shares:  [S_{i+1}], [result]
(2) 协作 SNARK 使用的 witness shares:            w_0,...,w_{m−1}
(3) 下一步 MPC 使用的状态 shares:                [S_{i+1}] 作为 S_{i+1}^{in}
```

公开根 `C_i, C_{i+1}` 是实例 `x_i`。绑定成立的最低要求：

- **输出一致性**：witness 中旧/新状态片段必须分别打开到公开根 `C_i`/`C_{i+1}`（R1CS C1.1/C1.6）；
- **执行一致性**：witness 必须就是本步 ORAM 转换电路实际计算出的线值，而不是任意另取的合法转换；
- **跨步连续性**：下一步使用的状态 shares 与上一步证明输出的根对应（verifier 强制，见 `verifier-chain.md`）；
- **恶意不可替换**：少于阈值合谋不能替换别人份额；全体合谋不能伪造满足关系的 witness（knowledge soundness）。

---

## D1. 同一 MPC 执行内生成证明关系 witness

### D1.1 构造（CONSTRUCTED / 依赖 VDORAM CompatCircuit 范式）

```
一次 ORAM 转换的 compatible circuit 同时产出:
  - 主输出 shares:      [S_{i+1}], [result]
  - 证明辅助线 shares:  path/stash/auth/pick/eq 等全部 R1CS witness 线
  - 公开输出:           C_{i+1}^{Tree_j}, C_{i+1}^{Stash_j}, C_{i+1}^{Top},
                        C_{i+1}^{Hist}, step_{i+1}
协作 SNARK Prove(pp, x_i, w_0..w_{m−1}) 在 MPC 中消费这些线值份额。
下一步 AddPrivate("in_state_j", S_{i+1}[j]) 使用同一批输出 shares。
```

论文层依据（VERIFIED）：VDORAM 论文 p4-5 明确 “utilize an MPC protocol for computing all necessary intermediate values as secret shares … apply collaborative zkSNARKs … using these secret shares as witnesses”（`EXCERPTS.md` L99-103）；协作 SNARK 定义中 `Prove` 本身在 MPC 中运行且 `abort otherwise`（p5 L144-151），并提供 knowledge soundness 与 t-zero-knowledge（L152-160）。

### D1.2 为什么不是“同源”三个字（CONSTRUCTED 论证）

1. **替换 witness**：若某参与方把 `[S_{i+1}]` 换成另一组合法 shares，公开根 `C_{i+1}` 由 MPC 打开并进入实例；替换后的 witness 无法同时打开 `C_i`、满足 R1CS 转换关系、又打开 `C_{i+1}`（抗碰撞 + knowledge soundness）。因此替换会被 prove abort 或 verify 拒绝。
2. **重放旧状态**：旧 witness 打开的是旧 `C_{i+1}`，与本步公开 `step_i` 和 `C_i` 不匹配；R1CS C1.9 强制 counter+1，verifier V1/V2 强制根与步数串联。
3. **all-prover 合谋**：MPC privacy 不再适用，但 SNARK knowledge soundness 要求即使全体合谋，伪造有效证明的概率可忽略（VERIFIED 威胁模型 p4）。
4. **<t 合谋**：MPC 主动安全（Keller–Scholl：dishonest majority、all but one corrupted，VERIFIED L2）阻止少数方偏离导致输出 shares 不一致；协作 SNARK 的 t-zero-knowledge 阻止 verifier/少数合谋方从 witness 学秘密。

### D1.3 安全假设 / 成本 / 适用性

| 项 | D1 |
| --- | --- |
| 安全假设 | 任意 m 方、active-secure dishonest-majority MPC（Keller–Scholl SPDZ 类）；协作 SNARK 满足 `(m,t)` t-zero-knowledge + knowledge soundness；公开根的抗碰撞哈希 |
| 额外通信 | **理论上无独立 share 重传**：辅助线与主输出在同一 MPC 中产生；但协作 Prove 本身仍需多方通信（论文未给 ORAM 实例数 → UNKNOWN） |
| 额外证明成本 | R1CS 规模见 `r1cs-constraints.md`；sublinear witness 仅含路径/stash/auth，不含整状态 |
| 任意参与方 | **支持**（VERIFIED L2 存在性 + VDORAM 任意方目标） |
| 目标达成 | correctness 可达（在后端假设下）；privacy 在 `<t` 合谋下可达；但**当前 artifact 未实现 verifier 链与兼容前端**（BLOCKED） |

### D1.4 当前 artifact 的工程状态（VERIFIED，沿用 R1 未重审）

- 回调 `OnR1csCircuitWithValuesGeneratedAsync` 在单方只做“落盘 JSON + `SelfVerify()`”，多方只落盘（`CollaborativeZkVm/Program.cs` L106-111 / L211-214）；
- `SelfVerify()` 只验单电路 R1CS 约束，且 `run-fake-verify` 是重组秘密的调试工具（`R1csCircuitWithValues.cs` L22-38）；
- 协作证明由外部 Rust client 逐电路手动运行，verifier 是 arkworks 单 proof 配对验证；无跨电路根/步数/锚点检查（`verifier-chain-check.md` §1-4）。

因此 D1 在**协议设计层 CONSTRUCTED**，在**固定 artifact 工程层 BLOCKED**。这不是“MPC 状态与证明在数学上无法绑定”，而是当前执行/证明接口没有提供该绑定。

---

## D2. 独立证明阶段（输出 shares → 再入 proof）

### D2.1 构造草案（CONSTRUCTED 框架 / 具体机制 UNKNOWN）

```
阶段 1: MPC 转换 → [S_{i+1}], [result]，打开公开根 C_{i+1}
阶段 2: 各方把自身 share 提交到 proof generation：
        - 用 SPDZ MAC/认证份额验证输入 share 未被替换；
        - 用 (step_i, C_i, C_{i+1}) 域分隔的 commitment/opening 绑定阶段边界；
        - 协作 Prove 消费经认证的 shares 与其承诺开启；
阶段 3: 验证 proof + verifier 根链；下一步使用阶段 1 的 shares。
```

### D2.2 必须额外具备的机制（缺一不可）

1. **份额认证**：每方 share 附 MAC/认证标签，证明阶段验证；否则恶意方可提交任意 share（UNKNOWN：点名文献没有给出与 ORAM witness 直接兼容的现成接口）。
2. **状态承诺开启绑定**：proof 阶段提交的 `(state, witness)` 必须开启到阶段 1 打开的 `C_{i+1}`；否则可提交“另一组合法状态”（由 R1CS 根约束挡住，但阶段边界仍需认证）。
3. **anti-replay**：承诺/证明公开输入包含 `step_i` 与 `C_i`；重复使用旧 proof 会因 step/root 不匹配被拒。
4. **anti-fork**：同一 `(step_i, C_i)` 产生两个不同 `C_{i+1}` 时，公开验证层需有唯一接受链（通常要公开公告板/日志，见 `verifier-chain.md`）。

### D2.3 对比与判定

| 项 | D1 同执行 | D2 独立阶段 |
| --- | --- | --- |
| 安全假设 | compatible front-end + active MPC + co-SNARK | 另加份额认证/MAC + commit-and-prove 接口 |
| 额外通信 | 无独立重传；Prove 本身通信 | share 重传 + MAC 验证 + commitment 开启 |
| 额外证明成本 | 与 R1CS 同阶 | 同阶 + 认证/承诺层 |
| 任意参与方 | 是（Keller–Scholl） | 取决于 MAC/commit-and-prove 是否支持任意方（UNKNOWN） |
| 当前目标 | 协议可达 / 工程 BLOCKED | 机制未从固定文献推导出来（UNKNOWN） |

**结论**：D1 是本轮唯一有明确协议依据的路线；D2 若缺少份额认证与承诺开启绑定，不能声称抗替换。两者都不能只用“witness 同源”作为证明。

---

## D3. 本轮判定

- **绑定可构造性：CONSTRUCTED（D1 协议层）**：在 compatible collaborative-SNARK 前端与主动安全 MPC 假设下，可以给出“实际转换输出份额 = witness 份额 = 下一步状态份额”的规则，并由根 + step + R1CS 三重约束挡住替换/重放。
- **工程实现：BLOCKED**：固定 artifact 只落盘 JSON、外部逐电路证明、verifier 无跨电路串联（VERIFIED）。
- **D2 具体机制：UNKNOWN**：不得补写成既有事实。
- **进入 GO 的必要条件未满足**：因此 `decision.md` 不判 GO_TO_MINIMAL_PROTOTYPE。
