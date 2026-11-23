# backend-facts.md — 当前 SNARK 后端事实（承诺构造所需）

> 2026-11-23 · 起点 `2556ece2fd040978ad89fd9ed61bd1bc15243947` · 固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d3`。
> 标记：**VERIFIED** 固定源码/原始论文一手文本直接支持 · **INHERITED** 从既有报告继承但未在本轮重新验证 · **INFERRED** 有依据推导 · **UNKNOWN** 证据不足 · **BLOCKED** 当前接口缺失。
> 本轮**纠正**一处长期继承的事实错误：电路域不是 BN254，而是 **BLS12-377 标量域**。

---

## 0. 最重要的纠正：电路域是 BLS12-377 Fr，不是 BN254 Fr

Correction-2 §E4、Correction-3 §4、Correction-4 §1 都写「BN254 `Fr`」。本轮从固定 artifact 的**一手源码**核对，该结论错误。

- **来源**：`BDS-SDU/vdoram-artifacts @ 10c90d3`，
  `CompatCircuit/CompatCircuitCore/GlobalConfig/ArithConfig.cs`。
- **原文**（逐字）：
  ```
  FieldSize => _fieldSize ??= BigInteger.Parse(
      "12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001".ToUpper(),
      NumberStyles.AllowHexSpecifier); // BLS12-377
  BitSize => _bitSize ??= Convert.ToInt32((FieldSize - 1).GetBitLength()); // 253
  ```
- **交叉验证**：该十六进制串精确等于 BLS12-377 标量域 `r`，见 CycloneMSM（ePrint 2022/1396, §2.1）逐字给出
  `r = 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`；
  本轮用 Python 复算 `(r−1).bit_length() = 253`，与源码注释一致。
- **直接支持**：MPC 与 R1CS 的算术域 `F = Fr(BLS12-377)`，`|F| = r ≈ 2^253`，位宽 `ArithConfig.BitSize = 253`。
- **状态**：**VERIFIED**（源码 + 原始论文 + 可复现算术）。

**对既有结论的连带影响（本轮只标注，不重算）**：

| 继承结论 | 旧值 | 纠正后 | 说明 |
| --- | --- | --- | --- |
| 域大小 | `≈2^254`（BN254） | `≈2^253`（BLS12-377） | VERIFIED |
| B1 单挑战 soundness | `≤2^-85` | `≈2^-84` | `enc<2^169` 不变，`2^169/2^253=2^-84`；**域缩小 1 bit，不是放宽安全定义** |
| B1 双挑战 soundness | `≈2^-170` | `≈2^-168` | 同上；Correction-3 已把 `2^-170` 条件化，本轮只是把域参数改对 |
| grinding 余量 | `q_H·2^-170` | `q_H·2^-168` | `q_H=2^128` ⇒ `≈2^-40`；仍需 `k≥4` 或不可 grind 随机带 |

> `enc < 2^169` 的上界来自 Correction-3 的 `L=20,B=128` 编码，本轮**不重算**该编码或约束成本；此处仅把域大小这一“单位”改对。

---

## 1. 曲线与证明系统

| 事实 | 内容 | 证据 | 状态 |
| --- | --- | --- | --- |
| 实验曲线 | BLS12-377 | VDORAM 论文 ePrint 2025/039 §Implementation 逐字：「The elliptic curve used in our experiment is BLS12-377, and the collaborative zkSNARKs variant employed is Plonk」 | VERIFIED |
| 协作证明变体 | **Plonk**，不是 Groth16 | 同上；prove 脚本 `client ... -d PlonkCompatCircuitMultiParty`（`collaborative-zksnark-mod.md` L57–58、`prove-r1cs-multiparty-inner.py` L50） | VERIFIED |
| Groth16 verifier 快照 | 存在但属另一模块 | `collaborative-zksnark-mod__groth16__src__verifier.rs`：泛型 `verify_proof<E: PairingEngine>`，`public_inputs: &[E::Fr]`，标准单 proof 验证（L27–61） | VERIFIED（文件存在）/ 与 Plonk 主路径关系 UNKNOWN |
| 证明系统泛型性 | verifier 不写死曲线 | `E::PairingEngine` 泛型，曲线由调用端实例化；本仓库快照未见实例化文件 | VERIFIED |
| 共享方案 | 论文实现基于 SPDZ / GSZ  lifts；authenticated share 含 `val + mac` | 协作 zkSNARK 实现论文 ePrint 2021/1530 §6 Fig.6（`AuthShare { val: AddShare, mac: AddShare }`，MAC 随公开常数由各方更新） | VERIFIED（论文文本） |

> 注意：VDORAM 主路径是 **Plonk + BLS12-377**，而本仓库 `groth16/verifier.rs` 是泛型 Groth16 快照。两者是否为同一部署版本的两个入口，本仓库证据无法判定 → **UNKNOWN**。本轮所有“电路内验证”讨论以 `Fr(BLS12-377)` 上的 R1CS/Plonkish 算术为准。

---

## 2. R1CS 域与 witness/公开输入接口

- **来源**：`CompatCircuit/CompatCircuitCore/Arithmetic/Field.cs`、`GlobalConfig/ArithConfig.cs`、
  `CollaborativeZkVm/ZkPrograms/ZkProgramExecutor.cs`、`R1csCircuits/R1csCircuitWithValues.cs`。
- **事实**：
  - `Field` = `(BigInteger Value, BigInteger FieldSize)`，所有 `+ − × / Pow/Inverse` 都在 `FieldSize = r` 上取模；`Inverse()` 用 `Pow(r−2)`（费马小定理）。
  - 编码：`EncodeBytes` = `BigInteger` 变长编码；`GetEncodedByteCount()` 变长；`BitDecomposition()` 位宽固定 253。
  - R1CS 线值 = `MpcValue` 列表；`SelfVerify()` 只检查单电路约束。
  - `ZkProgramExecutor` 明确区分 `AddPublic(string, Field)` 与 `AddPrivate(string, MpcValue)`：
    `in_global_step_counter`、`opcode_table_*` 为公开；`in_mem_addr`、`in_trace_*`、`in_private_input` 为私有 witness（L144–276）。
- **直接支持**：公开输入是 `Fr` 元素数组（verifier.rs `&[E::Fr]`）；电路内可以以公开输入形式暴露 `com_i`、`C_i`、`step_i` 等域元素；witness 是同一 `Fr` 上的线值。
- **不能支持**：verifier 会检查除单个 proof 之外的任何东西；challenge 派生接口；对 witness 每个份额的 MAC 覆盖证明（Correction-2 §E5 已核，本轮继承）。
- **状态**：**VERIFIED**（源码）。

---

## 3. Hash gadget 与域约束

- **来源**：`MimcEncryptGadget.cs`、`MimcHashGadget.cs`（固定 artifact 快照）。
- **事实**（与 Correction-2 §E1 一致，本轮定点复核源码文本）：
  - `DefaultRoundConstantStrValues` 65 轮常量；`DefaultSBox = 7`；每轮 `FieldAddGadget(3)` + `FieldConstPowGadget(7)`。
  - `MimcHashGadget`：`key = 0`，对 `preimageCount` 个输入逐个链式调用 `MimcEncryptGadget`，输出**一个** `Field`（域元素）。
  - 输入/输出均为 `Fr` 元素（`Field`），故输出天然落在 `F = Fr(BLS12-377)`，长度 ≈253 bit，**单个域元素**。
  - gadget 目录恰 19 个文件，**无** `Commitment`/`Pedersen`/`Poseidon`/`Merkle`（Correction-2 §E2 GitHub API 目录列表 VERIFIED；本轮继承）。
- **直接支持**：`H(k)=260·k` 乘法约束的记账口径（Correction-2 INFERRED），输出是一个 `Fr` 元素；同电路内重算 `H` 完全原生，无跨域问题。
- **不能支持**：MiMC 抗碰撞达到 128-bit 的安全裕度；MiMC 作为随机预言机的规约；Poseidon 参数；任何 hiding 承诺。
- **状态**：**VERIFIED**（源码参数与输出类型）/ **UNKNOWN**（安全裕度与 RO 假设）。

---

## 4. 同电路验证承诺关系的能力

| 问题 | 事实 | 状态 |
| --- | --- | --- |
| 电路内能否重算 MiMC 并把结果约束为公开输入？ | 能：`com_i − H(x‖s_i) = 0` 是 `Fr` 上的原生约束，`com_i` 可为 `AddPublic` | VERIFIED（接口）/ CONSTRUCTED（约束写法） |
| 电路内能否验证 G1  Pedersen `g^x h^s = C`？ | `x,s ∈ Fr` 原生，但 `C` 坐标在 `Fq(BLS12-377)`（**≠ Fr**），需非原生域算术 | INFERRED（域关系 VERIFIED；成本见下） |
| 是否有非原生域 gadget？ | gadget 目录 19 文件无位分解以外的跨域组件；只有通用 `BitDecompositionGadget` 等 | VERIFIED（目录）/ 专用非原生组件 BLOCKED |
| 是否有外部公开输入绑定 + 跨域验证组件？ | 无；verifier 只验单 proof，无 equality proof / 递归 / 桥接接口 | VERIFIED（Correction-2 §E5 继承） |
| 是否存在可复用曲线算术组件？ | 无曲线 gadget；`Field` 只覆盖 `Fr` 标量，不支持点运算 | VERIFIED |

**非原生成本参考（文献一手，供 B1/B3 判断，非本轮实测）**：

- Orrù–Kadianakis–Maller–Zaverucha, *Beyond the Circuit*, ePrint 2024/265 §1 逐字：
  「to simulate a non-native field multiplication for the BN254 curve base field using the BN254 scalar field, there is a **600x overhead**」；
  并指出 AES 在 BLS12-377 上用 Marlin 表达需 212,848 约束。
- *Efficient Foreign-Field Arithmetic in PLONK*, ePrint 2025/695 摘要逐字：优化后椭圆曲线模拟开销为「**one order of magnitude** (with respect to its native counterpart)」，且开源实现。
- *Reducing Participation Costs via Incremental Verification*, ePrint 2020/1522 §4：arkworks 非原生算术用于把 SNARK verifier 写进电路，引用 [DFKP16; KPS18; OWWB20]。

> 这些数字说明**非原生路线有明确代价区间（约 10×–600×，视技术而定）**，但都不是本 artifact 的实测值 → 本轮成本栏标 **UNKNOWN（有界：10×–600× 量级）**，不编造具体约束数。

---

## 5. 与冻结接口的兼容性

冻结接口（不得改）：

```
ictx_i = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)
W_pre,i = (old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i)
s_i = commitment_blinding_randomness
com_i = Com(Encode(ictx_i || W_pre,i); s_i)
rho_k = H(domain_k || ictx_i || com_i || transcript_context)
```

| 冻结要求 | 后端事实 | 状态 |
| --- | --- | --- |
| `Encode(ictx‖W_pre)` 输出一个可承诺值 | MiMC 链式 hash 输出一个 `Fr` 元素；但 8 字段总长远超 253 bit，必须先压缩（CRH/多轮 hash） | CONSTRUCTED 规则 / 具体编码 UNKNOWN |
| `com_i` 作为公开输入 | `AddPublic` + `&[E::Fr]` 支持 | VERIFIED |
| `s_i` 私有、不公开 | `AddPrivate` / 私有 witness 线支持 | VERIFIED（接口） |
| `s_i` 不作 ρ 种子 | ρ 由 `ictx‖com‖ctx` 派生；与后端无关 | CONSTRUCTED（沿用 Correction-4） |
| 同份 witness 绑定 | 电路内同线值重算承诺是原生 `Fr` 约束（若承诺是 hash 类）；Pedersen 需非原生/桥接 | 条件成立，见 `candidate-analysis.md` |

---

## 6. 核查小结

| 事实 | 结论 | 状态 |
| --- | --- | --- |
| 电路域 | `Fr(BLS12-377)`，253 bit，**非 BN254** | VERIFIED（纠正继承错误） |
| 证明系统 | Plonk + BLS12-377（主路径）；Groth16 泛型 verifier 快照另存 | VERIFIED / 关系 UNKNOWN |
| MiMC | 65 轮、SBox=7、输出一个 `Fr` 元素、无 hiding | VERIFIED |
| commitment gadget | gadget 目录无；全仓库穷尽 UNKNOWN | VERIFIED / UNKNOWN |
| 公开输入接口 | 存在；可暴露 `com_i`/`C_i`/`step_i` | VERIFIED |
| 同电路验证 G1 承诺 | 需非原生域算术；成本约 10×–600× 量级，非实测 | INFERRED / UNKNOWN |
| 认证随机源接口 | 无 | BLOCKED（继承 Correction-2 §E5） |

本轮不再核查 Keller–Scholl、Path ORAM、VDORAM 背景（已在 `docs/exp-doram-03-r1-correction/literature-evidence.md` 固定）。
