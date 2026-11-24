# ABA-03-D3-01 / Phase 5：统一验证关系与阻断项闭合性决策

> 实验仓起点：`03960aa941bcd8ef88fbd06a83cf7599682a5cbd`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：设计与可行性评估；不实现电路、不改上游、不解除任何 HOLD、不启动 D3-02。
>
> 候选结论：`GO_TO_INTERFACE_SPEC` / `HOLD_INSUFFICIENT_EVIDENCE` / `NO_GO_CURRENT_ARCHITECTURE`。
>
> 证据来源：`unified_statement.md`、`verifier_independence.md`、`event_completeness.md`、`dependency_and_cost.md`；既有证据见文内逐项引用。

---

## 1. 决策：`HOLD_INSUFFICIENT_EVIDENCE`

**理由**：统一 statement 的字段与关系骨架已经可以写出，P1-A-1 也有可复用的 verifier 侧最小路径；但“能否形成一条最小、可审计的接口改造路线”仍取决于多个未闭合条件：承诺 binding/hiding 与随机数机制、Pedersen 当前路径承载性、step↔trace row 对应、B4 count/order/completeness/termination、`exec_id`/context 锚定、VK 外部信任模型。任一关键关系仍为 `UNKNOWN` 或 `BLOCKED` 时，不能把候选关系图写成接口规格已可冻结。

**为什么不选 `GO_TO_INTERFACE_SPEC`**：可以写出候选 statement，不足以证明该 statement 可被现有或最小改造后的电路/证明系统正确产生。特别是 dummy trace row 绑定与 B4 仍是 `CONSTRUCTED`/`BLOCKED`，承诺方案未定型（`commitment_candidates.md` §2/§4），MPC 认证随机不可用（`opening_and_randomness.md` §0/§2）。

**为什么不选 `NO_GO_CURRENT_ARCHITECTURE`**：当前证据显示的是接口缺失和未决条件，不是已证明的数学矛盾或明确不可接受的结构性障碍。P1-A-1 可复用公开输入通道；标准 `verify_proof` 与 MiMC gadget 存在；C2/C3 的难点尚未被证明不可克服。因此不做整体 NO_GO。

**既有状态标签不变**：ABA-03 `HOLD`、ABA-03-C2 `REQUIRES_CIRCUIT_INTERFACE_CHANGE`、ABA-03-D1 `HOLD_INSUFFICIENT_EVIDENCE`、ABA-03-D2 `HOLD_INSUFFICIENT_EVIDENCE` 均保持原样；本轮不修改这些文档，不解除任何 HOLD。

---

## 2. 五个必答问题

### Q1. 最小可行接口需要改变哪些组件？

候选最小接口由三段组成（`CONSTRUCTED`，均未实现）：

1. **verifier 侧**：独立 verifier、固定/可信 VK、固定预期完整 opcode table（P1-A-1）、固定 `n`/step 边界期望值；这一段主要不依赖电路改动。
2. **电路 statement**：real 步 `fetch_lookup=reg0=trace_addr` 与范围；dummy 步 `lookup=reg0`、`trace_addr=p−1`、实际 trace row `mem_addr=p−1`；event_type 由 opcode 派生并进入公开 statement/承诺；step↔trace row 映射；B4 count/order/halt。
3. **承诺/证明接口（若选隐藏路径）**：每步公开 `com_i`，两侧电路各自正确约束 opening；Pedersen 同 `C` + 同消息下 `r` 相同是代数结果，但接入需非原生群运算与可信生成器；若选认证随机或递归组合，还需对应 MPC share/证明组合接口。

这三段中第 1 段有可复用通道证据，第 2、3 段仍需新增约束与新接口（`dependency_and_cost.md` §5）。

### Q2. 哪些问题可以通过 verifier 侧检查解决？

- P1-A-1：verifier 固定完整 opcode table，逐项比较 proof public inputs；公开输入通道已存在（`InstructionFetch...cs:126-156`、`plonk.rs:143-161`），不需要新增整程序承诺电路。
- VK 信任模型：预固定 VK 或可信 setup/ceremony 的分发问题属于 verifier 侧；当前现场 `test_rng()` 为源码事实，外部模型为 `UNKNOWN`（`verifier_independence.md` §3）。
- 最终公开值比较：verifier 可比较两份 proof 的 `com_i`、event_type、step 与固定期望值；前提是这些值已被电路正确约束。
- P1-A-2 digest 也可由 verifier 比较，但需先新增电路 table→digest 绑定，不属于“只靠 verifier 检查”。

### Q3. 哪些问题必须新增电路约束？

- 真实 Load/Store 地址三值相等与 `0≤addr<n`（B1）。
- dummy 的 `trace_addr=p−1`、`trace_val=0`、实际 trace row sentinel 绑定，且不得暴露/承诺 `reg0`（B2）。
- event_type 由 opcode 在电路内派生并绑定到公开 statement/承诺，不能由 prover 声明。
- step↔trace row 对应、step 单调/连续、事件无遗漏/无重复/无重排、halt 边界（B4）。
- 承诺 opening 重算与两侧同一 `C` 的关系（若选共享承诺路径）。
- step0 显式排除：无 Fetch proof、无承诺事件。

以上均为 `CONSTRUCTED`，当前无实现证据。

### Q4. 哪些问题必须改变证明系统或 MPC share 接口？

- Pedersen 承诺接入 CompatCircuit→PLONK：需 `CurveVar`/群运算与非原生域适配，当前 Fr-wire 路径不承载（`commitment_candidates.md` §2/§4）。
- 认证随机数：若方案要求 verifier 不见 `r` 且 prover 不能重采样，当前 additive-only、无 MAC、无可用 Beaver/SPDZ 路径阻断主动安全认证（`opening_and_randomness.md` §0/§2）。
- 递归/组合证明：当前 `plonk.rs:293-315` 是单电路 setup→prove→verify，无组合接口；递归不能读子 proof 私有 witness（`design_options.md` §3/C1 勘误）。
- 可信 VK 分发/预固定：不是电路约束，但改变 verifier 的证明系统信任接口。

### Q5. 哪些问题仍然没有可信的解决方案？

| 问题 | 状态 | 依据 |
| --- | --- | --- |
| MiMC 作为绑定承诺的公开安全归约 | `UNKNOWN` | `commitment_candidates.md` §1/§2 |
| Pedersen 在当前 PLONK/MPC 路径的可承载性 | `BLOCKED` | 群变量/域/share 不兼容，`commitment_candidates.md` §2 |
| 承诺随机数分布/保密性、认证、防重放完整生命周期 | `UNKNOWN` / `BLOCKED` | `opening_and_randomness.md` Q5–Q9 |
| `exec_id` 唯一性、verifier 锚定与跨执行防重放 | `UNKNOWN` | `context_and_replay.md` §1/§3 |
| step↔trace row 对应与 dummy row 绑定实现 | `CONSTRUCTED` / `UNKNOWN` | `circuit_interface.md` §2.2；`event_completeness.md` E7 |
| B4 count/order/completeness/termination | `BLOCKED` / `UNKNOWN` | `p2_binding_semantics.md` B4；`event_completeness.md` §1 |
| 外部 verifier 固定 VK / 接受 prover 自提 VK | `UNKNOWN`；条件风险 `CONDITIONAL INFERENCE` | `verifier_independence.md` §3 |
| 独立 `r` + 独立承诺 + 关联证明 | `FUTURE CANDIDATE` / `UNKNOWN` | `opening_and_randomness.md` Q2/Q4；`decision` 不设计 |

### Q6. 下一阶段是否值得投入实现成本？

**不建议投入电路/接口实现成本。** 当前最值得做的不是写电路，而是按已列条件做有界补证：确定承诺方案与 opening 约束边界、证明 step↔trace row 与 B4 的最小约束集合、明确 VK/exec_id 的信任来源。若后续要继续，应另行授权一个“条件闭合/规格前置”阶段；本轮不启动 D3-02，不进入接口实现。

---

## 3. 最小条件闭合路线（仅作后续评估边界）

```
Step 1 (verifier 侧, 无电路改动):
    独立 verifier + 固定/可信 VK + P1-A-1 完整 opcode table
Step 2 (statement 规格, 需电路约束):
    定义 step/event/trace/commitment 公开与私有边界
    证明 real/dummy 分类、地址关系、dummy row sentinel、step0 排除
Step 3 (B4, 需额外电路约束):
    count/order/completeness/termination 进入 verifier statement
Step 4 (承诺/证明接口, 视方案):
    承诺方案定型 + opening/binding/hiding + 随机数生命周期 + 域/share 适配
Step 5 (仅在上述闭合后):
    才评估是否进入独立接口规格或最小原型
```

该路线是 `CONSTRUCTED` 的评估边界，不是已批准的实现计划；Step 2–4 的任一关键项未闭合前，不发 `GO`。

---

## 4. 证据纪律与停止声明

- 本轮只新增五份 D3-01 文档，未改 C2/D1/D2、EXP-DORAM、源码、测试或配置；未重抓上游源码，未跑测试。
- 所有判断按 `VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED` 标注；条件性风险单独标 `CONDITIONAL INFERENCE`。
- 未用标准密码学性质替代当前接口可实现性；未把宿主检查当作 proof soundness；未把公开输入通道存在当作 verifier 已检查。
- 未实现承诺 gadget、未实现递归/组合、未解除任何 HOLD。
- 本轮完成后停止，等待独立审查；不得启动 D3-02、接口实现或电路实现。
