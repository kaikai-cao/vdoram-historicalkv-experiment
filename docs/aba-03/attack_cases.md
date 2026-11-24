# ABA-03 / Phase D：攻击反例设计（未实际执行）

> 标签口径：`VERIFIED` = 由固定源码直接确认的当前机制；`CONSTRUCTED` = 在规格/结构层面可写出的反例或设计缺陷，**未实际跑通证明系统**；`UNKNOWN` = 无证据，不宣称可构造或不可构造。
>
> 本轮没有运行任何电路、测试或证明生成；以下“可构造”均指**在缺失约束时的 witness/接口操纵空间**，不是已验证的实际攻击。

| # | 反例 | 攻击者控制什么 | 当前已有机制如何处理（证据） | 是否能构造通过验证的反例 | 需要新增什么约束才能拒绝 | 当前结论 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `n > Nmax` | 公开输入 `n`（`ZkProgramExecutor.cs:256-262` 只在 `PublicInput` 处 `AddPublic`，verifier 没有上界期望值） | 上游无 `n≤Nmax` 约束；`BubbleSortProgramGenerator.cs:79` 的 `globalStepsNoMoreThan` 只是执行器抛错阈值（`ZkProgramExecutor.cs:114-116`），不进入电路公开输入 | 结构可构造：当前没有任何电路约束比较 `n` 与 `Nmax` | B1：`n` 的 L 位 Boolean 分解 + 整元素字段等式 + 位串比较 `1≤n≤Nmax`；`2^L≤p` | `CONSTRUCTED`（结构可构造，未执行） |
| 2 | `addr = p−1` 绕过整数范围 | 私有 witness `reg0` / `trace_mem_addr` | `p−1` 是合法 dummy 哨兵 NegOne（`ZkVmExecutor...cs:941-943,989-997`）；Prove 电路明确忽略 `is_mem_op`（Prove 原始 L164-165）；对真实 Load/Store 没有范围检查 | 结构可构造：若只检查截断值 `(p−1) mod 2^L`（可能很小，如 `L=5` 时为 0）而不约束完整字段元素，就会把截断值误当作合法 `addr`；当前干脆没有比较。注意 `p` 为奇数，`p−1` 的低 L 位不可能全为 1 | B2：整元素字段等式 `addr=Σ2^j d_j` + Boolean + 位比较 `addr<n`；并用 `is_mem_op` 门控，非内存步才允许 `p−1` | `CONSTRUCTED` |
| 3 | 静态证书分析程序 A，实际执行程序 B | 公开 opcode 表（来自 `program.Opcodes`，`ZkProgramExecutor.cs:147-157`） | 证书是离线 Python 产物（`certificate.py:54-85`），绑定的是 Python `program_hash`；C# 执行从不读证书；`ZkProgramExecutor.cs:58` 直接取实例 opcode 表；无整程序承诺 | 结构可构造：两张表不同但各自哈希自洽，执行器外部核对不会发现“证书对应另一程序” | `program_hash = H_prog(整张 opcode 表)` 作为 verifier 固定公开输入；或把证书 digest 作为公开约束锚点 | `CONSTRUCTED` |
| 4 | PC 正确但 opcode 被替换 | opcode 表各行内容 | `InstructionFetchCircuitBoardGenerator.cs:158-213` 用 PC 选行；逐行哈希 `out_hash_opcode_table_row`（`:215-235`）与执行电路 `:243-263` 重算相等，但两边用的是**同一张被提交的表** | 结构可构造：把表中第 k 行改成 Store/Load 以外的值，行哈希随之重算，外部核对仍通过 | `program_hash` 固定整表 + 逐行承诺与整表承诺的包含关系；再按 `trace_binding_analysis.md` C1 逐步约束 `opcode` 语义 | `CONSTRUCTED` |
| 5 | 静态访存点存在，动态路径未经过该 PC | 分支标志/witness 路径 | 静态证书列出 PC 4/16/18/22/24/36；运行时没有把这些 PC 映射到事件，也没有要求它们出现 | 结构可构造：合法分支可跳过某个 PC；若策略要求“每个静态 PC 必须出现”，会误判；若策略只检查出现的事件，则跳过本身不构成越界 | 二选一：C1 对**每个** `is_mem_op=1` 步检查范围（不依赖静态 PC 必达）；或 C2 证明动态事件与证书映射一致 | `CONSTRUCTED`（设计层可构造） |
| 6 | 同一循环访存 PC 被执行多次 | 循环次数、`R0/R2/R3` 状态 | BubbleSort 内层 PC16/18/22/24 可重复执行（`BubbleSortProgramGenerator.cs:35-56`）；当前没有“静态 PC → 动态事件”的计数模型 | 结构可构造：把静态 PC 列表当作动态事件列表会少算重复访问，产生假阴性 | C2 中事件带 `step`，按 `is_mem_op` 逐步生成，允许同一 PC 多次出现，并以公开 `event_count` + 完整性约束闭合 | `CONSTRUCTED`（规格缺陷，未执行） |
| 7 | dummy Fetch 被错误计入真实访问事件 | 事件序列构造方式 | step>0 的非内存步仍调用 MemoryFetch，但 trace 写 `addr=p−1, val=0`（`ZkVmExecutor...cs:941-961,986-1007`）；Prove 电路忽略 `is_mem_op`（原始 L164-165） | 结构可构造：若验证方把 MemoryTrace 全行当访问事件，会引入伪越界地址 `p−1`，并高估事件数 | 用电路内派生的 `is_mem_op` 过滤事件；C1/C2 均须证明事件恰好对应 `is_mem_op=1` 的步，不能用 trace 行数代替事件数 | `CONSTRUCTED` |
| 8 | step 0 不执行 MemoryFetch，但其 trace 行被误当作访问事件 | 验证方事件接口设计 | `ZkProgramExecutor.cs:201-203` step0 直接 `memVal=zeroShare`、不构造 Fetch；但 `:389-402` 无条件追加一行 MemoryTrace（`AddMemoryTrace` 在 `:85-97` 直接 `memoryTrace.Add`）；该行由 `out_trace_*` 生成，`is_mem_op=0`（step0 选中 PC0 的非内存指令 `Set`）、地址哨兵 `p−1`、值 0；`MemoryTraceFetchCircuitBoardGenerator.cs:8` 的 `traceCount>0` 只约束 Fetch 电路实例，不表示 step0 无 trace 行 | 结构可构造（规格不一致）：把这行计为真实访问事件会与 `is_mem_op=0` 冲突；合法执行会被错误拒绝或事件数被高估 | 事件必须按电路内 `is_mem_op` 过滤；`event_count` 只计真实访存事件，不等于 MemoryTrace 行数；step0 行只能作为 dummy 行存在 | `CONSTRUCTED`（规格缺陷） |
| 9 | `thisRegisters[0]` 与 trace address 不一致 | 尝试同时提供两个不同的 witness 值 | Fetch 用 `thisRegisters[0]`（`ZkProgramExecutor.cs:226`）；`trace_mem_addr` 用 `inRegisterWires[0]`（`ZkVmExecutor...cs:227,989-997`）；构造同源，且状态哈希链连续（`:302-332`） | 当前构造下不可直接构造；若强行不同，需同时破坏哈希链。没有实测碰撞/绕过 | 显式电路内断言 `fetch_addr_i = reg0_i = trace_addr_i`，或两个电路输出共享公开逐步承诺 | `UNKNOWN`（未实际跑通，不能宣称成功绕过） |
| 10 | witness 给合法地址，真实执行状态越界 | 私有 reg0/witness 与哈希链 | pc/reg/addr 都是秘密分享，verifier 只见哈希（`ZkProgramExecutor.cs:226,292-294,488`；`:406`）；没有任何 `addr<n` 范围约束 | 结构可构造：在缺少 B2 的情况下，witness 中的“小地址”不会被约束成真实 reg0 的整数范围内值 | B2 范围检查 + B3 地址同一性；三者必须绑定在同一个可验证关系中 | `CONSTRUCTED`（结构可构造，未执行） |

## 额外边界说明

- 反例 1–8、10 的“可构造”来自**缺失约束**的接口/规格分析；若把 `UNKNOWN` 误写成“已验证攻击成功”属于 overclaim，本轮避免。
- 反例 9 是唯一一个当前构造已提供部分防护的点，但因缺少跨电路显式等式，安全性目前只是 `INFERRED`，不是 `VERIFIED`。
- 十个案例中没有任何一个在本轮实际运行；不产生新的实验数据。
