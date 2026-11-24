# ABA-03-D1 / Phase D：C1/C2/C3 的泄露与安全边界

> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35…`；起点 `f3933474…`。只读设计评估，不实现电路、不改 HOLD。
>
> 标签：`VERIFIED` = 固定源码/明确安全定义直接支持；`CONSTRUCTED` = 本轮候选设计（不是已实现性质）；`INFERRED` = 由源码事实推导；`UNKNOWN` = 缺必要证据；`BLOCKED` = 现有架构接口无法支撑结论。
>
> 重要原则：**承诺方案的设计目标不等于已实现的安全性质**。本文所有 C2/C3 的隐藏、防重放、完整性均为候选/推论，不写成已证明。

---

## 0. 分析方法

对 C1（直接公开地址）、C2（共享隐藏承诺）、C3（证明组合/递归）逐一分析八个维度。分析基于两类事实：

- 源码事实：地址/pc/opcode 当前均为私有 witness 或私有输出（`MemoryTraceFetch...cs:42`、`ZkVmExecutor...cs:996/1006`、`ABA-03-C2 §3`），跨电路仅宿主哈希 `throw`（`ZkProgramExecutor.cs:302-332,551-583`），vk 现场生成、无独立 verifier（`ABA-03-C2 §A5-A8`）。
- 候选设计属性：见 `design_options.md`。

四层信任边界继续沿用并**不得互相替代**：executor 本地检查 / MPC 参与方间检查 / proof 内约束 / 最终 verifier 检查（`ABA-03-C2 §3` 表）。

---

## 1. 逐维度分析

### D1. 地址机密性

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| C1 | **无地址机密性**。真实步 `reg0` 明文进入 public inputs（`design_options.md` §1），verifier 及任何观察者可见真实内存访问地址 | `INFERRED` |
| C2 | 目标为隐藏地址（承诺内隐藏）；但 hiding 强度未证（MiMC 输入熵/域大小；Pedersen 离散对数假设） | `CONSTRUCTED` + `UNKNOWN` |
| C3 | 若地址不入公开 statement 则可隐藏；但公开 statement 定义未定，递归电路是否间接泄漏未核验 | `UNKNOWN` |

### D2. 访问事件类型（`is_mem_op`）泄露

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| C1 | `is_mem_op` 作为公开字段 → 事件类型可见（哪些步是真实 Load/Store） | `INFERRED` |
| C2 | 若 `is_mem_op` 为公开分类字段（verifier 需它区分真实/dummy 承诺语义），则类型可见；若隐藏则 verifier 无法分类 | `CONSTRUCTED`（两难） |
| C3 | 类型在递归内验证，是否公开未定 | `UNKNOWN` |

**说明**：事件类型本身的可见性是 VDORAM 访问模式泄漏的一部分。当前上游 trace 中 `is_mem_op/is_mem_write` 是电路派生私有输出（`ZkVmExecutor...cs:968-981`），外部只见哈希（ABA-03 §A2）。任何要求公开事件类型的方案都改变这一现状。

### D3. step / PC / opcode 可见性

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| C1 | 三者作为公开字段 → 可见；step 当前已公开注入（`:393-395`），PC 当前私有（`:134-136`）、opcode 选中行当前私有（`:231-241`），提升为公开是新增 | `VERIFIED`（现状）+ `INFERRED`（提升后） |
| C2 | 三者进入承诺则隐藏；但 verifier 需某种 step 索引做对齐，若 step 公开则部分可见 | `CONSTRUCTED` + `INFERRED` |
| C3 | 由顶层 statement 决定，未定 | `UNKNOWN` |

### D4. 跨步链接与跨执行实例链接

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| C1 | 公开 step + 地址 → 可直接跨步链接形成访问序列；若无实例 nonce → 可跨执行实例链接 | `INFERRED` |
| C2 | 承诺若含 step 但不含实例 nonce → 同地址在不同执行可生成相同承诺（若 `r_i` 也不变）→ 跨实例链接风险；需实例 nonce 或每实例新随机 | `CONSTRUCTED` + `INFERRED` |
| C3 | 未定 | `UNKNOWN` |

### D5. 承诺重放 / 跨程序替换 / 跨 proof 拼接

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| C1 | 无承诺；但公开值可被重放——若 verifier 不锚定程序身份与实例，来自另一程序的公开字段可通过比较 | `INFERRED` |
| C2 | 承诺须含 `step_i`、程序身份字段与实例 nonce 才能防跨步/跨程序/跨实例重放；否则可复用同一 `com_i`。是否纳入取决于承诺内容设计与 verifier 固定值 | `CONSTRUCTED` + `INFERRED` |
| C3 | 顶层 statement 须含程序身份与实例锚点；未定义 | `UNKNOWN` |

**P1-A 的前置作用**：固定完整 opcode table 比较（`../aba-03-c2/verifier_interface_audit.md` §2）能缓解「跨程序替换」，但**不**缓解 C2 承诺重放（承诺内是否含程序身份是独立设计问题）。二者不可互相替代。

### D6. prover 选择性中止 / 重试 / 重新初始化

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| 通用 | 当前 vk 由 prover 进程 `test_rng()` 现场生成（`plonk.rs:302-304`），prover 可重新 setup 换 vk；无独立 verifier 固定 vk → prover 可反复重试直到得到有利 proof/公开值。这是**所有方案共有的前置缺口**，不因 C1/C2/C3 选择而消失 | `VERIFIED`（现场 vk）+ `INFERRED`（重试能力） |
| C1 | 公开地址由 prover 生成；配合现场 vk，prover 可重试 | `INFERRED` |
| C2 | 若 `r_i` 由 prover 选，可重采样承诺重试；若 `r_i` 由 verifier/MPC 固定则缓解 | `INFERRED` + `UNKNOWN`（机制未定） |
| C3 | 递归 setup 同样可能现场生成；未核验 | `UNKNOWN` |

### D7. dummy Fetch 与真实访问混淆

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| 通用 | Prove 电路忽略 `is_mem_op`（原始 L164-165）；trace 中真实行与 `p−1` 行共存；`is_mem_op` 为电路派生私有输出（`:968-976`），verifier 不可见明文 | `VERIFIED` |
| C1 | 公开 `is_mem_op` 与 `addr` → verifier 可直接区分（真实=`addr∈[0,n)`，dummy=`p−1`）；但要求 prover 输出的分类正确需额外约束证明分类来自 opcode | `INFERRED` |
| C2 | 真实/dummy 承诺语义不同，但 verifier 需公开分类或分类承诺；若分类仅由 prover 声明则可被操纵 | `CONSTRUCTED` + `INFERRED` |
| C3 | 递归内验证分类，未定义 | `UNKNOWN` |

### D8. 证明不完整 / 漏证 / 重复证明 / 乱序证明（B4 完整性）

| 方案 | 结论 | 标签 |
| --- | --- | --- |
| 通用 | 单步地址相等 ≠ 轨迹完整（`p2_binding_semantics.md` §3 B4）；上游无 verifier 可见的事件计数/顺序约束，step 由宿主公开注入（`:393-395`），跨电路靠宿主哈希 `throw` | `VERIFIED`（缺失）+ `INFERRED` |
| C1 | 公开 step 序列可做单调性检查，但需额外约束「无遗漏/无重复」；公开字段本身不保证 | `INFERRED` |
| C2 | 承诺逐 step 但无计数/顺序承诺则仍可漏证；需事件计数与 halt 边界 | `CONSTRUCTED` + `INFERRED` |
| C3 | 理论上可在递归电路内强制完整性，但当前无接口证据 | `UNKNOWN` |

---

## 2. 横切结论

1. **所有方案共享两个前置缺口**：独立 verifier + 固定 vk（否则 prover 可重试/重 setup）、P1-A 固定程序表（否则可跨程序替换）。这两个缺口不因 P2 方案选择而闭合。
2. **地址机密性与可验证性存在张力**：C1 用隐私换简单可验证；C2/C3 保隐私但引入承诺/递归的隐藏性质与随机性生命周期问题，关键项 `UNKNOWN`。
3. **B4 轨迹完整性在所有方案中都不是自动获得的**：必须显式设计事件计数、顺序、halt 边界约束；本文仅为候选，未实现。
4. **不得把宿主哈希检查或逐行哈希当作隐藏承诺或 verifier 绑定**：`out_hash_mem_trace`（含 step/随机 enc_key，`:1009-1017`）与宿主多重集比对（`:551-583`）都不满足稳定承诺/公开可验证约束的要求（`VERIFIED` 区分依据）。
5. **当前没有任何安全性质被证明已实现**：本文所有 C1/C2/C3 结论为 `INFERRED`/`CONSTRUCTED`/`UNKNOWN`/`VERIFIED`（仅指源码事实与明确缺口），不含「方案已安全」的声称。
