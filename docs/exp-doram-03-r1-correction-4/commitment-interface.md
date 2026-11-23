# commitment-interface.md — 角色分离后的承诺安全性质核查

> 2026-11-23 · 起点 `6586dd2` · 只核查三类候选，不引入 ORAM 文献综述、不重算成本。
> 标记：**VERIFIED** 固定源码/可复现事实 · **CONSTRUCTED** 本轮规则 · **INFERRED** 标准推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 接口缺失。

---

## 0. 层模型修正

Correction-3 把承诺分三层：L1 状态根、L2 `com(W_pre)`、L3 随机带承诺。本轮角色分离后：

| 层 | 对象 | 说明 | 状态 |
| --- | --- | --- | --- |
| L1 | 状态 Merkle root `C_i^{Tree/Pos/Stash/Meta/Hist}` | 只要求 binding；由 MiMC 链式 hash 提供 | VERIFIED 参数 / INFERRED 成本 |
| L2 | `com_i = Com(Encode(ictx_i‖W_pre,i); s_i)` | 要求 binding + hiding；`W_pre,i` 含 `r_tape,i`，不含 `s_i` | **BLOCKED**（无已定义安全候选） |
| — | 随机带 `r_tape,i` | **不再是独立的第三层承诺**；它是 L2 消息字段，其完整性由 L2 binding 覆盖，其生成由 MPC 认证随机源保证 | CONSTRUCTED 规则 / BLOCKED 生成 |

Correction-3 中“独立的 `com(r_tape)`”表述被撤回：它既与“`r_tape,i ∈ W_pre,i`”重复，又在 artifact 中无实现。**不得**把状态 Merkle root 的可验证性当作 L2 hiding 的依据。

---

## 1. 三类候选核查

设 `x = Encode(ictx_i‖W_pre,i)`（覆盖全部 8 字段），`s_i` 为承诺盲化随机数，电路域为 BN254 `Fr`。

### 1.1 确定性 MiMC/hash `com = H(x)`

| 项目 | 结论 |
| --- | --- |
| hiding | **无**。低熵 `x` 可被枚举；相同 `x` 跨步产生相同 `com` |
| binding | MiMC 抗碰撞假设（参数 VERIFIED，安全裕度 UNKNOWN） |
| opening verification | 从 `x` 重算 `H(x)` 并比较；无可盲化随机量可验 |
| `Fr` 电路兼容性 | 完全兼容；MiMC gadget 已有（VERIFIED，Correction-2 §E1） |
| 随机量要求 | 无 `s_i`；因此**不满足**“盲化随机量独立”的角色分离要求 |
| 绑定同一 SNARK witness | 电路内用同一 `W_pre,i` 线值重算即可，但无 hiding |
| artifact 可复用实现 | hash gadget 有，`Commitment` 接口无（VERIFIED，§E2） |
| 判定 | 仅可用于 **L1**；不可作为 L2（`BLOCKED`） |

### 1.2 随机化 MiMC/hash `com = H(x‖s_i)`

| 项目 | 结论 |
| --- | --- |
| hiding | **启发式**：字典攻击需同时猜 `s_i`，但无从 MiMC 抗碰撞到标准 hiding 的规约 |
| binding | 依赖 `s_i` 不可替换、不可重采样；否则 prover 可枚举 `s_i` 改 `com` 与 ρ（grinding） |
| opening verification | 电路内以私有 witness `(x, s_i)` 重算 `H(x‖s_i)` 并等于公开 `com_i` |
| `Fr` 电路兼容性 | 兼容；`s_i` 作为域元素 witness 并受位宽约束 |
| 随机量要求 | `s_i` 秘密、MPC 联合生成、域均匀、每步独立、与 `r_tape,i` 独立且带 MAC |
| 绑定同一 SNARK witness | 可：ORAM 约束与承诺重算共用同一 `W_pre,i` 线值（CONSTRUCTED 规则） |
| artifact 可复用实现 | hash gadget 有；承诺封装与认证随机源无（BLOCKED） |
| 判定 | **CONDITIONAL / BLOCKED**：接口形态可写，但 hiding 无安全定义依据 |

### 1.3 Pedersen-like `com = g^x h^{s_i}`

| 项目 | 结论 |
| --- | --- |
| hiding | `s_i` 域均匀时 perfect/statistical hiding（标准结论，INFERRED） |
| binding | 离散对数假设下计算 binding（INFERRED） |
| opening verification | 验证 G1 方程 `g^x h^{s_i} = C`；`x` 为单域元素时需先 `d=CRH(x)` 再承诺 `d` |
| `Fr` 电路兼容性 | **不匹配**：承诺值在 G1（坐标域 `Fq≠Fr`），`Fr` 电路验证需非原生 `Fq` 算术；内曲线方案需 artifact 不存在的 gadget（Correction-2 §E4） |
| 随机量要求 | `s_i` 域均匀、秘密、MPC 联合生成、每步独立 |
| 绑定同一 SNARK witness | 若电路内验 G1 方程，可共用 `x` 线值；但需非原生算术 → BLOCKED；若外部验证，需 Q3(c) 桥接接口 → BLOCKED |
| artifact 可复用实现 | gadget 目录 19 文件无 Pedersen/Commitment（VERIFIED，§E2） |
| 判定 | 安全定义最强，但**固定后端不可用** → CONDITIONAL / BLOCKED |

### 1.4 对照表

| 项 | 确定性 MiMC | 随机化 MiMC | Pedersen-like |
| --- | --- | --- | --- |
| hiding | 无 | 启发式，无规约 | perfect/statistical |
| binding | CRH | CRH + `s_i` 不可替换 | DL |
| opening verification | 重算 `H(x)` | 重算 `H(x‖s_i)` | 验 G1 方程 |
| `Fr` 兼容 | 是 | 是 | 否 |
| 随机量 | 无 | `s_i` 秘密联合生成 | `s_i` 域均匀联合生成 |
| 同 witness 绑定 | 可（无 hiding） | 可（规则层） | 需非原生/桥接 |
| artifact 实现 | hash 有 / 承诺无 | hash 有 / 承诺无 | 无 |

---

## 2. 禁止推断清单（逐条拒绝）

1. **确定性 hash 自动具有 hiding** → 拒绝。`H(x)` 对低熵 `x` 可直接枚举。
2. **秘密随机数自动使 hash commitment 获得标准 hiding** → 拒绝。`H(x‖s)` 的 hiding 无形式化规约；只能称启发式。
3. **Pedersen 的理论安全性自动意味着固定后端可直接使用** → 拒绝。`Fr` 电路与 G1 的 `Fq` 坐标不匹配，artifact 无曲线 gadget。
4. **外部验证承诺自动意味着 SNARK witness 与承诺对象一致** → 拒绝。必须有电路内同线值约束（`transcript-order.md` Q2）或显式桥接（Q3(b)(c)）。

本轮**不引入新的承诺方案候选**：上述三类已覆盖任务要求，且没有一类在固定 artifact 上同时满足 hiding、binding、opening verification 与后端兼容。强行选定会违反“不得把纸面构造写成已实现”。

---

## 3. 与 SNARK witness 的绑定结论

| 场景 | 绑定是否成立 | 状态 |
| --- | --- | --- |
| 电路内重算 `com_i`，与 ORAM 约束共用 `W_pre,i` 线值 | 规则层成立；`s_i` 为私有 witness 线 | CONSTRUCTED；方案安全性 BLOCKED |
| 电路外验证承诺，无桥接 | **不成立** | BLOCKED |
| 电路外 Pedersen 验证 + 电路内同 `x` | 需非原生 `Fq` | BLOCKED |
| `Encode` 覆盖 8 字段全部 | 必须；省略任一字段则绑定不完整 | CONSTRUCTED 规则 / BLOCKED 实现 |
| `ictx_i` 含 step/program/circuit/version/旧根/attempt | 是 | CONSTRUCTED |

---

## 4. 本轮判定

- L1 状态根：可继续使用（binding 足够）。
- L2 `com_i`：**BLOCKED**，不存在可审查的具体候选；随机化 MiMC 只有启发式 hiding，Pedersen 后端不兼容且无实现。
- L3 独立随机带承诺：撤回，已并入 L2 消息字段；生成接口 BLOCKED。
- 外部承诺 ↔ SNARK witness 一致性：**BLOCKED**。
- 不因 artifact 缺少 gadget 而选 NO_GO；这是实现阻塞，不是协议矛盾。
