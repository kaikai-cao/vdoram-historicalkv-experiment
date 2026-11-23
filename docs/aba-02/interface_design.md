# ABA-02 阶段 D：最小可验证的有界地址域系统接口（设计，不实现）

本阶段不实现任何电路，只给出若要把“有限地址域”作为系统接口所需的最小、可验证设计，并明确各层的证明责任。

## 1. 候选接口元组

对 BubbleSort（最明确候选）：

```text
(program_id, Nmax, n, input_constraints)
= ("BubbleSort", Nmax, n, 1 ≤ n ≤ Nmax, Nmax < p, [Nmax² < p 仅在确有乘法时需要])
```

- `program_id`：`BubbleSort` + 固定上游 commit `10c90d35` + 程序哈希（ABA-01-C1 的 `program.digest()`）。
- `Nmax`：容量上界，作为**新的**公共输入/电路参数（上游当前没有）。
- `n`：数组长度，上游已是公共输入（`BubbleSortProgramGenerator.cs` L19 `PublicInput 1`），但当前无范围约束。
- `input_constraints`：`1≤n≤Nmax` 必须成为受约束的公共语句。

BubbleSort 无字段乘法（地址线性），故 `Nmax²<p` 不是必须；SlidingWindow 有 `R0±k` 与字段累加，需要逐项增加整数语义约束后才可套用；ReverseInput 有减法 `R1−1`，需要 `n≥1` 与无下溢证明。

## 2. 七项责任划分

1. **Nmax 由谁选择**：由部署方/证明语句构造者在编译时或证明系统初始化时选定，作为公共参数写入证明语句；不是程序自身输入，也不是当前 `GlobalStepsNoMoreThan`（后者只是执行步长阈值，`ZkProgramExecutor.cs` L114–L116）。
2. **n 的公开性**：上游已把 n 作为公共输入（L19），应保持公开；私有的是数组元素（L21）。
3. **谁检查 `n≤Nmax`**：必须在**电路/证明系统**中约束（新增公共输入约束），不能只由调用方在链下检查。当前执行器无任何此类检查。
4. **范围约束的位置**：在 per-step 执行电路的公共输入/语句层，把 `n_min≤n≤Nmax` 作为 witness 外公开值并加约束；`Nmax<p`（及需要时的 `Nmax²<p`）作为语句常量。仅靠 LessThan gadget 的 253 位分解不足以约束 n 的上界。
5. **真实地址与程序级证书的关联**：ABA-01-C1 证书的每条访存含结构化字段（`loop_head`/`guard_pc`/`address_def_pc`/`address_source_register`/`proof_rule`）；执行电路需为每一步 Load/Store 提供 `addr<n`（或 `addr≤Nmax−1`）的电路内证明，并把该 per-step 事实与证书中的地址定义链规则对应。证书证明“程序结构推出地址界”，电路证明“本次执行地址满足该界”，两者是不同层，不能相互替代。
6. **程序哈希绑定证书**：证书 `program.program_hash` 已是规范指令序列的 sha256（ABA-01-C1 `cfg.py` `Program.digest()`）；接口应把该哈希作为证明语句的公开值，使证书只对该指令序列有效。
7. **失效机制**：任何指令变更（哈希变化）、`Nmax`/输入约束变化、或 analyzer/schema 版本变化（当前 `aba01-static-analyzer-0.2-c1`、`aba-01-c1/v1`）都必须使旧证书失效；检查器 `verify_certificate()` 已实现哈希/版本/指令数/source path/source commit 核对，电路层需复用同一绑定值。

## 3. 各层证明能力边界

| 层 | 能证明/验证 | 不能证明 |
| --- | --- | --- |
| 静态分析器（`analyze()`） | 固定程序结构下地址表达式可推出 `[0,n−1]`，关键寄存器写集合/守卫/数据流 | 本次执行的真实地址；n 的实际取值；电路是否已约束 n |
| 独立证书检查器（`verify_certificate()`） | 证书结构化字段与绑定程序一致、R-INPUT/R-INNER/R-OUTPUT 规则、哈希/版本/指令数绑定；不调用分析器 | 不重放执行 trace；不验证任意程序；不代替 R1CS；不证明 MPC/SNARK 安全 |
| VM 执行电路（需新增） | 每步 opcode/寄存器/地址的真实执行关系；新增 `n≤Nmax` 与 `addr<n` 约束 | 当前上游没有这些约束；`GlobalStepsNoMoreThan` 只是步长阈值 |
| 最终证明系统（需新增） | 把上述语句接入 SNARK/MPC 证明，绑定公开输入、程序哈希、证书 | 当前未实现；不声称静态证书已等价于密码学证明 |

## 4. 最小设计结论

- 可行的接口在逻辑上可定义，但**上游当前没有 Nmax 接口，也没有 n 的范围约束电路**；这是新增构造，不能描述为现有能力。
- 最成熟候选是 BubbleSort（已有静态证书和独立检查器）；ReverseInput/SlidingWindow 还需各自的静态规则与更严格的整数无回绕约束。
- `n=0` 的程序语义缺陷必须在接口层明确禁止（要求 `n≥1`），不能假设程序自行处理。
