# ABA-03-D1 / Phase F：P2 跨电路地址绑定最小改造可行性 — 决策

> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35…`；起点 `f393347477d96f7d804d80704272309db7ccf52a`。
>
> 性质：只读设计与可行性评估。本轮不选择最终协议、不实现电路、不改原始 VDORAM、不解除 ABA-03 的 `HOLD`、不运行测试。

---

## 1. 四选一决策

### 决策：`HOLD_INSUFFICIENT_EVIDENCE`

**理由**：带操作类型条件的绑定目标关系（B1–B4）已用固定 commit 源码精确定义，`is_mem_op` 门控语义已厘清（真实步三值相等、dummy 步 `trace_addr=p−1` 且不得强加相等、step0 无 Fetch），三类方案的同维度比较也已完成。但**没有任何一条方案具备"可实现的最小接口路径"所需的证据支撑**：

- C1 的最小路径存在但以真实地址明文公开为代价，构成不可接受的隐私缺口（`INFERRED`），不满足 `GO_MINIMAL_INTERFACE_DESIGN` 的"无已知不可接受隐私缺口"；
- C2 的隐藏承诺，其 hiding 强度、随机数 `r_i` 生命周期、MPC 认证随机、防重放字段均为 `UNKNOWN`（`design_options.md` §2、`leakage_and_security.md` D1/D5/D6），且当前仓库无可复用承诺接口；
- C3 的递归/组合接口、非原生域运算、成本关键项全部 `UNKNOWN`（`design_options.md` §3），固定 commit 无递归/proof-composition 证据。

因此既不能发出 `GO_MINIMAL_INTERFACE_DESIGN`，也没有证据断言"理论可行但需大重构"足以支撑 `GO_WITH_MAJOR_REDESIGN`（后者需要对 C2/C3 可行性有正面判断，当前缺）。架构未发现数学矛盾，故不选 `NO_GO_CURRENT_ARCHITECTURE`。按"关键承诺、验证或成本问题仍无法判断"的定义，选 `HOLD_INSUFFICIENT_EVIDENCE`。

**本决策与既有结论的关系**：ABA-03 的 `HOLD` 继续保持；ABA-03-C2 的 `REQUIRES_CIRCUIT_INTERFACE_CHANGE` 不被推翻或改写——本轮 D1 是在该判断之下的可行性评估，结论是"P2 所需的电路绑定接口其最小形态仍证据不足"。不修改任何既有文档。

---

## 2. 决策必须回答的七个问题

### Q1. 最小可行方案是哪一种？若没有，为什么？

**没有已证实在当前架构上可行的最小方案。**

- C1（直接公开地址）构造最简单、可复用公开输入通道，但真实地址明文公开是实质性隐私退化（`INFERRED`）。若 VDORAM 的地址机密性是目标，则 C1 不满足"无不可接受隐私缺口"，被排除为最小可行方案。
- C2（共享隐藏承诺）在隐藏地址前提下可闭合 B1/B2 的跨电路相等，但其隐藏性质、随机性与防重放均 `UNKNOWN`，当前仓库无共享承诺接口，无法判定为"可实现的最小路径"。
- C3（证明组合/递归）关键接口与成本全部 `UNKNOWN`，固定 commit 无递归接口证据。

因此最小可行方案**未确定**，需在承诺/递归接口与成本上有进一步证据才能定。

### Q2. P1-A（固定完整 opcode table 比较）是否可以作为独立前置条件复用？

**可以，且与本轮 P2 方案无关。** P1-A 复用现有 public-input 通道（opcode 表四列已是公开输入，`InstructionFetch...cs:126-156`、`plonk.rs:143-161`），由独立 verifier 持有预期完整表逐项比较 + 固定/可信 vk 即可闭合 P1（`../aba-03-c2/verifier_interface_audit.md` §2）。它缓解"跨程序替换"，但**不**闭合 P2 地址同一性，也**不**解决 C2 承诺重放（承诺是否含程序身份是独立设计问题，`leakage_and_security.md` D5）。

### Q3. P2 的最小新增接口究竟是什么？

按 B1–B4，最小新增接口是**带 `is_mem_op` 门控的跨电路地址同一性关系 + 事件完整性锚点**：

```
真实步 (is_mem_op=1)：fetch_addr = reg0 = trace_addr（完整域元素相等）+ 0≤addr<n
dummy 步 (is_mem_op=0)：trace_addr = p−1、trace_mem_val = 0；不要求 fetch_addr=trace_addr
step 0：无 Fetch proof，不计事件
B4：事件计数、顺序、halt 边界可验证
```

该关系必须以 verifier 可核对的形式表达：要么同一电路内断言并通过公开承诺/output 交给 verifier，要么两电路各自输出同一承诺由 verifier 比较。当前上游两者都没有（ABA-03-C2 §3：`fetch_addr`/`trace_addr` 均为私有、跨电路仅宿主哈希 `throw`）。

### Q4. 该接口是否会改变现有 proof statement 或电路关系？

**会。** 当前 proof statement 的公开输入只有 step counter、public input、opcode table 四列（`plonk.rs:143-161`），地址不在其中；且每步独立 setup/prove/verify（`plonk.rs:293-315`）。无论 C1（新增逐步公开字段）还是 C2（新增承诺输出）还是 C3（新增顶层 statement），都必须改变电路输出与 verifier 核对的 statement 结构。C2/C3 还需新增电路内承诺/递归关系。这不是"只加 verifier 配置"能完成的。

### Q5. 地址隐私是否还能维持？

- **C1**：不能，真实地址明文公开（`INFERRED`）。
- **C2/C3**：目标上可维持（承诺隐藏/地址不入 statement），但隐藏性质未证、随机数生命周期未定（`UNKNOWN`）。因此"在维持地址隐私的前提下闭合 P2"目前**只有候选构造，没有已验证路径**。

### Q6. 当前 MPC additive-share / proof 接口是否构成独立阻断项？

**不是已确认的独立阻断项，但是未决风险。** 当前 MPC 为 additive-only、无 MAC（见 `../exp-doram-06/rust-authenticated-share-path.md` B.1/B.4），proof 通路是单电路 setup→prove→verify（`plonk.rs:293-315`）。若 C2 需要认证随机来防 `r_i` 重采样，可能需要额外 MPC 交互；若 C3 需要递归，需要改造 prove 通路。是否达到"阻断"级别取决于具体承诺/递归方案选择，当前标 `UNKNOWN`（`cost_model.md` §3）。不把它写成独立 NO_GO。

### Q7. 下一步是否值得做一个最小电路原型？

**本轮不建议立即启动。** 在启动前应先闭合下列证据缺口，否则原型会建立在未定假设上：

1. 明确 C2 承诺的具体形式与 hiding 论证、随机数 `r_i` 的产生/绑定机制（含是否需要 MPC 认证随机）；或明确 C3 的递归/组合接口与非原生域可行性。
2. 明确 verifier 侧如何固定 vk、持有预期程序表/P2 承诺锚点，并给出公钥分发与实例 nonce 方案。
3. 给出 B4 完整性（事件计数、顺序、halt 边界）的具体电路表达。

在这三点之前做原型，无法判定是对 C1/C2/C3 中哪一条路径的有效验证。若后续 Evidence 闭合，可优先考虑 C2（在保地址隐私前提下）的最小原型；但本轮不启动。

---

## 3. 冻结与边界

- 本轮只新增 `docs/aba-03-d1/` 五份文档；未修改任何 ABA-01/02/03/C2 文档，未改源码、未加测试/CSV/benchmark。
- ABA-03 的 `HOLD` 继续保持；ABA-03-C2 的 `REQUIRES_CIRCUIT_INTERFACE_CHANGE` 保持。
- 不声称任何电路已实现、任何安全性质已证明、任何成本已实测。
- 完成后停止，不自动进入电路实现、ABA-04 或新一轮实验。
