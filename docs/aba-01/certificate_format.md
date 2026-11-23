# ABA-01 阶段 D：地址域证书格式与静态原型

## 1. 边界声明（重要）

本原型生成一个**静态证书原型（STATIC_CERTIFICATE_PROTOTYPE）**和一个独立结构检查器。
它证明的是“给定程序结构与输入约束，静态分析可推出全部 Load/Store 地址属于 `[0,n−1] ⊆ [0,Nmax−1]`”。
它**不是**端到端密码学证明：证书没有接入真实 R1CS 执行关系，没有约束 VM 执行时寄存器/内存 trace，也没有证明 `n ≤ Nmax` 由电路强制。

## 2. 实现文件与语言选择

沿用实验仓库既有 Python + `src/`/`tests/` 结构（与 EXP-DORAM 系列一致），未改动任何既有实验文件或上游 VDORAM：

- `src/aba_01/cfg.py`：固定 commit 的 42 条指令转录、Program 表示、规范 JSON 序列化与 `sha256` 绑定、CFG 后继与写寄存器集合。
- `src/aba_01/analyzer.py`：基于 CFG 回边与指令模式的静态分析器；输出逐访问点事实、不变量与 Field 条件。
- `src/aba_01/certificate.py`：证书生成与**不重跑分析器**的独立结构/哈希/范围检查器。
- `tests/test_aba_01.py`：正向、8 类负向、边界和证书失效测试。

## 3. 证书字段（schema `aba-01/v1`）

| 字段 | 含义 |
| --- | --- |
| `schema` | 固定为 `aba-01/v1` |
| `scope` | 固定为 `STATIC_CERTIFICATE_PROTOTYPE` |
| `status` | `PASS` / `FAIL` / `UNKNOWN` |
| `program.code_name` | `BubbleSort` |
| `program.source_commit` | `10c90d35464620a35ddb1e2c29d2e8725acedd52` |
| `program.source_path` | 固定上游路径（BubbleSortProgramGenerator.cs） |
| `program.program_hash` | `sha256:` + 规范指令序列摘要；任何指令变动都会改变它 |
| `program.instruction_sequence_id` | 摘要前 12 hex，便于人工比对 |
| `program.instruction_count` | 42 |
| `field.prime_hex` / `bit_size` | BLS12-377 标量域 / 253 |
| `nmax` | 公开容量上界 |
| `input_constraint` | `n_min`, `n_max`, `bound_register`；本原型要求 `1≤n≤Nmax` |
| `memory_accesses[]` | 每条 Load/Store 的 `pc`, `op`, `address_def_pc`, `address_expr`, `interval`, `status`, `dependencies`, `reason` |
| `invariants[]` | I1–I4 文本及其证明角色 |
| `field_conditions[]` | `n_range`, `field_no_wrap`, `bit_decomposition`, `bool_not` 的状态与依据 |
| `analyzer_version` | `aba01-static-analyzer-0.1` |
| `reasons[]` | 无法证明 / 不一致的具体原因 |

## 4. 生成规则（不得手工填写结论）

`build_certificate(program, constraint)` 调用 `analyze()`：

1. **输入约束不一致**（`n_min<1`、`n_max<n_min`、`Nmax≥p`、`Nmax²≥p`）→ `FAIL`。
2. 全局寄存器角色检查：R15 恒 1、R8 恒为初始 R1 的副本、R6 仅两个写点、R1 仅 PublicInput 与受守卫递减、R0 仅白名单定义链。任一失败 → 所有访问 `UNKNOWN`。
3. 由 CFG 回边识别 4 个循环；由 `LessThan`/`Not`/`JumpIfZero` 模式识别守卫，而不是按 PC 硬编码。
4. 输入/输出循环：计数器 R0 从 0 递增，守卫分别以 R1=n / R8=n 为上界 → 地址 `[0,n−1]`。
5. 排序内层：`R3=R2+1`、守卫 `R3<R1`、合并点 `R2=R3`；地址必须是 `Move R0,R2` 或 `Move R0,R3`，且外层 `R1≥1`、有 `Sub R1,R1,one` 的受守卫递减 → 地址 `[0,n−1]`。
6. 任一访问无法归类 → 该访问 `UNKNOWN` 并记录 `reason`；整体状态为 `UNKNOWN`。

证书不含示例输入值；测试 `test_certificate_never_uses_sample_input_values` 验证不含 `114/514/1919/810/114514`。

## 5. 独立检查器规则

`verify_certificate(cert, program, require_pass=False)`：

- 校验 schema、scope、status 枚举、analyzer version、field 参数；
- **重算 `program.digest()`** 与证书 `program_hash` 比对，并核对指令数量与 source commit；
- 校验 `n_min≤n_max`、`nmax` 与 `input_constraint.n_max` 一致、`Nmax<p`、`Nmax²<p`；
- 声明的每个 `pc` 必须是该程序真实的 Load/Store，且 `op` 与程序一致；**禁止用非访存 PC 做白名单**；
- 声明必须覆盖全部真实访存点，不得重复；
- `PASS` 访问必须给出 `[0,n−1]` 与证明依赖；`UNKNOWN` 访问不得被当成 PASS；
- 整体 `PASS` 要求所有访问 PASS 且无 reasons；`require_pass=True` 时拒绝非 PASS。

检查器不重新执行分析器：这是“独立读取并验证结构、程序哈希与范围声明”的含义。

## 6. 实际证书样例（默认 `1≤n≤16`）

```text
status: PASS
program_hash: sha256:2a91193fef2fb08ceccd92b9664444a4152c6fec806e51f8005de8b74d2741a6
instruction_count: 42
nmax: 16
field: 0x12ab655e...0001, bit_size=253
accesses:
  PC4  Store interval=[0, n-1] PASS
  PC16 Load  interval=[0, n-1] PASS
  PC18 Load  interval=[0, n-1] PASS
  PC22 Store interval=[0, n-1] PASS
  PC24 Store interval=[0, n-1] PASS
  PC36 Load  interval=[0, n-1] PASS
field_conditions:
  n_range:PASS, field_no_wrap:PASS,
  bit_decomposition:ASSUMED, bool_not:ASSUMED
```

`address_expr` 示例：PC4 = `R0 = input-loop counter, init 0, +1 per iteration`；PC24 = `R0 = R3 (R3=R2+1, guard R3<R1<=n)`；PC36 = `R0 = output-loop counter, init 0, +1 per iteration, bound R8=n`。

## 7. 负向行为映射

| 变异 | 结果 |
| --- | --- |
| `n>Nmax`（`n_min=17,n_max=16`） | `FAIL` |
| PC21 `Move R0,R7`（Store 无界源） | PC22 `UNKNOWN` |
| PC15 `Move R0,R5`（Load 无约束表达式） | PC16 `UNKNOWN` |
| PC14 改 `Noop`（删除边界判断） | 全部访问 `UNKNOWN` |
| PC5 `Add`→`Mul`（可回绕递增） | PC4 `UNKNOWN` |
| PC23 `Move R0,R7`（分支路径改写地址） | PC24 `UNKNOWN` |
| 改 PC16 后复用旧证书 | 检查器：`program hash mismatch` |
| 证书 `nmax` 与输入约束不一致 | 检查器：`Nmax disagrees` |
| 伪造非访存 PC / 放宽区间 / 漏访问点 | 检查器拒绝 |

## 8. 明确不做

不把证书接入 R1CS；不声称 `n≤Nmax` 已由电路约束；不声称 LessThan 位分解已逐门审计；不把静态通过描述为 MPC 实测或端到端 zkVM 证明。
