# ABA-03-D2 / Phase 1：共享隐藏承诺候选比较

> 固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`；起点 `b8a907b8…`。
>
> 只读源码 + 设计评估。不实现 gadget、不改源码、不解除任何 HOLD。
>
> 标签：`VERIFIED` = 固定 commit 源码事实；`CONSTRUCTED` = 本轮候选构造；`INFERRED` = 由源码/密码学定义推导；`UNKNOWN` = 缺证据；`BLOCKED` = 现有接口无法支撑结论。
>
> **本文件不把「两个电路输出相同哈希」等同于「私有地址同一性已获安全证明」**；同一性成立所需的密码学假设与电路约束在 `circuit_interface.md` 逐条给出。

---

## 0. 源码取证口径（新增证据，非上轮推论升级）

| 证据 | 固定 commit 路径 / blob SHA | 原始行号 | 能支持的结论 | 不能推出的结论 |
| --- | --- | --- | --- | --- |
| MiMC hash gadget | `CompatCircuit/CompatCircuitProgramming/Gadgets/MimcHashGadget.cs`，blob `bf11f4af5a46…` | L5-31 | 迭代结构 `k₀=0; kᵢ₊₁=Enc_{kᵢ}(preimageᵢ)`，输出 `k_n`；`VERIFIED` | 不能推出 collision resistance / hiding（源码无归约） |
| MiMC encrypt gadget | `.../MimcEncryptGadget.cs`，blob `8dd4c8aa6cf5…` | L6-60 | SBox=7（`DefaultSBox`，L14）；每轮 `x=(x+k+cᵢ)^7`，末 `+k`（L38-55）；轮常数硬编码 **65 个**（L12-13），注释称随机选取（SHA-3 举例）但源码未给出可复核生成过程（L10）；参考 zokrates-mimc（L36） | 不能推出轮常数确由 SHA-3 生成；不能推出对已知/选择攻击的安全性 |
| 既有 MiMC 调用点 | `ZkVmExecutorCircuitBoardGenerator.cs:1009-1017`（`out_hash_mem_trace`）、`InstructionFetchCircuitBoardGenerator.cs:215-235`（逐行 opcode 哈希） | — | gadget 在 VM/取指电路已被实际使用（`VERIFIED`） | 不能推出这些哈希是承诺；其 preimage 含 step 与随机 `enc_key`，是逐步摘要（ABA-03 §A2） |
| Pedersen commitment | `collaborative-zksnark-mod/crypto-primitives/src/commitment/pedersen/mod.rs`，blob `545309da29b7…` | L18-30, L45-110 | 标准 Pedersen 结构：`C = CRH_gens(input) + Σbit·h_bit`，输出 `C::Affine`（群元素）；generator 由 setup 用 `generator_powers`/`create_generators` 生成（L57-65） | 不能推出它接入 CompatCircuit 证明路径；不能推出生成器被 verifier 固定 |
| Pedersen 约束 gadget | `.../commitment/pedersen/constraints.rs`，blob `83ddcab16630…` | L16, L30, L44-76 | 约束域 `ConstraintF<C> = C::BaseField::BasePrimeField`（L16），输入 `UInt8`，输出群变量 `GG`（L53-61）；需 `CurveVar`/`GroupOpsBounds`（L48-51） | 不能推出与 C# 生成的 Fr-wire R1CS 兼容；不能推出低成本 |
| 证明路径引用 | `plonk.rs`（blob `ae077b0a…`）、`client.rs`（blob `44504e7c…`） | `plonk.rs:293-315` 全文 | 检索 `commitment/pedersen/crypto-primitives` 无命中；`client.rs` 的 `commitment` 命中均为 KZG/Marlin 多项式承诺与 Merkle **transcript**（L188-190、L256/309、L762-858），非 Pedersen 消息承诺 | 不能推出证明路径支持 Pedersen 消息承诺（证据为「未发现」） |
| 随机数来源 | `ZkProgramExecutor.cs:61` | L61, L159/288/540 | `inEncKey = FieldFactory.Random()`，宿主进程现场随机，逐电路私有输入并在宿主比对 `out_hash_enc_key`（L176-181 等） | 不能推出该值是 MPC 认证随机或可复用于承诺 openings |

---

## 1. 候选 A：MiMC 类域哈希承诺

候选形式：`com = H(domain || context || addr || r)`，其中 `H` 用固定 commit 的 `MimcHashGadget` 链式压缩（§0）。

### 维度分析

| 维度 | 结论 | 标签 |
| --- | --- | --- |
| **Binding** | 若把 `H` 当作随机预言机（RO），则找到 `H(x)=H(x')` 需约 `√p` 次（生日界）；若把 MiMC 当作**理想密码/块密码**并采用 Davies-Meyer 类结构，有经典哈希构造论证。但固定 commit 的 `MimcHashGadget` 是 `kᵢ₊₁=Enc_{kᵢ}(mᵢ)` 链式结构，源码未给出任何安全归约或参数分析文档，**不存在公开可验证的 binding 证明**可引用。65 轮 + 域约 253 bit 使朴素碰撞不可行是合理工程判断，但**不是被证明的 binding** | `INFERRED`（结构/轮数）+ `UNKNOWN`（归约） |
| **Hiding** | 普通哈希承诺的 hiding **依赖 `r` 的高熵**；若 `r` 均匀域元素，观察者对 `H(domain‖context‖addr‖r)` 的候选 `addr` 仍需猜 `r`，近似隐藏；若 `r` 可预测/复用/低熵，则小地址域可直接枚举 `addr` 命中承诺。源码 gadget 本身**不提供** hiding 属性证明 | `CONSTRUCTED` + `INFERRED`（条件于 `r`） |
| **小地址域安全性** | 地址空间 `[0,n)`，`n≤Nmax` 很小且公开 → 若缺少高熵 `r`（或 `r` 被复用/可预测），攻击者枚举全部 `addr` 并计算承诺即可恢复地址。隐藏性**完全系于 `r`**，不是哈希函数的固有属性 | `INFERRED` |
| **随机数要求** | `r` 应是**接近均匀的域元素**，每次承诺唯一、不可预测、不可重放；若 `r` 在多处复用，同一 `addr` 会给出相同 `com`（反而利于链接） | `INFERRED` |
| **域兼容性** | gadget 全程在 `F_p`（BLS12-377 标量域）内，输入输出均为域元素（`MimcHashGadget.cs:5-31`）；与 C# Fr R1CS 与 Rust `MFr` PLONK 值域一致 | `VERIFIED` |
| **电路成本** | 每 preimage 项 1 次 `MimcEncryptGadget`；每次加密 65 轮，每轮 `FieldAdd(3) + FieldConstPow(7)`，末 1 次 add（`MimcEncryptGadget.cs:38-55`）。约束**类型**可确认（加法、幂 7）；具体约束门数无 gadget 级实测 → `UNKNOWN` | `VERIFIED`（类型/轮数）+ `UNKNOWN`（门数） |
| **MPC 兼容性** | 加法与幂运算在 additive-share 上可做（`exp-doram-06` B.1/B.4）；无需新 share 类型或群运算。但 `r` 的认证/不可预测性在 additive-only 下无保证（见 `opening_and_randomness.md`） | `INFERRED` + `UNKNOWN`（随机性） |
| **实现证据** | gadget **已有并已用**（VM trace 哈希、逐行 opcode 哈希）；作为**承诺**使用是新的接口设计 | `VERIFIED`（gadget）/ `CONSTRUCTED`（承诺用法） |
| **多字段编码歧义** | `H` 对 `preimage_0..n` 逐项压缩且各项都是域元素；若 `domain/context/addr/r` 拼接方式不固定（例如 `(domain,context)` 与 `(domain‖context)` 可产生同一序列），会出现编码歧义。源码没有结构化 domain separator，须在设计中显式固定字段顺序与长度 | `VERIFIED`（无内建分隔）+ `INFERRED`（风险） |

**A 小结**：域兼容、电路已有、MPC 友好是其优势；但 binding 无公开归约、hiding 全系于 `r`、无内建 domain separation。作为承诺的安全性**未被证明**，只能作为候选。

---

## 2. 候选 B：Pedersen 类承诺

候选形式：`C = addr·G + r·H`（群元素）。

### 维度分析

| 维度 | 结论 | 标签 |
| --- | --- | --- |
| **Binding** | 在离散对数假设下，Pedersen 是完美 binding：不同 `(addr,r)` 给出同一 `C` 意味着找到 `G/H` 的 DL 关系。前提：`G,H` 的生成无已知陷门（setup ,potentially toxic waste）。固定 commit 的 `setup` 用 RNG 生成 generators（`pedersen/mod.rs:50-65`），**是否可验证生成、是否被 verifier 固定，源码未给出** | `INFERRED`（标准性质）+ `UNKNOWN`（生成器信任） |
| **Hiding** | Pedersen 在 `r` 均匀时信息论 hiding（完美隐藏）——这是相对 MiMC 的实质优势，尤其适合小地址域。前提仍是 `r` 均匀且不可预测 | `INFERRED`（标准性质）+ 条件于 `r` |
| **小地址域安全性** | 即使 `addr` 可枚举，均匀 `r` 使 `C` 在群中均匀分布，隐藏性不依赖地址空间大小（优于哈希承诺） | `INFERRED` |
| **随机数要求** | `r ∈ C::ScalarField`（`Randomness<C>(pub C::ScalarField)`，L30）；必须均匀、唯一、不可预测。源码 `UniformRand::rand` 存在（L32-37），但**该随机如何进入 MPC/电路 witness 未被证明路径覆盖** | `VERIFIED`（类型）+ `UNKNOWN`（路径） |
| **域兼容性** | 约束域 `ConstraintF<C> = C::BaseField::BasePrimeField`（`pedersen/constraints.rs:16`），输入是 `UInt8`（L60），输出 `GG: CurveVar<C, ConstraintF<C>>`（L53）。这与 C# 生成的 **Fr-wire R1CS** 和 `plonk.rs` 的 `MFr` PLONK **不是同一 wire/域模型**；需要额外的域/群适配 | `VERIFIED`（域定义）+ `INFERRED`（不兼容） |
| **电路成本** | 约束 gadget 需 `CurveVar`/`GroupOpsBounds`（L48-51），涉及群加法与标量乘的 R1CS 约束；是否属于原生域运算：**否**（群运算非 Fr 原生）。具体门数 `UNKNOWN` | `VERIFIED`（需群运算）+ `UNKNOWN`（门数） |
| **MPC 兼容性** | 当前证明路径是 additive-only、无 MAC、无 Beaver 文件（`exp-doram-06` B.1-B.3）；群元素的 MPC share 类型 `SpdzGroupShare` 存在但序列化全 `unimplemented!()`（B.2）。把 Pedersen 承诺送入现有 MPC PLONK 需要新 share 类型与群运算支持 | `VERIFIED`（现状）+ `BLOCKED`（当前路径承载） |
| **实现证据** | 实现**存在于固定 commit**（`crypto-primitives`，`(crh|commitment)/pedersen`，blob 见 §0），但 `plonk.rs` 不引用它，`client.rs` 无 CompatCircuit 分支调用 → **存在但未接入证明路径** | `VERIFIED`（存在 + 未接入） |

**B 小结**：标准密码学性质优于哈希承诺（信息论 hiding、DL binding），且 gadget 实现已在固定 commit 内；但其约束域/群变量模型与 CompatCircuit→PLONK 的 Fr-wire 通路不兼容，接入需要新 share 类型、群运算与可信生成器，**当前路径无法直接承载**。不得因理论性质优良就写成低成本可实现。

---

## 3. 候选 C：其他候选

本轮**不引入其他承诺方案**。理由：任务要求只在有明确理由时引入，且 A/B 已分别覆盖「域内哈希」与「群内承诺」两类根本不同路径；追加名称不会改变本轮四个核心问题（binding/hiding/随机数/上下文）的结论，只增加未经源码核实的推测。

---

## 4. 八维度对照表（同粒度）

| 维度 | A. MiMC 哈希承诺 | B. Pedersen 承诺 |
| --- | --- | --- |
| Binding | `INFERRED`（轮数/结构）+ `UNKNOWN`（无公开归约） | `INFERRED`（DL 假设）+ `UNKNOWN`（生成器信任） |
| Hiding | 条件于 `r` 高熵，`CONSTRUCTED`+`INFERRED` | 信息论 hiding（条件于均匀 `r`），`INFERRED` |
| 小地址域安全性 | 依赖 `r`，否则枚举攻击，`INFERRED` | 均匀 `r` 下不依赖地址大小，`INFERRED` |
| 随机数要求 | 均匀域元素、唯一、不可预测，`INFERRED` | `ScalarField` 均匀随机，`VERIFIED`（类型）+ `UNKNOWN`（路径） |
| 域兼容性 | Fr 原生，`VERIFIED` | 群基点域 + `UInt8`/`CurveVar`，`VERIFIED`（不兼容现状） |
| 电路成本 | 类型可确认（65 轮 ×(add+pow7)），门数 `UNKNOWN` | 需群运算，`UNKNOWN` |
| MPC 兼容性 | additive 可做运算，`INFERRED`；随机性 `UNKNOWN` | 需群 MPC share，`BLOCKED`（当前路径） |
| 实现证据 | gadget 已有且已用，`VERIFIED` | 实现存在但未接入证明路径，`VERIFIED` |

---

## 5. 本阶段结论

- **A（MiMC）**：路径最短（域内、gadget 已有），但 binding 无公开归约、hiding 全系于随机数、无内建 domain separation——安全语义不完整。
- **B（Pedersen）**：密码学性质最干净（信息论 hiding + DL binding），且 gadget 在固定 commit 内存在；但与当前 Fr-wire / additive-only PLONK 路径**域与 share 模型不兼容**，接入属于显著改造（见 `circuit_interface.md`、`decision.md`）。
- 两者都**不能**在本阶段写成"已具备共享隐藏承诺"。binding、hiding、随机数、域/接口四项需分别闭合；下一阶段（`opening_and_randomness.md`、`context_and_replay.md`）逐项处理。
