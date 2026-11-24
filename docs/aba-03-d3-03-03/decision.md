# ABA-03-D3-03-03 / Verifier Trust Root 最小化与研究路径决策

> 实验仓起点：`5c84f38c6df17acd458c1681a8ca18da0377281a`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：有边界的架构研究与决策分析；不实现 verifier / 电路 / ORAM / commitment，不修改既有原型。
>
> 证据来源：`trust_root_taxonomy.md`、`trust_model_comparison.md`、`coverage_matrix.md`、`minimal_architecture.md`、`evidence_and_references.md`。
>
> 阶段结论候选：`GO_TO_INTERFACE_DESIGN` / `GO_WITH_RESTRICTED_SCOPE` / `HOLD_INSUFFICIENT_EVIDENCE` / `NO_GO_CURRENT_ARCHITECTURE`。

---

## 1. 阶段结论：`NO_GO_CURRENT_ARCHITECTURE`

**结论限定（`INFERRED`）**：本结论针对“在当前固定 VDORAM C# frontend / Rust backend 架构上继续推进以实现原始可验证 RAM 安全目标”。它不是“密码学上不可能”的证明，也不是对所有可研究问题的 `NO_GO`。

核心理由：

1. 当前固定 commit 中不存在独立 verifier；VK 由 `test_rng()` 现场生成，public inputs/program opcode table 来自 prover JSON，最终 T 为 host 记录且不进 statement（`SOURCE_VERIFIED`）。
2. 加入 verifier 信任根只能修好“谁固定 statement / 用哪个 VK / 哪次执行”的层次 1 问题；R5–R8 与 B4-R2–R8 的层次 3/4 语义缺口仍在（`INFERRED` + `BLOCKED`）。
3. 覆盖矩阵显示：相同 `execution_id`、相同哈希字段、hash chain、签名、递归证明本身都不能替代 step、event type、step↔row、ordering、trusted T 与跨 proof 同执行绑定（`CONSTRUCTED` / `INFERRED`）。
4. Joint proof 与 separate proofs 两条路径均需重写现有证明接口/关系；承诺层、随机盐认证、递归接口与成本均 `UNKNOWN` 或 `BLOCKED`，当前没有可进入接口设计的最小闭合路径。
5. 因此不应为了给出 `GO` 而降低安全目标；也不应把“需要大量工程工作”直接等同于“没有研究价值”。

**总决策不变**：`HOLD_INSUFFICIENT_EVIDENCE` 仍为本仓总体状态；本轮新增的阶段标签 `NO_GO_CURRENT_ARCHITECTURE` 只限定当前架构推进方向。

---

## 2. 六个必答问题

### 2.1 Model A/B/C 哪一个是最小合理 trust model？

**答案（`INFERRED`）**：**Model A（固定配置的独立软件 verifier）**是单固定程序、固定期望输入场景下的最小合理 trust model。

- Model A 只要求独立 verifier、固定 VK、固定 program expectation、固定 public input expectation、verifier/调用方生成 `execution_id`、可信 `total_steps` 来源；不需要 TEE 或 registry。
- Model B 在 Agent/tool execution 场景中更贴近“调用方知道用户意图”，但增加调用方↔verifier 身份/编码一致性边界；它不是天然更强。
- Model C 仅在多程序、多版本、撤销、跨租户授权时增加必要能力；registry 会引入写入权、状态新鲜性、版本回滚等新信任根，不应预设更先进。

**但**：选 Model A 只闭合 statement 来源可信，不闭合 R5–R8/B4。

### 2.2 是否存在不需要新增信任根的路径？

**答案（`INFERRED` + `VERIFIED`）**：**不存在**能在当前架构下达到应用级验证且完全不新增 verifier 侧信任根的路径。

- 当前 setup/prove/verify 同进程、VK 现场生成、public inputs 来自 prover JSON、无 `execution_id`、T 不进 statement（`SOURCE_VERIFIED`）。
- 若 verifier 仍由 prover 同一主体控制，则 proof 自洽检查不能成为独立验证。
- 可以避免新增 TEE 与 registry，但不能避免“独立验证主体 + 固定 statement/VK 期望 + execution_id 生成方 + 可信 T 来源”这组最小信任根。
- 这些信任根仍不足以解决证明层语义缺口。

### 2.3 是否值得继续推进当前 VDORAM C# frontend / Rust backend？

**答案（`INFERRED`）**：**不建议按当前架构继续推进为可验证 RAM 系统。**

- 不建议进入“只加独立 verifier / 固定 VK / 配置文件”的增量工程路径；这会制造“已经可信”的假象。
- 当前 C#/Rust 代码可作为只读研究样本或历史基线，但不应作为下一阶段 GO 的实现目标。
- 若未来另立研究任务，必须先定义 R5–R8/B4 语义约束与 VK 固定路径，再谈接口改造。

### 2.4 Joint proof 与 Separate proofs，哪一种更适合下一阶段研究？

**答案（`INFERRED`）**：若未来**另立**“可验证执行语义绑定”研究，**优先研究 Joint proof 的语义最小性**；Separate proofs + public commitment bridge 作为对照路径，不作为当前仓立即实现目标。

- Joint proof：跨 proof 缝更少，R5–R8/B4 可在同一关系中表达；代价是需重写 VM/Fetch/Prove 关系与 VK，成本 `UNKNOWN`。
- Separate proofs：工程模块化更自然，但强依赖承诺 binding/opening/linking 与跨 proof 同执行绑定；承诺层和随机盐认证当前 `UNKNOWN`/`BLOCKED`。
- 两者都 `CONSTRUCTED` / `BLOCKED`；本轮不选已实现胜者。

### 2.5 是否有值得单独发表研究的密码学问题？

**答案（`INFERRED` + `UNKNOWN`）**：存在值得**单独定义和调研**的问题，但**不能现在宣称可发表或具有新颖性**。

候选问题：在宿主不可信、跨电路公开锚定受限的条件下，如何形式化并证明“执行事件完整性”与“跨 proof 同执行绑定”，使其严格区别于：

- proof 对给定 public input 自洽；
- verifier 固定配置可信；
- 外部签名/哈希链/递归验证通过。

门槛：需给出非组合式新语句或可证性质、与既有 zkVM/PCD/可验证计算工作的明确差异、最小可证定理与可复现实验。当前只有逻辑构造与证据边界，novelty `UNKNOWN`。

### 2.6 是否应该继续 ABA-03，还是将其作为当前架构下的 HOLD 结项？

**答案（`INFERRED`）**：**作为当前架构下的 HOLD 结项。**

- 不启动 ABA-03-D3-03-04、不实现 verifier/anchor/counter/commitment、不改 VM/Rust backend。
- 总决策 `HOLD_INSUFFICIENT_EVIDENCE` 不变；B4 仍 `B4_RELATION_PARTIALLY_FORMALIZED`；D3-03-01 `BLOCKED_BY_CURRENT_INTERFACE`；D3-03-02 `BLOCKED_BY_TRUST_MODEL`。
- 若未来转向 Agent 执行可信性/密码学绑定机制，应另立任务包，不因本轮完成而自动启动。

---

## 3. 为什么不是其他结论

| 候选结论 | 不采用的理由 | 标签 |
| --- | --- | --- |
| `GO_TO_INTERFACE_DESIGN` | verifier 信任根、R5–R8、B4、承诺/桥接与成本均未闭合；接口设计会固化缺失语义 | `INFERRED` |
| `GO_WITH_RESTRICTED_SCOPE` | 本轮没有授权新研究问题的最小可证目标；当前架构仍缺语义约束，不能把“受限”写成可进入原型 | `INFERRED` |
| `HOLD_INSUFFICIENT_EVIDENCE` | 作为**总决策**保留；作为**本轮阶段结论**不够精确，因为本轮已能判定“当前架构继续推进”不可取 | `INFERRED` |
| `NO_GO_CURRENT_ARCHITECTURE` | 与证据一致：当前架构的多数关键语义不在证明关系中，且新增 verifier 不足以闭合 | 采用 |

---

## 4. 证据等级汇总

| 结论类型 | 证据等级 | 说明 |
| --- | --- | --- |
| 当前无独立 verifier、VK 现场生成、public inputs 来自 prover、T host 记录、无 execution_id/program_id | `SOURCE_VERIFIED` | 固定 commit 与既有审计文档可核对 |
| 主路径为 Plonk，Groth16 verifier 为另存泛型快照，与主路径关系未知 | `SOURCE_VERIFIED` + `UNKNOWN` | 不得把 Groth16 setup 语境套到主路径 |
| Trust Root 分类、Model A/B/C 比较、覆盖矩阵、两架构草案 | `CONSTRUCTED` / `INFERRED` | 候选设计/逻辑分析，未实现 |
| R5–R8 / B4 当前接口缺口 | `BLOCKED_BY_CURRENT_INTERFACE` / `BLOCKED` | 既有判定，不改写 |
| 外部部署是否有独立 verifier、registry、TEE、固定 VK | `UNKNOWN` | 证据未覆盖 |
| 可发表新颖性、成本、递归/承诺具体开销 | `UNKNOWN` | 未做文献深度对比与实测 |

---

## 5. 状态冻结与一致性声明

- 阶段结论：`NO_GO_CURRENT_ARCHITECTURE`（限定当前架构推进）。
- 总决策：`HOLD_INSUFFICIENT_EVIDENCE`，不解除。
- `BLOCKED_BY_TRUST_MODEL`、`BLOCKED_BY_CURRENT_INTERFACE`、`B4_RELATION_PARTIALLY_FORMALIZED` 均不变。
- P1-A / VK / P2 既有标签不变；D3-02、D3-03-01、D3-03-02 及 C1 冻结文档不回改。
- 冻结步数语义保持：`total_steps = T` 含 step 0，`last_step_index = T-1`，Fetch 索引 `[1,T-1]`、事件数 `T-1`，step 0 无 Fetch proof / 无 Fetch commitment event。
- 本轮未实现 verifier、counter、anchor、commitment、recursion、ORAM 或电路；未运行测试；未改源码/配置/数据。
- 本轮只新增六份文档；不得回写为任何历史阶段已通过或已实现。

---

## 6. 停止边界

本轮六份文档完成并提交推送后立即停止：

- 不启动 D3-03-04 或任何新原型；
- 不修改 VM 电路、Rust backend、C# frontend；
- 不构造新 commitment gadget 或递归 proof；
- 不扩展 ORAM 性能实验；
- 不解除任何 HOLD。

等待独立审查后再决定是否另立研究任务。
