# ABA-03 / Phase C：静态证书到执行 trace 的绑定分析

> 核心问题：**被 `addr<n` 约束的地址，是否就是 VM 实际执行的那个地址？** 本文只分析绑定路径，不实现电路。
>
> 关键源码事实（详见 `source_trace_audit.md`）：
> - `fetch_addr = thisRegisters[0]`（`ZkProgramExecutor.cs:225-226`）；
> - `trace_mem_addr` 在 Load/Store 时取自 `inRegisterWires[0]`（`ZkVmExecutorCircuitBoardGenerator.cs:224-227,989-997`），非内存步写 `p−1`；
> - 二者构造同源，但分处 Fetch 电路与 Executor 电路；现有跨电路一致性只靠执行器外部哈希核对（`:302-332,404-408,567-583`）；
> - verifier 只见公开哈希，不见 pc/reg/addr 明文；上游无整程序承诺。

## C1. 每步直接绑定

### 约束关系

对每个执行步 `i`，在同一个可验证关系中强制：

```
pc_0 = 0
(op_i, arg0_i, arg1_i, arg2_i) = Select(opcode_table, pc_i)
is_mem_op_i = (op_i = Load) OR (op_i = Store)

is_mem_op_i = 1  ⇒  fetch_addr_i = reg0_i = trace_addr_i
                     0 ≤ trace_addr_i < n
is_mem_op_i = 0  ⇒  trace_addr_i = p−1, trace_mem_val_i = 0

reg0_{i+1} = RegTransition(op_i, arg_i, reg_i, mem_val_i)   # 上游 :793-874
pc_{i+1}   = NextPC(op_i, pc_i, flags_i)                    # 上游 :376-384,466-497

program_hash = H_prog(opcode_table)                         # 新增公开锚点
```

`program_hash` 与整张表由 verifier 固定；`Select` 使用上游 `InstructionFetchCircuitBoardGenerator.cs:158-213` 的现有骨架。跨电路同一性用新增共享逐步承诺 `H_step(step,pc,opcode,reg0,is_mem_op)` 或两个电路输出同一个 `trace_addr` 公开承诺来闭合。

### 成本与性质（符号级）

- **约束规模**：每步增加 1 次地址范围检查（位分解 + Boolean + 比较器）、1 次 `fetch_addr=reg0=trace_addr` 同一性断言、1 次逐步承诺；`program_hash` 只在整表上算一次。无 gadget 级实测数据，数量标 `UNKNOWN`。
- **程序灵活性**：低。逐步约束与具体 opcode 表绑定，换程序就要换公开表与 `program_hash`。
- **完整性**：强。每个 `is_mem_op=1` 的步都被检查，不需要“静态访存点列表 → 动态事件”的映射，天然覆盖循环多次执行与未执行分支。
- **对现有代码侵入**：中等。上游已有 pc/opcode 选择、寄存器转移、trace 字段派生骨架；新增的是范围检查、公开 `program_hash`、以及跨电路地址同一性承诺。

## C2. 程序级访问事件摘要

### 构造

从 VM trace 派生**动态访问事件序列**

```
E = [(step_k, pc_k, opcode_k, addr_k)]_{k=1..m}
```

其中 `E` 恰好是全体 `is_mem_op=1` 的步按 step 递增排列的子序列；公开 `m = event_count`。再把静态证书中的访存点（PC 4/16/18/22/24/36，规则 R-INPUT/R-INNER/R-OUTPUT）映射到 `E` 并核对次数/区间。

### 必须处理的情况

| 情况 | 处理方式 | 若忽略会怎样 |
| --- | --- | --- |
| 循环同一 PC 多次执行 | 按 step 产生**多个**事件；证书 PC 只能作为“允许访问的 PC 集合”，不能作为事件数上限 | 把静态 PC 列表当动态列表会漏掉重复访问，安全性看似通过实则未覆盖 |
| dummy Fetch | 用 `is_mem_op=1` 过滤；Prove 电路本身忽略 `is_mem_op`（Prove 原始 L164-165），traces 中仍有 NegOne 行 | 把 dummy 计为真实事件会引入 `addr=p−1` 的伪访问 |
| step 0 | 无 trace 行（`ZkProgramExecutor.cs:201-203`），事件从 step≥1 开始 | 要求 step0 提供事件会与执行器语义冲突 |
| 分支未执行的静态访存 PC | 不产生事件；证书只能说明“若执行则该地址有界” | 要求每个静态 PC 至少出现一次会拒绝合法执行路径 |
| 程序提前终止 | 以 `out_halt` 步为界，公开 `event_count=m` 并证明 `E` 无遗漏 | 证明者可截断事件序列，隐藏越界访问 |
| 事件计数、顺序、完整性 | 需逐步 running index：遇到 `is_mem_op=1` 则 index+1；最后断言 `index = m`；并约束 step/pc 单调递增 | 只检查“出现的事件合法”无法排除“删掉的事件非法” |

### 成本与性质（符号级）

- **约束规模**：比 C1 多一套事件索引、递增/计数约束、以及 `event_count` 公开输入；`UNKNOWN` 具体数量。
- **程序灵活性**：高。静态证书可作为策略层复用，且事件序列本身可审计。
- **完整性**：依赖上述“无遗漏”约束；若只做摘要不做完整性，存在删除事件的攻击面。
- **对现有代码侵入**：高。上游 Prove 电路不接受 pc/opcode，也没有事件序列概念（`MemoryTraceProve...cs` 原始 L8、L43-49、L61-78、L80-212），需要新增一层电路或大改 trace 表示。

## C3. 比较与选择

| 维度 | C1 每步直接绑定 | C2 程序级事件摘要 |
| --- | --- | --- |
| 安全性假设 | 公开 opcode 表与 `program_hash` 由 verifier 固定；哈希抗碰撞；`fetch=reg0=trace_addr` 同一性在电路内闭合 | 同左，另加：事件序列完整性（无删/插/重排）可证 |
| 证明者可操纵空间 | 只能选择满足范围与程序语义的 reg0/witness；无法隐藏任何 `is_mem_op=1` 步 | 若完整性未闭合，可删去越界事件；闭合后与 C1 接近 |
| verifier 可检查信息 | `program_hash`、公开表、每步哈希承诺、`n`、`Nmax`、`event_count` 不需要 | 还需 `event_count` 与事件承诺；可见信息更多但接口更复杂 |
| 电路约束规模 | 每步一次范围检查 + 同一性断言；无事件索引 | 多一套索引/计数/单调性约束，规模更大（`UNKNOWN`） |
| 对现有 VDORAM 侵入 | 中：复用 IF/IE/trace 字段派生，新增范围检查与承诺 | 高：需新增事件层，Prove 电路当前无 pc/opcode 输入 |
| 循环支持 | 天然支持，每步独立检查 | 支持，但必须显式处理重复 PC 事件 |
| 条件分支支持 | 天然支持：未走到的步不产生约束 | 支持，但静态 PC 不得当成必达事件 |
| 与静态证书关系 | 可不依赖证书做安全，证书仅作离线文档 | 证书成为策略层，必须证明它与动态事件对应 |

### 选择

**最小可行候选：C1（每步直接绑定）**。理由：它不需要定义“静态 PC → 动态事件”的完整映射，就能保证任何真实 `Load/Store` 的地址都满足 `0≤addr<n`，直接回答本轮最关键的问题；对现有代码的侵入也小于 C2。

**本轮最终决策仍是 `HOLD`**（见 `decision.md`）。C1 要真正成立，还缺两个尚未在上游定义/核验的接口锚点：

1. `program_hash = H_prog(整张 opcode 表)` 作为 verifier 固定公开输入——上游完全没有整程序承诺（只有逐行哈希，且 preimage 含随机 `enc_key` 与 step）；
2. `fetch_addr = reg0 = trace_addr` 的**电路内**同一性——上游只用“同一 reg0 被两处使用”的构造事实 + 执行器外部哈希核对，verifier 看不到明文，也没有共享承诺。

在这两点闭合前，把 C1 写成“已可实现”会越过本轮边界；因此不发出 `GO_TO_MINIMAL_CIRCUIT_PROTOTYPE`。

## C4. 解除 HOLD 的最小条件

1. 明确 `H_prog` 的域分隔、输入编码（43 行 × 4 列）与公开输入接口，并给出 verifier 固定该值的协议步骤；
2. 明确 `fetch_addr` 与 `trace_addr` 的共享承诺位置（同一电路内断言，或两个电路输出同一公开承诺并由 verifier 核对）；
3. 在上述接口上做一个最小原型，验证“替换 opcode 表 / 替换 reg0 / 提供越界 addr”三类 witness 均被拒绝；
4. 再评估是否可把静态证书从“离线文档”提升为“被电路强制的策略层”。
