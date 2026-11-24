# ABA-03-D3-03-02 / Phase 6：Execution Anchor 与 Verifier Trust Model 决策

> 实验仓起点：`62ec3827bc89fb495daf68735ab93d1ea0b1e7c0`；固定上游 `10c90d35…`。
>
> 性质：只读信任模型审计与候选 statement 设计；不实现 commitment / anchor / verifier / 电路，不跑测试，不改既有文档，不解除任何 HOLD，不改 P1-A / VK / P2 既有标签，不回改 D3-03-01。
>
> 证据来源：`trust_boundary_inventory.md`、`execution_anchor_statement.md`、`verifier_vk_trust_model.md`、`proof_composition_binding.md`。
>
> 阶段结论候选：`ANCHOR_INTERFACE_FEASIBLE` / `ANCHOR_INTERFACE_PARTIAL` / `BLOCKED_BY_TRUST_MODEL`。

---

## 1. 阶段结论：`BLOCKED_BY_TRUST_MODEL`

**核心判断（`VERIFIED` + `INFERRED`）**：当前固定 commit 中**不存在** verifier-trusted execution anchor。program identity、execution identity、public input provenance、可信 T、VK identity、跨 proof binding 六项能力中，没有一项具备"verifier 固定或可信取得"的来源。当前所谓验证是 prover 进程内用现场 `test_rng()` 生成的 VK、prover 自己 JSON 的 public inputs 检查 prover 自己的 proof 自洽（`plonk.rs:293-315`），固定快照全目录检索无 `execution_id`/`program_id`/`program_hash`（`trust_boundary_inventory.md` §1/§2），最终 `total_steps`（T）只是 host 记录且不进 statement（快照 L601）；按冻结语义 T 含 step 0，末 step index 为 `last_step_index = T-1`。

**按本轮关键判据**："若可信来源最终仍然是 prover 自己，结论就应该是阻断，而不是接口可行。" —— 当前六项字段的可信来源**全部是 prover/host 自己**，故阶段结论为 `BLOCKED_BY_TRUST_MODEL`。

**边界**：这是**信任模型**的阻断判断（verifier 无可信来源），不是"密码学上无法设计 ExecutionAnchor 结构体"的证明；也不是"架构永远不可能"。候选 statement/模型可写（`CONSTRUCTED`），但接入需要新增信任根或改变信任模型。

**关键区分（不得混淆）**：
- 密码学上可构造：ExecutionAnchor 字段集、commitment 方案、verifier 模型 A/B/C、跨 proof 绑定三方案（`CONSTRUCTED`）。
- 当前架构中可接入：**无**——六项能力当前均不可 verifier-check。
- 需新增信任根：Model C 注册表、固定 VK 分发、verifier 生成的 execution_id。
- 需改变信任模型：从"prover 自测"变为"独立 verifier + 固定 statement"，必然改变当前信任边界。

---

## 2. 六个必答题逐项回答

1. **当前架构是否已有 verifier-trusted execution anchor？** —— **否**（`VERIFIED`）。无独立 verifier、无固定 VK、无 execution_id/program_id、T 不进 statement、无跨 proof 公开绑定。
2. **最小 anchor statement 包含哪些不可缺少的字段？** —— `protocol_version`、`program_id`（verifier 派生）、`execution_id`（verifier 生成）、公开输入（或承诺）、`total_steps`（若显式列出 `last_step_index`，须约束为 `total_steps - 1`）、`vk_id`（`execution_anchor_statement.md` §3）。`initial/final_state_commitment`、`program_commitment` 属可选、引入承诺信任面，非必需。
3. **T 应由谁固定或可信取得？** —— 由 verifier 固定预期 `total_steps = T`（含 step 0），或由电路内 step counter 受约束产生并由 verifier 核对（`total_steps` 进 statement）；`last_step_index = T-1` 必须由同一 counter 派生，Fetch 事件域为 `[1,T-1]`、共 `T-1` 个，step 0 无 Fetch proof / 无 Fetch commitment event。`total_steps` 必须来自受约束 counter 或 verifier 可信来源，不能是 prover 自报，也不能只用 `expected_step_bound` 上界替代（`expected_step_bound` 不等于实际 `total_steps`）；本轮术语修正不代表已实现 counter 或可信 T（`execution_anchor_statement.md` Q3/Q4）。
4. **VK 应由谁固定，如何绑定 program/circuit？** —— 由可信 setup/ceremony 生成、可信分发给 verifier 并固定（Model A/C）；通过 `vk_id ↔ program_id/circuit_digest` 映射绑定。固定 VK ≠ 固定 program，两者并列必需（`verifier_vk_trust_model.md` §5）。
5. **program identity 如何防止 prover 自行替换？** —— 最小路径 P1-A-1：verifier 固定预期完整 opcode table，逐项比对 proof public inputs + 固定 VK；无需新增电路承诺（比 digest 方案简单）。当前缺 verifier 主体与固定表（`verifier_independence.md` §2.2）。
6. **execution_id 如何防止跨执行 proof 拼接？** —— 必须由 verifier/可信调用方在请求开始时生成并固定，写入**所有**相关 proof 的 statement，绑定 program/输入/`total_steps`（及受约束派生的 `last_step_index`）/VK；当前无此对象，prover 侧 `enc_key` 不满足（`execution_anchor_statement.md` Q2；`proof_composition_binding.md` §0 第 1 条）。
7. **哪种 proof composition 方向最可行，证据是什么？** —— 逻辑上 Option A（统一 anchor）跨 proof 边界最可控、Option C（联合证明）边界最少，但两者都依赖承诺层与 verifier 固定 anchor 前置；当前**无证据**支持任一方向可接入（三方案均 `CONSTRUCTED`、当前 `BLOCKED`）。本轮不选胜者（`proof_composition_binding.md` §4/§5）。
8. **哪些信任假设是不可消除的？** —— 至少三项：① 一个 verifier 可信持有 VK 与预期 statement 的信任根（固定配置或注册表）；② VK↔program 映射的写入权受控；③ execution_id 的产生方（verifier/可信调用方）被信任。这些假设只能转移（如从 prover 转到注册表），不能消除（`verifier_vk_trust_model.md` §3）。
9. **当前架构能否在不引入新信任根的前提下完成上述绑定？** —— **不能**（`INFERRED`）。六项能力全部要求把字段从"prover/host 自我声明"提升为"verifier 可检查"，必然引入新可信来源或改变信任模型；不存在既不引入信任根、又不改信任模型的绑定方案。
10. **是否值得进入独立 anchor/verifier 接口原型？** —— **不建议**（本轮结论）。当前阻断是信任模型整体缺口，不是单点接口缺失；在 verifier 固定来源（VK、statement、execution_id、T）与承诺层、P2/B4 前置闭合前做原型，只会把 self-declared 数据换个封装。若后续继续，应先授权"信任根与前置闭合"工作。

---

## 3. 能力—来源—接口—代价映射表（必答表）

| 能力 | 当前实现 | 最小可信来源 | 必要接口 | 隐私/信任代价 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Program identity | opcode table 是 prover JSON 的 public input；检索无 program_id/hash（`VERIFIED` 缺失） | verifier 固定预期完整 opcode table（P1-A-1）或可信派生 program_id | 独立 verifier + 固定 VK + 逐项比对 | 无隐私代价；新增"固定表分发"信任 | `BLOCKED_BY_TRUST_MODEL` |
| Execution identity | 无 execution_id；`enc_key=Random()` 每执行一值、私有 witness（`VERIFIED` 缺失） | verifier/可信调用方生成并固定 execution_id | 写入所有 proof statement + 绑定 program/输入/T/VK | 公开 id 通常可接受；新增"id 产生方可信"假设 | `BLOCKED_BY_TRUST_MODEL` |
| Public input provenance | public inputs 全部来自 prover JSON（`plonk.rs:143-161`） | verifier 固定/校验期望 public input | verifier 持有期望值并比对 | 无隐私代价；新增"期望值来源可信"假设 | `BLOCKED_BY_TRUST_MODEL` |
| Trusted T | halt 是 public output（电路算），但 break 由 host、`total_steps`（T）=host 记录且不进 statement（快照 L419-421/L601） | verifier 固定 `total_steps = T`（含 step 0）或电路 counter 受约束产生 + verifier 核对；`last_step_index = T-1` 由同一 counter 派生 | 电路 counter + halt↔`last_step_index` 绑定 + `total_steps` 进 statement（`[1,T-1]` 共 `T-1` 个 Fetch 事件）；`expected_step_bound` 仅为上界 | 公开 T 通常可接受；需改 VM 电路 | `BLOCKED_BY_TRUST_MODEL`（电路侧 `BLOCKED_BY_CURRENT_INTERFACE`） |
| VK identity | `test_rng()` 现场生成、同函数 setup/prove/verify（`plonk.rs:302-304`） | 可信 setup/ceremony + 可信分发 + verifier 固定 | 独立 verifier + `vk_id↔program_id` 映射 | 新增"注册表/分发"信任根（Model C）或配置信任（Model A） | `BLOCKED_BY_TRUST_MODEL` |
| Cross-proof binding | 三 proof 只靠宿主内部哈希比对；无共享公开承诺/递归（快照 L174-181/L306-332/L410-583） | 受约束公共 anchor + 各 proof 电路内绑定（或联合证明） | Option A/B/C 三选一 + 承诺层 | 承诺 binding/hiding 信任面；递归接口改造 | `BLOCKED_BY_TRUST_MODEL`（承诺层 `UNKNOWN`/`BLOCKED`） |

---

## 4. 密码学可构造 vs 架构可接入 vs 信任根（明确区分）

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 密码学上可构造 | ExecutionAnchor 字段集、commitment、Model A/B/C、Option A/B/C 均可写出逻辑骨架 | 各文档 §`CONSTRUCTED` 条目 |
| 当前架构中可接入 | **无**——六项能力当前均不可 verifier-check | `trust_boundary_inventory.md` §5；`proof_composition_binding.md` §1 |
| 需新增信任根 | Model C 注册表、固定 VK 分发、verifier 生成 execution_id、固定 program 表 | `verifier_vk_trust_model.md` §3 |
| 需改变信任模型 | 从 prover 自测 → 独立 verifier + 固定 statement；必然扩大/转移信任边界 | 本轮全篇；`../aba-03-d3-03-01/decision.md` §6 问 6 |

**禁止的写法已避免**：未把"可以使用 hash/签名/承诺"写成"问题已解决"；未把字段写进 anchor 就称为已锚定；未把相同 id/hash 写成已绑定；未把链存在写成链完整；未把递归写成可读私有 witness。

---

## 5. UNKNOWN / BLOCKED 清单

**UNKNOWN**：
- 外部部署是否有独立 verifier / 固定 VK / 可信分发（现有证据未覆盖）；
- 单独替换 opcode public wire 后证明是否仍成功（未做攻击实验）；
- 跨 proof 身份拼接、重放、anchor equivocation、链截断是否可在当前实现实际复现（未运行）；
- 承诺层 binding/hiding/opening 能否闭合（MiMC 无归约、Pedersen 接入不承载）；
- 各候选方案的具体成本（门数、时间、proof 字节、递归开销）。

**BLOCKED（信任模型/架构缺必要能力）**：
- 固定 commit 无独立 verifier 主体、VK 现场生成、public inputs 来自 prover（`plonk.rs:293-315`）；
- 无 execution_id / program_id / program_hash（快照全检索无命中）；
- `total_steps`（T）不进 statement、break 与最终 T 由 host 控制（快照 L419-421/L601）；`last_step_index = T-1` 未受约束，Fetch 域 `[1,T-1]` 的可信 T 来源缺失；
- 无 VK↔program 绑定、无 verifier 固定 statement；
- 无跨 proof 共享公开承诺、无递归/组合证明接口；
- 承诺层（binding/hiding）——属前置未决（`../aba-03-d2/decision.md`）。

---

## 6. 状态冻结与一致性声明

- **阶段结论 `BLOCKED_BY_TRUST_MODEL`**；**B4 仍为 `B4_RELATION_PARTIALLY_FORMALIZED`**（旧文档不改）；**总决策仍 `HOLD_INSUFFICIENT_EVIDENCE`**。
- **P1-A / VK / P2 既有标签不变**：P1-A-1 仍为独立 verifier 侧前置（`CONSTRUCTED`）；VK 证据层级仍按 D1-C1（VERIFIED / UNKNOWN / CONDITIONAL INFERENCE）；P2 地址同一性仍需电路接口改动。本轮未重新评估或解除这些标签。
- **D3-03-01 不回改**：`BLOCKED_BY_CURRENT_INTERFACE` 与依赖图、UNKNOWN/BLOCKED 清单保持原样。
- **未实现** commitment、execution anchor、verifier、电路、原型；**未运行**测试或性能实验；**未改**任何既有文档、源码、测试、配置、数据。
- 只读复用固定 commit 源码快照与既有审计文档；只读核对了快照接口与行号（未混入其他版本源码）；grep 确认固定快照无 `execution_id`/`program_id`/`program_hash`。
- 冻结语义保持：real: `lookup=trace=reg0`；dummy: `lookup=reg0`、`trace=p−1`、不强加 lookup=sentinel、不承诺/不公开 `reg0`；step 0 有 VM 执行与 trace row，但无 Fetch proof、无 Fetch commitment event。
- **术语勘误（本轮唯一变更）**：`total_steps = T` 为 VM 总执行步数（含 step 0），`last_step_index = T-1` 为最后实际执行的 step index，Fetch 事件索引 `[1,T-1]`、总数 `T-1`；不再使用旧的语义不明确末步字段。本轮未实现 counter，也未取得 verifier 可信 T；所有既有判定与 HOLD 不变。
- **完成后停止**：不启动下一阶段（D3-03-03 等），不实现 R5–R8 电路，不启动独立 verifier/anchor 原型，不扩展到 P1-A / VK / P2 的实现，不解除任何 HOLD。等待独立审查。
