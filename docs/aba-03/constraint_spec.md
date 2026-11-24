# ABA-03 / Phase B：地址约束规格（仅规格，不实现）

> 固定域：BLS12-377 标量域 `F_p`；`p = 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`，位长 253（实验仓 `src/aba_01/cfg.py:20-23`）。上游 `Field.cs:14-25` 只保证 `0 ≤ value < p`，不提供整数序。
>
> 本文只写**待实现的约束关系**，不声称 R1CS/Halo2 已实现，不给出未测量的约束数。

## 0. 变量与定义

| 符号 | 域 / 类型 | 角色 | 现有状态 |
| --- | --- | --- | --- |
| `Nmax` | 公开常量（建议随电路固定；若做公开输入须由 verifier 固定） | 最大数组容量，`n ≤ Nmax` | 上游无；实验证书 `CONSTRUCTED` |
| `n` | `F_p`；**公开输入** | 程序输入长度；`ZkProgramExecutor.cs:256-262` 在 `PublicInput` 处 `AddPublic` | 上游公开但**无界** `VERIFIED_SOURCE` |
| `addr_i` | `F_p`；私有 witness | 第 i 步真实访存地址；实现上等于 `trace_mem_addr_i` | 上游私有输出 `VERIFIED_SOURCE` |
| `pc_i` | `F_p`；私有 witness | 第 i 步 PC；step 0 电路内归零 | 上游私有输入 `VERIFIED_SOURCE` |
| `opcode_i` | 枚举字节（域元素表示）；由公开 opcode 表按 `pc_i` 选出 | 第 i 步操作类型 | 上游公开表 + 私有选中行 `VERIFIED_SOURCE` |
| `program_id` / `program_hash` | 公开承诺 | 整张 opcode 表的身份锚点 | 上游**不存在**整程序承诺 `VERIFIED_SOURCE`（缺失） |
| `step_i` | 公开值 | 全局步计数；`ZkProgramExecutor.cs:145` `AddPublic` | 上游已有 `VERIFIED_SOURCE` |
| `is_mem_op_i` | `{0,1}` | `Load OR Store`，由 opcode 在电路内导出 | 上游 `ZkVmExecutor...cs:968-976` `VERIFIED_SOURCE` |
| `fetch_addr_i` | `F_p`；私有 witness | MemoryFetch 电路实际查找地址 | 上游 = `thisRegisters[0]`（`ZkProgramExecutor.cs:226`）`VERIFIED_SOURCE` |
| `reg0_i` | `F_p`；私有 witness | VM 地址寄存器 | 上游 `ZkVmExecutor...cs:227` `VERIFIED_SOURCE` |

**记法约定**：`L = bit_length(Nmax)`，即 `2^{L-1} ≤ Nmax < 2^L`。必须满足 **`2^L ≤ p`**（p 极大，实际 Nmax 很小时自动成立）。此条件是本文所有小范围分解不发生字段回绕的基础。

## B1. 输入范围 `1 ≤ n ≤ Nmax`

### 候选约束

1. **公开性**：`n` 必须是 verifier 可见的公开输入；不能只放在 witness 里。
2. **规范位分解**：引入 `L` 个 witness 位 `c_0..c_{L-1}`，逐位强制 Boolean：
   `c_j·(c_j − 1) = 0`
   并强制字段等式：
   `n = Σ_{j=0}^{L-1} 2^j · c_j   (in F_p)`
   因为 `Σ 2^j c_j ≤ 2^L − 1 < p`，该等式在域中成立即意味着 `n` 的整数代表元就是这个小和，**不存在模 p 回绕**。
3. **下界**：`n ≠ 0`，等价 `OR_j c_j = 1`（或引入辅助位 `z = Σ c_j`，约束 `z ≥ 1`）。
4. **上界**：用位比较器强制 `Σ 2^j c_j ≤ Nmax`；比较在**整数位串**上做，不在域序上做。
5. **容量关系**：`Nmax < p` 只是必要非充分。真正需要的是 `2^L ≤ p`；否则 `L` 位和可能绕过域表示唯一性。另需 `Nmax+1 < p` 以避免任何 `n+1` 辅助量回绕（即使本规格不用 `n+1` 也建议保留）。

### 是否足够

**不足够**。`n≤Nmax` 只限制输入长度，完全不限制 `addr_i`；必须配合 B2、B3。

### 风险点

- 若只把 `n` 的“低 L 位”交给比较器而不强制字段等式，证明者可给出高位非零的字段元素，低 L 位看起来合法但整体不等。
- 若用域上的 `<` 比较（例如 `n < Nmax` 直接写成域元素比较），这是**无意义**的：`F_p` 没有整数序；必须位分解后比较。

## B2. 地址范围 `0 ≤ addr_i < n`

### 候选约束

对第 i 步：

1. **地址是字段元素**：`addr_i = trace_mem_addr_i = reg0_i`（真实访存时），由上游 `ZkVmExecutorCircuitBoardGenerator.cs:224-227,989-997` 构造；本规格要求把它显式约束成一个可检查的等式，而不是只依赖构造同源。
2. **规范位分解**：引入 `L` 位 `d_{i,j}`，逐位 Boolean，并强制
   `addr_i = Σ_{j=0}^{L-1} 2^j · d_{i,j}   (in F_p)`
   同样由 `2^L ≤ p` 排除域回绕。
3. **整数比较**：在位串上强制 `addr_i < n`（用 `d` 与 `c` 的位比较器），**不得**用域元素大小比较。
4. **分情况门控**：
   - `is_mem_op_i = 1` ⇒ 强制上述范围检查；
   - `is_mem_op_i = 0` ⇒ 强制 `addr_i = p−1`（NegOne 哨兵）且 `trace_mem_val_i = 0`，与上游 `ZkVmExecutor...cs:941-961,986-1007` 一致。
5. **字段别名防御**：`p−1` 的低 L 位可能全部为 1；仅检查低位会把它误判为一个“小整数”。第 2 条的**整元素字段等式**排除了这一点：`p−1` 不满足 `< 2^L` 的小和表示。因此必须同时做“完整字段等式 + 位比较”，不能二选一。

### 是否足够

**单独不足够**。它保证“被检查的 witness 地址在范围内”，但尚未保证该地址就是 VM 实际执行时用于访存的地址；见 B3。

## B3. 程序语义与 trace 绑定

### 必须存在的约束关系

1. **程序身份锚点（新增）**：
   - 公开 `program_hash = H_prog(全部 opcode 行)`，verifier 用固定期望值核对；
   - 整张 opcode 表仍是公开输入（上游 `InstructionFetchCircuitBoardGenerator.cs:126-156`），但必须由 verifier 固定，而不是由 prover 自由提交；
   - 上游只有逐行 `out_hash_opcode_table_row`（`InstructionFetch...cs:215-235`）和含 step/随机 `enc_key` 的状态哈希（`ZkProgramExecutor.cs:61`），**没有**整程序承诺，故此项为新增公开输入 + 新增承诺。
2. **PC ↔ opcode（上游已有骨架，需外部锚定）**：
   - `pc_0 = 0`；`pc_i` 经 `FieldEquals` 选中 opcode 表行（`InstructionFetch...cs:158-169`）；
   - `opcode_i, arg0_i, arg1_i, arg2_i` 必须来自被 `program_hash` 锚定的那张表；
   - 下一 PC 由操作语义决定：默认 `pc+1`（`ZkVmExecutor...cs:376-384`），跳转由 `JumpIfZero`（`:466-497`）处理。
3. **opcode ↔ 真实访存（上游电路已推导，需显式断言）**：
   - `is_mem_op_i = (opcode_i = Load) OR (opcode_i = Store)`（`:968-976`）；
   - Load/Store 地址取 `reg0_i`（`:224-227,989-997`）；
   - `Store` 写值取 `reg{arg0}_i`（`:929-937`），`Load` 读值来自 `in_mem_val_i`（`:220-222`）。
4. **地址同一性（关键新增）**：
   - 断言 `fetch_addr_i = reg0_i = addr_i`；
   - 上游中 `fetch_addr_i` 来自 `thisRegisters[0]`（`ZkProgramExecutor.cs:226`），`addr_i` 来自 `inRegisterWires[0]`（`ZkVmExecutor...cs:227`），构造同源但**分属不同电路**，没有 in-circuit 等式；
   - 最小做法是引入一个共享的公开逐步承诺（例如 `H_step(magic, step, pc, opcode, reg0, is_mem_op)`），两个电路都输出它，由 verifier 核对；更彻底的做法是把地址断言放进同一个电路。
5. **寄存器状态转移（上游已有，需复核可复用）**：`out_reg_i` 的组合在 `ZkVmExecutor...cs:793-874`，执行器 `:369-373` 写回；当前哈希链保证“同一次执行自洽”（`:302-332`），但不锚定外部固定值。需要确认这些约束能否被 verifier 直接检查，而不是只检查哈希摘要。
6. **静态证书的角色必须明确二选一**：
   - **不依赖证书做安全**：对**每一个** `is_mem_op_i=1` 的步执行 B2，则任意程序都无法产生越界访问；静态证书只是离线文档，其 PC 列表不参与验证；
   - **依赖证书做优化**：必须额外证明动态事件序列与证书的访存点集合/次数一致（见 `trace_binding_analysis.md` 的 C2），否则静态 PC 列表不能当成动态事件列表。

### 是否足够

B1 + B2 + B3 的第 1–5 项构成一条完整的安全链：**公开锚定的程序表 → 逐步 pc/opcode → 派生 is_mem_op 与 reg0 → 被范围检查的地址 = VM 实际 fetch 地址**。但第 4 项和第 5 项的接口在上游尚未定义/核验，因此本轮只给出规格，不判定已可实现。

## B4. 本规格明确不做的事

- 不证明 `addr<n` 的 R1CS 映射已经写出。
- 不证明 Halo2 电路已经实现或协同证明后端可用。
- 不把静态证书 `PASS` 当作运行时已强制。
- 不给出任何未实测的约束数、witness 数或性能数字（见 `validation.md`）。
