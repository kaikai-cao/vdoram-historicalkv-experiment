# ABA-03-D3-03-03 / 最小可行架构路径

> 实验仓起点：`5c84f38c6df17acd458c1681a8ca18da0377281a`；固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：架构构造分析；不实现电路、verifier、ORAM、commitment gadget，不修改既有原型。
>
> 标签：`CONSTRUCTED` / `UNKNOWN` / `BLOCKED`。本文所有方案均为候选构造，不代表已实现或已通过安全证明。

---

## 0. 冻结语义与共同前提

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

两条架构都必须满足：

1. `execution_id` 由 verifier/可信调用方生成，不来自 prover 自报；
2. VK 与 program expectation 由 verifier 固定，`vk_id↔program_id` 显式绑定；
3. `total_steps` 来自受约束 counter 或 verifier 可信固定值；`last_step_index = T-1` 派生且同约束；
4. `expected_step_bound` 仅是上界；
5. proof 中相同的 `execution_id`、哈希字段或 hash chain 终值不自动等于 witness 绑定；
6. verifier 信任配置不替代 R5–R8/B4 语义约束（见 `coverage_matrix.md`）。

---

## 1. Architecture 1：Joint proof（单一证明关系闭合）

### 1.1 构造描述（`CONSTRUCTED`）

一个关系 `R_joint` 同时约束 VM 执行、Fetch 事件生成、事件序列、trace row 对应和终止锚点：

```
R_joint(x, w) = 1

x（候选 statement 字段）:
  protocol_version, program_id / opcode_table_digest,
  public_input_digest, execution_id,
  initial_state_commitment（可选）, final_state_commitment（可选）,
  total_steps = T, last_step_index = T - 1,
  expected_step_bound（上界，可选同时存在）,
  vk_id / version

w（候选私有 witness）:
  VM trace rows, opcode/is_mem_op 派生值,
  Fetch events for steps [1, T-1],
  trace row addresses / values, counter states,
  commitment randomness/openings（若采用承诺）
```

该描述只是关系草案，不是已存在电路。

### 1.2 需要修改哪些 VM 输出

当前固定 commit 中关键量是 host 循环变量、私有派生值或 host 记录；联合证明要求把它们提升为**同一关系内可约束对象**：

| 当前对象 | 当前状态 | Joint proof 要求 | 标签 |
| --- | --- | --- | --- |
| `globalStepCounter` | host 循环变量，public input 由 host 注入 | 电路内 counter 初值、递增、终值受约束，`total_steps` 为 public output | `CONSTRUCTED`；当前 `BLOCKED_BY_CURRENT_INTERFACE` |
| `out_halt` / `break` | halt 是 VM public output，break 由 host 控制 | halt 与 `last_step_index = T-1` 在同关系中绑定；host break 不能单独决定 T | `CONSTRUCTED` / 当前 `BLOCKED` |
| `is_mem_op` | 私有派生，Prove 不接收/忽略 | opcode → `is_mem_op` → event type 同关系约束 | `CONSTRUCTED` / 当前 `BLOCKED` |
| `out_trace_mem_addr` | real=`reg0`、dummy=`p−1`，私有派生 | step↔trace row↔event type 同关系绑定；dummy 不承诺/不公开 `reg0` | `CONSTRUCTED` / 当前 `BLOCKED` |
| Fetch event step | 当前无 proof 层 step-index 序列 | `[1,T-1]` 全事件域、无空洞、无重复、有序约束 | `CONSTRUCTED` / 当前 `BLOCKED` |
| 跨电路哈希比对 | 宿主多重集计数 | 不再作为 proof soundness 替代品；改由同关系约束承担 | `INFERRED` |

### 1.3 R5–R8 如何进入同一关系

- **R5 step provenance**：counter 列在关系内从初值递增；每个事件携带受约束 step。
- **R6 event type**：opcode 约束 `is_mem_op = Load ∨ Store`，event type 由同一 `is_mem_op` 决定。
- **R7 step-row**：每个 step 的 trace row 地址/值列与事件在同一 witness 行或同一查找/排列参数中绑定。
- **R8 termination**：halt 与 counter 终值绑定；`total_steps = last_step_index + 1`。

### 1.4 B4 各项如何表达

| B4 项 | Joint proof 表达方式（候选） | 标签 |
| --- | --- | --- |
| R2 coverage | step-index 集合覆盖 `[1,T-1]`；配合计数 `T-1` | `CONSTRUCTED` |
| R3 injectivity | step↔event 一一映射，无重复 step、无重复 event slot | `CONSTRUCTED` |
| R4 ordering | `step_{j+1} = step_j + 1` 或与有序索引表约束；不能只靠 prover 自报单调 | `CONSTRUCTED` |
| R5 trusted step | 同关系 counter 生成，或 verifier 固定 T 与 counter 核对 | `CONSTRUCTED` |
| R6 event type | opcode/`is_mem_op`/event type 同关系 | `CONSTRUCTED` |
| R7 step-row | 同关系内 trace row 绑定 | `CONSTRUCTED` |
| R8 trusted T | counter 终值与 halt 绑定，`total_steps` 进 statement | `CONSTRUCTED` |

### 1.5 verifier statement 与 VK

- verifier statement 至少包含 program 引用、public input 引用、`execution_id`、`total_steps`、VK/version 与域标签；`last_step_index` 若显式列出，必须约束为 `total_steps - 1`。
- VK 必须固定并绑定 program/circuit；当前现场 `test_rng()` 不满足。
- 仅固定 statement 与 VK 仍不够；上述 B4 约束必须真正在关系中实现。

### 1.6 必须重写与未知成本

- 必须重写/新增：VM 执行电路输出、Fetch 事件生成约束、trace row 绑定、counter/halt 约束、verifier statement 与 VK 固定路径（`BLOCKED`）。
- 当前固定 upstream 不能仅靠 verifier 配置补丁完成 Joint proof。
- 约束数、证明大小、prove/verify 时间、递归需求、内存峰值均 `UNKNOWN`；本轮未测量，不得用工程测试代替成本结论。

### 1.7 架构 1 标签

`CONSTRUCTED`（关系草案） / `BLOCKED`（当前接口） / `UNKNOWN`（成本与可证明性细节）。

---

## 2. Architecture 2：Separate proofs + public commitment bridge

### 2.1 构造描述（`CONSTRUCTED`）

VM proof 与 Fetch/history proof 分离，通过公开承诺与 linking/opening proof 桥接：

```
P_vm       : 证明 VM 执行与 anchor 摘要 D_exec
P_fetch    : 证明 Fetch 事件序列与摘要 D_event
P_link     : 证明 D_exec / D_event / execution_id / T / program_id 指向同一执行
```

`P_link` 可以是独立 bridging proof，也可以由上层递归电路验证两个子 proof 对公开 statement 成立；两种都需要把公共锚点写进上层 statement。

### 2.2 两侧分别承诺什么

| Proof | 候选承诺内容 | 必要约束 | 标签 |
| --- | --- | --- | --- |
| `P_vm` | execution trace digest、step counter 终值、halt 状态、初始/最终状态摘要 | VM 逐步转移、counter、halt↔T；摘要必须由关系计算而非 prover 自报 | `CONSTRUCTED` |
| `P_fetch` | 事件序列摘要、每事件 step/type/trace-row 绑定摘要、终值 | `[1,T-1]` 覆盖、单射、顺序、real/dummy 类型、step↔row | `CONSTRUCTED` |
| `P_link` | 公共承诺打开/链接关系、共享 `execution_id`、`total_steps`、program/VK 版本 | opening/linking proof 必须受约束；不能只比较字段字符串 | `CONSTRUCTED` |

### 2.3 承诺是否需要 hiding / binding / 同执行绑定

- **binding**：必需。若承诺不 binding，prover 可对同一承诺给出不同 opening，桥接无效。
- **hiding**：取决于地址/输入隐私目标，不是完整性必需；若需要隐藏 `reg0`，dummy 仍只承诺 `p−1`、不承诺/不公开 `reg0`（冻结语义）。
- **同执行绑定**：必需。`execution_id`、`total_steps`、`program_id`、`vk_id`、协议版本与摘要必须同时进入所有相关 statement，并由 `P_link` 约束它们引用同一执行。
- 当前承诺层 binding/hiding/opening 未决（`docs/aba-03-d2/decision.md`），随机盐认证在 additive-only MPC 路径下 `BLOCKED`；桥接方案因此仍 `UNKNOWN`/`BLOCKED`。

### 2.4 如何避免 prover 提交两组不一致 witness

- 必须让两个摘要由各自 proof 关系计算，并由 `P_link` 对**同一公开承诺**做 opening/linking 约束。
- 若 prover 只是提供 `D_exec`、`D_event` 并声称它们相等，则不一致 witness 无法阻止。
- 若 `D_event` 是 prover 可自由重算的 hash chain 终值，且起点/终点/内容都无可信来源，则 chain 自洽不证明事件内容完整性。
- 这些约束尚未设计，标 `CONSTRUCTED`；当前实现 `BLOCKED`。

### 2.5 opening/linking proof 由谁验证

- 必须由 verifier 在固定 statement 上验证，不能由宿主 C# 后置计数比对替代。
- verifier 需要固定：`execution_id`、`total_steps`、`program expectation`、`vk_id/version`、承诺方案参数与域分离标签。
- 若依赖 registry 提供 VK/版本，则引入 Model C 的写入权与新鲜性信任根；不是免费。

### 2.6 `execution_id` / T / program_id / VK 如何绑定

| 字段 | 绑定要求 | 不足做法 |
| --- | --- | --- |
| `execution_id` | verifier/调用方生成，写入 P_vm/P_fetch/P_link 全部 statement | prover 侧 `enc_key`；只写在一个 proof |
| `total_steps` | 受约束 counter 或 verifier 固定值；`last_step_index = T-1` 同约束 | prover 自报 T；`expected_step_bound` 上界 |
| `program_id` | verifier 固定表派生或可信 registry 映射；与 `vk_id` 显式绑定 | prover 自报 id；相同 opcode 表字段 |
| `vk_id` | verifier 固定 VK/版本并域分离 | prover 现场生成 VK；无版本绑定 |

### 2.7 hash chain 是否足够

- 不够。hash chain 顺序敏感，但若无可信起点/终值且未逐项绑定 step/type/trace row，省略+复制或重算自洽链无法区分。
- hash chain 可作为摘要组件，但必须嵌入上述 binding/opening/linking 关系，不能单独作为完整性证明（`INFERRED`）。

### 2.8 递归证明能解决什么，不能解决什么

- 能：在公开 statement 层面验证子 proof 的验证结果，压缩 verifier 工作量；可把“多个 proof 对各自公开 statement 有效”写成上层关系（L4/L5，`CONSTRUCTED` + `PAPER_CLAIM`）。
- 不能：自动读取两份子 proof 的私有 witness 并直接比较 `reg0`、event row 或其他隐藏值；除非这些内容被承诺并通过 opening/linking 显式约束。
- 不能：修复缺失的 R5–R8 语义；递归只改变验证结构，不改变被证明关系的语义。
- 不能：移除 verifier 配置/VK/statement 来源信任根。

### 2.9 架构 2 标签

`CONSTRUCTED`（桥接草案） / `UNKNOWN`（承诺层、递归接口、成本） / `BLOCKED`（当前无跨 proof 承诺与验证接口）。

---

## 3. 两路径对照

| 维度 | Joint proof | Separate proofs + bridge |
| --- | --- | --- |
| 语义闭合路径 | 同一关系内更直接 | 需要 commitment/linking/recursion 额外层 |
| 跨 proof 同一性 | 天然减少跨 proof 缝 | 核心难点 |
| verifier statement | 字段更集中 | 字段分散，需显式统一锚点 |
| 承诺层依赖 | 可选，取决于状态/隐私设计 | 强依赖 binding/opening/linking |
| 对当前架构改造 | 需重写 VM/Fetch/Prove 关系与 VK | 需改证明接口、新增桥接与承诺接口 |
| 成本证据 | `UNKNOWN` | `UNKNOWN` |
| 当前状态 | `BLOCKED` | `BLOCKED` |

**本阶段不宣称任一路径已实现或已通过安全证明。** 路径取舍见 `decision.md`；无论选择哪条，都必须先满足 R5–R8/B4 语义约束，而不是先写 verifier 外壳。
