# ABA-03-D3-03-03 / Trust Root 分类

> 实验仓起点：`5c84f38c6df17acd458c1681a8ca18da0377281a`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：有边界的架构研究；只做分类与依赖分析，不实现 verifier / 电路 / ORAM / commitment。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。本文中的 `VERIFIED` 指本仓既有固定快照/审计可核对事实，不等于本轮新实验验证。

---

## 0. 冻结定义与四类信任根

### 0.1 执行步数冻结语义（沿用 D3-03-02-C1）

```
total_steps = T
last_step_index = T - 1
Fetch event indices = [1, T - 1]
Fetch event count = T - 1

step 0:
  VM execution = yes
  trace row = yes
  Fetch proof = no
  Fetch commitment event = no
```

`last_step_index` 是从 `total_steps` 派生的最后实际执行 step index，不能表示 `total_steps` 本身；`expected_step_bound` 只是上界，不等于实际 `T`（`VERIFIED`，本仓冻结）。

### 0.2 四类信任根的区分

| 类别 | 含义 | 本轮判断 | 标签 |
| --- | --- | --- | --- |
| 1. 密码学证明不可避免的外部假设 | 证明系统 soundness 所依赖的 setup/CRS 假设（依系统而异）、验证算法正确性、对“公开 statement 由谁决定”的外部选择 | 无法在纯 proof 内自我消除；但不同 SNARK 系统的 setup 假设不可混用。透明/递归方案可移除某一类 setup 信任，但不移除 verifier 主体与 statement 来源 | `INFERRED` |
| 2. 当前实现缺失造成的工程依赖 | 独立 verifier 主体、固定 VK 分发、verifier 生成 execution_id、verifier 固定 program/public input 期望、可信实际 T | 当前固定 commit 中均缺；属于可工程新增的最小信任面，但新增后仍不等于语义闭合 | `VERIFIED`（缺失事实） + `CONSTRUCTED`（候选补齐） |
| 3. 可由固定配置、可信调用方或证明约束替代的信任根 | registry ↔ 固定配置；TEE ↔ 普通独立软件 verifier；verifier 固定 T ↔ 电路 counter 产生 T；program_id ↔ 固定 opcode table | 存在替代路径；选择取决于部署模型，不能预设 registry/TEE 更先进 | `CONSTRUCTED` / `INFERRED` |
| 4. 加入后仍不能解决 B4 / 跨 proof 绑定的信任根 | “我信任这个 verifier”、“相同 execution_id”、“相同哈希字段”、hash chain、普通签名 | 只能建立配置/引用可信，不能替代证明关系对 step、事件类型、step↔row、顺序、终止与跨 proof 同一性的约束 | `BLOCKED`（当前关系） / `INFERRED` |

**核心边界（`INFERRED`）**：信任根决定 verifier 接受什么 statement；它不决定 proof 关系实际约束了什么，也不决定多个 proof 是否绑定到同一次执行。

---

## 1. A. Verifier 身份与执行环境

| 问题 | 当前证据 / 候选设计 | 判断 | 标签 |
| --- | --- | --- | --- |
| 谁运行 verifier？ | 固定 commit 中 setup/prove/verify 在同一进程路径（`docs/aba-03-d3-03-02/verifier_vk_trust_model.md` §1；`docs/aba-03-c2/verifier_interface_audit.md`） | 当前无独立 verifier 主体 | `VERIFIED` |
| verifier 是否独立于 prover？ | 最小要求是 verification 主体、VK 与 statement 期望不由 prover 同时生成/提供 | 不独立时，proof 自洽检查不构成应用级验证 | `INFERRED`；当前缺失 `VERIFIED` |
| verifier 是否可信、是否可能被替换？ | 候选：固定 verifier 二进制/配置、签名分发、可信安装基线；签名只保护分发来源，不证明语义约束 | 需要 verifier 身份与配置完整性；外部部署是否有此机制 `UNKNOWN` | `CONSTRUCTED` + `UNKNOWN` |
| 是否需要 TEE？ | 普通独立软件 verifier 可在“proof + 固定 statement + 固定 VK”模型下满足最小验证目标；TEE 仅在需防止宿主篡改 verifier 代码/配置时增加保护 | TEE 是额外信任根，不是最小必要条件 | `INFERRED` |
| 若不使用 TEE，普通独立软件 verifier 能否满足目标？ | 对“验证固定 statement 上的 proof”可以满足；对“执行事件完整性”不能单独满足 | 答案依赖后续 R5–R8/B4 证明关系，不依赖 TEE | `CONSTRUCTED` + `INFERRED` |

**A 小结**：最小 verifier 信任根是“独立运行的验证主体 + 固定配置/固定期望”，不是 TEE。当前固定 commit 不满足独立性（`VERIFIED`）；外部是否存在独立 verifier 仍 `UNKNOWN`。

---

## 2. B. Verification Key

必须分开三类信任，不得混为一项：

| 子项 | 分析 | 标签 |
| --- | --- | --- |
| setup 信任 | 由证明系统决定。Groth16 属 preprocessing SNARK 语境；PLONK 属 universal/updatable SRS 语境（见 L2/L3）。本仓既有后端事实定位主路径为 Plonk（非 Groth16），`groth16/verifier.rs` 为另存泛型快照、与主路径关系 `UNKNOWN`（S13）；本轮沿用该定位，不把 Groth16 setup 语境套到主路径 | `PAPER_CLAIM`（文献） + `SOURCE_VERIFIED`（主路径定位） + `UNKNOWN`（Groth16 快照关系） |
| VK 分发信任 | verifier 必须通过可信分发或固定配置取得正确 VK；不能接受 prover 临时提供 VK 作为本次验证依据 | `CONSTRUCTED`；当前现场 `test_rng()` 为 `VERIFIED` 缺失 |
| 验证算法正确性 | `verify_proof` 实现正确性与实例/VK 匹配是工程与密码学实现信任；与“VK 来自哪里”不同 | `INFERRED`；当前只核对接口存在（`VERIFIED`） |

| 问题 | 当前证据 / 候选设计 | 判断 | 标签 |
| --- | --- | --- | --- |
| VK 由谁生成？ | 当前 `test_rng()` 现场生成（`verifier_vk_trust_model.md:18`；`decision.md:52`） | 非 verifier 固定；当前无可信 setup/ceremony 证据 | `VERIFIED` |
| 是否需要可信 setup / ceremony？ | 取决于证明系统：per-relation preprocessing 与 universal/updatable SRS 的信任面不同 | 不能把不同系统的 setup 假设混用 | `PAPER_CLAIM` + `INFERRED` |
| VK 如何分发、固定和更新？ | 候选：verifier 内置固定 VK，或由可信 registry 分发并版本化 | 固定配置最简单；registry 只在多程序/撤销场景增加必要能力 | `CONSTRUCTED` |
| `vk_id` 与 `program_id` 如何绑定？ | 固定 VK 只绑定电路/证明系统结构，不自动绑定应用 program；需显式映射与 verifier 比对 | 当前无此绑定 | `CONSTRUCTED`；当前缺失 `VERIFIED` |
| 是否必须 verifier 内置固定 VK？ | 最小模型下可由 verifier 固定配置持有；registry 是替代不是必需 | `Model A` 可满足单固定程序部署 | `INFERRED` |

**B 小结**：VK 信任根最小化为“可信来源的 VK + verifier 固定持有 + `vk_id↔program_id` 显式绑定”；setup 信任与分发信任必须分别记录。当前均不满足（`VERIFIED`），外部假设 `UNKNOWN`。

---

## 3. C. Program Identity

| 机制 | 解决什么 | 不能解决什么 | 标签 |
| --- | --- | --- | --- |
| 固定 opcode table（P1-A-1） | verifier 持有预期完整表，逐项比对 proof public inputs；无需新增整程序承诺 | 当前表中整表无约束、输入来自 prover JSON；固定表比对只证明“公开 wire 等于预期表”，不自动证明执行时每步按该表选择 opcode | `CONSTRUCTED`；当前通道事实 `VERIFIED` |
| 程序哈希 / `program_commitment` | 给程序一个稳定摘要，可隐藏具体内容或将表承诺放入 statement | 哈希/承诺值若由 prover 提供且无 verifier 预期值，不比明文更可信；承诺 binding/hiding/opening 当前未决 | `CONSTRUCTED` / `UNKNOWN` |
| `program_id` | 由 verifier 从固定表可信派生，作为轻量身份引用 | `program_id` 只是标签；必须由 verifier 派生或固定，prover 自报标签无意义 | `CONSTRUCTED` |

| 问题 | 分析 | 标签 |
| --- | --- | --- |
| verifier 如何知道待验证程序？ | 固定预期表 / 固定摘要 / 固定 id，三选一或并用；必须 verifier 侧可核对 | `CONSTRUCTED` |
| 如何保证 program identity 对应实际执行的 VM 程序？ | 需要 opcode 表进入 proof statement 且被电路逐行选择约束；当前整表无约束、无 verifier 期望值 | `BLOCKED`（当前接口） |
| 是否存在 prover 自报 `program_id`？ | 当前无 `program_id` 实体；opcode 表来自 prover JSON，prover 可填信道层面值；单独替换后证明是否成功仍 `UNKNOWN` | `VERIFIED`（通道） + `UNKNOWN`（攻击结果） |

**C 小结**：最小路径是 verifier 固定完整 opcode table 并逐项比对（P1-A-1），`program_id` 可由该表派生；程序哈希/承诺不是必须且引入未决承诺信任面。当前无法证明 program identity 对应实际执行（`BLOCKED`）。

---

## 4. D. Execution Identity

| 问题 | 当前证据 / 候选设计 | 判断 | 标签 |
| --- | --- | --- | --- |
| `execution_id` 应由谁生成？ | verifier 或可信调用方在请求开始时生成并固定；不能由 prover 生成 | prover 生成的 `enc_key = Random()` 不满足 | `CONSTRUCTED`；当前缺失 `VERIFIED` |
| 是否需要防跨执行 proof 拼接和重放？ | 需要。否则不同 proof 可各自对自洽 statement 有效，却不属于同一次执行 | 当前无跨 proof 共享公开绑定 | `INFERRED` + 当前 `BLOCKED` |
| 如何绑定 program / public input / VK / 执行上下文？ | `execution_id` 必须写入所有相关 proof 的 statement/transcript，并绑定 program expectation、public input、`total_steps`、`vk_id` | 只写在一个 proof 里不够 | `CONSTRUCTED` |
| verifier 生成随机 nonce 是否足够？ | 不充分。nonce 只是唯一性标识；仍需 statement 内绑定、所有 proof 引用、域分离与 transcript 绑定 | 相同 nonce ≠ witness 同一性 | `CONSTRUCTED` + `INFERRED` |
| 当前是否具备？ | 固定快照无 `execution_id`；prover 侧 `enc_key` 为私有 witness | 当前无实体 | `VERIFIED` |

**D 小结**：`execution_id` 的最小生成方是 verifier/可信调用方，不是 prover；防拼接需要“每次唯一 + 所有 proof statement 引用 + 跨字段绑定”，单独 nonce 或相同字段不构成证明。

---

## 5. E. Public Input Provenance

| 问题 | 当前证据 / 候选设计 | 判断 | 标签 |
| --- | --- | --- | --- |
| public input 是谁提供的？ | 当前全部来自 prover JSON（`plonk.rs:143-161`） | 来源未固定 | `VERIFIED` |
| verifier 固定预期值？ | 对公开输入（如 n、opcode table、program 引用）由 verifier 持有期望值并逐项比对 | 最小可信路径 | `CONSTRUCTED` |
| 可信调用方提供？ | 调用方可签名/认证请求输入；verifier 校验签名后把值作为固定 statement | 引入调用方身份信任，不替代电路约束 | `CONSTRUCTED` |
| 外部系统签名？ | 签名解决“输入来自谁”，不解决“输入与私有 witness 的关系是否满足语义” | 不得用签名替代电路内约束 | `INFERRED` |
| 私有输入如何分析？ | 私有 witness 不需要 verifier 知道值，但必须由证明关系约束其与公开 statement 的关系；`enc_key` 等私有随机盐不能自动成为可信锚点 | 隐藏 ≠ 可信 | `CONSTRUCTED` + `INFERRED` |
| “进入 proof statement”是否等于来源可信？ | 否。proof 只证明相对给定 public input 自洽；public input 本身仍需 verifier 固定或可信取得 | 这是 Model B/statement substitution 风险核心 | `INFERRED`；当前 `SOURCE_SUPPORTED` |

**E 小结**：public input provenance 的最小信任根是 verifier 固定期望值或可信调用方认证；公开/私有输入都必须与证明层语义约束分开讨论。

---

## 6. F. Trusted Execution Length

冻结语义见 §0.1。下表比较五条路径：

| 路径 | 信任假设 / 最小接口 | 适用场景 | 不能解决的问题 | 标签 |
| --- | --- | --- | --- | --- |
| verifier 固定实际 `total_steps = T` | verifier 对本次执行独立知道 T；T 进 statement 并与 proof 核对 | 固定公开工作量、回归测试、单程序固定执行 | 若 T 依赖私有输入或执行路径，verifier 未必能独立知道；不能证明 halt 与事件序列真实一致 | `CONSTRUCTED`；当前缺失 `VERIFIED` |
| 电路内 counter 约束产生 T | VM 电路新增 step counter、递增约束、halt↔`last_step_index` 绑定，`total_steps` 作为 public output 进 statement；`last_step_index = T-1` 受同一 counter 约束 | 通用执行证明；信任最小但需改电路 | 单独 counter 不证明 Fetch 事件存在/顺序/类型/trace row；仍需 R5–R8 与 B4 约束 | `CONSTRUCTED`；当前 `BLOCKED_BY_CURRENT_INTERFACE` |
| 可信执行环境报告 T | TEE 证明执行环境与步数；verifier 信任 attestation | 宿主不可信且需保护 verifier/计数过程 | 新增硬件/证明信任根；attestation 报告 T 不等于 VM 语义约束或事件完整性 | `INFERRED` / `UNKNOWN`（外部部署） |
| prover 自报 T | prover 提供 T 值 | 无安全语义场景 | 可被前缀截断；不能作为可信终止锚点；当前 host 记录且不进 statement | `VERIFIED`（当前事实） + `BLOCKED`（作为信任根） |
| `expected_step_bound` | verifier 固定上界，约束 `total_steps ≤ bound` | 资源上限/DoS 防护 | 不等于实际 T；无法排除 prover 声明较小 T 的前缀截断；`count(events)=T-1` 仍需真实 T | `VERIFIED`（host 阈值） + `INFERRED`（边界） |

**F 小结**：最小可信 T 路径是“受约束 counter 产生 `total_steps`，verifier 核对；`last_step_index` 派生并同约束”，或固定执行下 verifier 直接固定 T；TEE 不是必需，prover 自报与上界不可替代。

---

## 7. 最小信任根集合（候选，不是闭合证明）

在 Model A 下，最小 verifier 侧信任面可写为：

1. 独立 verifier 主体，其代码/配置来源可审计；
2. verifier 固定 VK，并固定 `vk_id↔program_id` 映射；
3. verifier 固定 program expectation（完整 opcode table，或可信派生 `program_id`）；
4. verifier/可信调用方生成并固定 `execution_id`，写入所有相关 proof statement；
5. verifier 固定或认证 public input expectation；
6. 可信 `total_steps = T`：verifier 固定，或由电路 counter 受约束产生并核对；`last_step_index = T-1` 派生。

**明确边界（`INFERRED`）**：以上六项只闭合“由谁决定 statement / 用哪个 VK / 哪次执行”，**不闭合** R5–R8 的证明层缺口，也不闭合 B4-R2–R8 的事件完整性；后者必须进入证明关系本身，见 `coverage_matrix.md`。

---

## 8. 本阶段分类结论

- 当前固定 commit 的 verifier 侧信任根**不完整**（`VERIFIED`）：无独立 verifier、VK 现场生成、public inputs/program 表来自 prover、无 `execution_id`、T 不进 statement。
- 最小新增信任面不需要 registry 或 TEE（`INFERRED`）；固定配置 + 独立软件 verifier 足以承担“固定 statement 验证”的角色。
- 所有新增信任根都只提升 statement 来源可信，不自动提升证明语义；R5–R8/B4 仍 `BLOCKED_BY_CURRENT_INTERFACE` / `BLOCKED_BY_TRUST_MODEL`（既有判定不变）。
- 外部真实部署是否具备上述任一项仍 `UNKNOWN`；本轮不把候选最小集合写成已实现能力。
