# ABA-03-D3-03-02 / Phase 1：现有信任边界盘点

> 实验仓起点：`62ec3827bc89fb495daf68735ab93d1ea0b1e7c0`；固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
>
> 性质：只读信任模型审计。复用 `docs/source-snapshot/` 固定源码快照与既有审计文档（`../aba-03-c2/verifier_interface_audit.md`、`../aba-03/source_trace_audit.md`、`../aba-03-d3-01/verifier_independence.md`、`../aba-03-d3-03-01/interface_evidence_inventory.md`、`../aba-03-d2/context_and_replay.md`）；只读核对了固定快照的接口与行号，未改任何文件、未实现电路/verifier、未运行测试。
>
> 标签：`VERIFIED`（固定快照/接口直接支持）· `CONSTRUCTED`（本轮候选接口/约束）· `INFERRED`（由已验证事实推导）· `UNKNOWN`（缺证据）· `BLOCKED`（当前架构缺必要能力）。
>
> **行号口径**：本文引用的 `ZkProgramExecutor.cs` 行号以当前 `docs/source-snapshot/CompatCircuit__CollaborativeZkVm__ZkPrograms__ZkProgramExecutor.cs` 快照为准（快照含 4 行头：SOURCE/PATH/BLOB SHA/空行）。部分既有文档引用的是去头"原始行号"（= 快照行号 − 4），本文在关键处并列标注"快照 Lx / 原始 Ly"，便于交叉核对。BLOB SHA：`24ddf044e895b1ecb0a6da7652de27dc4e5fb4a2`。

---

## 0. 核心方法学边界：谁有权定义一个字段？

本轮关键判据是：**一个字段出现在 proof 的 public input 中，不等于 verifier 信任它。** 必须把每个字段归入五类来源之一，且只有后两类才可能构成 verifier 可信依据：

| 来源类别 | 定义 | 是否 verifier-trusted |
| --- | --- | --- |
| **prover 声明的 public input** | 值来自 prover 侧 JSON，经 `named_public_values` 进入 verify 的 `&public`（`plonk.rs:143-161,203-247`） | 否 |
| **verifier 预先固定的 public input** | verifier 持有独立期望值并逐项核对 | 是（当前缺失） |
| **verifier 从可信外部取得的参数** | 固定/可信分发的 VK、预期 opcode table、预期 T，经可信通道取得 | 是（当前缺失） |
| **circuit 约束产生的 public output** | `IsPublicOutput` 随 proof 公开，但正确性取决于电路约束与输入来源 | 条件性（值公开 ≠ 来源可信） |
| **host 执行器自行检查的值** | C# 执行期 `if (...) throw` 或 host 侧哈希多重集比对 | 否（不进 R1CS、不进 public inputs） |

**总基线（`VERIFIED`）**：当前 `plonk.rs:293-315` 在同一函数内 `setup → prove → reveal → verify`；VK 由 `test_rng()` 现场生成（`plonk.rs:302-304`）；public inputs 全部来自 prover JSON（`plonk.rs:97-110,143-161,203-247`）；固定 commit 无独立 verifier 主体（`client.rs:36-65`，`proof.rs` verify 仅在 `#[cfg(test)]`，`verifier_interface_audit.md` §A8）。因此当前路径中**没有任何字段具备 verifier 独立可信来源**——verifier 检查的是"prover 给出的 proof 相对 prover 给出的 public inputs、相对 prover 进程生成的 vk"是否自洽。

---

## 1. Program identity 盘点

| 审计项 | 固定快照事实 | 来源/行号 | 标签 |
| --- | --- | --- | --- |
| opcode table 生成 | 整张表 `opcode_table_{i}_{op,arg0,arg1,arg2}` 声明为 `Wire.NewPublicInputWire` | `InstructionFetchCircuitBoardGenerator.cs:126-156`（既有证据） | `VERIFIED` |
| 进入 VM 电路的方式 | 执行器逐行 `AddPublic($"opcode_table_{i}_…")`；快照 L157-160（原始 L153-156） | `ZkProgramExecutor.cs` 快照 L157-160 | `VERIFIED` |
| 执行电路内部使用 | 执行电路把 opcode 四列作为 `NewPrivateInputWire` 逐项比对常量 | `ZkVmExecutorCircuitBoardGenerator.cs:231-241,273-347` | `VERIFIED` |
| **program hash / program_id 是否存在** | 固定快照全目录检索 `program_id|programId|program_hash|ProgramId` **无命中** | `docs/source-snapshot/` grep（本轮只读核对） | `VERIFIED`（缺失） |
| 逐行 opcode 哈希能否作稳定 program digest | **不能**：`out_hash_opcode_table_row` 的 preimage 含 `global_step_counter` 与每次执行随机 `enc_key`，且只哈希"当前选中行"，不覆盖整表 | `InstructionFetchCircuitBoardGenerator.cs:215-235`；`MagicNumber.cs:21-24`；`source_trace_audit.md` A3 | `VERIFIED`（缺失）+ `INFERRED` |
| verifier 是否持有预期表/摘要 | 否：无独立 verifier；`verify_proof(pvk, proof, public_inputs)` 仅三参数、只做长度+pairing | `verifier.rs:27-61`；`verifier_interface_audit.md` §B | `VERIFIED` |
| prover 能否自行替换 program 与对应 public input | 通道层面：opcode 表是 prover JSON 的 public wire，prover 可填；**单独替换后证明是否仍成功 = UNKNOWN**（约束与 wire 同出一份 JSON，未单独分析） | `plonk.rs:203-247`；`verifier_interface_audit.md` §B 替换论证边界 | `VERIFIED`（通道）+ `UNKNOWN`（攻击结果） |

**Program identity 边界结论**：opcode table 是**可用的 public-input 通道**（P1-A-1 可复用，`verifier_independence.md` §2.2），但"通道存在"≠"verifier 已固定预期表"。当前无稳定 program_id/digest、无 verifier 独立期望值、无 program→VK 绑定。**prover 在选择 program 语义上不受 verifier 约束**（`CONSTRUCTED` 层面的判断，攻击是否实际跑通 `UNKNOWN`）。

---

## 2. Execution identity 盘点

| 审计项 | 固定快照事实 | 来源/行号 | 标签 |
| --- | --- | --- | --- |
| 是否存在 execution_id | 固定快照全目录检索 `execution_id|executionId|ExecutionId` **无命中** | `docs/source-snapshot/` grep（本轮只读核对） | `VERIFIED`（缺失） |
| 每次执行的随机量 | `inEncKey = MpcShareFromExistingShare(FieldFactory.Random())`，每次执行取一次（快照 L65 / 原始 L61） | `ZkProgramExecutor.cs` 快照 L65 | `VERIFIED` |
| `enc_key` 能否充当 execution_id | 需额外证明：跨执行唯一、不可预测、被 verifier 锚定、绑定 program/输入/T；当前这些均缺。`enc_key` 仅作哈希 preimage 的随机盐，语义上是"每次执行一值"，非"执行实例身份" | `ZkProgramExecutor.cs:61`；`context_and_replay.md` §1 | `VERIFIED`（每执行一值）+ `UNKNOWN`（实例身份语义） |
| `enc_key` 是否进入 proof statement | 否：`AddPrivate("in_enc_key", …)`（快照 L163/L292）；只在宿主做哈希一致性比对（快照 L180/L308 → 原始 L176/L302） | `ZkProgramExecutor.cs` 快照 L163/L292/L180/L308 | `VERIFIED` |
| 不同 proof 能否复用同一 execution_id | 无 execution_id 概念，问题退化为"能否复用同一 `enc_key`/context 重放"，无状态机约束 | `opening_and_randomness.md` §3 Q8/Q9；`context_and_replay.md` §3.3/§3.5 | `UNKNOWN` |
| 跨 execution 重放/错误拼接风险 | 无 execution 级锚点；跨 proof 无共享公开值 → 存在结构性风险，但是否可在当前实现复现 = `UNKNOWN` | `context_and_replay.md` §3.3；`d3-03-01/decision.md` §2 遗漏 3 | `CONSTRUCTED_ATTACK`（风险判断）/ `UNKNOWN`（复现） |

**Execution identity 边界结论**：当前架构**不存在** execution identity 这一对象。唯一的每执行随机量 `enc_key` 是私有 witness，既不被 verifier 持有，也未绑定 program/输入/T。因此"哪一次执行"这个问题在当前证明接口中**无法回答**，只能诉诸 prover/host 的自我声明（`VERIFIED` 缺失 + `INFERRED`）。

---

## 3. Public input provenance 字段级证据表

对每个字段回答六问：① 谁生成 ② 谁能修改 ③ 是否进入 proof statement ④ 是否受电路约束 ⑤ verifier 是否有独立期望值 ⑥ 是否与同一次 execution 绑定。

| 字段 | ① 生成者 | ② 可修改者 | ③ 进 statement | ④ 电路约束 | ⑤ verifier 独立期望值 | ⑥ execution 绑定 | 来源/行号 | 标签 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opcode table 四列 | prover（执行器 `AddPublic`） | prover | 是（public input） | 表本身为输入，电路逐行选择；整表无约束 | **否** | 否 | `ZkProgramExecutor.cs` 快照 L157-160；`plonk.rs:143-161` | `VERIFIED` |
| initial VM state（pc/reg 初值） | prover（私有输入） | prover | 否 | 逐步哈希链自洽 | 否 | 否 | `ZkVmExecutor...cs:134-136,177`；`source_trace_audit.md` A1 | `VERIFIED` |
| public input（如 n） | prover（执行器 `AddPublic`） | prover | 是（public input） | 取指电路 revealed op 使用 | **否** | 否 | `ZkProgramExecutor.cs` 快照 L265/L268/L283 | `VERIFIED` |
| global step counter（每步） | host C# 循环变量（快照 L113-116） | host/prover | 是（public input，快照 L149/L287） | 无电路递增约束；L87 依赖"MPC 参与方诚实"的假设 | 否 | 否 | `ZkProgramExecutor.cs` 快照 L113-116/L149/L287 | `VERIFIED` |
| final halt | VM 电路 public output（快照 L339 / 原始 L335 段） | prover witness 影响 | 是（public output） | 电路计算 `out_halt` | 否 | 否 | `ZkVmExecutor...cs:902-906`；`ZkProgramExecutor.cs` 快照 L339/L419-421 | `VERIFIED` |
| final T | host `ExecuteResult.GlobalStepCounter = globalStepCounter`（快照 L601 / 原始 L597） | host | **否**（不在 public input 集合） | 无 | 否 | 否 | `ZkProgramExecutor.cs` 快照 L600-601 | `VERIFIED` |
| memory trace hash | Prove 电路 `out_{i}_hash_mem_trace` public output + VM `out_hash_mem_trace` | prover witness | 是（public output） | 行内哈希/排序/值完整性约束 | 否 | 否 | `MemoryTraceProve...cs`（原始 L61-78）；`ZkProgramExecutor.cs` 快照 L410；跨电路靠 host 多重集比对 | `VERIFIED` |
| execution result hash | 无统一"执行结果摘要"对象；只有逐步哈希链与逐行 trace 哈希 | — | 部分（哈希 public output） | 逐步链自洽 | 否 | 否 | `source_trace_audit.md` A3；`opening_and_randomness.md` | `VERIFIED`（缺失）+ `UNKNOWN` |

**字段级结论（`VERIFIED` + `INFERRED`）**：全部八个字段中，"进 proof statement"的几项（opcode table、public input、step counter、halt、trace hash）**来源均为 prover/host**，verifier 独立期望值为**空**；final T 甚至不进 statement。没有任何字段满足"verifier 固定或可信取得"。宿主执行的 `if (...) throw` 检查（快照 L174-181/L306-332/L551-583）与哈希多重集比对（快照 L410 附近、`source_trace_audit.md` A2）都不进 R1CS、不进 public inputs，对 verifier 不可见——**不得当作 proof soundness 或 verifier 检查**。

---

## 4. 三类"看似可信实则不可信"的陷阱（本轮重点）

1. **public input 陷阱**：opcode table、step counter 是 public input，但值来自 prover JSON。若无 verifier 独立期望值逐项核对，它们只是"prover 声明的公开值"。
2. **public output 陷阱**：`out_halt`、trace 行哈希是电路 public output，值随 proof 公开，但 (a) 其正确性依赖输入来源（输入由 prover 提供），(b) halt 的 `break` 由 host 控制（快照 L419-421），(c) 最终 T 不由 halt 电路输出决定而由 host 记录（快照 L601）。公开 ≠ 可信锚点。
3. **随机量陷阱**：`enc_key` 每执行随机，看似可作"执行唯一性"来源，但它是私有 witness、不被 verifier 持有、未绑定 program/T/输入，且随机数随机性本身不提供"身份"或"防重放"语义（防重放需可信 `execution_id`+context 绑定+verifier 检查，`opening_and_randomness.md` §5 E）。

---

## 5. 本轮盘点结论

- Program identity、Execution identity、Public input provenance 三条线**共用同一个根缺口**：固定 commit 无独立 verifier 主体、无 verifier 固定/可信取得的期望值（VK、opcode table、T、execution_id 全缺）。
- 这构成一个**信任模型的整体缺口**，而非三个可分别打补丁的小问题：即便设计出 step counter 或承诺，若其锚点最终仍来自 prover，只是把自我声明重新包装。
- 本结论是"当前接口与信任边界"的判断（`VERIFIED` 缺失），不是"密码学上不可能"的证明。候选 statement 与 verifier 模型见 `execution_anchor_statement.md`、`verifier_vk_trust_model.md`，总判定见 `decision.md`。
