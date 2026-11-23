# evidence.md — 定点源码与必要性质核查

> 2026-11-23 · 起点 `bc6d774` · 只核查本轮五项必要事实，不做 ORAM 文献综述。
> 状态：**VERIFIED** 一手源码/API 列表/可复现算术 · **INFERRED** 有依据推导 · **UNKNOWN** 证据不足 · **CONDITIONAL_CONSTRUCTION** 依赖条件。
> 每条按「来源 → 位置 → 直接支持 → 不能支持 → 状态」记录。

---

## E1. 固定 VDORAM artifact 的 MiMC 参数与调用方式

- **来源**：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`，本地源码快照。
- **位置**：
  - `CompatCircuit/CompatCircuitProgramming/Gadgets/MimcEncryptGadget.cs`，blob `8dd4c8aa6cf58b3b5227f01709e80a87f50b7a14`，L16–20：`DefaultRoundConstantStrValues` 共 65 项，`DefaultSBox = 7`，`RoundCount = RoundConstants.Count`；L43–54 每轮 `FieldAddGadget(3)` 后接 `FieldConstPowGadget(7)`。
  - `CompatCircuit/CompatCircuitProgramming/Gadgets/MimcHashGadget.cs`，blob `bf11f4af5a46081fc98f9090bf5357aa307b2c41`，L24–32：key = 0，逐个 preimage 链式调用 `MimcEncryptGadget`。
  - `BoolAndGadget.cs`，blob `0bf09fdb…`，L14：`BoolAnd` = `FieldMulGadget`。
  - `SelectComposeGadget.cs`，blob `dc19cb7a…`，L25–40：每候选每字段一次 `FieldMul`。
- **直接支持**：65 轮、`SBox=7`、hash 的 k-preimage→k-encrypt；AND 与秘密选择各按乘法门计费；故 `H(k)=260·k` 的乘法约束计数（配合 `x⁷` 的 4 次乘法）有源码依据。
- **不能支持**：MiMC 抗碰撞安全裕度是否达 128-bit；Poseidon/P128Pow5T3 参数；Pedersen 曲线与 gadget。
- **状态**：**VERIFIED**（源码事实）+ **INFERRED**（260k 约束数由源码轮数与 S-box 加法链推导）。

---

## E2. 固定 artifact 的 commitment / hash 接口

- **来源**：GitHub API `contents/CompatCircuit/CompatCircuitProgramming/Gadgets?ref=10c90d3…` 定点列表（2026-11-23 获取）；本地快照目录交叉核对。
- **位置**：该目录恰 19 个文件：`BitDecompositionGadget, BoolAndGadget, BoolNotGadget, FieldAddGadget, FieldConstPowGadget, FieldEqualsGadget, FieldGreaterEqualThanGadget, FieldLessThanGadget, FieldMulGadget, FieldNegGadget, FieldNormGadget, FieldSubGadget, GadgetIncompleteCircuitBoard, GadgetInstance, IGadget, LowBitGadget, MimcEncryptGadget, MimcHashGadget, SelectComposeGadget`。
- **直接支持**：在该 gadget 目录内**不存在**任何名为 `Commitment` / `Pedersen` / `Poseidon` / `Merkle` 的实现；哈希接口只有 MiMC。本地快照全目录 `grep -i commitment|pedersen` 无命中。
- **不能支持**：整个仓库其他目录也绝对没有承诺原语（本次只列了 gadget 目录）；不能据此断言协议层不可能用外部承诺，只能断言**当前 artifact 没有可直接调用的承诺接口**。
- **状态**：**VERIFIED**（目录列表）/ **UNKNOWN**（全仓库穷尽性）。

---

## E3. B1 commit-then-challenge 所需的承诺安全性质

- **来源**：本轮数学推导 + 前序 `docs/exp-doram-03-r1-correction/stash-soundness.md` §B2–B3；不引入新的文献综述。
- **位置**：`stash-soundness.md` B2（顺序：witness 固定 → com(W) → ρ → 指纹约束），B2 soundness 误差计算 `d/|F|`、两挑战约 `2^-170`。
- **直接支持**：挑战必须在 witness 承诺之后派生；com 必须 binding；若 com 不 hiding 则 transcript 泄露 witness； Schwartz–Zippel 误差公式在挑战均匀随机时成立。
- **不能支持**：固定文献集合中存在“ORAM stash 的 commit-then-challenge 已发表实例”；artifact 已提供 com(W) 接口；FS 在多方共享 transcript 下的具体安全规约。
- **状态**：**CONSTRUCTED**（顺序与误差公式）/ **UNKNOWN**（直接文献实例与接口）。

---

## E4. Pedersen-like 承诺在当前域与 R1CS 环境的适用性

- **来源**：标准承诺定义（perfect hiding / computational binding）+ 固定 artifact 的证明后端证据（前序 `evidence.md` F1/F2.4；`collaborative-zksnark-mod__groth16__src__verifier.rs`）。
- **位置**：`verifier.rs` L27–61 为 arkworks 标准 Groth16 单 proof 验证；证明系统标量域为 BN254 `Fr`，而 G1 坐标域为 `Fq≠Fr`（arkworks BN254 标准配置）。
- **直接支持**：Pedersen 的 hiding/binding 有明确安全定义，优于“MiMC + 随机盐”；在 `Fr` 上验证 `g^x h^r` 需非原生域算术，若改用基域为 `Fr` 的内曲线则仍需 Artifact 不存在的曲线 gadget（结合 E2）。
- **不能支持**：当前 artifact 已有 Pedersen 实现；非原生算术的具体约束倍率；替换后 proof 成本与通信的实测值。
- **状态**：**INFERRED**（域不匹配与成本方向）/ **CONDITIONAL_CONSTRUCTION**（可实现性）。

---

## E5. 当前 collaborative SNARK 接口是否暴露承诺/挑战/认证 witness

- **来源**：固定 artifact 源码快照，前序 `docs/exp-doram-02-r1/source-evidence/`。
- **位置**：
  - `CompatCircuit__CollaborativeZkVm__Program.cs` L106–111（单方：落盘 `*.single.r1cs.json` 后 `SelfVerify()`）、L211–214（多方：仅落盘 `*.party{id}.r1cs.json`）；
  - `R1csCircuitWithValues.cs` L10/L22–38：`WireValues` 为 `MpcValue` 列表，`SelfVerify()` 只检查单电路乘积/线性约束，且拒绝 secret share 输入；
  - `collaborative-zksnark-mod__groth16__src__verifier.rs` L27–61：标准单 proof `verify_proof`；
  - `prove-scripts/collaborative-zksnark-mod.md` 与 `prove-r1cs-multiparty-inner.py`：外部 Rust client 逐电路手动证明；
  - `MpcValue.cs`：`Field Value + bool IsSecretShare` 纯记录，可跨 session 持有。
- **直接支持**：R1CS + witness 由同一执行的线值生成并落盘；份额可跨步承载；verifier 只验单 proof。
- **不能支持**：witness commitment 的公开 transcript 项；challenge 派生/重算接口；对 proof witness 每个输入份额的 MAC 覆盖证明；跨电路根/step/历史串联。
- **状态**：**VERIFIED**（接口事实）；缺失部分为 **BLOCKED**（D2 不因本轮而解封）。

---

## E6. 定点核查小结

| 事实 | 结论 |
| --- | --- |
| MiMC 参数与 hash 成本 | VERIFIED 源码 + INFERRED 计数，可继续用于本轮报价 |
| 承诺接口 | gadget 目录内无承诺/Pedersen/Poseidon/Merkle 实现（VERIFIED）；全仓库穷尽 UNKNOWN |
| B1 顺序与 soundness 公式 | CONSTRUCTED 数学；直接文献实例 UNKNOWN |
| Pedersen 适用性 | 定义明确但域/后端不匹配，CONDITIONAL_CONSTRUCTION |
| co-SNARK 接口 | 只落盘 + 外部逐电路证明（VERIFIED）；com/challenge/认证 witness 全缺（BLOCKED） |

本轮不扩展 Keller–Scholl、VDORAM、Path ORAM 背景调查；这些已在 `docs/exp-doram-03-r1-correction/literature-evidence.md` 固定。
