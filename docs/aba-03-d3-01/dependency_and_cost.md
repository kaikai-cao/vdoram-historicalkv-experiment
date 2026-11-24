# ABA-03-D3-01 / Phase 4：阻断项依赖关系与符号成本边界

> 实验仓起点：`03960aa941bcd8ef88fbd06a83cf7599682a5cbd`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只复用既有证据的接口/成本边界分析；不实现电路、不跑 benchmark、不填具体门数/时间/字节数。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。
>
> 证据来源：`../aba-03-d1/cost_model.md` §0–§4；`../aba-03-d1/design_options.md` §1–§4；`../aba-03-d1/leakage_and_security.md` §1/§2；`../aba-03-c2/verifier_interface_audit.md` §2/§4；`../aba-03-d2/commitment_candidates.md` §0/§2/§4；`../aba-03-d2/opening_and_randomness.md` §0/§2/§5；`event_completeness.md`；`verifier_independence.md`。

---

## 0. 一句话结论

七个未决问题不是同一个问题的不同说法：**P1-A 与 VK 锚定主要落在 verifier 侧，可优先独立闭合；地址/承诺/dummy trace row/B4 主要落在电路 statement；Pedersen 路径和认证随机数还可能需要新的证明系统或 MPC share 接口。**当前不存在一条已被证据闭合的最小路线，因此成本只能做符号级边界，具体数值一律 `UNKNOWN`。

---

## 1. 依赖矩阵

| 问题 | 必要前提 | 可否独立解决 | 对现有接口的影响 | 当前状态 |
| --- | --- | --- | --- | --- |
| 隐藏地址 binding | 承诺方案定型；正确 opening；同承诺下消息相同 ⇒ Pedersen `r` 相同；不同消息同 `C` 需 DL 困难 | 否：依赖承诺方案、域适配、随机数与 opening 约束 | 若 MiMC：新增 Fr 内承诺重算但 binding 无归约；若 Pedersen：需群运算/非原生域与可信生成器，当前 Fr-wire/PLONK 路径不承载 | `UNKNOWN`（MiMC binding）；`BLOCKED`（Pedersen 接入当前路径） |
| Fetch/VM 地址一致性 | 两侧 opening 与同一 `com`，或合并电路内直接相等；real 步三值相等 + 范围 | 否：依赖隐藏地址 binding 与 step/event 对齐 | 需新增跨电路公开承诺输出与比较，或把地址关系放进同一电路；当前地址私有且无共享公开值 | `CONSTRUCTED` + `UNKNOWN` |
| Dummy trace row 绑定 | step↔row 对应；`trace_addr=p−1` 与实际 row.mem_addr 绑定；lookup 仍为 `reg0` 且不公开 | 部分：sentinel 约束可单独定义，但完整绑定依赖 step↔row 与事件类型 | 需新增 event_type 从 opcode 派生、sentinel 约束与 row 引用；当前 Fetch 不输出/强制 row.mem_addr | `CONSTRUCTED` + `UNKNOWN` |
| P1-A 程序身份 | verifier 可信预期 `OP_exp`（或 digest）、固定/可信 VK | 是（最小路径 P1-A-1 主要 verifier 侧）；不解决 P2/B4 | 可复用现有 opcode public-input 通道；P1-A-2 digest 需新增电路承诺 | P1-A-1 `CONSTRUCTED`；现状缺失 `VERIFIED` |
| B4 事件完整性 | count/order/completeness/termination；step↔row；event_type 绑定；跨执行 context | 否：依赖 step、event、trace 与执行边界的统一 statement | 需新增事件计数、单调/无重复、halt 边界与 proof 集合完整性约束；宿主检查不可替代 | `BLOCKED` / `UNKNOWN` |
| VK 外部锚定 | verifier 信任模型：预固定 / 可信 setup / 接受 prover 自提 | 是（trust 与分发模型可独立决定）；不解决程序语义或 P2 | 当前 compat 路径同函数现场 setup 为 `VERIFIED`；外部模型为 `UNKNOWN`；接受自提 VK 且无锚定仅 `CONDITIONAL INFERENCE` | `UNKNOWN`（外部）+ `CONDITIONAL INFERENCE`（条件风险） |
| Context / replay | `exec_id` 唯一且 verifier 锚定；step/program/event 进 context；随机数和重放机制分离 | 否：依赖执行实例来源、P1-A、step 与 event 绑定 | 需新增 `exec_id`/context 公开或承诺化字段及 verifier 固定期望；当前无机制 | `UNKNOWN` |

---

## 2. 依赖图（文字版）

```
P1-A-1（verifier 固定 OP_exp + 固定 VK）
    └─→ 程序语义可信；不→ 地址同一性；不→ B4

VK 锚定（verifier 信任模型）
    └─→ proof 验证可信前提；不→ 程序语义；不→ P2/B4

承诺 binding + opening 正确性
    └─→ 同一 com + 同消息 ⇒ 消息地址相同（条件性）
    └─→ Pedersen 同 C + 同 m ⇒ r 相同 mod q（代数结果）
    └─→ 仍不→ B4

step↔trace row 对应 + opcode 派生 event_type
    └─→ real/dummy 分类与 trace row 哨兵绑定
    └─→ B4 的必要子集，但 count/order/halt 仍需独立约束

B4 count/order/completeness/termination
    └─→ 依赖 step/event/trace/context 的统一 statement
    └─→ 不由承诺相等或 P1-A 推出

Context / replay
    └─→ 依赖 verifier 固定 exec_id + P1-A + step/event 绑定
    └─→ 随机数随机性本身不是防重放机制
```

---

## 3. 三类边界（谁来解决）

| 类别 | 问题 | 最小处理方式 | 依据 |
| --- | --- | --- | --- |
| verifier 侧检查可解决 | P1-A-1 程序表逐项比较；VK 固定/信任模型；公开承诺或 event_type 的最终比较；固定 `n`/step 边界期望值 | 独立 verifier 持有可信参数与期望值；复用 public-input 通道与标准 `verify_proof` | `verifier_interface_audit.md` §2/§4；`verifier_independence.md` §2/§3 |
| 必须新增电路约束 | real 步 `fetch=reg0=trace_addr` 与范围；dummy sentinel + 实际 row 绑定；event_type 来自 opcode；step↔row；B4 count/order/halt；承诺 opening 重算 | 在 VM/Fetch/Trace/组合电路中新增关系和公开 statement | `p2_binding_semantics.md` B1–B4；`circuit_interface.md` §2；`event_completeness.md` §1 |
| 必须改变证明系统 / MPC share 接口 | Pedersen 群运算与非原生域适配；若采用认证随机则需 SPDZ/Beaver 路径；递归/组合证明接口；非 prover 自提 VK 的可信 setup/ceremony 接口 | 需评估新增群变量、share 类型或递归 statement；当前路径不承载 | `commitment_candidates.md` §0/§2；`opening_and_randomness.md` §0/§2；`design_options.md` §2/§3；`cost_model.md` §2 |

**不得混同**：verifier 侧能检查公开值的前提是这些值已被电路约束正确产生；电路约束能产生正确单步关系，不代表事件序列完整；协议层可信参数能防止 setup 自洽，不代表程序语义或地址同一性已闭合。

---

## 4. 符号成本边界

沿用 `../aba-03-d1/cost_model.md` 的记号：`T` 为总步数（含 step0），`M` 为真实内存事件数，`D = T − 1 − M` 为 dummy Fetch 数，`L = bit_length(Nmax)` 且 `2^L ≤ p`。结构骨架只表示类别，不代表实测：

```
C_total_add ≈ T · C_commit/event + M · C_real + D · C_dummy + C_prog + C_vk/verifier
              (+ C_recursive 若选证明组合)
```

其中每项的具体约束数、乘法门数、prove 时间、通信轮次、内存与 proof 字节数全部 `UNKNOWN`。

| 成本维度 | 符号级边界 | 数值状态 |
| --- | --- | --- |
| 新增公开输入数量 | P1-A-1 复用现有 opcode 四列；候选新增 `com_i/event_type_i/exec_id/n` 等，`O(T)` 或一次性字段 | 具体字段数和字节数 `UNKNOWN` |
| 新增私有 witness 数量 | 承诺 opening `r_i`（若选承诺）、event_type 派生值、trace row 引用、可能的 `pc_i/opcode_i` 保持私有 | `UNKNOWN` |
| 新增哈希/承诺/比较关系 | 承诺重算每电路每步一次（若选隐藏承诺）；P1-A-1 为 verifier 侧逐项比较；B4 新增计数/顺序/等价比较 | 调用次数可符号表达；门数 `UNKNOWN` |
| 是否涉及非原生群运算 | MiMC 路径 Fr 原生但 binding 未证；Pedersen 需群变量/CurveVar 与可信生成器，当前路径不兼容 | `UNKNOWN` / `BLOCKED`（当前路径） |
| 是否需要递归或证明组合 | 合并电路路径不需要递归；共同承诺顶层比较可能需要组合 statement；当前无递归接口证据 | `UNKNOWN`（未选方案） |
| 是否需要 MPC authenticated randomness | 若承诺随机数需防 prover 重采样且 verifier 不见 `r`，可能需要认证随机；当前 additive-only、无 MAC、无可用 Beaver 路径 | `BLOCKED`（当前架构能力）；是否方案必需 `UNKNOWN` |
| verifier 额外检查工作 | P1-A-1 逐项比较整表；公开 `com/event_type/step` 比较；B4 边界与 context 检查 | 具体比较次数/时间 `UNKNOWN` |

### 4.1 明确的错误等价（不得重复）

- R1CS/PLONK 约束数 `≠` MPC 乘法数 `≠` 通信轮次 `≠` prove 时间 `≠` verifier 成本。
- 公开输入通道存在 `≠` verifier 已检查。
- gadget 存在 `≠` 已接入 CompatCircuit→PLONK 路径。
- 标准密码学性质 `≠` 当前电路接口可实现性。
- 宿主端检查 `≠` proof soundness。

---

## 5. 对“最小可行路线”的边界判断

结构上最小、可审计的候选路线可拆成三段，但均需后续授权验证：

1. **verifier 侧（不必然改电路）**：独立 verifier + 固定/可信 VK + P1-A-1 完整 opcode table 逐项比较；固定 `n`/step 边界期望值。
2. **电路 statement（需新增约束）**：real/dummy 分类由 opcode 派生；real 三值相等 + 范围；dummy 哨兵 + 实际 trace row 绑定；event_type 与 `step` 进入公开 statement 或承诺；B4 count/order/halt。
3. **证明系统/MPC 接口（视方案而定）**：若选隐藏承诺，必须先闭合 binding/hiding/opening/随机数与域适配；若选认证随机或递归组合，还需对应 share/证明接口。

这三段中只有第 1 段具备可复用通道证据；第 2、3 段的必要关系多为 `CONSTRUCTED` / `UNKNOWN`。因此本阶段**不能**给出已闭合的最小实现路线，也不能估算可信的具体成本。
