# ABA-03-D3-01 / Phase 3：B4 事件完整性必要条件

> 实验仓起点：`03960aa941bcd8ef88fbd06a83cf7599682a5cbd`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只复用既有证据建立 B4 条件清单；不重抓源码、不实现电路、不解除 HOLD。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 主要证据：`../aba-03-d1/p2_binding_semantics.md` §1、B1–B4；`../aba-03/source_trace_audit.md` A2；`../aba-03-d2/context_and_replay.md` §2/§3.4/§4；`../aba-03-d2/circuit_interface.md` §2；`../aba-03-d1/leakage_and_security.md` D8；`../aba-03-d1/cost_model.md` §0。

---

## 0. 一句话结论

B4 不是“比较两份承诺”或“event count 正确”就能推出的性质。它要求把 **step、事件、Fetch proof、VM trace row、类型与终止边界**放进同一可验证 statement；当前固定 commit 只有部分源码事实（step0 无 Fetch、step≥1 均构造 Fetch、类型由 opcode 派生、trace 内部有排序/一致性检查），没有 verifier 可见的计数、顺序、无遗漏和终止约束。整体状态：`BLOCKED`（作为可验证关系）；候选构造为 `CONSTRUCTED`。

---

## 1. B4 必要条件清单

| 编号 | 必要条件 | 候选表达（非现有实现） | 证据 / 标签 | 说明 |
| --- | --- | --- | --- | --- |
| E1a | 总 Fetch 事件数 | `N_all = T − 1`，其中 `T` 含 step0 | step0 无 Fetch `VERIFIED`（`:201-203`）；每 step≥1 构造一次 Fetch `VERIFIED`（`:205-228`）；计数关系为 `CONSTRUCTED` | `N_all` 是**总** Fetch 数，不是 dummy 数 |
| E1b | 真实 Fetch 事件数 | `N_real = M`，`M` 为真实 Load/Store 数 | 类型由 opcode 派生 `VERIFIED`（`ZkVmExecutor...cs:968-976`）；计数关系为 `CONSTRUCTED` | real Fetch 与真实 Load/Store 一一对应 |
| E1c | Dummy Fetch 事件数 | `N_dummy = T − 1 − M` | 由 E1a/E1b 与 `p2_binding_semantics.md` B2 推导：`INFERRED`；约束为 `CONSTRUCTED` | `T−1−M` 是 **dummy** 数，**不是**总数 |
| E1d | 三类计数加和一致 | `N_all = N_real + N_dummy` | 代数恒等式 `INFERRED`；写成电路约束为 `CONSTRUCTED` | 无遗漏/无重复还须由 E9 独立证明，加和本身不证明完整性 |
| E2 | step 0 例外显式化 | step0 只有 trace row，无 Fetch proof、无承诺事件，event_count 不含 step0 | `VERIFIED_SOURCE`（无 Fetch `:201-203`、仍 append `:389-402`）+ `CONSTRUCTED`（事件序列排除） | 不得因 trace 行数增加而把 step0 计为真实事件 |
| E3 | 每个 step≥1 的 Fetch 恰好对应一个执行步 | 对每个 `i≥1`，存在一个且仅一个 Fetch statement，其 `step_fetch = step_i` | 每步构造 Fetch 为 `VERIFIED`（`:205-228`）；proof/statement 绑定为 `CONSTRUCTED` | 源码事实不等于 proof 中“恰好一次”已被证明 |
| E4 | real/dummy 类型由 opcode 在电路内派生 | `is_mem_op_i == (opcode_i ∈ {Load, Store})`，event_type 由该值绑定进公开 statement 或公开承诺 | 派生路径 `VERIFIED`（`ZkVmExecutor...cs:968-976`）；Prove 忽略 `is_mem_op` 为 `VERIFIED`（原始 L164-165）；公开绑定 `CONSTRUCTED` | 不能让 prover 自由声明 event_type |
| E5 | 真实 Load/Store 地址关系 | `fetch_lookup_addr_i = reg0_i = trace_addr_i` 且 `0≤addr_i<n` | `INFERRED` + `CONSTRUCTED`（`p2_binding_semantics.md` B1）；范围约束当前缺失 `VERIFIED_SOURCE` | 完整域元素相等 + 位分解范围，不用低位截断 |
| E6 | dummy Fetch 语义 | `fetch_lookup_addr_i = reg0_i`；`trace_addr_i = p−1`；`trace_val_i=0`；禁止 lookup==trace 断言；不承诺 `reg0` | `VERIFIED_SOURCE`（`:941-943,989-1007`、`:226`）+ `CONSTRUCTED`（承诺/trace row 绑定） | dummy lookup 仍是 `reg0`，但不得公开或承诺该值 |
| E7 | 每个 Fetch 绑定正确 VM trace row | `FieldEquals(row_i.mem_addr, expected_addr)`，其中 real 期望 `reg0`、dummy 期望 `p−1`；`row_i` 与 `step_i` 一一对应 | `CONSTRUCTED` + `UNKNOWN`；`circuit_interface.md` §2.2 新增 dummy sentinel 约束为候选 | 当前 Fetch 只按地址选择 `mem_val`，不输出/强制 trace row；step↔row 对应未证 |
| E8 | trace 内部顺序与值一致性 | 维持 Prove 电路已有排序/同址值不变检查，并把它纳入统一 statement | `VERIFIED`（`source_trace_audit.md` A2：Prove 检查排序与同址值不变）+ `INFERRED`（不足以满足 E8 全部） | trace 内部检查不等于“所有事件均存在且无重排” |
| E9 | 无遗漏、无重复、无重排 | 事件序列按 step 单调、相邻 step 连续或经 halt 边界解释；每个 step 的事件证明唯一 | `BLOCKED` / `UNKNOWN`（`p2_binding_semantics.md` B4；`context_and_replay.md` §3.4/§4） | event count 正确不推出顺序正确；事件存在不推出无遗漏 |
| E10 | 跨 execution 重放不可行 | `exec_id` 唯一且 verifier 锚定，context 绑定 program/step/event | `UNKNOWN`（`context_and_replay.md` §1、§3.3）；P1-A 不解决 | 随机数随机性不是防重放机制 |
| E11 | 执行终止 / 异常中止 / 最大步数进入 statement | verifier 固定 halt 条件与 `T`/`step_bound`；异常中止不得输出“成功完整轨迹”证明 | `UNKNOWN` / `CONSTRUCTED`；`source_trace_audit.md` A3 说明 `globalStepsNoMoreThan` 是执行器阈值，不是电路约束 | 当前无 verifier 可检查的 halt 边界 |
| E12 | 宿主检查不得冒充证明约束 | 宿主 `throw` 与哈希多重集检查不进入 R1CS/public inputs | `VERIFIED`（`ZkProgramExecutor.cs:170-181,302-332,551-583`；`verifier_interface_audit.md` §3） | 四层检查必须分开，不可互相替代 |

---

## 2. 三类“不能自动推出”的边界

1. **event count 正确 ≠ 顺序正确**：计数只给出事件数，无法证明事件按 step 排列、无重排或无重复（E9）。`p2_binding_semantics.md` B4 已明确“单步相等 ≠ 轨迹完整”。
2. **每个事件存在 ≠ 没有遗漏**：即使每个已给出 proof 的事件都合法，也不能排除某个应存在的 Fetch 未被提交；需要 verifier 可检查的 completeness 关系（E3/E9）。
3. **宿主检查 ≠ proof soundness**：执行器内部 `throw`、哈希多重集比对、逐行哈希结果都不进入 verifier statement（`verifier_interface_audit.md` §3）；不能写成 verifier 已检查。

---

## 3. 事件序列候选模型（非现有实现）

```
Events = [event_i | i = 1..T−1]                 # step 0 排除
event_i = (step_i, is_mem_op_i, addr_i, row_ref_i, proof_i)

constrain N_all   = T − 1                         # 总 Fetch 数（step0 排除）
constrain N_real  = M                             # 真实 Fetch 数
constrain N_dummy = T − 1 − M                     # dummy Fetch 数（不是总数）
constrain N_all   = N_real + N_dummy
constrain count(Events)        == N_all
constrain count(real_events)   == N_real
constrain count(dummy_events)  == N_dummy
constrain step_i 单调且与执行步对应               # 需新增
constrain event_i.row_ref_i ↔ row_i              # 需新增 step↔trace row 映射
constrain is_mem_op_i 由 opcode_i 电路派生        # 电路派生已 VERIFIED；公开绑定 CONSTRUCTED
constrain real:  fetch_lookup == reg0 == trace_addr, 0≤addr<n
constrain dummy: fetch_lookup == reg0, trace_addr == p−1, 不承诺 reg0
constrain halt:  最后 step 或异常中止边界由 verifier 固定
```

其中 `N_all = T−1`、`N_real = M`、`N_dummy = T−1−M`（`T−1−M` 是 dummy 数，**不是**总数）及三类事件语义来自既有证据；`count/order/completeness/halt` 四类约束均为 `CONSTRUCTED`，当前无实现证据。加和式 `N_all = N_real + N_dummy` 是代数恒等式，不能替代 E9 的无遗漏/无重复证明。

---

## 4. 当前可复用项与缺口

| 项 | 当前状态 | 是否可复用 |
| --- | --- | --- |
| step0 无 Fetch 的源码语义 | `VERIFIED` | 可作为事件模型硬边界，但需在事件序列中显式排除 |
| 每 step≥1 构造 Fetch | `VERIFIED` | 可作为“候选一一对应”的起点，仍需 proof 绑定 |
| `is_mem_op` 由 opcode 电路派生 | `VERIFIED` | 是派生骨架；需新增公开 statement 绑定 |
| Prove 电路 trace 排序/同址值检查 | `VERIFIED` | 只覆盖 trace 内部一致性，不替代 E9 |
| event_count / step 单调 / halt 边界 | `UNKNOWN` / `CONSTRUCTED` | 不可复用，需新增约束 |
| step↔trace row 对应 | `CONSTRUCTED` / `UNKNOWN` | 不可宣称已实现 |
| 跨 execution 防重放 | `UNKNOWN` | 需 `exec_id` 与 verifier 锚定 |

---

## 5. B4 小结

- B4 当前为独立阻断项，不因承诺相等、P1-A 或 VK 固定而自动闭合。
- 最小候选事件 statement 可写出（`CONSTRUCTED`），但 E7/E9/E10/E11 均无实现证据。
- 本轮不提出具体电路实现，也不把候选约束写成上游事实；完整条件清单进入 `dependency_and_cost.md` 的依赖矩阵与 `decision.md` 的最终决策。
