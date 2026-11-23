# ABA-01-C1：静态分析器与证书检查器健全性补丁

## 1. 任务边界

只修 ABA-01 的两个核心缺陷：分析器漏检关键状态寄存器初始化、独立检查器没有验证证明关系。固定程序仍是 `BDS-SDU/vdoram-artifacts` @ `10c90d35` 的 Bubble Sort（43 条指令，PC 0–42）。不接 R1CS，不碰 HistoricalKV，不改上游。

## 2. M1 反例复现（阶段 A）

修改前（`src/aba_01/analyzer.py` v0.1 / `certificate.py` v1）实际运行结果：

```text
PC10 变体：Instr("Set", 2, FIELD_PRIME - 1)
analyze(mutated, InputConstraint(1,16)).status      == "PASS"
analyze(...).reasons                                 == []
build_certificate(...).status                        == "PASS"
verify_certificate(cert, mutated, require_pass=True) == CheckResult(ok=True, errors=())
```

 auditor 手工伪造证书文本字段同样通过：`address_expr="forged"`、`dependencies=["forged"]`、`address_def_pc=999` 仍得到 `ok=True`。这与任务预期一致，按实际代码如实记录，未修改记录迎合预期。

**为什么原分析器漏检：**

1. 原 `analyze()` 只检查 `R15/R8/R6/R1/R0` 的写集合，**完全没有检查 R2 与 R3**。PC10 从 `Set R2,0` 改成 `Set R2,p−1` 不改变任何被检查的写集合。
2. 内层循环判定只用 `_has_instr(head, tail, Instr("Add",3,2,15))` 等**存在性检查**，不验证 R2 初值、R3 定义源、R2 更新、PC13 守卫、PC14 退出、PC20 分支汇合之间的数据流关系。域运算下 `(p−1)+1 ≡ 0`，守卫 `R3<R1` 成立而真实地址仍为 `p−1`，存在性模式无法区分。
3. 原检查器对 `address_expr`/`dependencies` 只要求非空，`interval` 只比较字符串，`address_def_pc` 等结构化字段根本没被读取。

## 3. 分析器新增不变量（阶段 B）

`ANALYZER_VERSION` 升为 `aba01-static-analyzer-0.2-c1`。新增集中式 `global_structure_reasons(program)`，在任何访问分类之前执行：

| 检查项 | 具体要求 |
| --- | --- |
| 写集合 | R0/R1/R2/R3/R6/R8/R15 的 `writers_of()` 必须精确等于固定程序集合。R2 的全写集合为 `(3,6,7,10,26,36,39,40)`（它在输入/输出循环兼作临时寄存器，不是异常）；R3 仅 `(12,)`。 |
| 初始化 | PC10 必须是 `Set R2,0`；PC12 必须是 `Add R3,R2,R15`；PC26 必须是 `Move R2,R3`；PC0 `Set R15,1`；PC2/PC35 分别是输入/输出循环 R0 初始化，且紧邻各自 loop head 之前。 |
| 更新 | PC5/PC38 `Add R0,R0,R15`；PC11 `Set R6,0`、PC25 `Add R6,R6,R15`；PC32 `Sub R1,R1,R15`；R1 仅 PublicInput + 受守卫递减；R8 仅 PC9 `Move R8,R1` 且不在循环内。 |
| 守卫 | PC8 必须识别为反向 `R0<R1`；PC14 为 `R3<R1`；PC31 为 `0<R6`；PC41 为反向 `R0<R8`。任一守卫模式变化即失败。 |
| 控制流位置 | PC5/10/11/12/26/32/38 必须位于期望循环内；PC9 必须在所有循环外；PC20 必须是 `JumpIfZero 7,26`（交换/不交换分支都汇合到 PC26）。 |

保留原四组循环不变量 I1–I4，并把 `R2=0`（PC10）、`R3=R2+1`（PC12）、`R2=R3`（PC26）、分支汇合 PC26 写入 I3 文本。任一全局检查失败：所有访问降级为 `UNKNOWN`，整体 `UNKNOWN`，不会 PASS。对无法继续证明的程序返回 `UNKNOWN`；仅输入约束本身不可能满足（如 `n>Nmax`、`n=0`）返回 `FAIL`。

修复后 M1 实际结果：`status=UNKNOWN`，reasons 含 `PC10 is ['Set', 2, p-1, 0], expected ['Set', 2, 0, 0]` 和 `sort inner-loop pattern ... not recognised`。

## 4. 结构化证书字段（阶段 C1）

每条访存现在包含：`pc`、`op`、`address_register`(=VM 地址线 R0)、`address_def_pc`、`address_source_register`、`loop_head`、`guard_pc`、`proof_rule`、`interval`、`status`、`dependencies`、`reason`。`address_expr` 保留仅供人读，**不参与验证**。schema 升为 `aba-01-c1/v1`。

原始程序（默认 `1≤n≤16`）真实证书样例：

```text
status: PASS   schema: aba-01-c1/v1   scope: STATIC_CERTIFICATE_PROTOTYPE
program_hash: sha256:2a91193fef2fb08ceccd92b9664444a4152c6fec806e51f8005de8b74d2741a6
instruction_count: 43
PC4  Store  addr_reg=0 def=2  src=None loop=3  guard=8  rule=R-INPUT  [0,n-1] PASS
PC16 Load   addr_reg=0 def=15 src=2   loop=12 guard=14 rule=R-INNER  [0,n-1] PASS
PC18 Load   addr_reg=0 def=17 src=3   loop=12 guard=14 rule=R-INNER  [0,n-1] PASS
PC22 Store  addr_reg=0 def=21 src=2   loop=12 guard=14 rule=R-INNER  [0,n-1] PASS
PC24 Store  addr_reg=0 def=23 src=3   loop=12 guard=14 rule=R-INNER  [0,n-1] PASS
PC36 Load   addr_reg=0 def=35 src=None loop=36 guard=41 rule=R-OUTPUT [0,n-1] PASS
field_conditions: n_range:PASS, field_no_wrap:PASS,
                  bit_decomposition:ASSUMED, bool_not:ASSUMED
```

## 5. 独立检查器新增规则（阶段 C2/C3）

`verify_certificate()` **不调用 `analyze()`**：模块级 mock 让 `analyze()` 抛异常后，`verify_certificate(cert, P, require_pass=True)` 仍 `ok=True`（测试 `test_checker_never_calls_analyze`）。检查器自带一套独立 CFG/guard 推导与固定结构检查，逐项比对证书字段：

- **绑定**：schema/scope/status/analyzer version、code name、source path、source commit、program hash、instruction count(=43)、field prime/bit size、`bound_register==1`、`nmax` 与 `n_min/n_max` 一致、`1≤n_min≤n_max`、`Nmax<p`、`Nmax²<p`。
- **访存集合**：声明的每个 PC 必须是当前程序真实 Load/Store，`op` 一致，全覆盖、无重复；非访存 PC 不得伪装。
- **独立重算**：从绑定程序重算 `loop_head`、`guard_pc`、`address_def_pc`、`address_source_register`、`proof_rule`，与证书字段逐一比对。例：篡改 `address_def_pc=999` → `PC 4 address_def_pc 999 != program-derived 2` 且 R-INPUT 规则再报 `address def is not input counter`；篡改 `guard_pc=999` → `PC 16 guard_pc 999 != program-derived 14`；篡改 `proof_rule='R-OUTPUT'` → `PC 16 proof_rule 'R-OUTPUT' != program-derived 'R-INNER'`。
- **R-INPUT**：R15=1、PC2 `Set R0,0`、PC5 `Add R0,R0,R15`、PC6/7/8 守卫序列、R1 是 PublicInput 且仅受守卫递减、地址定义必须是输入计数器。
- **R-INNER**：R2 初值 0（PC10）+ 全写集合、R3 唯一写点 PC12 `Add R3,R2,R15`、PC26 `Move R2,R3`、R6 结构、PC13/14 守卫与退出、PC20 汇合到 PC26、R1 绑定、R0 必须来自 PC15/21 的 R2 或 PC17/23 的 R3 且源寄存器与定义一致。
- **R-OUTPUT**：R8 是初始 R1 副本且不再写、PC35 初始化、PC38 递增、PC39/40/41 守卫 `R0<R8`、地址定义是输出计数器。
- **整体 PASS**：额外要求程序通过独立固定结构检查、所有访存 PASS、无 reasons；`require_pass=True` 拒绝非 PASS。

## 6. 返回 UNKNOWN / 拒绝的情形

- 关键寄存器写集合、初始化值、更新指令、守卫序列或循环位置被破坏：分析器 `UNKNOWN`，任何伪造 PASS 被检查器拒绝；
- 控制流或地址表达式无法识别：该访存 `UNKNOWN`，不乐观接受；
- 输入约束不可能（`n>Nmax`、`n=0`）：`FAIL`；
- 证书字段与程序独立推导不一致、访存点覆盖不符、非访存 PC、重复/伪装/放宽区间：检查器拒绝。

## 7. 能力边界

这是**固定 Bubble Sort + 有限证明规则**的健全性补丁：分析器/检查器不是通用静态分析器，不是 Lean/Coq/SMT 定理证明器；不重放运行时寄存器/内存 trace，不代替 R1CS 约束，不证明 MPC 或协同 SNARK 安全性。静态规则通过 ≠ 端到端密码学证明。
