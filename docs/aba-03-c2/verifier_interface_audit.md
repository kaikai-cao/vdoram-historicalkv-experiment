# aba-03-c2 — Verifier 侧程序身份与地址绑定接口审计

> 日期：2026-11-24 · 起点 commit `8197b1391c9ee6947f7ccd907521a3b8b2d57982`
> 固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 性质：只读接口审计。不改 HOLD、不设计新协议、不实现电路、不运行测试。
> 标签：`VERIFIED`（固定 commit 源码事实或可复核 blob 证据）/ `CONSTRUCTED`（本轮或前序实验侧构造，非上游）/ `INFERRED`（由源码事实推导）/ `UNKNOWN` / `BLOCKED`。

---

## 0. 一句话结论

**两者都缺，但缺口性质不同（勘误 C1 收紧）。** 现有路径缺少独立 verifier（proof 由 prover 进程用现场生成的 vk 与自身提供的 public inputs 自测）。**P1 可复用现有 public-input 通道闭合**：opcode table 已是公开输入，独立 verifier 可持有预期完整表逐项比较（方案 P1-A），整程序 commitment 仅为可选的摘要化方案（P1-B），不是唯一路径。**P2 无法只靠 verifier 闭合**：地址是私有 witness、跨电路无共享公开绑定，必须新增电路/证明接口层面的同一性关系。可复用项为「公开输入通道 + 标准 verify 函数 + 逐行哈希 gadget」。决策：`REQUIRES_CIRCUIT_INTERFACE_CHANGE`（整体目标需补验证接口与 P2 电路绑定接口）；ABA-03 的 `HOLD` 不解除。

---

## 0.1 证据可得性与一处历史判断纠正

- `docs/exp-doram-02-r1/verifier-chain-check.md` §5、`docs/exp-doram-03-r1/verifier-chain.md` E4 曾把 verifier 缺口记为「外部 `collaborative-zksnark-mod`（codeup.aliyun.com 独立仓库），不在固定 commit 证据范围，UNKNOWN」。
- 本轮用固定 commit 的 git tree（`tree.json`：`sha=10c90d35…`，`url=api.github.com/repos/BDS-SDU/vdoram-artifacts/git/trees/10c90d35…`）复核：该子树在固定 commit 内共 **1067 个条目**，含 `collaborative-zksnark-mod/mpc-snarks/src/{plonk,client,proof,lib}.rs` 与 `collaborative-zksnark-mod/groth16/src/verifier.rs`。按 tree 中 blob SHA 只读抓取原文，得到：

| 文件 | 固定 commit blob SHA | 行数 |
|---|---|---|
| `mpc-snarks/src/plonk.rs` | `ae077b0a13efa8f88b885a035635513aa86dccc8` | 315 |
| `mpc-snarks/src/client.rs` | `44504e7cc085c19e68c1fad868008df903234b0b` | 1019 |
| `mpc-snarks/src/proof.rs` | `72a48de63974785576d59419591e133590888256` | 508 |
| `mpc-snarks/src/lib.rs` | `31e1bb209f98ec5fc6b7cbea4c4766a555c87247` | 7 |
| `groth16/src/verifier.rs` | `bfe07ac2ed72af1dfb57e202e932e49fe58c4897` | 58 |

- `groth16/src/verifier.rs` 的 SHA 与既有落盘快照 `docs/exp-doram-02-r1/source-evidence/collaborative-zksnark-mod__groth16__src__verifier.rs` 第 3 行 `BLOB SHA` 完全一致（交叉核验通过）。
- 因此 verifier 侧源码**可以从固定 commit 可靠定位**，P1/P2 不标 `BLOCKED`。旧文档的「外部 UNKNOWN」按本轮证据收紧为「固定 commit 内可核验」；本轮按范围要求**不修改**那些旧文档，仅在此记录。
- C# 侧证据沿用 `D:/tmp/aba01/src/`（无头文件，行号即原始行号）与 `docs/source-snapshot/`、`docs/exp-doram-02-r1/source-evidence/`（快照头部 4 行，原始行号 = 快照行号 − 4）。

---

## 1. Phase A：真实验证路径（逐环节）

| # | 环节 | 仓库 / commit / 文件 / 函数 / 行号 | 输入 → 输出数据结构 | 谁控制 | 标签 |
|---|---|---|---|---|---|
| A1 | R1CS + witness 生成 | `vdoram-artifacts@10c90d35` · `CollaborativeZkVm/ZkPrograms/ZkProgramExecutor.cs` L187/411/586（`GetR1csCircuitWithValues()`）；`R1csCircuitWithValues.cs` 原始 L6/L14-20 | 电路约束 + `IReadOnlyList<MpcValue> WireValues` + `PublicWireCount` + Product/Sum constraints | prover（执行器）生成 | VERIFIED |
| A2 | 落盘 JSON | 同上 · `CollaborativeZkVmExperiment/Program.cs` L251-254（单方）、L335-338/L411-414（多方）、L603-605/L717-719（回调）；`JsonSerializerHelper.Serialize` | `{instance}.{name}.single.r1cs.json` / `.party{j}.r1cs.json`；wire 值含 `is_secret_share` 标志 | prover 侧落盘；回调多方路径仅落盘、无 `SelfVerify()` | VERIFIED |
| A3 | 外部客户端接收 | `collaborative-zksnark-mod/mpc-snarks/src/client.rs`（blob `44504e7c…`）L941-945：`opt.args.first()` 作为 json 路径；L200-210 `run_bls_compat_circuit` | CLI 参数 → `compat_circuit_r1cs_json_path: &str` | 调用方（prover/实验方）传路径 | VERIFIED |
| A4 | JSON → PLONK 电路 | `plonk.rs`（blob `ae077b0a…`）L97-110 `WireValue`/`CompatCircuitR1csJson` schema；L261-267 读文件；L112-172 `to_empty_plonk_circuit`；**L203-247 `to_plonk_circuit_multi_party`** | `Vec<WireValue>` → `(v_c: PlonkCircuit<F>, c: PlonkCircuit<MF>, public: HashMap<String,F>)`；L212-216 secret→`MF::from_add_shared`、public→`from_public` | prover 提供全部 wire 值；public map 取自 prover JSON 的 `public_wire_count` 以内 wire | VERIFIED |
| A5 | Setup + Prove | `plonk.rs` L293-315 `mpc_prove_and_verify_compat_circuit`：L302 `let setup_rng = &mut test_rng();`、L303 `universal_setup`、L304 `circuit_setup(&srs, &v_circ)` 得 `(pk,vk)`；L311 `MpcPlonk::prove`；L312 `mpc_pf.reveal()` | SRS / `(pk,vk)` / `MpcProof` → `pf`（本地明文 proof） | **vk 在证明进程内由 `test_rng()` 现场生成**，非 verifier 预先固定 | VERIFIED |
| A6 | Verify（同进程） | `plonk.rs` L314 `LocalPlonk::verify(&vk, &v_circ, pf, &public)`；`verifier.rs`（blob `bfe07ac2…`）L27-61 `verify_proof(pvk, proof, public_inputs)` 只做长度 + pairing 等式（L32-43/L61） | `vk + v_circ + pf + public` → `bool`（断言） | public inputs 即 A4 的 prover JSON public map；**无 prover 之外的期望值来源** | VERIFIED |
| A7 | proof / public / commitments 输出格式 | `plonk.rs` L312 `pf = mpc_pf.reveal()` 后直接进 L314 verify；全函数**无** proof 落盘、无网络发送、无 commitment 序列化 | 明文 proof 仅存活于进程内 | — | VERIFIED |
| A8 | verifier 取验证密钥/public/程序身份 | 固定 commit 全树检索：无 `verify-only` CLI 子命令；`client.rs` L36-65 `Computation` 枚举只有 `PlonkCompatCircuit{Local,MultiParty}` 等 prove-and-verify 自测项；`proof.rs`（blob `72a48de6…`）L69-299 的 verify 均在 `#[cfg(test)]` 基准测试内 | 无独立 verifier 接口 | — | VERIFIED（在本固定 commit 范围内） |

**A 路径要点**：所谓「外部 verifier」在固定 commit 内**不存在独立主体**。L293-315 一条命令完成 setup→prove→reveal→verify；vk 由 `test_rng()` 现场生成，public inputs 来自 prover 自己的 JSON。`verify_proof` 本身是标准 arkworks 形式（与历史快照一致），但它验证的是「prover 给出的 proof 相对 prover 给出的 public inputs、相对 prover 进程生成的 vk」是否自洽。证明生成成功 **不等于** verifier 侧绑定成功。

---

## 2. Phase B：P1 程序身份锚点

| 问题 | 回答 | 证据 | 标签 |
|---|---|---|---|
| opcode table 是否作为 proof public inputs 的一部分？ | **是**。`InstructionFetchCircuitBoardGenerator.cs` L126-156 以 `Wire.NewPublicInputWire($"opcode_table_{i}_arg0/arg1/arg2/op")` 声明；`ZkProgramExecutor.cs` L147-157 `AddPublic($"opcode_table_{i}_…")`；Rust 侧经 `plonk.rs` L128-161 进入 `named_public_values` 并作为 verify 的 `&public` | C# 原始行号 + `plonk.rs:143-161` | VERIFIED |
| verifier 是否独立持有预期 opcode table 或其 digest？ | **否**。无独立 verifier（§A8）；`verify_proof` 只有 `pvk/proof/public_inputs` 三参数（`verifier.rs:27-31`），public_inputs 全部来自 prover JSON | `plonk.rs:293-315`、`verifier.rs:27-61` | VERIFIED |
| 是否有 verifier 侧固定 program ID / program hash / 电路专属 vk？ | **否**。vk 由 `test_rng()` 现场生成（`plonk.rs:302-304`）；C#/Rust 全树检索 `program_id|program_hash|digest` 无命中（详见 `../aba-03/source_trace_audit.md` §证书绑定项） | `plonk.rs:302-304` + 检索 | VERIFIED |
| 逐行哈希能否被 verifier 绑定到一张固定的完整表？ | **不能**。`out_hash_opcode_table_row` 的 preimage 含 `inGlobalStepCounter` 与随机 `enc_key`（`InstructionFetchCircuitBoardGenerator.cs:215-235`，`MagicNumber.cs:21-24`）；执行器把该行输出作为私有输入送入 ZkVm 电路（`ZkProgramExecutor.cs:284-287`）并在宿主比对（`:326-332`）。它是逐步状态摘要，不是稳定 program digest；且只有「当前选中行」哈希，没有覆盖整表的承诺 | 原始行号 + `../aba-03/source_trace_audit.md` | VERIFIED |
| 替换 opcode table 后是否有可核实的验证拒绝路径？ | **没有在本 commit 证据内找到 verifier 侧拒绝路径**。分层表述如下（见下方「替换论证的证据边界」）。C# 的「manually verified by verifiers」是注释（`ZkVmExecutorCircuitBoardGenerator.cs:247-248`），不是代码 | `plonk.rs:203-247,293-315` | VERIFIED（public map 进入 verify；无独立 verifier 持有期望表）；实际攻击是否跑通 = `UNKNOWN`（本轮不运行） |

**替换论证的证据边界（勘误 C1）**：

- **已验证**：opcode table 作为 public inputs 进入 Rust 侧 public map（`plonk.rs:143-161`；C# 侧 `InstructionFetchCircuitBoardGenerator.cs:126-156`、`ZkProgramExecutor.cs:147-157`）。
- **已验证**：当前路径没有独立 verifier 持有预期 opcode table 或其 digest（§A8、本表第二行）。
- **未验证**：仅替换 JSON 中 opcode public wire 值、而保持其余 witness 与约束不变时，是否仍能成功证明。现有源码没有证明这种单独替换必然成功——`to_plonk_circuit_multi_party`（`plonk.rs:203-247`）同时从同一份 JSON 取约束结构与全部 wire 值，单独改动 public 行与其他字段之间的关系未被单独分析。
- **合理推论（非攻击结果）**：若攻击者可同时控制电路描述、witness 与 setup，则可能构造另一套自洽的证明流程；这是**架构风险推论**，不是已执行攻击的结论。
- **攻击实验状态**：`UNKNOWN`。本轮不运行任何攻击实验，不声称替换必然成功或必然失败。

**P1 结论**：`VERIFIED` — opcode table 已进入 public inputs，公开输入通道与标准 verify 函数可复用；**独立 verifier 与其固定期望值（表或 digest）缺失**。整程序 commitment 不是唯一闭合路径，见下。

### P1 最小闭合路径（勘误 C1：区分两种方案）

**方案 P1-A：固定完整表比较（可复用现有 public-input 通道）**

- 独立 verifier 持有**预期完整 opcode table**（可由固定上游字节码离线生成并可信分发）；
- verifier 从 proof 的 public inputs 中取得 opcode table（该通道已存在：`plonk.rs:143-161` + C# `AddPublic` 点，无需新增电路输出）；
- verifier 逐项比较 public table 与预期 table，不一致则拒绝；
- 使用与该电路匹配、且预先固定/可信分发的 verification key 验证 proof（替换当前 `test_rng()` 现场生成 vk 的做法）。
- **该方案不要求新增电路级整程序 commitment**；它复用现有公开输入通道，缺的是独立 verifier 主体、固定 vk 与固定预期表这三项接口/配置。

**方案 P1-B：固定 digest 比较（可选的摘要化方案）**

- 电路将完整 opcode table 与一个稳定的 `program digest` 绑定（新增电路内承诺关系）；
- verifier 持有预期 digest 并核对，公开输入从整表压缩为单个 digest；
- 这需要额外的电路承诺关系，属于**可选的摘要化方案**，不是 P1 的唯一闭合方式。

**两方案关系**：P1-A 是 P1 的最小闭合路径（复用现有 public-input 通道）；P1-B 是在此之上的摘要化优化。不得把 P1-B 描述为 P1 的必要或唯一路径。

---

## 3. Phase C：P2 地址同一性

| 问题 | 回答 | 证据 | 标签 |
|---|---|---|---|
| Fetch 电路 `in_mem_addr` 如何进入 proof statement？ | **不进入公开 statement**。`MemoryTraceFetchCircuitBoardGenerator.cs:41-43` 为 `Wire.NewPrivateInputWire`；`:52` `FieldEqualsGadget(in_trace_mem_addr_wires[row], in_mem_addr)` 在电路内比对 trace 与入参。执行侧 `ZkProgramExecutor.cs:225-226` `AddPrivate("in_mem_addr", thisRegisters[0])` | 原始行号 | VERIFIED |
| VM 电路 `out_trace_mem_addr` 如何进入 proof statement？ | **不进入**。`ZkVmExecutorCircuitBoardGenerator.cs:224-227` 实际地址源是 `inMemAddrWire = inRegisterWires[0]`（原 `in_mem_addr` 已注释），而 `in_this_reg_i` 是私有输入（`:177`）；`:960` `out_mem_addr`、`:996/1006` 非内存步 trace 地址均为 `IsPrivateOutput = true` | 原始行号 | VERIFIED |
| 两者是否由同一公开输入 / 共同承诺 / 递归状态承诺绑定？ | **否**。两者分别是两个电路的私有 witness/私有输出；public inputs 集合只有 step counter、public input、opcode table 四列（`plonk.rs:143-161` + C# `AddPublic` 点）。跨电路没有共享公开承诺，proof statement 内无地址明文 | 原始行号 + `plonk.rs:143-161` | VERIFIED |
| 外部 executor 的哈希连续性检查是否属于 verifier 实际验证的一部分？ | **不属于**。这些检查是 C# 宿主执行期 `if (...) throw`：`ZkProgramExecutor.cs:170-181`（pc/enc_key）、`:302-332`（enc_key/pc/registers/opcode row）、`:551-583`（内存证明哈希多重集）。被比较的哈希值是电路 `IsPublicOutput`，随 JSON 落盘，但「连续性断言」本身既不进 R1CS、也不进 public inputs | 原始行号 | VERIFIED |
| verifier 能否独立检查两个电路使用同一个地址？ | **不能**。prover 自测路径只做「每电路相对自身 public inputs 自洽」；地址不在 public statement，verifier 无可核对值；宿主检查对 verifier 不可见 | 综合上述 | VERIFIED |

**四类检查必须分开**（不得互相替代）：

| 层次 | 固定 commit 中的实际位置 | 是否 verifier 可见 |
|---|---|---|
| executor 本地检查 | `ZkProgramExecutor.cs:170-181,302-332,551-583` 宿主 `throw` | 否 |
| MPC 参与方间检查 | `MpcPlonk::prove` 内 share 运算；`mpc_pf.reveal()` 公开 proof（`plonk.rs:311-312`）；无 MAC（见 `../exp-doram-06/rust-authenticated-share-path.md` B.1/B.4） | 否 |
| proof 内约束 | R1CS → PLONK；`FieldEqualsGadget(in_trace_mem_addr_wires[row], in_mem_addr)` 等电路内一致性（`MemoryTraceFetch...cs:52`） | 仅通过 pairing 等式间接成立；值本身不可见 |
| 最终 verifier 检查 | `plonk.rs:314` + `verifier.rs:27-61` | 是，但只见 prover 提供的 public inputs 与现场 vk |

**P2 结论**：`VERIFIED` — 地址同一性在构造上同源（`reg0`），但**跨电路共享公开承诺 / 电路内同一性约束缺失**，verifier 无法独立闭合 `fetch_addr = reg0 = trace_addr`。

---

## 4. Phase D：结果与决策

| 条件 | 现有机制 | verifier 可验证性 | 缺口 | 证据等级 |
|---|---|---|---|---|
| P1 完整程序身份 | opcode table 四列为 public input（`InstructionFetchCircuitBoardGenerator.cs:126-156`），该通道可直接复用；标准 `verify_proof` 存在；逐行哈希 `out_hash_opcode_table_row` 含 step 与随机 enc_key（仅影响 P1-B） | 无独立 verifier；vk 现场 `test_rng()` 生成；public inputs 来自 prover JSON；无期望表/digest | ① 独立 verifier；② 固定/可信分发的 vk；③ 固定预期**完整 opcode table**并逐项比较（P1-A，复用现有 public-input 通道，够用）；或可选的稳定 digest + 电路承诺（P1-B，摘要化方案，非必需） | VERIFIED |
| P2 Fetch/trace 地址同一性 | 构造上同源于 `reg0`；电路内 Fetch 侧 `FieldEquals` 比对；跨电路靠宿主哈希 `throw` 检查 | 地址是私有 witness/私有输出，不在 proof statement；verifier 无可核对值；宿主检查不可见 | ① 电路内 `fetch_addr = reg0 = trace_addr` 同一性断言，或两电路共享公开承诺 `H_step(step,pc,opcode,reg0,is_mem_op)`；② verifier 侧公开输入锚定该承诺 | VERIFIED |

### 决策：`REQUIRES_CIRCUIT_INTERFACE_CHANGE`

**明确回答「缺电路约束、verifier 接口、还是两者都缺」（勘误 C1 收紧）：P1 缺 verifier 接口，P2 缺电路绑定接口。**

1. **P1 — 缺 verifier 接口，不缺电路承诺**：固定 commit 内不存在独立 verifier 主体；proof 在 prover 进程内用现场 vk 与自身 public inputs 自测（`plonk.rs:293-315`），无「prover 之外」的期望值来源（§A5-A8）。但 opcode table 已是公开输入，只要补上独立 verifier + 固定 vk + 固定预期完整表（P1-A），即可复用现有通道闭合 P1，**不必然需要新增电路级整程序承诺**；新增 digest 承诺（P1-B）只是可选摘要化方案。
2. **P2 — 缺跨电路绑定接口**：即便补上独立 verifier，地址仍不在 proof statement，verifier 拿不到可核对值；必须新增电路/证明接口层面的 `fetch_addr = reg0 = trace_addr` 同一性关系，并由 verifier 锚定相关公开承诺或状态。**这是明确需要新增电路绑定关系的部分。**
3. **不是 NO_GO**：架构无数学矛盾；可复用项为公开输入通道、标准 `verify_proof`、逐行哈希 gadget、MPC prove 数据通路（受 additive-only 限制，见 `../exp-doram-06/rust-authenticated-share-path.md` B.5/B.6）。
4. **保留 `REQUIRES_CIRCUIT_INTERFACE_CHANGE`**：理由是整体目标既要补齐 P1 的验证接口，又必须补上 P2 的电路绑定接口；其中 P2 的电路新增是硬需求，P1 的最小闭合路径（P1-A）可复用现有 public-input 通道。不再暗示 P1 本身必然需要新增 program commitment。

### 对下一阶段的含义（本轮不执行）

- **P1 的最小闭合**：补独立 verifier、固定/可信分发的 vk、固定预期完整 opcode table 并逐项比较 public inputs（P1-A）；可复用现有 public-input 通道，不必然改电路。可选地再做稳定 digest + 电路承诺（P1-B）做摘要化。
- **P2 的最小闭合**：必须新增电路/证明接口层面的跨电路地址同一性关系（同电路断言或共享公开承诺），并由 verifier 锚定该公开值；仅补 verifier 不足以闭合。这部分超出「最小化修改现有 VDORAM」的范围。
- 本轮不解除 ABA-03 的 `HOLD`，不启动 ABA-04，不设计新协议，不写电路。

---

## 5. 边界声明

- 本轮只读、只新增本文档；未运行测试、未修改任何既有文档、未修改上游源码或固定 commit 快照。
- 所有 Rust 结论来自固定 commit 的可复核 blob（SHA 见 §0.1）；`plonk.rs`/`client.rs`/`proof.rs` 原文抓取到 `D:/tmp/aba01/rust_src/`，仅作审计证据，不属于本仓库交付物。
- 「未发现」限定于固定 commit 与本轮检索范围；不等于 VDORAM 论文层面不存在相应设计。
- 类别严格区分：prover（生成 R1CS/witness/JSON）、executor（C# 宿主检查）、MPC participant（share 运算/reveal）、verifier（标准 verify 函数，但无独立主体）。
- 未把 proof 生成成功当成 verifier 绑定成功；未把宿主 hash 检查当成公开可验证约束；未虚构外部客户端仓库或验证行为（相反，本轮证明其位于固定 commit 内）。
- 决策为审计判断，不含任何「已实现/已验证安全」的声称。
