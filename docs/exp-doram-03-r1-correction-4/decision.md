# decision.md — EXP-DORAM-03-R1-Correction-4 最终判定

> 2026-11-23 · 起点 `6586dd28d3d7f4dce8d51815c96f4ea4be7eba9c` · 只就本轮六份文件作判定。
> D2、跨步 verifier chain、选择性 abort 按任务包允许继续 **BLOCKED**，其影响在 §4 列明。

---

## 0. 唯一最终决策：**HOLD**

不是 `GO_TO_MINIMAL_PROTOCOL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：本轮没有发现协议级矛盾或威胁模型不可兼容。三个随机量角色已彻底分离，依赖图无环；公开验证仍不需要公开秘密地址或路径。固定 artifact 缺少 gadget **不是** NO_GO 的理由（任务包明确禁止据此判 NO_GO）。
- **不 GO**：GO 要求的五项中，只有“角色完全分离”满足；L2 具体承诺候选、承诺与 SNARK witness 的完整接口、随机源与 grinding 的可执行处理均未闭合。

---

## 1. GO 门槛逐条核对

| GO 条件 | 状态 | 依据 |
| --- | --- | --- |
| 三种随机量角色完全分离 | **满足**（CONSTRUCTED） | `W_pre,i`（8 字段，含 `r_tape,i`）、`s_i`（消息外盲化随机数）、`r_tape,i`（状态更新带）；I1–I5 无环检查通过 |
| 至少一个具体、可审查的 L2 承诺候选 | **不满足**（BLOCKED） | 确定性 MiMC 无 hiding；随机化 MiMC 仅启发式；Pedersen 有定义但 `Fr` 后端不兼容且 artifact 无实现 |
| hiding、binding、opening verification 定义清楚 | **部分**（规则清楚、方案 BLOCKED） | 三类方案逐项列出性质；但没有一类同时满足三项并可在固定后端落地 |
| 承诺与 SNARK witness 的绑定接口完整 | **不满足**（BLOCKED） | 电路内同线值约束是 CONSTRUCTED 规则；外部承诺 → SNARK witness 的桥接（Q3(b)(c)）无接口；`Encode` 覆盖 8 字段需具体承诺实现 |
| 随机源与 grinding 风险有明确处理方案 | **不满足**（BLOCKED） | 规则层有联合生成、MAC、不可重采样、`attempt_i` 作废；执行层无认证随机带，`q_H·2^-170` 防护无法落地 |

结论：**1/5 满足，2/5 部分，2/5 未满足** → HOLD。

---

## 2. 三种角色分离的完成度

| 对象 | 最终定义 | 状态 |
| --- | --- | --- |
| `W_pre,i` | `(old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i)`；被承诺消息；不含 `s_i` | CONSTRUCTED |
| `s_i` | commitment opening randomness；不属于消息、不进 ORAM 状态、不作 ρ 种子；MPC 联合生成、MAC、不可重采样、每步独立 | CONSTRUCTED 规则 / BLOCKED 实现 |
| `r_tape,i` | 状态更新随机带；属于消息、被 `com_i` 覆盖；派生 `r_t` 由 R1CS 绑定到 `nonce'=nonce+r_t` | CONSTRUCTED 算术 / BLOCKED 生成 |

`com_i = Com(Encode(ictx_i‖W_pre,i); s_i)`；`ρ_k = H(domain_k‖ictx_i‖com_i‖ctx)`；`ictx_i` 含 step/program/circuit/version/旧根/`attempt_i`。依赖图无 `ρ→com/W_pre` 的边。

---

## 3. 承诺与 SNARK witness 绑定结论

- **电路内验证**（推荐形态）：`com_i − Com(Encode(ictx_i‖W_pre,i); s_i) = 0` 与 ORAM 约束共用同一组 `W_pre,i` 线值，`s_i` 为私有 witness 线。规则层 **CONSTRUCTED**；但所选承诺方案仍需同时具备 hiding 与 `Fr` 兼容性 → **BLOCKED**。
- **电路外验证**：无桥接接口，外部承诺成功不等于 witness 一致 → **BLOCKED**。
- **编码覆盖**：必须覆盖全部 8 字段；省略 `r_tape,i` 或 `eviction_aux` 会造成“承诺后换字段”漏洞 → CONSTRUCTED 规则 / BLOCKED 实现。

---

## 4. 究竟是什么在阻塞研究（必须明确）

| 阻塞源 | 性质 | 具体含义 | 状态 |
| --- | --- | --- | --- |
| **① 承诺构造** | 方案/理论层 | L2 缺少同时给出 hiding、binding、opening verification 且兼容 `Fr` R1CS 的具体候选；随机化 MiMC 无 hiding 规约，Pedersen 无后端 gadget | **BLOCKED**（首要） |
| **② MPC 随机源** | 协议/工程接口层 | `s_i`、`r_tape,i` 需同一 MPC 执行的认证随机带、MAC 覆盖、不可由单方重采样、失败作废；artifact 只有落盘 + 外部逐电路证明 | **BLOCKED**（直接支撑 ① 与 grinding） |
| **③ SNARK witness 绑定** | 接口层（依赖 ①） | 电路内同线值约束在规则层已完成；外部承诺桥接（同参数 Pedersen 或 `π_open`）不存在 | **BLOCKED**（选定 ① 后才可闭合） |
| **遗留 D2** | 协议/工程层 | 同执行 ORAM 输出份额、辅助 witness、公开根与协作证明输入未证明使用同一批认证线值 | BLOCKED（影响 ②③ 的可执行性） |
| **遗留跨步 verifier chain** | 工程层 | verifier 只验单 proof，未强制 `C_{i+1}^{out}=C_{i+1}^{in}` 与 step/History 连续 | BLOCKED（影响端到端，不影响本轮角色定义） |
| **选择性 abort** | 协议层 | 固定长度 abort 必要但不充分；中止与秘密独立性、拒绝打开份额处理未证 | UNKNOWN / BLOCKED |

**优先级**：先解 ①（承诺构造），因为 ②/③ 的接口形态取决于选定哪类承诺；② 是 grinding 与 nonce 隐私的公共依赖；③ 在 ① 确定后才可判断是电路内验证还是外部桥接。

---

## 5. 随机源与 grinding 结论

- `s_i` 可重采样 ⇒ 改 `com_i` ⇒ 改 ρ，直接复活 Correction-3 的 `q_H·2^-170` 问题；`r_tape,i` 在消息内，改它须改 `com_i`，同理。
- 防护规则：MPC 联合生成 + MAC + 不可重采样 + 每步独立 + `attempt_i` 域分离 + 失败后随机量作废。
- 上述规则全部为 CONSTRUCTED，**执行层无接口 → BLOCKED**；因此 grinding 在固定 artifact 上仍未被消除。
- 固定长度 abort 不得被写成已解决选择性 abort（见 §4）。

---

## 6. 相对 Correction-3 的保留 / 修正 / 撤回

### 保留
- 去循环依赖 `W_pre → com → ρ → W_post → π` 与七阶段结构；
- `2^-170` 的条件化结论、`enc<2^169`、两次独立哈希与拒绝采样；
- MiMC 参数、gadget 目录无承诺实现、co-SNARK 只落盘单 proof 的既核证据；
- D2 / 跨步 verifier chain / 选择性 abort 的 BLOCKED 状态与整体 HOLD。

### 修正
- 承诺消息与盲化随机数分离：`r_i ∈ W_pre` → `s_i ∉ W_pre`；
- `ictx_i` 由 5 元组扩为 6 元组（增 `attempt_i`）；
- 七阶段中阶段 2/3/6 的输入输出与可见性；
- 层模型：独立的 `com(r_tape)` 撤回，`r_tape,i` 并入 L2 消息字段。

### 撤回
- `commitment_opening_randomness` 作为 `W_pre,i` 字段的写法；
- “`r_i` 同时作为消息字段与盲化随机数”的角色混淆；
- Correction-3 中“L3 独立随机带承诺”的表述。

---

## 7. 停止条件

六份文件完成；提交推送并核对本地/远端 SHA 后立即停止。不写代码、不跑 benchmark、不重算成本、不重开 D1/Eviction 审查、不启动原型。下一轮仅对用户报告做一次有边界的独立审查。
