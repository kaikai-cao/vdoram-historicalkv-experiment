# threat-model-compatibility.md — 威胁模型兼容性审计

> 以 VDORAM 原论文威胁模型为准，不自行替换。原文见 `paper/EXCERPTS.md` p4-5/p10-11/p14；本地 PDF `paper/vdoram-ndss2026.pdf`（NDSS'26 官方，1,167,622 bytes）。
> 标注：VERIFIED（论文/源码原文直接支持）/ INFERRED / UNKNOWN / BLOCKED。

## 0. VDORAM 威胁模型（逐字核实，VERIFIED）

来自论文 §III-A "System and Threat Model"（PDF p4）：

| 角色/属性 | 原文要点 | 精确含义 |
| --- | --- | --- |
| Provers — correctness | *"The group of provers is considered malicious to verifiers: it is assumed that 0 provers will act honestly, i.e., all provers are eager to collude to compromise the correctness"* | 对正确性：**0 个诚实 prover**，全体可合谋 |
| Provers — privacy | *"at least t (e.g., t = 1) provers will act honestly to protect their secrets"* | 对隐私：至少 **t 个**（示例 t=1）诚实即可 |
| MPC 协议 | *"We adopt a dishonest-majority MPC protocol"*；p5 *"typically t = m − 1"*, additive secret sharing | 不诚实多数 MPC，加法秘密共享 |
| 公开可验证性 | *"even if all provers collude, a public verifier can still verify the integrity"*，via collaborative zkSNARK | 全体合谋也不能伪造通过验证的证明（knowledge soundness） |
| Collaborative zkSNARK | `(m,t)`：t-zero-knowledge（少于 t 合谋不泄露 witness）；knowledge soundness 即使全体合谋 | 隐私阈值 t 与正确性分离 |
| 参与方数量 | p14 Table III：*"VDORAM (ours) ≥ 1 provers"*；p9 *"arbitrary number of provers beyond just two or three"* | **任意数量 prover** 是核心目标 |
| 隐私声明 | p10：寄存器（含 pc）、内存值/地址/访问类型均隐藏；访问次数 = 指令周期数（公开 T） | 访问模式隐藏，T 公开 |
| 公开信息例外 | p11：I/O 指令类型、总迭代数 T 公开 | 明确列出的例外 |

## 1. 五问逐条回答

### Q1: prover 合谋破坏 correctness 时，公开证明能否拒绝非法状态转换？

- **对 VDORAM 现有状态（pc/registers/memory trace）：能（VERIFIED）**。论文定义 knowledge soundness：全体 prover 合谋产生假证明的概率可忽略（p4/p11）；源码体现为每步 hash 连续检查（`ZkProgramExecutor.cs` L322-328/L355-371）与 Prove 期 hash-count 比对（L580-586）进入 zkSNARK witness。
- **对 ORAM 状态转换：不能（BLOCKED）**。没有 `S_i → S_{i+1}` 的电路/约束，malicious prover 提交任意 `H(S_{i+1})` 时 SNARK 无关系可验（详见 `state-binding-analysis.md` §4.2）。
- **重要区分**：论文"只检查 RAM 状态完整性"（p5/p6）指的是**现有 RAM 状态**（pc/R/M/halt）的合法转换；把 ORAM 物理状态纳入"RAM 状态"需重新定义关系，不是自动继承。

### Q2: 访问模式隐私依赖多少诚实参与方？

- **VERIFIED**：论文 p4 *"at least t (e.g., t = 1) provers will act honestly"*；p5 `(m,t)` collaborative zkSNARK 的 t-zero-knowledge 与 dishonest-majority MPC 的隐私阈值一致。示例配置为 t=1（即 m−1 可腐化）。
- 结论：访问模式隐私依赖**至少 t 个诚实 prover**（示例 t=1，即只要一个诚实即可）。这是相当强的隐私鲁棒性。

### Q3: 所有 secret-share holders 合谋时哪些隐私目标不可能实现？

- **VERIFIED**：若全部 m 个 prover 合谋（腐化数 ≥ t 门槛被突破），加法秘密共享的隐私归零——`t=1` 时任意 1 个诚实即可保隐私，全部合谋则所有份额可重构，隐私尽失。
- 但 correctness 仍由 zkSNARK 保证（p4：全体合谋只威胁 privacy，不威胁 integrity）。即：**全体合谋 → 隐私不可能，但伪造证明仍不可能**。这是论文设计的明确边界。

### Q4: ORAM 子协议安全模型是否与 VDORAM MPC 模型兼容？

- 论文 p4 列出的可用 DORAM：2-party Circuit ORAM [48]（基于 SPDZ，active security）、3-party RAM-MPC [23]（malicious，log overhead）。这些都是**固定方数、特定腐化门槛**的协议。
- **INFERRED（核心冲突）**：
  - VDORAM MPC = dishonest-majority（典型 t = m−1，即容许多数腐化）；
  - Circuit ORAM/3-party RAM 的安全性绑定在 2 方或 3 方、特定门槛；把它们的 ORAM 状态机嵌入 m 方（m 任意）的 VDORAM 执行，需要**重新证明**其在 dishonest-majority 混合域 MPC 下的安全性，不能直接引用。
  - 半诚实 DORAM（论文 p2 [63][56]）缺乏可验证性，更不能未经改造套入"恶意 prover 也会合谋"的场景。
- **BLOCKED**：论文自己给出不使用这些 DORAM 的理由（p9：*"insubstantial number of parties ... does not align with our VDORAM aims"*）。因此任何引入它们的方案都必须面对同样的参与方数量冲突。

### Q5: 参与方数量限制是否违背 VDORAM 任意参与方目标？

- **VERIFIED 冲突**：论文 p9 原文明确现有高效 DORAM 只支持 2-3 方，与 "*arbitrary number of provers beyond just two or three*" 目标冲突；p14 Table III 强调 VDORAM 独有能力是 "*≥ 1 provers*"。
- **判定：BLOCKED**。若候选 Path ORAM 方案要求固定 2 或 3 方（如 Circuit ORAM、Falk 3-party RAM），就直接违背 VDORAM 的核心定位。这不是"实现细节"，是研究目标层面的冲突。
- 除非找到并证明一个"支持任意 m 方 + dishonest-majority + 恶意安全 + 公开可验证接口兼容"的 DORAM——本证据集中没有这样的候选，标 UNKNOWN。

## 2. 额外审计点（任务包 §4 特别要求）

| 检查项 | 结论 | 标注 |
| --- | --- | --- |
| 候选 ORAM 即使本身安全，是否仍适配参与方数量/腐化假设/公开证明结构？ | 现有候选（2/3 方）不适配；"安全"与"可接入 VDORAM"是两件事 | VERIFIED（冲突）/ UNKNOWN（无适配候选） |
| 半诚实 ORAM 能否未经证明套入？ | 不能。论文 p2 明确半诚实 DORAM 缺乏可验证性；VDORAM 正确性假设 0 诚实 prover | VERIFIED |
| 不为 GO 而弱化威胁模型 | 本审计保留论文全部原始假设（全体合谋破坏 correctness、t 诚实保隐私、任意 m 方），未作任何弱化 | VERIFIED（纪律声明） |
| 混合域（Fp + Z2ⁿ）需求 | 论文 p4-5：zkSNARK witness 需布尔域辅助数据，故 MPC 需支持混合域（daBit/edaBit） | VERIFIED。ORAM 若引入位级 leaf/stash 操作，须同样在混合域内可证——本仓库有 daBit/edaBit 原语但无 ORAM 接线 |

## 3. 元结论

威胁模型层面存在**两条独立的结构性张力**：

1. **参与方数量**：Path ORAM 的高效 DORAM 实现（2-3 方）与 VDORAM 任意 m 方目标直接冲突（论文自己承认并因此放弃 DORAM 路线）。
2. **状态绑定 × 合谋**：全体 prover 合谋破坏 correctness 的假设要求 ORAM 状态转换也必须被公开 SNARK 验证；而当前框架没有可验证的 ORAM 状态转换关系（`state-binding-analysis.md` BLOCKED）。

二者叠加意味着：**即使找到支持任意方的 ORAM 协议，若不能同时给出"恶意合谋下仍可公开验证的状态转换证明"，仍不满足 VDORAM 威胁模型。** 这不是可通过调参或工程优化绕过的。

## 4. 证据索引

- `paper/EXCERPTS.md` p2（半诚实 DORAM 无可验证性、恶意 DORAM 内部可验证≠公开可验证）、p4（§III-A 威胁模型全文）、p5（(m,t) 定义、t=m−1、混合域、合谋下公开验证）、p9（DORAM 方数冲突、线性扫描理由）、p10（隐私声明、T 公开）、p11（Definition IV.1 安全定义、I/O 例外）、p14（Table III ≥1 provers）。
- `source-evidence/...MpcExecutorFactory.cs` L18-21（Beaver/EdaBits/DaBits 预处理）、`...EdaBitsKaiShare.cs`、`...DaBitPrioPlusShare.cs`（混合域份额原语，对应论文 daBit/edaBit）。
