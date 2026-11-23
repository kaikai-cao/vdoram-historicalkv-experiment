# ABA-01：验证记录

## 1. 范围与提交

- 起始 commit：`ea8a62bb9a3b460b85acbc16265d3beb9a30092a`（P1 后 main，工作区干净，local=remote）。
- 最终 commit：本轮提交（`ABA-01: static address-domain certificate prototype`）；推送后本地与 `origin/main` 一致，实际哈希见交付报告第 1 项。
- 固定上游：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`，只读取证（GitHub blob 抓取 + WebFetch 补抓），**未修改上游仓库**。
- 未修改：任何 EXP-DORAM 文档/CSV/模型代码、results/、data/、C#/Rust 执行器、witness/R1CS 接口。

## 2. 新增文件（11 个）

| 文件 | 内容 |
| --- | --- |
| `docs/aba-01/source_semantics.md` | 固定 commit 源码语义、42 条指令 PC、6 条 Load/Store 的 R0 来源、循环结构、VM 指令语义、n 约束缺失证据 |
| `docs/aba-01/invariants.md` | CFG、B1–B4 不变量、交换/不交换分支、n=0/1/Nmax/>Nmax、末次迭代 |
| `docs/aba-01/field_soundness.md` | 模数/位宽、LessThan 规范整数语义、无回绕/下溢逐项分析、四类条件区分 |
| `docs/aba-01/certificate_format.md` | schema、生成/检查规则、实际样例、负向映射、边界声明 |
| `docs/aba-01/validation.md` | 本文件 |
| `docs/aba-01/decision.md` | 最终决策与六项结论 |
| `src/aba_01/__init__.py` | 包标识 |
| `src/aba_01/cfg.py` | 固定指令序列、Program、规范哈希、CFG 后继与写寄存器集合 |
| `src/aba_01/analyzer.py` | 基于回边与指令模式的静态分析器（PC 非白名单） |
| `src/aba_01/certificate.py` | 证书生成 + 独立结构/哈希/范围检查器 |
| `tests/test_aba_01.py` | 22 项测试：正向、8 类负向、边界、证书失效 |

（6 份文档 + 4 个源码文件 + 1 个测试文件 = 11；实际以提交后 `git show --stat` 为准。）

## 3. 测试命令与实际结果

| 命令 | 结果 |
| --- | --- |
| `python -m unittest tests.test_aba_01 -v` | `Ran 22 tests ... OK` |
| `python -m unittest discover -s tests -v` | `Ran 172 tests ... OK`（原 150 + 新 22） |
| `git diff --check` | 无输出 |
| `git status --short` | 仅列出 `docs/aba-01/`、`src/aba_01/`、`tests/test_aba_01.py` |
| `git diff --stat` | 空（本轮全部为新增文件，提交前均未跟踪） |

环境：系统 Python 3.13.x，在仓库根目录运行；`tests/test_aba_01.py` 通过 `from src.aba_01...` 导入，命令有效。Git 的 `LF will be replaced by CRLF` 为 Windows autocrlf 提示，未产生内容差异。

## 4. 证书样例（默认 `1≤n≤16`）

```text
status: PASS
scope: STATIC_CERTIFICATE_PROTOTYPE
program_hash: sha256:2a91193fef2fb08ceccd92b9664444a4152c6fec806e51f8005de8b74d2741a6
instruction_count: 42
nmax: 16
field: 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001, bit_size=253
PC4  Store  [0, n-1] PASS   R0 = input-loop counter, init 0, +1 per iteration
PC16 Load   [0, n-1] PASS   R0 = R2 (R3=R2+1, guard R3<R1<=n)
PC18 Load   [0, n-1] PASS   R0 = R3 (R3=R2+1, guard R3<R1<=n)
PC22 Store  [0, n-1] PASS   R0 = R2 (swap branch, same guarded address)
PC24 Store  [0, n-1] PASS   R0 = R3 (swap branch, same guarded address)
PC36 Load   [0, n-1] PASS   R0 = output-loop counter, bound R8=n
field_conditions: n_range:PASS, field_no_wrap:PASS,
                  bit_decomposition:ASSUMED, bool_not:ASSUMED
```

检查器结果：`verify_certificate(cert, BUBBLE_SORT, require_pass=True).ok == True`。

## 5. 失败 / 拒绝案例

| 变异 | 实际结果 |
| --- | --- |
| `n>Nmax`（`n_min=17, n_max=16`） | 分析 `FAIL`；`checker(require_pass=True)` 拒绝 |
| PC21 `Move R0,R7` | PC22 `UNKNOWN` |
| PC15 `Move R0,R5` | PC16 `UNKNOWN` |
| PC14 改 `Noop` | 全部访问 `UNKNOWN`，原因含 `guard unrecognisable` |
| PC5 `Add`→`Mul` | PC4 `UNKNOWN` |
| PC23 `Move R0,R7` | PC24 `UNKNOWN` |
| 改 PC16 后复用旧证书 | 检查器报 `program hash mismatch` |
| 证书 `nmax=32` 但输入约束 `n_max=16` | 检查器报 `Nmax disagrees` |
| 以 PC6（LessThan）冒充访存点 | 检查器报 `not a Load/Store` |
| 把 `[0,n−1]` 放宽为 `[0,n]` | 检查器拒绝 |
| 删除一个访问点 | 检查器报 `coverage mismatch` |
| `n=0` | 分析 `FAIL`（`n_min must be >=1`） |

## 6. 未解决 / 明确不声称

1. `n ≤ Nmax`、`n ≥ 1` **当前 VDORAM 电路没有约束**；证书把它们作为外部假设。
2. `n=0` 时程序仍访问 `mem[0]`（输入 Store 与输出 Load 都在守卫前），地址域命题在 `n=0` 下不成立；本轮只如实记录并排除，未修改上游。
3. 位分解预编译电路内部未逐门审计；`Not` 不强制输入布尔（本程序巧合只接 LessThan 输出）。
4. R6 计数上限依赖保守假设 `Nmax² < p`。
5. 证书未接入 R1CS 执行关系；不绑定运行时寄存器与内存 trace，不构成端到端密码学证明。
6. 未做 MPC 微基准、未推广到其他程序、未开始 HistoricalKV 替换。
