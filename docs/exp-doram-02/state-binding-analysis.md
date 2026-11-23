# state-binding-analysis.md — State Binding 组件审计（本轮核心）

> 基线：VDORAM artifact @ `10c90d35464620a35ddb1e2c29d2e8725acedd52` · 论文 NDSS'26 eprint 2025/039
> 标注：VERIFIED / INFERRED / UNKNOWN / BLOCKED
> 源码在 `source-evidence/` 与 `../source-snapshot/`；论文在 `paper/EXCERPTS.md`。

## 0. 结论（先给判定）

**这是四个组件中最关键、且唯一构成结构性阻断的组件。** 研究负责人的预判成立：需要的不是一个独立 ORAM 读写接口，而是一个"能被 VM 执行证明持续约束的状态机"。

现状分三层，必须严格区分（这也是任务包的硬性要求）：

| 层次 | 现状 | 标注 |
| --- | --- | --- |
| (1) MPC 内部正确计算状态 | 底层原语可计算加法秘密共享上的转换（INFERRED），但无 ORAM 状态对象、无跨 session 保存 | BLOCKED（持久化） |
| (2) SNARK 验证状态转换关系 | VDORAM 只证明**现有 5 类状态**（pc/registers/hash/memoryTrace）的转换完整性；**没有** ORAM 状态转换关系可证 | VERIFIED（现有范围）/ BLOCKED（ORAM 状态） |
| (3) 外部协议保证连续性与不可回滚 | 现有 `*Hash*` 机制保证 hash 连续，但仅覆盖 registers/pc/trace；ORAM 状态无对应承诺链 | VERIFIED（现有范围）/ BLOCKED（ORAM 状态） |

**净判定：BLOCKED**——在"每一步 ORAM 状态转换必须被公开 SNARK 验证并绑定到下一步"这一要求下，当前 VDORAM 架构没有可承接 ORAM 状态的状态槽，且 session 生命周期明确在步骤之间销毁份额。

## 1. 最小状态转换关系（设计草案，INFERRED）

按任务包要求定义：

```
(S_i, op_i, addr_i, value_i) -> (S_{i+1}, result_i)
```

其中候选赋值（依 VDORAM 威胁模型决定公开/秘密）：

| 量 | 建议可见性 | 理由 | 标注 |
| --- | --- | --- | --- |
| `S_i`（ORAM 状态：pos map + tree + stash 份额） | 秘密共享，且每步公开承诺 `H(S_i)` | 访问模式隐私要求 provers 不知 leaf/stash（论文 p8-9） | INFERRED |
| `op_i` | 秘密（opmasked）；仅 I/O/halt 例外公开 | 论文 p10-p11 "opmasked"、I/O 指令类型例外 | VERIFIED |
| `addr_i` | 秘密（`in_mem_addr = reg0`） | 源码 L230；论文 p10 隐私声明 | VERIFIED |
| `value_i` | 秘密（份额） | 论文 p5 加法共享 | VERIFIED |
| `result_i` | 秘密份额，绑定 `in_mem_val`（L302） | 源码 + R1 | VERIFIED |
| `H(S_i)` | 公开承诺（每步更新） | 需外部可验证连续性 | INFERRED（新设计） |

注意：即使 S_i 用公开承诺 `H(S_i)` 绑定，若 SNARK 不验证 `H(S_{i+1})` 与 `(S_i, op, addr, val) → S_{i+1}` 的关系，一个 malicious prover 仍可用**任意** `S_{i+1}` 的 hash 替换——即"承诺了状态"不等于"证明了转换"。这正是任务包 §D 要求的区分。

## 2. 现有 VDORAM 的跨 step 状态与绑定机制（VERIFIED）

### 2.1 存在的状态（源码 `ZkProgramExecutor.cs`）

| 状态 | 初始化 | 每步更新 | 可见性 |
| --- | --- | --- | --- |
| `thisProgramCounter` | L70 `zeroShare` | L364 `= privOutProgramCounter` | 秘密份额 |
| `thisRegisters` | L73 `Repeat(zeroShare, regCount)` | L376 `= privOutRegisters` | 秘密份额 |
| `hashThisProgramCounter` | L71 `Zero` | L358 `= pubOutHashNextProgramCounter` | 公开 hash |
| `hashThisRegisters` | L74 `Zero` | L370 `= pubOutHashNextRegisters` | 公开 hash |
| `memoryTrace` | L88 空 | L393-405 每步追加一行 | 秘密份额 |
| `hashMemoryTraceCount` | L103 空字典 | L108 计数递增 | 公开 hash 的多重集 |

**没有任何 ORAM 状态槽**（position map / tree / stash）。

### 2.2 绑定机制（VERIFIED）

- 每步执行电路输出 `out_hash_next_registers` / `out_hash_next_program_counter`（L355-371），VM 电路内部把 `hash(thisRegisters)` 与新寄存器绑定，外部检查 `hashThisRegisters != newOutHashThisRegisters` 则抛错（L322-328）。
- 每步 memory trace 行计算 `out_hash_mem_trace`（`ZkVmExecutorCircuitBoardGenerator.cs` L1013-1017），证明阶段重算 hash 并比对 count（L571-587）。
- **关键**：这些机制证明的是"每个状态（pc/registers/trace）在 VM 语义下的转换完整性"——即 pc 按指令前进、寄存器按 op 更新、trace 行一致。它们**不是** ORAM 状态转换证明，因为没有 ORAM 状态参与这些电路。

### 2.3 session 生命周期（BLOCKED 的直接证据）

- `MpcExecutorFactory.NextExecutor()`（`source-evidence/...MpcExecutorFactory.cs` L45-67）：
  - L46-48：若上一 executor 未完成则抛错。
  - L50：`this._prevMpcShareStorage?.UnregisterSession()`——新 session 前注销旧 session。
  - L52：用 `NextSessionID++` 建新 storage。
- `MpcSharedStorage.Dispose()`（`...MpcSharedStorage.cs` L47-55）清空 `_partyCompleted`、`_partyOnline`、`_exposedBoolShareVectors`、`_exposedBigIntegerShareVectors`。
- `MpcSharedStorageSessionManager.UnregisterSession()`（L95-111）移除 session。
- `ZkProgramExecutor` 每步多次调用 `NextExecutor`（L142/213/250/481/536）。

**结论**：MPC session 是短命的通信/份额交换容器，step 之间不保留份额。跨 step 状态只能靠**显式地作为电路输入输出**（registers 模式）。ORAM 状态要跨 step，必须仿此模式——但那意味着把整个 pos map + tree + stash 作为每一步电路的输入/输出线（规模随 N 线性），这既无现成实现，也与"公开证明每步转换"的约束冲突（见 §3、§4）。

## 3. 初始状态如何承诺（INFERRED / UNKNOWN）

- 现有系统初始化：`thisRegisters = zeroShare`、`hashThisRegisters = Zero`（L73-74），pc 同理（L70-71）——一个"全零 + 公开零 hash"的初始状态。
- ORAM 初始状态需：所有逻辑块为 dummy、随机 leaf 分配、stash 空、公开承诺 `H(S_0)`。
  - 随机 leaf 分配需可信初始化或 MPC 内生成（论文 trusted initializer 生成 preprocessing，p4）。
  - `H(S_0)` 必须在公开实例中固定，否则 prover 可选择初始状态。
- 本仓库无 `S_0`、无 `H(S_0)`、无 ORAM setup 电路——UNKNOWN（需新设计）。

## 4. 每步状态更新 + 下一步强制使用（BLOCKED）

这是最关键的一点，分两个子问题：

### 4.1 下一步能否强制使用上一步新状态？（现有 registers 可以，ORAM 不行）

- Registers 模式：`out_reg_i` 是电路私有输出（`ZkVmExecutorCircuitBoardGenerator.cs`），executor 把它赋给 `thisRegisters`（L376），下一步 `AddPrivate("in_this_reg_i", thisRegisters[i])`（L296-298）——**闭环成立**：下一步电路的输入份额就是上一步的输出份额，且 SNARK witness 覆盖这条线。
- ORAM 若要照做：需要每一步电路把 `S_{i+1}`（整个 ORAM 状态份额）作为输出，下一步作为输入。但：
  - 电路规模随 N（pos map）+ 树节点数 × Z + stash S 线性增长；每步都展开整个状态 → 与 T 相乘的成本（见 `complexity-model.md`）。
  - 更根本：现有 VM 电路的输出线集合是固定的（registers/pc/mem_val/trace/hash），**没有 ORAM 状态输出线**；要加必须改 `ZkVmExecutorCircuitBoardGenerator.cs` 的电路输出接口——这不是"接入一个接口"，而是改变 VM 电路契约。

判定：**BLOCKED**（无输出线/输入线契约，session 不保留份额）。

### 4.2 SNARK 是否验证"状态转换"而非"独立承诺"？（VERIFIED：现有只验证前者的一部分）

- 现有 collaborative zkSNARK 对 instruction fetch / execution / trace verification 电路生成证明（论文 p10 §IV-D step 11），witness 包含所有输入输出与中间值及 hash digest。
- 对 registers：SNARK 验证 `out_reg_i` 由 `in_this_reg_i` + 指令语义正确产生（电路约束），因此转换被证明，不只是承诺。
- 对 ORAM 状态：**没有**电路把 `S_i → S_{i+1}` 的 ORAM 语义（path read/write 正确性）展开为 R1CS 约束——因为 ORAM 电路不存在。若只加一个 `H(S_{i+1})` 承诺而不展开转换，则 malicious prover 可以对任意 `S_{i+1}` 出承诺，SNARK 无法拒绝（知识soundness 只保证"知道某个 witness"，不保证该 witness 是正确 ORAM 转换）。
- 论文明确其设计哲学："efficient proofs focused on only checking the integrity of RAM states, as opposed to validating the entire sequence of computations"（p5/p6）——即证明 RAM 状态完整性。ORAM 状态若要纳入，必须定义"ORAM 状态完整性"关系并做成 R1CS，这是一项新协议工作。

判定：**BLOCKED**（无可证的 ORAM 转换关系）。

## 5. 状态替换 / 跳步 / 重放 / 回滚（INFERRED / BLOCKED）

| 攻击 | 现有 registers/trace 防护 | ORAM 状态下 |
| --- | --- | --- |
| 状态替换（用别的 S） | `hashThisRegisters` 连续检查（L322-328） | 无 `H(S)` 链，可替换 → BLOCKED |
| 跳步（跳过若干 step） | 全局 `globalStepCounter` 公开递增（L116）；trace 时间戳单调（论文 p8） | 若 S 无 step 绑定，可跳 → BLOCKED |
| 重放（复用旧状态） | hash 链 + trace 时间戳防重放 | ORAM 无 hash 链 → BLOCKED |
| 回滚（回到先前 S） | 同上 | 同上 → BLOCKED |

**是否可能出现**：现有防替换机制**不能自动覆盖** ORAM 状态；除非把 `H(S_i)` 与 `globalStepCounter`、registers hash、trace hash 绑定进同一公开承诺链，并由 SNARK 约束每步转换——这正是缺失的部分。

## 6. Historical Log 与 ORAM 状态转换的一致性（INFERRED）

- 现有 HistoricalKV trace 行 `(addr, t, op, val)` 记录**逻辑**内存访问（论文 p8 Fig.4-5）；R1 的 `fetch_address/trace_address` 分离保持逻辑语义。
- ORAM 状态转换（leaf 重分配、stash 重排、路径回写）是**物理**状态变化，与逻辑 `(addr, val)` 无一一对应。
- 要求"Historical Log 与 ORAM 状态转换使用同一组操作语义"意味着：要么把物理操作也写入 trace（破坏访问模式隐私——leaf 是秘密），要么证明两者存在某种一致关系（需要新的 relation）。二者都无现成实现 → UNKNOWN / BLOCKED。
- 但有一点可借用：论文 p8-9 的 `Export()` 要求"导出全部历史含被覆盖值"，这正好是 R1 E1 的历史日志——**双结构中的历史侧已验证可保留**（E1 结论），缺的是 ORAM 侧状态绑定。

## 7. 最终状态与完整执行历史绑定（INFERRED / BLOCKED）

- 现有：`hashMemoryTraceCount`（L103-108）+ Prove 期 count 比对（L582）+ trace 排序一致性，把最终 trace 与执行历史绑定。
- ORAM 的最终状态 `S_T` 若不与 `H(S_0..S_T)` 链绑定，则无法证明"该 S_T 来自 T 步合法转换"。
- 需要的新机制（均无实现）：每步 `H(S_i)` 进入公开实例；SNARK 约束 `H(S_{i+1}) = Commit(Transition(S_i, op_i, addr_i, val_i))`；最终 `H(S_T)` 与 trace hash 一同公开。

## 8. 八项必答与三层区分汇总

| 任务包 §D 核查项 | 结论 | 标注 |
| --- | --- | --- |
| 初始状态如何承诺 | 无 ORAM 初始承诺；需新设 `H(S_0)` | UNKNOWN |
| 每次更新如何生成新承诺 | 无；现有只有 pc/reg/trace hash | BLOCKED |
| 下一步强制使用新状态 | registers 有闭环，ORAM 无（无输出/输入线、session 销毁） | BLOCKED |
| SNARK 验证转换 vs 独立承诺 | 现有验证 registers/pc/trace 转换；ORAM 无转换电路 | VERIFIED（范围）/ BLOCKED（ORAM） |
| Historical Log 同一操作语义 | 逻辑 trace 可保留；物理 ORAM 状态未绑定 | INFERRED/BLOCKED |
| 替换/跳步/重放/回滚 | 现有防护不覆盖 ORAM 状态 | BLOCKED |
| 最终状态绑定历史 | 无 H(S) 链 | BLOCKED |
| 三层区分 | (1) MPC 计算：BLOCKED 持久化；(2) SNARK 验证：BLOCKED 无关系；(3) 外部连续性：BLOCKED 无承诺链 | — |

**这是唯一的、最关键的系统性障碍**：缺的不是 ORAM 读写接口，而是"ORAM 状态转换可被 VM 执行证明持续约束的状态机"。在这一点解决之前，任何 Path ORAM 实现都无法接入 VDORAM 的公开证明流程。

## 9. 证据索引

- `source-evidence/...MpcExecutorFactory.cs` L45-67；`...MpcSharedStorage.cs` L47-55；`...MpcSharedStorageSessionManager.cs` L95-111。
- `../source-snapshot/ZkProgramExecutor.cs` L70-74/L88-108/L116/L205-236/L296-302/L322-328/L355-376/L393-412/L571-587。
- `../source-snapshot/ZkVmExecutorCircuitBoardGenerator.cs` L990-1017（trace 字段 + hash）。
- `../source-snapshot/MemoryTraceProveCircuitBoardGenerator.cs`（排序 + 值完整性）。
- `paper/EXCERPTS.md` p4（威胁模型）、p5/p6（"只检查 RAM 状态完整性"）、p8-9（HistoricalKV/线性扫描）、p10-11（ΠVDORAM 流程、隐私声明、安全定义）。
