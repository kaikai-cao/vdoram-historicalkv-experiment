# ABA-03-D3-03-03 / 三种最小 Trust Model 比较

> 实验仓起点：`5c84f38c6df17acd458c1681a8ca18da0377281a`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：信任模型比较；不选择即实现，不把 Model C 预设为更先进。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。

---

## 0. 比较前提

- 三模型都假设存在一个真正的 verifier 主体，而不是 prover 进程内 self-check；当前固定 commit 不满足（`VERIFIED`）。
- 三模型都只回答“verifier 凭什么接受某个 statement”，不自动回答“proof 是否约束了 R5–R8/B4 语义”。
- 冻结步数语义沿用：`total_steps = T` 含 step 0，`last_step_index = T-1`，Fetch 索引 `[1,T-1]`、事件数 `T-1`，step 0 无 Fetch proof / 无 Fetch commitment event。
- 证明系统语境按主路径 Plonk 记录；Groth16 preprocessing/per-relation setup 只作文献对照，Groth16 快照与主路径关系 `UNKNOWN`（证据 S13）。

---

## 1. 总览表

| 维度 | Model A：固定配置独立软件 verifier | Model B：可信调用方 + 独立 verifier | Model C：可信注册表 / VK Registry |
| --- | --- | --- | --- |
| 核心假设 | verifier 独立运行；program identity、VK、预期公开输入由可信配置固定 | 调用方认证 program/输入/execution_id；verifier 独立验 proof；双方通过 statement/transcript 绑定 | registry 维护 program_id、VK、协议版本、授权关系；verifier 查询或持有可信 registry 状态 |
| 最小新增信任根 | 独立 verifier 主体 + 固定配置 + 固定 VK + execution_id 生成方 + `total_steps` 来源 | 在 A 基础上增加可信调用方身份与调用方↔verifier 编码一致性 | 在 A 基础上增加 registry 写入权、状态新鲜性、版本/撤销治理 |
| 是否需要可信 setup | 需要可信 setup/分发，但 setup 类型依证明系统；不因选 A 而消失 | 同 A | 同 A；registry 不替代 setup 信任 |
| program identity 来源 | verifier 固定预期 opcode table 或可信派生 `program_id` | 调用方认证，verifier 必须与自身固定表/映射比对 | registry 映射；需防止 prover 自报 id |
| execution_id | verifier 或可信调用方生成，写入所有 proof statement | 通常由调用方生成并由 verifier 校验为本次请求值 | 可由 verifier/registry 联合生成；需防跨租户/跨版本重放 |
| `total_steps = T` | verifier 固定实际 T，或由受约束 counter 产生并核对 | 调用方可提供 T 估计，但 verifier 不得只信调用方自报；仍需可信 T/counter | registry 版本可固定预期上界，不提供实际 T 语义 |
| 配置更新/版本 | 固定部署最简单；更新需签名配置与版本域分离 | 调用方与 verifier 必须同步版本；不一致是新增失败面 | 支持动态程序/VK 更新与撤销，但引入回滚/新鲜性问题 |
| 是否更适合 Agent/tool execution | 固定目标场景足够 | 更贴近“调用方知道用户意图”的场景，但新增跨系统绑定风险 | 多程序、多租户、需撤销时更贴近 |
| 是否单点信任 | verifier 配置来源单点 | 调用方与 verifier 两个边界 | registry 是显式单点，除非另有治理机制 |
| 对 R5–R8 | 只可能提供 `total_steps` 的 verifier 侧来源；不产生 step/is_mem_op/step↔row 约束 | 同 A；调用方认证不产生电路语义 | 同 A；registry 映射不产生电路语义 |
| 对 B4 | 不能替代 R2–R8 证明关系；不能把信任配置写成事件完整性 | 同 A；调用方签名不能替代完整性约束 | 同 A；registry 授权不能证明序列正确 |
| 当前仓状态 | 候选，未实现 | 候选，未实现 | 候选，未实现 |
| 标签 | `CONSTRUCTED`；当前 `BLOCKED_BY_TRUST_MODEL` | `CONSTRUCTED`；当前 `BLOCKED_BY_TRUST_MODEL` | `CONSTRUCTED`；当前 `BLOCKED_BY_TRUST_MODEL` |

---

## 2. Model A：固定配置的独立软件 verifier

### 2.1 假设

- verifier 软件独立于 prover 运行；
- program identity、VK 与预期公开输入由可信配置固定；
- `execution_id` 由 verifier 或可信调用方生成；
- 实际 `total_steps = T` 由 verifier 固定，或由证明内 counter 产生并核对；`last_step_index = T-1` 派生。

### 2.2 最小可信组件

1. 独立 verifier 主体（当前固定 commit 无此主体，`VERIFIED`）；
2. verifier 固定 VK，且 `vk_id↔program_id` 显式绑定（`CONSTRUCTED`）；
3. verifier 固定预期 opcode table 或由该表派生 `program_id`（`CONSTRUCTED`）；
4. verifier 固定/认证 public input expectation（`CONSTRUCTED`）；
5. request-scoped `execution_id` 生成与 statement 写入（`CONSTRUCTED`）；
6. 可信 `total_steps` 来源（`CONSTRUCTED`；当前 path `BLOCKED`）。

### 2.3 配置更新与版本管理

- 单固定程序部署可用签名配置 + 版本号 + 域分离完成，不必然需要在线 registry（`INFERRED`）。
- 更新 VK 或 program table 时，必须防止 prover 选择旧版本 statement；版本应进入 statement 域标签。
- 配置完整性保护的是“verifier 用哪份期望”，不证明该期望对应的事件序列被完整执行。

### 2.4 是否需要可信 setup

- 需要区分 setup 信任与 VK 分发信任：主路径 Plonk 的 SRS 信任模型与 Groth16 per-relation 语境不同（S13、L2/L3）。
- 固定 VK 不自动等于可信 setup；现场 `test_rng()` 生成 VK 是当前已验证缺失项。

### 2.5 适用部署模型

- 单一固定程序、固定期望输入、少量版本、离线分发 VK 与配置。
- 不适合动态多程序、频繁撤销或跨租户授权；那些场景才可能需要 Model C。

### 2.6 对 R5–R8 / B4 的边界

- Model A 只能把“谁固定 statement / 谁生成 execution_id / 谁提供 T”讲清楚。
- R5 step provenance、R6 `is_mem_op` binding、R7 step-to-trace binding、R8 termination 均需证明关系内部语义约束；Model A 不产生这些约束（`BLOCKED`）。
- B4-R2–R8 同理；信任执行锚点不等于事件完整性（`INFERRED`）。

---

## 3. Model B：可信调用方 + 独立 verifier

### 3.1 假设

- 调用方负责认证 program、public input 与 `execution_id`；
- verifier 独立检查 proof；
- 双方通过明确 statement/transcript 绑定，而不是共享口头约定。

### 3.2 信任边界

| 边界 | 可信内容 | 不可自动推出 |
| --- | --- | --- |
| 调用方 | 本次请求的意图：用哪个程序、输入是什么、请求唯一 id | proof 确实按该意图执行；R5–R8/B4 完整 |
| verifier | proof 对给定公开 statement 是否成立；VK 是否本次预期 | 该 statement 是否就是调用方原始意图（除非有签名/摘要绑定） |
| 双方桥接 | 同一份 canonical statement encoding 与 transcript 域分离 | 私有 witness 相同；跨 proof 同执行 |

### 3.3 是否产生新的跨系统身份绑定问题

- 是。调用方的 `program_id` 与 verifier 的固定表/映射必须一致；调用方输入摘要与 verifier public input 必须一致；请求 nonce 与所有 proof statement 必须一致。
- 若 verifier 只收到 prover 转交的“调用方声明”，而无可信签名/固定摘要，则 Model B 退化为 prover 自报（`INFERRED`）。
- 签名解决来源认证，不替代电路内语义约束（`CONSTRUCTED`）。

### 3.4 如何防止调用方与 prover 输入不一致

- 调用方对输入摘要、program 引用、`execution_id`、协议版本签名；verifier 只接受该签名摘要对应的 public statement。
- 若 verifier 持有的值与 prover 提供的 public input 不同，验证必须失败；不能靠宿主日志后验协调。
- 即便如此，私有 witness 与公开输入的关系仍需 proof 关系约束（`INFERRED`）。

### 3.5 是否比 Model A 更适合 Agent/tool execution

- 在 Agent/tool 场景中，调用方通常最接近用户意图，Model B 在“请求语义来源”上更自然。
- 但它不是严格更强：它增加了调用方↔verifier 一致性边界，若该边界未受约束，反而多一个拼接缝。
- 结论：适合特定部署，不是当前架构的自动升级（`INFERRED`）。

### 3.6 对 R5–R8 / B4 的边界

- 同 Model A：调用方认证只提升 statement 来源可信，不产生执行语义约束。
- 不能把调用方信任写成事件完整性证明。

---

## 4. Model C：可信注册表 / VK Registry

### 4.1 假设

- registry 维护 `program_id`、VK、协议版本、授权关系；
- verifier 查询或持有可信 registry 状态；
- registry 的写入、更新、撤销与状态新鲜性均有可审计机制。

### 4.2 registry 的可信根

- 谁有权写入 mapping？谁可升级 VK？谁可撤销 program？这些是新增信任根，不是由“使用 registry”自动解决。
- registry 状态新鲜性本身是问题：verifier 需要固定版本、查询证明或包含证明，否则可能接受旧映射（`INFERRED`）。
- 单点信任可能通过治理/透明日志缓解，但不能预设已消除（`UNKNOWN`）。

### 4.3 VK 更新、撤销、版本回滚

- 必须显式版本化并进入 statement 域分离；否则 prover 可用旧 VK/旧表构造自洽 proof。
- 撤销需要状态新鲜性证明或 verifier 固定当前版本；仅“registry 中有一条撤销记录”不等于 verifier 已检查。
- registry 不提供实际 `total_steps`，也不证明 halt 与事件序列对应。

### 4.4 program 与 VK 的映射

- `vk_id↔program_id` 是必要映射；registry 可以承载它，但固定配置也可承载。
- 映射存在 ≠ 映射正确；正确性的根源是 registry 写入权/治理，不因数据结构是 registry 而增强。

### 4.5 registry 是否成为单点信任

- 在单 verifier 部署中通常成为显式单点；可通过多签、透明日志、可验证状态转移转移信任，但这些是新假设与成本（`CONSTRUCTED` / `UNKNOWN`）。

### 4.6 是否真的比 Model A 增加必要能力

- 仅在多程序、多版本、频繁撤销、跨租户授权场景下增加必要能力。
- 对单程序固定部署，Model C 主要增加治理面与新鲜性问题，不增加 R5–R8/B4 证明能力。
- **不得预设 Model C 更先进或更安全**（`INFERRED`）。

---

## 5. 共同不可解项

三模型共同无法解决：

1. R5 step provenance：step 来源仍须受约束 counter/可信执行锚点，信任配置不产生 step 语义。
2. R6 `is_mem_op` binding：需 opcode→event type 的电路约束；签名/配置不能替代。
3. R7 step-to-trace binding：需在同关系内约束或公共承诺桥 + opening/linking proof。
4. R8 actual T：需可信 T 或受约束 counter；registry/调用方只能固定期望，不证明真实终止。
5. B4-R2–R8：覆盖、单射、顺序、类型、step-row、可信 T 都是证明关系语义，不是 verifier 身份问题。
6. 跨 proof 同执行绑定：相同 `execution_id`/哈希字段不是 witness 同一性证明；需 statement 内公开锚定与 linking/opening 关系。

---

## 6. 比较结论

- 最小合理 trust model 在单固定程序部署下是 **Model A**；Model B 在 Agent/tool 调用场景有自然优势但增加跨系统绑定；Model C 只在动态治理场景增加必要能力，不是默认更优。
- 三模型都只提升 statement 来源可信；不把任何模型写成 R5–R8/B4 的闭合方案。
- 三模型当前均为 `CONSTRUCTED`，当前实现状态为 `BLOCKED_BY_TRUST_MODEL`，外部部署事实 `UNKNOWN`。
- 选择模型不能替代后续证明层研究；最终决策见 `decision.md`。
