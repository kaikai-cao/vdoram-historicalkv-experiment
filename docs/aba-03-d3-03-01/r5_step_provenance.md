# ABA-03-D3-03-01 / Phase 2：R5 — Step Provenance 可实现性

> 实验仓起点：`9788d5c1888ac28ee936892d36086cac32423115`；固定上游 `10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 目标：事件 step 必须来自可信 VM 执行位置，而非 prover 任意填写。本轮只读审计 + 接口候选，不实现电路。
>
> 证据来源：`interface_evidence_inventory.md` §1 组件 1/3/6；`../aba-03/source_trace_audit.md` A1/A2；`../aba-03-d3-02/event_sequence_relation.md` R5。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。

---

## 1. 固定实现中的 step 来源（VERIFIED）

| 事实 | 源码证据 | 标签 |
| --- | --- | --- |
| step 是 C# host 循环变量 `int globalStepCounter`，`for (...=0;;++)` | `ZkProgramExecutor.cs:113-116` | VERIFIED |
| 每步 `globalStepCounterField = FieldFactory.New(globalStepCounter)` | `ZkProgramExecutor.cs:122` | VERIFIED |
| 以 `AddPublic("in_global_step_counter", globalStepCounterField)` 注入三个电路（IF/MF/IE） | `ZkProgramExecutor.cs:149,287`；VM 侧声明 `NewPublicInputWire`（ZkVmExecutor L106-107 原始） | VERIFIED |
| trace 的 step 列由 host 用 public 值填：`incomingTraceRow["global_step_counter"] = MpcShareFromPublicValue(globalStepCounterField)` | `ZkProgramExecutor.cs:397-398` | VERIFIED |
| 源码注释明言有序性依赖 MPC 诚实假设 | `ZkProgramExecutor.cs:87`："we assume that globalStepCounter is ordered. As long as MPC parties honestly behave, this assumption holds." | VERIFIED |
| 最终 step 记录为 `ZkProgramExecuteResult.GlobalStepCounter` | `ZkProgramExecutor.cs:601` | VERIFIED |
| step0 特判：IF/VM 电路在 step0 把 pc/reg 哈希归零 | `ZkVmExecutorCircuitBoardGenerator.cs:110-217` 原始 | VERIFIED |

**直接结论（VERIFIED）**：当前 step 是 host 用循环变量生成的 **public input**，不是电路内部由状态转移约束递增产生的计数器。电路把 `in_global_step_counter` 当作给定公开值，用于 step0 归零与哈希 preimage；没有任何约束验证"这一步的 step 恰好等于上一步 step + 1"或"step 来自同一执行"。

---

## 2. 三种候选来源分析

### R5-A：VM 电路内部 step counter

- **现有状态**：`BLOCKED`。当前无电路内 step counter；step 是外部 public input（`L149,287`）。
- **候选接口（`CONSTRUCTED`）**：在 VM 电路中新增一个私有状态线 `step_i`，约束：
  ```
  step_0 = 0
  step_{i+1} = step_i + 1              # 电路内递增约束
  step_i == in_global_step_counter     # 若保留现有 public input 则绑定
  ```
  并将 `step_i` 或其对执行语义的承诺纳入 public statement。
- **能否约束初值与递增**：能（`step_0=0` + 增量门是标准算术约束），但需改 VM 电路 statement 与每步 witness 接口。
- **Fetch 事件能否绑定同一步 counter**：只有在同一电路或跨电路公共承诺下才能（`CONSTRUCTED`）；当前 Fetch 电路不接收 step（Fetch L13-14 列含 global_step_counter 但作为 trace 私有列读入，不作 step 语义约束）。
- **跳步/重复/外部注入空间**：若仅保留 host public input 而不加电路内 counter 约束，则 prover/host 可任意填 step（跳步、重复）而不被证明拒绝 → 当前存在此空间（`INFERRED`，基于 L87 注释与 L149 注入方式）。
- **证据等级**：候选 `CONSTRUCTED`；上游现状 `VERIFIED`（无 counter）+ 攻击空间 `INFERRED`。

### R5-B：Host 注入 step

- **现有状态**：`VERIFIED`（现状）+ `BLOCKED`（作为可信来源）。
- host 传入的 step 是 witness 还是 public input？答：是 **public input**（`AddPublic("in_global_step_counter",...)`，L149/287），随 proof 进入 statement。
- 是否有独立电路关系约束其与 VM 执行顺序一致？答：**没有**。L87 明确依赖 MPC 诚实假设；电路把 step 当给定值。
- verifier 能否识别 host 提供的 step 是否伪造？答：当前**不能**。public input 来自 prover JSON（`plonk.rs:143-161`），无 verifier 固定预期 step 序列。
- **结论**：host 注入 step 即使作为 public input，也不构成可信 provenance——它只是"prover 声明的公开值"。「在 proof public inputs 里」≠「被 verifier 用可信来源检查」。
- **证据等级**：`VERIFIED`（机制与缺失）+ `INFERRED`（provenance 不成立结论）。

### R5-C：公开 step index

- **现有状态**：step counter 已是 public input（`VERIFIED`）。
- 公开 step 是否泄露不必要执行信息？答：step index 本身（0..T−1）通常不泄露**内存地址**，但暴露总步数 T 与事件位置；若步数/控制流敏感，`T` 与位置公开是隐私退化点（`UNKNOWN` 是否可接受，沿用 D3-02 结论）。
- 公开 index 是否自动证明来自真实 VM 执行？答：**否**。公开一个值不等于证明其来源；仍需 R5-A 一类电路约束把它绑定到执行状态转移。
- 是否仍需 R5-A 约束？答：**是**。公开 step 只是让 verifier 可见，不能替代"step 由电路按执行顺序产生"的约束。
- **证据等级**：`VERIFIED`（公开性）+ `INFERRED`（来源不自动成立）。

---

## 3. 四个必答题

**Q1. 当前固定实现是否已有可信 step provenance？**
否（`VERIFIED`）。step 由 host 循环变量生成并以 public input 注入，电路无递增约束，源码注释明确依赖 MPC 诚实假设（L87）。verifier 只见 prover 提供的 public input，无可信来源核对。

**Q2. 最小需要修改哪些证明接口？**
（`CONSTRUCTED`）① VM 电路：新增电路内 step counter 状态 + 初值/递增约束；② public statement：绑定 step 序列（或其对执行语义的承诺）到 proof；③ 若 step 使 prover 可见但需来源可信，须让 verifier 固定/可信取得执行起始状态或将 step 与 pc/opcode 哈希链在同一电路绑定。具体改动门数/成本 `UNKNOWN`。

**Q3. R5 是否必须与 R4 同一电路关系中约束？**
是（`INFERRED`，强）。R4（顺序）检查"提交序列按可信 step 顺序排列"，其"可信 step"正是 R5 的产物。若 R5 的 step 与 R4 的顺序检查分属不同证明且无公共承诺桥接，则 R4 只能检查 prover 自报 step 的单调性，退化回"集合正确、顺序任意"（D3-02-C1 已明确）。因此 R4 要真正生效，必须与 R5 的可信 step 在**同一电路关系**或**经受约束的公共承诺**中绑定。

**Q4. 若分成子证明，跨证明绑定需要什么公共输入或承诺？**
（`CONSTRUCTED`）跨证明时，VM 子证明须把"每步可信 step（或其承诺/摘要）"作为 public input 或受约束的公共承诺输出；Fetch 子证明须把每个事件引用的 step 绑定到同一公共承诺并给出 opening 约束。两层证明属于同一 execution instance 还需 execution 级公共锚点（如 execution_id 承诺，属 P2/context 未决）。递归验证器不能读子证明私有 witness，所有跨证明关系必须经受约束的公共输入/承诺（沿用 D1-C1/D3-02 硬约束）。承诺的 binding/hiding/opening 仍为未决（`../aba-03-d2/decision.md`）。

---

## 4. 状态小结

| 项 | 结论 | 标签 |
| --- | --- | --- |
| 当前可信 step provenance | 无；step 是 host public input，无电路递增约束 | `VERIFIED` |
| R5-A 电路内 counter | 需新增电路状态与约束 | `CONSTRUCTED` + `BLOCKED`（接口缺失） |
| R5-B host 注入 | 可作 public input，但不构成可信来源 | `VERIFIED` |
| R5-C 公开 index | 可见 ≠ 来源可信，仍需 R5-A | `VERIFIED` + `INFERRED` |
| 是否改电路 | 是（新增 counter 与绑定约束） | `CONSTRUCTED` |
| 是否改 prover/verifier 接口 | 是（statement 绑定 + verifier 可信来源） | `CONSTRUCTED` |
| 与 R4 同电路 | 必须同电路或公共承诺桥接 | `INFERRED`（强） |
| 成本 | 门数/时间/字节全 `UNKNOWN` | `UNKNOWN` |

**R5 当前状态：`BLOCKED_BY_CURRENT_INTERFACE`** —— 固定架构中 step 只是 host 提供的 public input，缺少电路内可信产生与绑定接口；候选接口均为 `CONSTRUCTED`，未实现、未测量。
