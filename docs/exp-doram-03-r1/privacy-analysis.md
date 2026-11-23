# privacy-analysis.md — 任务 F：隐私泄露分析

> 2026-11-23 · 起点 `b88f3db` · 纸面分析。
> 状态取值严格限定：`HIDDEN` / `LEAKED` / `CONDITIONALLY HIDDEN` / `UNKNOWN`。
> 观察方：单诚实参与方（1/m share）、`<t` 合谋、全体 prover（privacy 不适用）、公开 verifier（只见公开输入与 proof）。
> **硬规则：secret-shared ≠ 访问模式自动隐藏；Merkle root 公开 + proof size 固定 ≠ 执行轨迹无泄露。**

---

## F1. 泄露矩阵

| 信息 | 单个诚实参与方 | 少于阈值合谋 | 所有参与方合谋 | 公开 Verifier |
| --- | --- | --- | --- | --- |
| 逻辑地址 `fetch_address` | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| ORAM leaf / leaf′ | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| Tree path | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| 操作类型 Load/Store/NOOP | HIDDEN | HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| dummy / real Fetch | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| PositionMap 更新 | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| Stash occupancy | HIDDEN | HIDDEN | LEAKED | HIDDEN |
| Stash overflow | HIDDEN | HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| MPC transcript | CONDITIONALLY HIDDEN | CONDITIONALLY HIDDEN | LEAKED | CONDITIONALLY HIDDEN |
| Merkle roots（公开值） | LEAKED | LEAKED | LEAKED | LEAKED |
| HistoricalLog（内容） | HIDDEN | HIDDEN | LEAKED | CONDITIONALLY HIDDEN |

**读表说明**：

- `LEAKED` 在“所有参与方合谋”列是 VDORAM 威胁模型的**预期**：correctness 下 0 honest，privacy 仅在 `<t` 合谋时要求。不得据此说设计缺陷，也不得说全体合谋仍有隐私。
- “Merkle roots 公开值 = LEAKED”只指根值本身可见；根背后的状态内容仍由哈希单向性与 t-zero-knowledge 隐藏（见 F2.4）。
- 所有 `CONDITIONALLY HIDDEN` 都是真实剩余泄露面，条件在 F2 展开；没有一项被写成无条件 HIDDEN 来换取好看结论。

---

## F2. 逐项讨论

### F2.1 MPC 公开通信模式（transcript）

- 构造要求每步固定跑 `D` 层 ORAM access、固定 `(L_j+1)Z_j` 路径读、`R_j` stash 比较与固定 eviction；秘密分支只能用 `select`，不能产生公开 if。
- 在 Keller–Scholl SPDZ 类协议（VERIFIED L2）下，主动安全保证 `<t` 合谋不能从协议消息中学到秘密索引；但**通信轮次/消息长度的固定性取决于实现**，网络层 timing、丢包重传、预处理失败不在 proof 语义内 → `CONDITIONALLY HIDDEN`。
- 若实现中 stash overflow 触发公开 abort（F2.3），transcript 长度/终止行为变成数据相关 → 条件失效。

### F2.2 固定长度与秘密分支

- dummy Fetch 与真实访问执行同一电路形状：都做 POS LOOKUP/READ PATH/STASH FIND/eviction/Merkle 更新；差别仅在秘密选择位与 trace 行字段。
- `[op]` 为 one-hot 秘密，APPLY OP 用算术加权而不是明文 switch；若某实现把 op 作为公开 opcode，则“操作类型”列在 verifier 侧升级为 LEAKED。
- 禁止用 `[leaf]` 直接索引数组：那不是 oblivious access，会把物理路径写进内存访问模式（构造层已排除，见 `merkle-oram-construction.md` A1.2）。

### F2.3 Stash overflow 的概率与可观察性

- honest 执行下，给定解析界 `14·0.6002^R` 要求 `R≥114`（2⁻⁸⁰）或 `R≥179`（2⁻¹²⁸）；理论界不替代实现安全参数。
- R1CS C1.5 强制 `occ≤R`，诚实路径不产生 abort；但恶意 prover 若能让公开验证看到“这一步没有 proof/abort”，理论上可把它当作秘密相关的一比特信道。固定文献与本 artifact 都没有给出“恶意选择性 abort 不泄露”的完整协议级论证 → verifier 列 `CONDITIONALLY HIDDEN`，并把选择性 abort 列为 blocker 候选（见 `decision.md`）。
- 若把 overflow 编码为秘密标志并同时给出“合法 overflow 处理路径”的证明（而非 abort），可去掉这一条件；本轮未构造该路径，标 UNKNOWN。

### F2.4 Merkle roots 是否泄露状态变化

- 每个诚实步都会改变至少一个路径/stash root，因此 verifier 能观察到“状态变了”这一事实；由于每步都变，该事实与秘密无关。
- 根值本身是 `H(state)` 的输出；本轮 MiMC 默认参数（VERIFIED 源码）未被重新做抗碰撞/伪随机评估，不能写成“零知识承诺”。对 `<t` 合谋隐藏依赖 hash 单向性 + co-SNARK t-zero-knowledge；若 hash 被攻破或 witness 泄露，根会变成泄露面。
- 根**不记录**被访问 leaf/path； auth path 只在 witness 中，不进入公开实例。

### F2.5 SNARK witness 是否真正零知识

- VDORAM 论文定义 `(m,t)` collaborative zkSNARK 的 t-zero-knowledge：少于 t 方合谋时，prover 与 verifier 不能获得 witness 信息（VERIFIED，`EXCERPTS.md` L152-160）。这是**协作**零知识，不是单 prover zkSNARK 自动成立。
- 若后端仅提供普通 Groth16/Plonk 而对多方 witness 没有 t-zero-knowledge，则本矩阵中“verifier HIDDEN”的多项不成立 → 该情形标 UNKNOWN，不能默认。
- knowledge soundness 与零知识是两件事：全体 prover 合谋下 privacy 不适用，但 soundness 仍须成立（VERIFIED 威胁模型 p4）。

### F2.6 公开 step count / access count 是否额外泄露

- `step_i` 与 `accessCount_i = step_i−1`（step 0 特例）都由公开执行长度决定，不是秘密相关分支；构造本身固定每步一次 Fetch，所以不新增“哪一步是真访问”的信息。
- 若某程序按秘密条件提前停机或跳过 Fetch，则终止时间/步数会泄露；本轮固定 VM 语义排除了这一点，但**应用层是否遵守**不在协议内，标条件性。
- proof 数量 = T，固定；proof size 固定是 SNARK 性质，不证明 MPC transcript 无泄露（F2.1）。

---

## F3. 与本轮三个验收重点的对应

1. **Merkle 增量**：F2.4 说明根只暴露“状态变化”而无 leaf/path；但增量性本身不能掩盖递归层与 eviction 的通信形状（F2.1/F2.2）。
2. **绑定真实 MPC**：若 proof witness 不是同执行输出（D1）或缺少份额认证（D2），verifier 看到的合法状态机可能不是 VM 实际使用的 → 隐私矩阵中“verifier HIDDEN”只针对 witness 内容，不针对“witness 是否真实”。
3. **执行轨迹覆盖**：本矩阵明确把 transcript、overflow、dummy Fetch、历史日志单列；没有用“root 公开、proof 固定大小”替代它们。

---

## F4. 未闭合项（UNKNOWN）

- 任意方 active-secure co-SNARK 后端对本 ORAM witness 的 t-zero-knowledge 实例证据（固定文献未给）。
- 恶意 prover 选择性 abort 的无泄露处理。
- 网络层 timing/重传等信道是否固定（实现相关，proof 语义外）。
- `HistoricalKV.Export()` 若把完整历史公开给 verifier，则 HistoricalLog 列会从 CONDITIONALLY HIDDEN 变为 LEAKED；本轮假设只公开承诺与证明所需公开输入。
