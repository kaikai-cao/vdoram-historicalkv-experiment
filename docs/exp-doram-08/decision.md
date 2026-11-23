# EXP-DORAM-08 — 最终决策

## 决策：`CONDITIONAL_PASS`

四选一中的唯一结论。不是 `BLOCKED_SOURCE_EVIDENCE`（关键 gadget 与执行路径均已取得并 VERIFIED）；不是 `NO_GO_COST_ADVANTAGE`（源码推导权重下 Fetch 相存在真实原语优势）；不是 `PASS_TO_MPC_MICROBENCHMARK`（优势依赖未证实条件，且当前后端不具备承载路径，见下）。

## Q7 逐项回答

**1. E1 的优势是否只存在于抽象扫描次数？**
不只。在当前执行器下，E0 每行与 E1 每槽都执行同一 `FieldEquals`（389 次 Beaver 乘法），因此抽象扫描数 `t → n` 的降低**线性映射**为秘密乘法数的降低：`393t−2 → 393n−2`。但优势**限于 Fetch 相**：`MemoryTraceProve` 对相同 trace 行执行相同 MiMC/门，R1CS 侧 E0=E1，端到端优势未被证明。

**2. 在合理的 MPC 原语成本参数下，优势是否仍成立？**
在当前源码能证实的参数（`c_eq=389, c_sel=1`）下成立：10/16 格（`T/n≥4`）E1 更便宜。但敏感性给出明确反例：`c_eq/c_sel=1`（比较变便宜）且 `c_upd/c_sel=100`、STORE=90% 时只剩 3/16 格胜（中位 9.53× 反劣）。所以**优势是条件性的，不是权重无关的真理**。

**3. 哪些参数范围内优势可能成立？**
- `T/n > 2`（只读／共享 eq 的理论边界；已测格中体现为 `T/n≥4` 全胜）；
- `sep_eq` + 全 STORE 时 `T/n ≳ 4`；
- 地址域确为有界 `[0,n−1]`，`n` 固定且小于 `T/2`；
- 每行/槽比较显著贵于每槽更新（当前源码事实）；
- 只比较 Fetch 相秘密乘法数，不把 Prove 侧计入收益。

**4. 哪些情况会让 E1 反而更贵？**
- `n ≥ T/2`（`n=T/2` 恰为只读交叉点，成本相等）；
- 比较原语被优化（如一次位分解摊薄 n 次比较）而条件更新变贵；
- 独立重算 eq + 高 STORE 比例（最坏 63.77×）；
- 端到端计入相同的 Prove 成本后，Fetch 收益被摊薄甚至消失；
- 目标地址并非有界域（R1 审计：目标系统全域有界 = UNKNOWN）。

**5. 当前是否值得进入独立 MPC 微基准实验？**
**有条件值得，但仅限最小化原语微基准**：测 `FieldEquals`、`LowBit`、`SelectCompose`、条件更新在当前执行器下的相对权重，以验证 `c_eq/c_sel=389` 这一主导假设。不值得现在做完整 E1 执行实现或性能结论，因为：①EXP-DORAM-06 已证当前 C#→Rust witness 路径无 SPDZ MAC/auth，微基准只能测非认证执行路径；②Prove/R1CS 侧成本 UNKNOWN 且为共同项；③`share_eq` 可行性无电路证据。若该微基准证实权重假设，才具备重新评估的条件。

**6. 现有 VDORAM 后端是否能直接承载该方案？**
不能。当前 `CompatCircuit` JSON witness 走 `MF::from_add_shared`，不带 MAC；`MpcValue` 只有 `{Field, bool}`，无认证标签；EXP-DORAM-06 判定 `NO_GO_CURRENT_ARCHITECTURE`。E1 需要新的秘密状态表示与认证更新契约，属后端契约重做，不是 adapter。

**7. 本轮对研究价值的最终回答**
影子表是**有界地址域下 Fetch 相的真实原语成本优化**，不是 Python 参考模型假象；但它不是端到端的证明系统优化，也不被当前后端直接支持。是否值得继续，取决于一个尚未验证的重量级假设：每槽比较远贵于每槽更新。

## 已证实 / 条件成立 / 未知 / 阻断

| 类别 | 内容 |
| --- | --- |
| **已证实（VERIFIED/DERIVED）** | Fetch 每行一次 `FieldEquals` 无提前退出；`FieldEquals=389` Beaver 乘法（含 386 次秘密求逆）；`LowBit=3k−2`；`SelectCompose=k`；Fetch 全电路 `393t−2`；秘密乘法走 Beaver 三元组 + 1 barrier/次；串行执行无批处理；E0/E1 trace 相同 → Prove 侧相同 |
| **条件成立（ASSUMED 明确标注）** | `share_eq` 可复用同轮 eq（`c_upd=1`）；所有乘法等权；有界地址域（R1: CONSTRUCTED/UNKNOWN） |
| **未知（UNKNOWN）** | R1CS 约束数 / `MpcCircuit→R1CS` 映射；`r_setup,r_output`；在线字节数；Rust `inv_pair` 是否可用于 Fetch 路径（当前证据指向“不可”）；位分解摊薄比较的可行性；Prove 侧绝对成本 |
| **阻断（BLOCKED）** | 当前后端无 SPDZ MAC/auth 数据，不能承载认证秘密状态；目标系统全域有界未证 |

## 下一阶段允许做什么

只允许：在当前 C# 执行器上做**最小化原语权重微基准**（比较/低比特/选择/条件更新），并把结果写为新实验；可并行审计 `share_eq` 的电路可行性。不得把微基准结果升级为论文性能结论。

## 明确不做

不启动 EXP-DORAM-09；不实现完整 E1 电路；不做 Path ORAM / AVL / DPF / Merkle；不实现真实 SPDZ；不改上游、C#/Rust 主执行路径或 witness 接口；不修改 R1/历史 CSV；不用 R1CS 约束数冒充秘密乘法数；不用 Python 时间冒充 MPC 时间；不在权重未知时宣称 E1 普遍更优。
