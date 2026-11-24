# ABA-03-D3-03-03 / Trust Root 对 R5–R8 与 B4 的覆盖矩阵

> 实验仓起点：`5c84f38c6df17acd458c1681a8ca18da0377281a`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：覆盖能力分析；只判断信任根能否闭合语义，不实现电路、不新增证明。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。

---

## 0. 四个层次必须分开

**不能因为 verifier 信任某个执行锚点，就声称事件序列完整性已经成立。**

| 层次 | 问题 | 能推出什么 | 不能推出什么 |
| --- | --- | --- | --- |
| 1. verifier 信任配置 | verifier 是否持有正确的 VK、program expectation、public input expectation、`execution_id`、T 来源 | statement 来源可信；本次请求身份与版本可区分 | proof 是否真的约束了执行语义 |
| 2. verifier 验证密码学 proof | `verify_proof(vk, proof, public_inputs)` 是否通过 | proof 对给定公开输入自洽 | 公开输入本身可信；私有 witness 满足应用语义 |
| 3. proof 关系实际约束的语义 | 电路中是否约束 step、事件类型、trace row、顺序、终止 | 被约束的关系成立 | 其他 proof 是否使用同一执行/witness |
| 4. 证明之间绑定到同一执行 | 所有 proof 是否引用同一公开 anchor/opening/linking 关系 | 跨 proof 同一性有公开锚点 | 锚点内容本身自动完整；哈希相同自动等于 witness 相同 |

当前固定 commit 中：层次 1 缺失（`BLOCKED_BY_TRUST_MODEL`），层次 2 存在但只是 prover 进程内 self-check（`VERIFIED`），层次 3 多处缺失（`BLOCKED_BY_CURRENT_INTERFACE`），层次 4 缺失（`BLOCKED`）。

---

## 1. 冻结符号

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

`expected_step_bound` 仅为上界，不等于实际 `total_steps`；`count(events)=T-1` 依赖真实 T（`VERIFIED` + `INFERRED`）。

---

## 2. D3-03-01 的 R5–R8 覆盖

| 目标 | Trust Root 本身能否解决 | 还需要什么 | 当前状态 / 证据 | 标签 |
| --- | --- | --- | --- | --- |
| **R5：step provenance** | 不能。verifier 固定配置可规定“step 从哪来是允许的”，但不能产生 step 来源事实 | 受约束 counter / trusted execution anchor；step 必须进入电路并绑定事件与 trace row | 当前 `globalStepCounter` 是 host 循环变量；`in_global_step_counter` 是 public input；trace step 列 host 填写；无电路 counter 递增约束（`r5_step_provenance.md`） | `CONSTRUCTED`（候选） / 当前 `BLOCKED_BY_CURRENT_INTERFACE` |
| **R6：`is_mem_op` binding** | 不能。配置可固定 opcode 表，但 `is_mem_op` 是执行期派生量 | opcode → `is_mem_op` → Fetch event type 的电路约束；dummy/real 分支必须受同一关系约束 | `is_mem_op = BoolOr(Load, Store)` 私有派生；Prove 不接收 pc/opcode、明确忽略 `is_mem_op`（`r6_r7_event_trace_binding.md`） | `CONSTRUCTED` / 当前 `BLOCKED_BY_CURRENT_INTERFACE` |
| **R7：step-to-trace binding** | 不能。verifier 信任 trace 摘要来源也不能推出每一行对应正确 step | 同一证明关系中的 step↔trace row 约束，或公共承诺桥 + opening/linking proof | Fetch 电路不接收 step/type；`out_trace_mem_addr` real=`reg0`、dummy=`p−1` 为 VM 私有派生；跨电路只有 host 哈希多重集比对（`r6_r7_event_trace_binding.md`） | `CONSTRUCTED` / 当前 `BLOCKED_BY_CURRENT_INTERFACE`；桥接 `UNKNOWN` |
| **R8：termination / actual T** | 部分：verifier 可固定实际 T 作为配置，但“执行真的在该 T 停止”不能靠配置证明 | 受约束 counter + halt↔`last_step_index` 绑定；`total_steps` 进 statement；`last_step_index = T-1` 受同一 counter 约束 | `out_halt` 是 VM public output，但 `break` 由 host 控制；最终 T 为 host 记录且不进 statement（`r8_termination_anchor.md`） | `CONSTRUCTED` / 当前 `BLOCKED_BY_CURRENT_INTERFACE` |

**R5–R8 小结**：信任根最多为 R8 提供“verifier 固定 T”的外部来源；R5/R6/R7 必须进入证明关系，R8 的 halt 语义也必须进入证明关系。增加 verifier 不等于 R5–R8 通过。

---

## 3. B4-R2–R8 覆盖

> B4 充分条件沿用 D3-02-C1：`R2 ∧ R3 ∧ R4 ∧ R5 ∧ R6 ∧ R7 ∧ R8`，且 T 必须 verifier 固定或可信锚定。

| 目标 | Trust Root 本身能否解决 | 还需要什么 | 当前状态 / 证据 | 标签 |
| --- | --- | --- | --- | --- |
| **B4-R2：coverage**（每个 step≥1 恰有一个 Fetch 事件） | 不能。verifier 固定 T 只定义域 `[1,T-1]`，不证明域被覆盖 | 全事件域覆盖证明：事件 step 集合包含 `[1,T-1]`，且与计数 `T-1` 联用 | 计数相等无法区分省略+复制反例；当前无 step-index 序列电路约束（`event_sequence_relation.md`） | `CONSTRUCTED` / 当前 `BLOCKED` |
| **B4-R3：injectivity**（无重复映射） | 不能。信任根不检查事件映射重数 | 无重复 step↔event 约束；与 R2 联用形成双射 | 同 R2；宿主多重集计数不是 proof soundness | `CONSTRUCTED` / 当前 `BLOCKED` |
| **B4-R4：ordering**（按可信 step order 排列） | 不能。计数器产生 step 值不等于序列顺序已排序 | `step_{j+1}=step_j+1` 或与有序索引表的约束；不能只看 prover 自报单调 | D3-02-C1 反例 `E*=[e1(1),e2(2),e3(3)]` vs `P=[e1(1),e3(3),e2(2)]` 显示 R2+R3 不足 | `CONSTRUCTED`（逻辑反例） / 当前 `BLOCKED` |
| **B4-R5：trusted step generation**（step 来源可信） | 不能。verifier 配置不能生成执行期 step | 受约束 VM step 来源；与 D3-03-01 R5 的差异是此处强调“可信生成”，前者强调“证明接口可接入” | host 循环变量 + public input，非电路 counter | `CONSTRUCTED` / 当前 `BLOCKED_BY_CURRENT_INTERFACE` |
| **B4-R6：event type binding**（real/dummy 由 opcode 决定） | 不能。固定 opcode 表只定义允许集合，不绑定本次事件类型 | opcode / `is_mem_op` / event type 同关系约束；dummy 与 real 分支均受约束 | `is_mem_op` 私有派生、Prove 忽略；dummy 只承诺 `p−1`、不承诺/不公开 `reg0` 的冻结语义保持 | `CONSTRUCTED` / 当前 `BLOCKED_BY_CURRENT_INTERFACE` |
| **B4-R7：step-row binding**（step↔trace row） | 不能。信任 trace 摘要不能推出逐行对应 | 同关系内 step↔row 约束，或可信公共承诺 + opening/linking proof | 当前跨电路 host 哈希比对；Prove 不接收 step/type | `CONSTRUCTED` / 当前 `BLOCKED` |
| **B4-R8：trusted T**（可信实际总步数） | 部分：verifier 可固定 T 或可信取得 T，这是必要外部锚点 | 仍需 halt↔`last_step_index` 绑定与 counter；固定 T 不证明事件序列到 T 完整 | 当前 T host 记录、不进 statement；`expected_step_bound` 只是上界 | `CONSTRUCTED` / 当前 `BLOCKED_BY_CURRENT_INTERFACE` |

---

## 4. 跨 proof 同执行绑定（横向缺口）

| 机制 | 能否作为完整性证明 | 原因 | 标签 |
| --- | --- | --- | --- |
| 相同 `execution_id` | 不能 | 只是公开引用；除非写入所有 proof statement 并绑定 program/input/T/VK，否则仍是标签 | `CONSTRUCTED` + `INFERRED` |
| 相同哈希字段 | 不能 | 相同哈希值可由 prover 自洽重算；不证明 underlying witness 相同 | `CONSTRUCTED` |
| hash chain 终值 | 不能单独成立 | 顺序敏感但不保证事件内容正确；若首尾都由 prover 提供且不绑定可信来源，重算自洽链无完整性 | `INFERRED`；D3-02 已记录 |
| 普通签名 | 不能替代电路约束 | 签名证明“谁说了什么”，不证明 statement 与私有 witness 的关系 | `CONSTRUCTED` |
| 递归证明 | 只能验证子 proof 对公开 statement 成立；不能自动比较私有 witness | 需把公共承诺/opening/linking 写进上层 statement | `CONSTRUCTED` + `INFERRED` |

---

## 5. 矩阵结论

1. **Trust root 本身能解决的是层次 1**：谁固定 VK、program、public input、execution_id 与 T 来源。
2. **Trust root 本身不能解决层次 3/4**：R5–R8 与 B4-R2–R8 的语义必须由证明关系约束，且跨 proof 必须绑定到同一执行。
3. 当前最薄弱项不是“少一个 verifier”，而是 **VM/Fetch/Prove 三段关系没有同一执行内的可信语义桥**。
4. 任何后续方案若只写“增加独立 verifier + 固定 VK + execution_id”，而没有 counter、事件类型、step-row、ordering、T 与跨 proof linking 约束，均应判为 `BLOCKED`，不得标 `VERIFIED`。
5. 覆盖矩阵支持 `decision.md` 的结论：verifier 信任根是必要但远非充分条件。
