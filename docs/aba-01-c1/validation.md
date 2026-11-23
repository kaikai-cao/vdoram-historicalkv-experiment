# ABA-01-C1：验证记录

## 1. 基线与提交

- 分支：`main`
- 起始 commit：`125bca6a961e66d8d25ef51aa2eaad4dababc9b4`
- 基线核验：`git rev-parse HEAD` = `git rev-parse origin/main` = 起始 commit；`git status --short --branch` 仅显示 `## main...origin/main`（工作区干净）；`git diff --check` 无输出。
- 固定上游：`BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`（未修改）。
- 最终 commit：见本文件末「提交记录」；提交并推送后 `HEAD` 与 `origin/main` 一致。

## 2. 修改文件

修改（7 个）：

| 文件 | 变更 |
| --- | --- |
| `src/aba_01/analyzer.py` | v0.2-c1：新增 `global_structure_reasons()` 与 R2/R3 写集合、初值、更新、守卫、控制流位置检查；`AccessFact` 增加结构化证明字段；分析失败时全局降级。 |
| `src/aba_01/certificate.py` | schema `aba-01-c1/v1`；独立 CFG/guard 推导、R-INPUT/R-INNER/R-OUTPUT 规则、字段逐项重算比对；`verify_certificate()` 不调用 `analyze()`。 |
| `src/aba_01/cfg.py` | 仅注释：指令数量 42→43（PC 0–42）。 |
| `tests/test_aba_01.py` | 保留原 22 项；新增 M1–M10、13 项证书篡改/文本伪造、3 项检查器独立性与指令数测试，共 48 项。 |
| `docs/aba-01/source_semantics.md` | 指令数量 42→43，PC 0–42。 |
| `docs/aba-01/certificate_format.md` | 同步 schema/analyzer version/结构化字段/独立规则/样例/负向映射；指令数 43。 |
| `docs/aba-01/validation.md` | 原有指令数量 42→43。 |

新增（3 个）：`docs/aba-01-c1/{fix,validation,decision}.md`。

未修改：EXP-DORAM 模型/测试、`results/`、`data/` 历史数据、上游 VDORAM、C#/Rust 执行器、MPC/witness/R1CS/SNARK 后端、HistoricalKV。

## 3. 正向测试

- 原始 `BUBBLE_SORT` + `InputConstraint(1,16)`：分析器 `PASS`、`reasons=[]`，6 条访存（PC4/16/18/22/24/36）全部 `PASS`、`interval=[0,n-1]`，`verify_certificate(..., require_pass=True).ok=True`。
- `n=1`、`n=Nmax=16`：`PASS`。
- 证书不含示例输入值（`114/514/1919/810/114514`）测试通过。
- 程序哈希绑定 43 条指令；任何单条指令改变都会改变摘要（原有测试保留）。

## 4. 程序变异测试（M1–M10）

全部满足「不得 PASS」，分析器为 `UNKNOWN` 或 `FAIL`，证书 `require_pass=True` 被拒绝：

| 编号 | 变异 | 实际结果 |
| --- | --- | --- |
| M1 | PC10 `Set R2,p−1` | `UNKNOWN`；reasons 含 PC10 期望 `Set R2,0` 与内层模式未识别。伪造 PASS 被检查器拒绝（含 `PC10` 错误）。 |
| M2 | PC10 `Set R2,3` | `UNKNOWN` |
| M3 | PC10 `Move R2,R7`（无约束源） | `UNKNOWN` |
| M4 | PC12 `Add R3,R2,R7` | `UNKNOWN` |
| M5 | PC26 `Move R2,R7` | `UNKNOWN` |
| M6 | PC33 改为额外写 R2 | `UNKNOWN` |
| M7 | PC33 改为额外写 R3 | `UNKNOWN` |
| M8 | PC13 `LessThan R4,R2,R1` | `UNKNOWN`（守卫不匹配） |
| M9 | PC14 改 `Noop` | `UNKNOWN`（守卫/结构不匹配） |
| M10 | PC20 改 `JumpIfZero 7,29` | `UNKNOWN`（分支不再汇合 PC26） |

原有 8 类负向测试（n>Nmax、无界 Store、无约束 Load、删边界、回绕递增、分支改写、旧证书复用、nmax 不一致）全部保留并通过。

## 5. 证书篡改测试

13 项全部被独立检查器拒绝：

1. `address_def_pc` → `PC 4 address_def_pc 999 != program-derived 2` + R-INPUT 规则拒绝；
2. `address_source_register` → 与程序派生值不符；
3. `guard_pc` → `PC 16 guard_pc 999 != program-derived 14`；
4. `loop_head` → 与程序派生循环头不符；
5. `proof_rule` → `PC 16 proof_rule 'R-OUTPUT' != program-derived 'R-INNER'`；
6. 访存点区间 `[0,n−1]`→`[0,n]`；
7. 访存点 PC 改为别的真实访存点（重复 + 覆盖不符）；
8. `bound_register` 1→8；
9. `program.source_path` 伪造；
10. `program_hash` 伪造；
11. `instruction_count` 43→42（旧错误数量）；
12. `field.prime_hex` 改为 `p+2`；
13. 仅替换 `address_expr`/`dependencies` 为看似合法文本但破坏 `address_def_pc`：仍被拒绝（文本不是证据）。

另：在 M1 破损程序上手工把 UNKNOWN 证书整体与全部访存改成 PASS、清空 reasons，检查器仍拒绝并报 PC10 结构错误。

## 6. 检查器独立性测试

- `test_checker_never_calls_analyze`：将 `src.aba_01.certificate.analyze` 临时替换为抛异常函数后调用 `verify_certificate(cert, P, require_pass=True)`，仍 `ok=True`（finally 恢复原函数）。
- `test_forged_pass_on_broken_program_is_rejected`：M1 上伪造 PASS 被拒绝。
- `test_instruction_count_is_43`：`len(P.instrs)==43`、证书 `instruction_count==43`。

## 7. 完整测试与 Git 检查

验收命令（仓库根目录，系统 Python 3.13.14，无需额外 PYTHONPATH）：

```text
python -m unittest tests.test_aba_01 -v     -> Ran 48 tests ... OK
python -m unittest discover -s tests -v     -> Ran 198 tests ... OK
git diff --check                            -> 无输出（clean）
git status --short                          -> 仅授权文件修改 + 新增 docs/aba-01-c1/
git diff --stat                             -> 7 files changed, 572 insertions(+), 95 deletions(-)
```

Windows `core.autocrlf` 对未触碰的历史 `data/traces/*.jsonl` 给出 LF→CRLF 提示，不改变文件内容；`git diff --check` 无错误，`git status` 中这些历史文件未出现。

## 8. 提交记录

- 实现提交：`484230eb0d907bfdba60fb290d48b04d7fbd3801`（`fix(aba-01-c1): harden analyzer and independent certificate checker`，10 文件，782 insertions / 95 deletions）。
- 最终 commit：以本文件所属文档提交为准；推送后 `git rev-parse HEAD` = `git rev-parse origin/main`，`git status --short --branch` 为 `## main...origin/main`（工作区干净）。
- 首次 `git push origin main` 遇到代理 `CONNECT tunnel failed, 502`；短超时重试第 1 次即成功，无 API 回退、无强推、无额外分支或 PR。
