# ABA-03-D3-01 / Phase 2：独立验证者、P1-A 与 VK 锚定

> 实验仓起点：`03960aa941bcd8ef88fbd06a83cf7599682a5cbd`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只复用既有证据的 verifier 侧分析；不重抓源码、不实现电路、不解除 HOLD。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED` / `CONDITIONAL INFERENCE`。
>
> 主要证据：`../aba-03-c2/verifier_interface_audit.md` §A1–A8、§2、§4；`../aba-03-d1/leakage_and_security.md` D6（勘误 C1）；`../aba-03-d2/context_and_replay.md` §1/§3.2/§3.6；`../aba-03/source_trace_audit.md` A3。

---

## 0. 一句话结论

P1-A 与 VK 锚定是**两个独立的 verifier 侧前置条件**：P1-A 回答“证明对应的是否是预期程序和 opcode 语义”，VK 锚定回答“verifier 用什么密钥、在什么信任模型下验 proof”。前者有最小路径 P1-A-1（固定完整 opcode table + 逐项比较现有 public inputs，不必然改电路），后者有证据分级的信任模型；两者都不解决 P2 的电路内地址同一性，也不解决 B4 事件完整性。

---

## 1. 当前验证路径的证据基线

| 事项 | 证据 | 标签 |
| --- | --- | --- |
| opcode table 四列作为 public inputs 进入 verify | `InstructionFetchCircuitBoardGenerator.cs:126-156`；`ZkProgramExecutor.cs:147-157`；`plonk.rs:143-161`（`verifier_interface_audit.md` §2） | `VERIFIED` |
| public inputs 来自 prover JSON，不是 verifier 期望值 | `plonk.rs:97-110,203-247,293-315`；`verifier_interface_audit.md` §A4/A6 | `VERIFIED` |
| 当前 compat 路径在同一函数内 setup→prove→verify | `plonk.rs:293-315` | `VERIFIED` |
| setup 使用 `test_rng()` 现场生成 VK | `plonk.rs:302-304` | `VERIFIED` |
| 固定 commit 范围内无独立 verifier / verify-only 主体 | `client.rs:36-65`；`proof.rs` verify 在测试代码；`verifier_interface_audit.md` §A8 | `VERIFIED`（限于固定 commit） |
| 外部部署是否存在独立 verifier、固定 VK、可信分发 | 现有证据未覆盖 | `UNKNOWN` |
| 若外部 verifier 接受 prover 自提 VK 且无其他可信锚定，可能重选 setup | 带前提推论，非已执行攻击（`leakage_and_security.md` D6 勘误） | `CONDITIONAL INFERENCE` |

**重要边界**：public input 通道存在 ≠ verifier 已检查；标准 `verify_proof` 存在 ≠ 独立 verifier 主体存在；当前现场 setup 为源码事实 ≠ 外部固定 VK 能力已被证实不支持。

---

## 2. P1-A：程序身份与 opcode 语义

### 2.1 待回答的问题

独立 verifier 必须能回答：

1. proof 对应的程序是否是预期程序？
2. opcode table 是否与 verifier 预期一致？
3. 程序身份是否跨执行稳定？
4. prover 能否自行替换程序语义或公开 opcode 输入？

当前证据：opcode table 已是 public inputs，但没有独立 verifier 持有预期表或 digest；替换后的实际攻击是否成功未验证（`verifier_interface_audit.md` §2 的“替换论证的证据边界”）。因此“公开输入存在”只能说明**可复用通道**，不能说明检查已发生。

### 2.2 P1-A-1：verifier 固定预期完整 opcode table，逐项比较 public inputs

**构造**（`CONSTRUCTED`；源自 `verifier_interface_audit.md` §2“方案 P1-A”）：

```
verifier 持有 OP_exp（来自固定程序的可信分发）
proof public inputs 提供 OP_pub（通道已存在）
for each row i:
    require OP_pub[i] == OP_exp[i]
verifier 用与电路匹配且预先固定/可信分发的 VK 验证 proof
```

| 维度 | 结论 | 标签 |
| --- | --- | --- |
| 是否需要改电路 | **不必然**。整表已在 public inputs，逐项比较为 verifier 侧工作；无需新增整程序 commitment 电路 | `VERIFIED`（通道在）+ `CONSTRUCTED`（检查流程） |
| 需要新增什么 | 独立 verifier 主体、可信分发的 `OP_exp`、固定/可信 VK、拒绝不一致表的策略 | `CONSTRUCTED` |
| 能否阻止 prover 自行替换公开表 | 若 verifier 真逐项比较且 VK 固定，则不一致表被拒；当前路径无此 verifier，不能声称已实现 | `CONSTRUCTED` + `VERIFIED`（现状缺失） |
| 程序身份跨执行稳定性 | 可由同一 `OP_exp` 承担稳定引用；但 P1-A-1 不自动给压缩 program_id，也不解决承诺跨执行重放 | `INFERRED` |
| 与 P2 的关系 | 只闭合程序语义，不证明地址同一性或事件完整性 | `VERIFIED`（边界） |

### 2.3 P1-A-2：verifier 检查稳定 program digest

**构造**（`CONSTRUCTED`；源自 `verifier_interface_audit.md` §2“方案 P1-B”）：

```
电路将完整 opcode table 绑定到稳定 program_digest
program_digest 作为 public input
verifier 持有预期 digest 并核对
```

| 维度 | 结论 | 标签 |
| --- | --- | --- |
| 是否需要改电路 | **需要**：新增 table→digest 的电路承诺/哈希绑定关系，并把 digest 放进 statement | `CONSTRUCTED` |
| 公开规模 | 可从整表压缩为单 digest，但电路新增承诺约束；净成本 `UNKNOWN` | `CONSTRUCTED` + `UNKNOWN` |
| 稳定性 | digest 需对 opcode table 的规范编码稳定；当前逐行哈希 preimage 含 step 与随机 `enc_key`，不是稳定 program digest（`source_trace_audit.md` A3） | `VERIFIED`（缺失）+ `CONSTRUCTED` |
| 与 P1-A-1 比较 | 是摘要化候选，不是 P1 的必要或唯一路径；**不得声称 digest 一定优于完整表** | `CONSTRUCTED` |
| 与 P2/B4 的关系 | 不自动闭合地址同一性或事件完整性 | `VERIFIED`（边界） |

### 2.4 P1-A 小结

- 最小闭合路径是 P1-A-1：不改电路即可建立 verifier 侧程序语义检查骨架（`CONSTRUCTED`）。
- P1-A-2 是可选摘要化方案，需要新增电路承诺关系；是否值得取决于后续接口规格与成本证据，本轮不选择。
- 两者都必须与固定/可信 VK 配套；否则 verifier 检查的 public inputs 与 proof 仍可能来自同一不可信主体。

---

## 3. VK 锚定：三种 verifier 模型

证据层级严格沿用 `../aba-03-d1/leakage_and_security.md` D6 勘误 C1：

| 事项 | 结论 | 标签 |
| --- | --- | --- |
| 当前 compat 路径使用 `test_rng()` 现场 setup | 源码事实（`plonk.rs:302-304`） | `VERIFIED` |
| 当前 setup、prove、verify 在同一函数内 | 源码事实（`plonk.rs:293-315`） | `VERIFIED` |
| 外部 verifier 是否持有固定 VK | 无证据 | `UNKNOWN` |
| 外部 verifier 是否接受 prover 提供 VK | 无证据 | `UNKNOWN` |
| 接受 prover 自提 VK 且无可信锚定 → 可能 setup 重选风险 | 仅在两个前提同时成立时适用，非攻击结果 | `CONDITIONAL INFERENCE` |

### 模型 1：verifier 预先固定 VK

- verifier 持有与预期电路/程序匹配的 VK，并在 verify 前不依赖 prover 提供 VK。
- 这是 P1-A-1/P1-A-2 与任何 P2 接口改造的**共同前置**（`CONSTRUCTED`）。
- 当前固定 commit 未展示该模型；外部是否存在为 `UNKNOWN`。
- 仍需程序身份检查：固定 VK 不等于固定 `OP_exp`。

### 模型 2：verifier 通过可信 setup / ceremony 获取 VK

- VK 来自可审计 setup 或 ceremony，可信分发给 verifier；prover 与 verifier 都不现场随意生成。
- 是否能与当前 additive-only MPC prove 路径共存，现有证据不足 → `UNKNOWN`。
- 该模型只回答 VK 来源，不回答程序身份、地址同一性或 B4。

### 模型 3：verifier 接受 prover 提供 VK

- **不得**写成固定上游已证实的事实。
- 只有在“外部 verifier 接受 prover 自提 VK”且“无其他可信锚定”两个前提下，才存在 setup 重选风险 → `CONDITIONAL INFERENCE`。
- 该模型下即便 P1-A-1 的 public table 比较存在，也不能排除 prover 更换 VK/电路描述形成另一套自洽证明；这是前提性推论，不是已执行攻击。

### 3.1 三种模型的最小结论

| 模型 | 能否作为最小路线 | 当前证据 | 备注 |
| --- | --- | --- | --- |
| 预固定 VK | 可作为候选前置 | `CONSTRUCTED`；外部状态 `UNKNOWN` | 与 P1-A-1 组合最简 |
| 可信 setup/ceremony | 可作候选，但接口未证 | `UNKNOWN` | 需独立评估 prove/MPC 路径改造 |
| 接受 prover 自提 VK | 不应作为安全基线 | `CONDITIONAL INFERENCE` | 非上游已证实行为 |

---

## 4. 与 P2、B4 的边界

| 问题 | P1-A 是否解决 | VK 锚定是否解决 | 需要的其他机制 |
| --- | --- | --- | --- |
| 程序语义替换 | 是（P1-A-1 最小） | 否（仅保证验的是固定电路） | 固定 `OP_exp` 与拒绝策略 |
| 地址同一性（Fetch/VM） | 否 | 否 | 电路内同一性约束或共享公开承诺（`../aba-03-d1/design_options.md` §2） |
| dummy 类型与 trace row 绑定 | 否 | 否 | 电路内 opcode 派生 event_type + sentinel/trace row 约束 |
| B4 计数/顺序/终止 | 否 | 否 | 独立事件计数、顺序、halt 约束（`p2_binding_semantics.md` B4） |
| 跨执行重放 | 否 | 否 | `exec_id`、context 绑定与 verifier 检查（`context_and_replay.md` §3） |

**结论**：P1-A 与 VK 锚定可以并列为 verifier 侧前置，但必须分别记录状态；它们不能被合并成“verifier 接口已闭合”，也不能替代 P2/B4 的电路约束。
