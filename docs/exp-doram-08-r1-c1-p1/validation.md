# EXP-DORAM-08-R1-C1-P1：验证记录

## 1. 提交范围

- 起始 commit：`e07218832ea58655751842c053e5db7bd7a79998`
- 本地 `main` 与 `origin/main` 起始一致，工作区干净，`git diff --check` 无输出（Phase 0 通过）。
- 最终 commit：本补丁提交（`fix: parameterize E0 LowBit cost coefficient`），推送后 `main` 与 `origin/main` 一致；实际哈希见交付报告第 1 项与 `git log -1 --format=%H`。

## 2. 修改文件

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `src/exp_doram_08_r1/costs.py` | 修改 | `e0_total_closed()` 的 `K` 由 `+3` 改为 `p.lowbit_not + p.lowbit_and` |
| `tests/test_exp_doram_08_r1.py` | 修改 | 新增 `TestLowBitParameterizationP1`（6 项测试），保留原有 34 项 |
| `docs/exp-doram-08-r1-c1-p1/fix.md` | 新增 | 原硬编码位置、修正表达式、默认值不变理由、测试覆盖 |
| `docs/exp-doram-08-r1-c1-p1/validation.md` | 新增 | 本文件 |
| `docs/exp-doram-08-r1-c1-p1/decision.md` | 新增 | 最终决策与限制 |

未修改：`results/exp_doram_08_r1/` 三份 CSV、`docs/exp-doram-08-r1/`、`docs/exp-doram-08-r1-c1/`、`docs/exp-doram-08/`、其他实验目录、上游 VDORAM、C#/Rust 执行器及 witness/R1CS 接口。

## 3. 测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `python -m unittest tests.test_exp_doram_08_r1 -v` | `Ran 40 tests ... OK`（原 34 + 新 6） |
| `python -m unittest discover -s tests -v` | `Ran 150 tests ... OK`（全仓库，含新增 6 项） |
| `git diff --check` | 无输出（干净） |
| `git diff --cached --check` | 提交前复查，无输出（干净） |

测试模块导入方式说明：项目无 `.venv`，使用系统 `python`（Python 3.13.14），在仓库根目录以 `python -m unittest ...` 运行；`tests/test_exp_doram_08_r1.py` 通过 `from src.exp_doram_08_r1.costs import ...` 导入，仓库根目录即工作目录，命令有效，无需额外 `PYTHONPATH`。

新增用例有效性反向验证（内存模拟旧硬编码，无文件写入）：

- 非默认参数下 `e0_total_closed` 与 `e0_total_by_sum` 在 `T=2/5/17` 失配（388≠394、3910≠3970、53368≠54184）。
- 非默认参数下交叉条件与真实成本符号在 4 个 `(T,variant,n)` 点失配：`(65,B,33)`、`(67,A,33)`、`(67,B,34)`、`(128,B,65)`。
- 默认参数下 `T=0..129` 旧式与修正后逐点相等。

修正后全部一致性断言通过。

## 4. CSV 未修改的 Git 证据

提交前执行：

```
git status --short -- results/exp_doram_08_r1/
```

输出为空，表明三份 R1 CSV 无任何工作区改动。同期 `git status --short` 仅列出

```
 M src/exp_doram_08_r1/costs.py
 M tests/test_exp_doram_08_r1.py
```

（以及本阶段新增的 `docs/exp-doram-08-r1-c1-p1/` 未跟踪文件）。`git diff --check` 与 `git diff --cached --check` 均无输出。

说明：Git 在 `data/traces/*.jsonl` 及两处修改文件上给出 `LF will be replaced by CRLF` 的换行告警，属 Windows 平台 autocrlf 提示，不产生内容差异（`git status --short` 未列出这些文件），不影响 CSV 未修改结论。

## 5. 结论边界

本轮只验证成本模型的参数化一致性（逐步模型、闭式模型、交叉条件三者使用同一套 LowBit 系数）。单元测试通过**不是**真实 MPC 性能验证；`c_eq=389` 等权重仍为源码推导假设，未经执行侧实测。EXP-DORAM-06 的当前架构 `NO_GO_CURRENT_ARCHITECTURE` 结论不变。
