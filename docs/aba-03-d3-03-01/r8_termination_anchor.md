# ABA-03-D3-03-01 / Phase 4：R8 — Termination Anchor 可实现性

> 实验仓起点：`9788d5c1888ac28ee936892d36086cac32423115`；固定上游 `10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 目标：证明事件序列覆盖真实执行到的最后一步，而非 prover 自行声明较短 T。本轮只读审计 + 接口候选，不实现电路。
>
> 证据来源：`interface_evidence_inventory.md` §1 组件 5/6/7；`../aba-03/source_trace_audit.md` A3；`../aba-03-d3-02/completeness_attack_matrix.md` A7；`../aba-03-d3-02/candidate_constructions.md` B。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。

---

## 1. 固定实现中的终止语义（VERIFIED）

| 事实 | 源码证据 | 标签 |
| --- | --- | --- |
| halt 是 VM 电路 public output | `ZkVmExecutorCircuitBoardGenerator.cs:902-906` 原始（`out_halt`） | VERIFIED |
| host 读 `pubOutHalt = GetOutput("out_halt").AssumeNonShare()` | `ZkProgramExecutor.cs:339` | VERIFIED |
| 循环 break 由 host C# 控制：`if (pubOutHalt == One) break;` | `ZkProgramExecutor.cs:419-421` | VERIFIED |
| 步数上限 `GlobalStepNoMoreThan`，超出 `throw`（执行器阈值） | `ZkProgramExecutor.cs:34,118-120`；BubbleSort 初始化见 `source_trace_audit.md` A3 | VERIFIED |
| 最终 T 作为 host 返回值记录 | `ZkProgramExecutor.cs:601`（`GlobalStepCounter = globalStepCounter`） | VERIFIED |
| T 不在 circuit public input 集合（public input 只有 step counter/public input/opcode table） | `plonk.rs:143-161` + C# `AddPublic` 点，见 `verifier_interface_audit.md` §A4 | VERIFIED（既有证据） |
| 无独立 verifier、vk 现场生成 | `plonk.rs:293-315` | VERIFIED（既有证据） |

**直接结论（VERIFIED + INFERRED）**：当前"终止"是 host 读到 VM 电路的 `out_halt` public output 后，在 C# 控制流中 break，并把最终步数记录为返回值。这个 T 是 **host 记录值**，不是进入 proof statement 的可信终止锚点；verifier 既无固定预期 T，也无电路约束证明"事件序列覆盖到真实 halt 步"。

---

## 2. 三种"看似足够"但实则不足的锚定（明确排除）

1. **`count(events)=T−1` 不能独立锚定真实 T**（`INFERRED`）：计数只对 prover 声明的 T 自洽；prover 声明更短 `T′` 并只提交前缀时 `count(P)=T′−1` 照样成立（D3-02 A7 结构性盲区）。
2. **prover 自报 T 不能作为可信终止证明**（`VERIFIED` 现状 + `INFERRED`）：T 当前不进 public input，即使让它进 public input，也只是 prover 提供的公开值，无 verifier 可信来源核对。
3. **哈希链最终摘要若无可信终值，不能独立证明完整性**（`INFERRED`，沿用 D3-02 B）：prover 可对任意（含截断后的）前缀重算自洽链；必须另有可信终值或执行电路输出的终止承诺。

---

## 3. 四种候选方案分析

### R8-A：Verifier 固定 T

- **T 由谁确定**：需 verifier 从外部可信来源取得预期 T（`CONSTRUCTED`）。
- **verifier 如何取得预期 T**：固定 commit 无机制 → `UNKNOWN`。可能的外部来源（可信执行配置、预期程序+输入的确定性步数）本轮不假设已存在。
- **T 是否与 program/execution 绑定**：当前无 execution_id / program_id 可信锚点（P2/context 未决），T 单独固定无法防止同一 proof 被复用到不同执行 → `UNKNOWN`。
- **是否允许同一 proof 用于不同 T/执行**：若 T 不是 proof statement 的一部分，允许；修复需把 T 与 execution 锚点同时纳入 statement（`CONSTRUCTED`）。
- **证据等级**：候选 `CONSTRUCTED`；取得机制 `UNKNOWN`。

### R8-B：公开最终 step counter

- **最终 counter 是否来自 VM 电路状态**：当前最终 counter 是 host 循环变量（L113/601），非电路状态 → `VERIFIED`（现状）；候选可新增电路内 counter（R5-A，`CONSTRUCTED`）。
- **是否有从初始到最终的完整状态转换约束**：当前无（step 是 public input，无递增约束，L87 依赖 MPC 诚实）→ `BLOCKED`。
- **仅公开最终值是否足够**：否（`INFERRED`）。公开最终 T 不证明中间无跳步/截断；必须配合逐步递增约束（R5-A）与终止状态证明。
- **证据等级**：`VERIFIED`（现状）+ `CONSTRUCTED`（候选）+ `INFERRED`（不充分结论）。

### R8-C：终止状态约束

- **halt 条件在哪里产生**：VM 电路 `out_halt`（L902-906），由 opcode 派生（Halt 指令）。
- **是否存在可验证的 halt 状态**：out_halt 是 public output（可验证其布尔值），但它只说明"本步是 halt"，不证明"之前所有步都被纳入且未提前截断" → `VERIFIED`（halt 输出存在）+ `UNKNOWN`（覆盖性）。
- **是否可能在未真正 halt 时截断执行**：当前可能——host 在 `pubOutHalt==One` 时 break，但 prover/host 若提供较短执行并声明相应 T，无电路约束阻止（配合 L118 步数上限非 halt 证明）→ `INFERRED`。
- **能否证明 Fetch 事件序列覆盖最后一个有效 VM step**：需把 halt 步与事件序列末项在同一电路/公共承诺中绑定（`CONSTRUCTED`），当前无 → `BLOCKED`。
- **证据等级**：候选 `CONSTRUCTED`；覆盖性 `UNKNOWN`/`BLOCKED`。

### R8-D：执行摘要或最终承诺

- **摘要绑定字段**：候选绑定 `program/execution instance/final step/事件序列摘要`（`CONSTRUCTED`）；当前逐行哈希含 step 与随机 enc_key（Prove L65-82），但 enc_key 每次执行随机（`ZkProgramExecutor.cs:65`），不能稳定充当执行摘要。
- **摘要由谁生成**：当前无可信执行摘要；候选需 VM 执行电路输出终态承诺（`CONSTRUCTED`）。
- **verifier 是否拥有可信预期值或可验证生成关系**：当前无 → `UNKNOWN`/`BLOCKED`。
- **关键限制**：若摘要由 prover 生成且无可信终值/生成关系，退化为"哈希链自洽"问题，不能锚定 T（同 §2.3）。
- **证据等级**：候选 `CONSTRUCTED`；可信来源 `UNKNOWN`。

---

## 4. R8 当前状态与最小接口缺口

| 项 | 结论 | 标签 |
| --- | --- | --- |
| 当前可信终止锚定 | 无；halt 是 public output，break/T 由 host 控制，T 不进 statement | `VERIFIED` |
| R8-A verifier 固定 T | 需外部可信 T 且与 execution 绑定；机制缺失 | `CONSTRUCTED` + `UNKNOWN` |
| R8-B 公开最终 counter | 公开值不够，需 R5-A 递增约束 | `CONSTRUCTED` + `INFERRED` |
| R8-C 终止状态约束 | halt 输出存在，覆盖性无约束 | `VERIFIED` + `BLOCKED` |
| R8-D 执行摘要 | 需可信终值/生成关系，当前无 | `CONSTRUCTED` + `UNKNOWN` |
| 是否改电路 | 是（step counter + halt↔事件末项绑定） | `CONSTRUCTED` |
| 是否改 prover/verifier 接口 | 是（T/execution 锚点进 statement + verifier 可信取得） | `CONSTRUCTED` |
| 成本 | 门数/时间/字节全 `UNKNOWN` | `UNKNOWN` |

**R8 当前状态：`BLOCKED_BY_CURRENT_INTERFACE`** —— 固定架构中终止步是 host 记录值，缺少 verifier 可检查的终止锚定接口；`count`/自报 T/无可信终值的哈希链均被明确排除。所有候选接口均为 `CONSTRUCTED`，未实现、未测量。这一结论直接支撑决策文档对"是否值得进入接口原型"的判断。
