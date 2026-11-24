# ABA-03-D3-02 / Phase 4：B4 候选构造比较（不作选择）

> 实验仓起点：`e93e882ab01dca5c44768f0be8a1a81a246c4318`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读构造比较。所有方案均为 `CONSTRUCTED` 候选，**未实现、未测量、未选择胜者**；没有实现或测量数据的成本项一律 `UNKNOWN`。不实现电路、不重抓源码、不运行测试。
>
> 标签：`VERIFIED_SOURCE` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 证据来源：`b4_security_goal.md`、`event_sequence_relation.md` §2/§4、`completeness_attack_matrix.md` §1；`../aba-03-d1/design_options.md` §2/§3；`../aba-03-d3-01/dependency_and_cost.md` §3。

---

## 0. 比较框架

四个候选按“不公开真实地址、不把 dummy lookup 强设为 `p−1`”的共同隐私约束评估。每项固定回答六维：

1. 安全性直觉（能覆盖哪些攻击类别）；
2. 必要约束；
3. 隐私影响；
4. 证明接口改动；
5. 主要成本项（符号级，数值 `UNKNOWN`）；
6. 未解决问题。

**先给结论性判据**：`completeness_attack_matrix.md` §3 指出，要排除“数量相同、内容不同”的序列，需要 `R2 覆盖 + R3 注入 + R5 step 绑定 + R6 类型 + R7 trace + R8 终止` 联合。任何方案若不能同时提供 **step 索引可信产生** 与 **每步内容绑定到该 step**，都不能声称解决 B4；普通哈希链尤其不能替代完整性证明（见 B）。

---

## A. 连续 step-index 绑定

**思路**：每个 Fetch 事件携带 step index，约束为从 1 到 `T−1` 的连续序列（无空洞、无重复）。

### 安全性直觉
- 若 step_j 由电路约束产生（非 prover 自由填）、两两不同、取值于 `[1,T−1]`、且数量为 `T−1`，由鸽巢原理得 step 集合恰为 `[1,T−1]` → 直接排除 A1 遗漏、A2 复制（step 冲突）、A8 多余（`step>T−1`）、A3 重排（单调要求）。
- **不能单独解决**：A4 step substitution（若 step 可伪造）、A5 type forgery（step 对但类型错）、A6 trace substitution、A7 prefix truncation（若 `T` 由 prover 自报）。必须叠加 R5/R6/R7/R8。

### 必要约束（`CONSTRUCTED`）
```
step_j ∈ [1, T−1]                 # 范围
step_j 两两不同                    # 注入
step_{j+1} = step_j + 1           # 连续/单调（更强，直接给出顺序）
T 由 verifier 固定或电路证明       # 否则 A7 盲区
每步内容 (type, addr, row) 绑定该 step  # R5/R6/R7
```

### 隐私影响
- step index 作为公开输入暴露执行步数 `T` 与事件位置；不暴露真实 `reg0`。dummy 仍只承诺 `p−1`，lookup `reg0` 保持私有。
- 若步数/控制流本身敏感，`T` 与 step 位置公开是隐私退化点（`UNKNOWN` 是否可接受）。

### 证明接口改动
- 需把 step 从宿主公开注入（`ZkProgramExecutor.cs:393-395`）升级为电路约束产生的可信值 → 改 VM 电路 statement。
- 需新增“每步恰好一个事件、step 连续、内容绑定”约束 → 改 Fetch/组合电路（`CONSTRUCTED`）。

### 主要成本项（符号级）
- 新增公开输入：step 序列 `O(T)`；verifier 固定 `T`。
- 新增约束：step 范围/注入/连续比较，`O(T)` 量级；具体门数 `UNKNOWN`。
- prove 时间、proof 字节、通信轮次：`UNKNOWN`。

### 未解决问题
- step 如何由电路可信产生而非宿主注入（`UNKNOWN`）；
- `T` 的真实终止步锚定（R8，`UNKNOWN`）；
- 与 pc/opcode/addr 的同电路绑定（`source_trace_audit.md` A1 末行，当前缺失）；
- 注入性检查的证明层实现（`CONSTRUCTED`）。

---

## B. 事件累积承诺（链式哈希 / 累积承诺并绑定最终摘要）

**思路**：对事件序列做链式哈希 `H_0=IV, H_i=H(H_{i-1}, encode(e_i))`，把 `H_{T-1}` 作为公开摘要绑定；verifier 比较摘要。

### 安全性直觉
- 哈希链对**顺序敏感**：交换两项改变最终摘要 → 理论上覆盖 A3 重排。
- 若 `H_{T-1}` 由**可信方固定或 VM 执行电路独立产生**（而非 prover 自报），省略/复制会改变摘要 → 可覆盖 A1/A2/A8。
- **关键限制**：普通哈希链本身只是 commitment，不是完整性证明。若 `H_0` 与 `H_{T-1}` 都由 prover 提供，prover 可对任意（含省略+复制后的）序列重算一条自洽链 → **什么都证明不了**。必须满足：
  1. 每个 `encode(e_i)` 内容正确绑定到 step i（R5/R6/R7）；
  2. 最终摘要 `H_{T-1}` 由 verifier 固定或由可信 VM 执行电路输出；
  3. `IV` 与终止步 `T` 可信锚定（R8）。
- 单独使用**不能**解决 A4/A5/A6（链上内容是错的仍自洽），也**不能**解决 A7（prover 只对前缀建链并自报 `T′`）。

### 必要约束（`CONSTRUCTED`）
```
H_0 = IV                                  # 初始值可信固定
∀ i: encode(e_i) = (step_i, type_i, addr_i, row_i)   # 内容受 R5/R6/R7 约束
H_i = H(H_{i-1}, encode(e_i))              # 链内顺序绑定
H_{T-1} 公开并被 verifier 比较             # 终值可信
T 由 verifier 固定 / 电路证明              # R8
```

### 隐私影响
- 摘要 `H_{T-1}` 公开不泄露单个地址（若基元是隐藏承诺 / 哈希）；但 `encode` 若直接含明文地址会泄露 → 需把地址以隐藏承诺或哨兵形式纳入（`CONSTRUCTED`）。
- dummy 只编码 `p−1` 与类型，不编码 lookup `reg0`（保持冻结语义）。

### 证明接口改动
- 需在电路内实现链式哈希更新与终值公开输出；若地址用 Pedersen 承诺，涉及非原生群运算与可信生成器（当前路径不承载，`dependency_and_cost.md` §1）。
- 需 verifier 固定/可信获得终值 → 改 verifier 信任接口（`UNKNOWN`）。

### 主要成本项（符号级）
- 新增哈希/承诺调用 `O(T)`（每事件一次链更新 + 每事件地址承诺重算若选隐藏路径）；具体门数/时间/字节 `UNKNOWN`。
- verifier 额外检查：终值比较（一次或少量）；`UNKNOWN` 具体成本。

### 未解决问题
- 终值 `H_{T-1}` 的**可信来源**（谁固定、如何防 prover 自报）——这是本方案成败关键，`UNKNOWN`；
- 与 R5/R6/R7 内容绑定的组合方式；
- MiMC 无公开 binding 归约、Pedersen 当前路径不承载（承诺层未决，`../aba-03-d2/decision.md`）；
- 若仅用普通哈希链而无可信终值，方案不成立——不得写成已解决 B4。

---

## C. VM step 与 Fetch 电路内直接绑定

**思路**：在 VM 执行关系中直接产生或约束 Fetch 事件，使“执行一步”与“产生该步事件”在同一电路内完成，避免跨电路同一性缺口。

### 安全性直觉
- 若 VM 电路在每步直接输出该步的 `(step, type, addr, row)` 并约束其进入公开 statement，则 step、type、addr、row 与执行语义天然同电路绑定 → 直接覆盖 A4/A5/A6/A9（step/type/row 伪造），配合 step 连续可覆盖 A1/A2/A3/A8。
- **仍需**：终止步 `T` 的可信表达（R8，A7 盲区）与 step 覆盖关系（R2）——同电路绑定不自动证明执行在正确 halt 处结束。

### 必要约束（`CONSTRUCTED`）
```
VM 电路每步输出 event_i = (step_i, is_mem_op_i→type_i, trace_addr_i, row_i)
step_i 连续、从 1 到 T−1（step0 排除）
real:  trace_addr_i = reg0_i, 0≤addr_i<n     # 完整字段范围，防 A9
dummy: trace_addr_i = p−1, 不承诺 reg0
is_mem_op_i 由 opcode 派生（已有 BoolOr，ZkVmExecutor...cs:968-976）
T / halt 边界进入 statement
```

### 隐私影响
- 需把 type/step/承诺 公开或承诺化；真实 `reg0` 保持私有（隐藏承诺路径）。C1 直接公开地址路径有不可接受隐私退化（`design_options.md` §1），本方案不采用。
- 同电路绑定减少跨电路信息泄漏面（相比两电路对同一承诺）。

### 证明接口改动
- **改动最大**：需修改 VM 执行电路本身（当前 Prove 电路不接收 pc/opcode，原始 L164-165；trace step 为宿主注入，`:393-395`），新增事件输出与连续 step 约束。
- 若地址用隐藏承诺，仍需承诺方案定型与 opening（`UNKNOWN`/`BLOCKED`）。

### 主要成本项（符号级）
- 新增约束在 VM 电路内部，`O(T)` 量级；具体门数/时间/字节 `UNKNOWN`。
- 可能需要把 opcode/pc 纳入 statement，增加 Witness 与约束；`UNKNOWN`。

### 未解决问题
- 上游 VM 电路结构是否允许在不破坏 Fixed VK 的前提下增加输出（需重新 setup）→ `UNKNOWN`；
- 承诺/范围约束的域适配（real 地址范围 `0≤addr<n` 当前缺失，`source_trace_audit.md` A4）；
- R8 终止绑定；与 P1-A（opcode 表可信）的衔接——本轮不改 P1-A。

---

## D. 递归或组合证明

**思路**：用子证明分别证明 VM 执行与 Fetch 事件序列，再由上层递归/组合证明绑定二者。

### 必须遵守的既有结论（硬约束）
- **递归验证器不能直接读取子证明的私有 witness**（`design_options.md` §3/C1 勘误）。任何跨证明关系只能通过以下方式实现：
  1. 子证明把相关量放进**公共输入**；
  2. 子证明对相关量做**承诺**，上层用承诺及其约束证明建立关系；
  3. 把两个关系**合并到同一个证明**中。
- 当前 `plonk.rs:293-315` 是单电路 setup→prove→verify，无递归/组合接口证据（`../aba-03-d3-01/dependency_and_cost.md` §3）。

### 安全性直觉
- 若 VM 子证明公开输出每步事件承诺/摘要，Fetch 子证明公开输出逐事件承诺/摘要，上层比较公开值或验证承诺关系，可在不暴露地址的前提下绑定两序列 → 理论上覆盖跨电路同一性与部分完整性。
- **不能单独解决**：若子证明自身不保证事件完整性（A1/A2/A7），上层比较的是“被提交的内容”，无法发现未提交的事件；仍需子证明内部的 R2/R3/R8。
- 上层只能见公共输入/承诺，私有地址比较必须经承诺（回到 binding/hiding 未决）。

### 必要约束（`CONSTRUCTED`）
```
子证明1(VM):  公开输出 (event_i 承诺或摘要, T, halt 边界)
子证明2(Fetch): 公开输出 (event_i 承诺或摘要)
上层:  验证两子证明 + 比较公开承诺/摘要 + 约束 step 覆盖/顺序/终止
跨证明量必须走公开输入或承诺（不得读私有 witness）
```

### 隐私影响
- 地址若以隐藏承诺公开，可保持隐私；但承诺方案（Pedersen 非原生域 / MiMC 无归约）未定 → 隐私与 binding 均未闭合。
- 递归公开摘要本身不泄露单步地址。

### 证明接口改动
- **需证明系统级改造**：递归/组合验证电路、兼容的 VK、公共输入/承诺接口；当前无此接口（`UNKNOWN`/`BLOCKED`）。

### 主要成本项（符号级）
- 递归验证开销、子证明数量 `O(T)` 或按批次；具体门数/时间/字节/轮次 `UNKNOWN`。
- 可能需可信 setup/ceremony 支撑递归电路 → `UNKNOWN`。

### 未解决问题
- 递归接口与当前 additive-only MPC prove 路径能否共存 → `UNKNOWN`；
- 承诺方案定型（同 B）；
- 子证明内部完整性（R2/R3/R8）——递归本身不补；
- 与 P1-A/VK 的衔接——本轮不改这些结论。

---

## 1. 四方案横向对照

| 维度 | A 连续 step-index | B 累积承诺 | C 电路内直接绑定 | D 递归/组合 |
| --- | --- | --- | --- | --- |
| 覆盖 A1/A2/A8（遗漏/复制/多余） | 强（step 注入+覆盖） | 仅当终值可信 | 强（同电路 step 连续） | 依赖子证明完整性 |
| 覆盖 A3 重排 | step 单调 | 链顺序敏感 | 同电路顺序 | 依赖子证明 |
| 覆盖 A4/A5/A6/A9 | 需叠加 R5/R6/R7 | 不能单独 | 强（同电路） | 依赖子证明/承诺 |
| 覆盖 A7 前缀截断 | 需 T 可信（R8） | 需 T 可信（R8） | 需 T/halt 进 statement | 需子证明 R8 |
| step 可信产生 | 难点（当前宿主注入） | 需 R5 | 同电路天然 | 需子证明公开 step |
| 隐私（不泄露 reg0） | 可保持 | 可保持（承诺） | 可保持（隐藏路径） | 可保持（承诺） |
| 证明接口改动 | 中（VM statement） | 中（终值可信接口） | 大（改 VM 电路） | 大（递归接口） |
| 承诺层依赖 | 可选 | 强 | 可选/强 | 强 |
| 主要成本 | step 约束 O(T) | 哈希链 O(T) | VM 约束 O(T) | 递归验证开销 |
| 数值成本 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| 未决核心 | step 来源、T | 终值来源、R5/R6/R7 | 电路改造可行性、T | 递归接口、承诺、子证明完整性 |

---

## 2. 比较结论（不选择胜者）

1. **没有单一方案独立覆盖全部攻击类别**。四者都依赖 `R8`（真实终止步 `T` 的可信锚定）与 `R5/R6/R7`（每步内容绑定）；这两类缺口不是任何“看起来完整的哈希链或 step 列表”能自动补齐的。
2. **A 与 C 在 step 绑定上最直接**，但 A 依赖 step 可信产生（当前宿主注入）、C 依赖改 VM 电路（当前 Prove 不接收 pc/opcode）。
3. **B 的风险最易被误判**：普通哈希链无可信终值等于无完整性；必须明写 `H_{T-1}` 来源与内容绑定，否则不成立。
4. **D 受既有递归硬约束限制**，且当前无递归接口证据；它把问题转移为“子证明自身是否完整”，并未消除 B4 的核心难点。
5. **共同隐私边界**：四方案都可在不公开真实 `reg0`、不把 dummy lookup 强设为 `p−1` 的前提下表述；但承诺层（MiMC binding 无归约、Pedersen 当前路径不承载）与 content binding 仍是未决前提。
6. 本轮**不选择胜者、不进入接口规格**；各方案成本全为 `UNKNOWN`，是否值得实现另轮评估。
