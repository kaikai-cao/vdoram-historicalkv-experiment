# EXP-DORAM-08-R1-C1：验证记录

## 1. 测试命令与结果

```bash
cd /d/Research/vdoram-historicalkv-experiment

# 本轮模型测试（34 项，含本轮新增 4 项）
PYTHONPATH="src;tests" python -m unittest tests.test_exp_doram_08_r1 -v

# 全仓库测试
PYTHONPATH="src;tests" python -m unittest discover -s tests -p 'test_*.py'

# 空白/冲突检查
git diff --check
```

结果：

| 项目 | 结果 |
| --- | --- |
| R1 模块测试（修正后） | **34 项通过**（原 30 + 新增 4） |
| 全仓库测试 | **144 项通过**（原 140 + 新增 4） |
| `git diff --check` | 干净（无空白错误） |
| 首次 R1 模块运行 | 一次通过，无需二次修正 |

新增 4 项测试：`test_append_T0_T1_T2`、`test_append_step0_store_not_omitted`、`test_read_only_threshold_exact`、`test_cross_threshold_predicts_readonly_winner`、`test_mixed_rw_threshold_matches_parameterised_formula`（其中阈值精确验证由 `test_read_only_threshold_near_half` 改写而来，实为 5 处测试变更、净增 4 项）。

修正的既有断言：`test_three_models_common_append` 中 E1 追加增量 `(T−1)*7` → `T*7`，并对 E0/E1-A/E1-B 三者同时做"逐步 = 闭式"与"增量 = T×append_mults"双重校验。

## 2. 逐步 / 闭式一致性

| 模型 | 测试覆盖 | 结果 |
| --- | --- | --- |
| E0 | `T=0..11`、`append_mults∈{0,7}`、`T=1/2` 手工闭式 | 逐步 = 闭式，全部相等 |
| E1-A | `T∈{0,1,2,5,6,17}`、`n∈{1,4,5,8,16}`、`steps∈{∅,{0},{1},{0,2,4},{0,3,7}}`、`shared/separate`、`append∈{0,7}` | 逐步 = 闭式，全部相等 |
| E1-B | 同上 | 逐步 = 闭式，全部相等 |
| 三模型共同追加 | `T=10`、`steps` 四种、`append_mults=7` | 三者增量均 `T*7 = 70`；step 0 STORE 场景 `T=1` 增量 `7` |

手工复算锚点：`e0_total_closed(2, append=am) = (393·1−2) + 2am = 391 + 2am`；`e1a(1,n,{0},append=am) = n·(389+2) + am`。

## 3. 交叉条件验证

| 检查 | 期望 | 实测 |
| --- | --- | --- |
| E1-A 只读阈值 | `n < T/2` | `T∈{2,32,64,128,1024,4096}` 全部 `assertAlmostEqual(thr, T/2, places=9)` |
| E1-B 只读阈值 | `n < (393T−4)/780` | 同上 T 集合全部 `places=9` 相等 |
| 阈值 ↔ 实际胜负 | `T=64, n∈{8,16,31,32,33,48,64}` | E1-A/E1-B 的 `e1<e0` 与不等式判断逐点一致（n=32 时 E1-A 恰 TIE） |
| 读写混合参数化式 | `[A0−cx(T−1)]/[fx(T−1)+U]` | `T=128`、100% STORE、shared/separate 双模式 `places=9` 相等 |
| STORE 位置 | step 0 阈值 < 无 STORE 阈值 | 通过；`T=128` 下 `64.000 → 63.503`（仅 step0）、`63.676`（127 个 positive shared） |

## 4. CSV 重新生成

命令：

```bash
PYTHONPATH="src" python -m src.exp_doram_08_r1.sensitivity
```

| 文件 | 数据行 | 变化 |
| --- | --- | --- |
| `results/exp_doram_08_r1/symbolic_costs.csv` | 960 | 新增 `model_version=R1-C1` 列；成本值不变（默认 `append_mults=0`） |
| `results/exp_doram_08_r1/sensitivity_raw.csv` | 1280 | 新增版本列；**E1-A 的 `threshold_n_continuous` 四组值修正**（32.1586→32.0000 等，见 `cost-corrections.md` §1.5）；E1-B 列不变；`winner` 全表不变 |
| `results/exp_doram_08_r1/sensitivity_summary.csv` | 80 | 新增版本列；聚合胜负统计不变（E1-A/E1-B 源码权重各 99/160 胜） |

行数与参数范围保持：`n∈{16,64,256,1024}`、`T∈{64,256,1024,4096}`、STORE 比例 `{0,0.1,0.5,0.9,1.0}`、`{uniform,step0,no_step0}`、`{shared,separate}`、`{E1-A,E1-B}`、`eq_ratio∈{1,389}`、`upd_ratio∈{2,100}`。所有行带 `parameter_status`（`DERIVED` 仅 `389/2`，其余 `ASSUMED`）与 `model_version`。

## 5. 旧文件未修改证明

`git status --short`（本轮改动前基线 clean）：

```
 M results/exp_doram_08_r1/sensitivity_raw.csv
 M results/exp_doram_08_r1/sensitivity_summary.csv
 M results/exp_doram_08_r1/symbolic_costs.csv
 M src/exp_doram_08_r1/costs.py
 M src/exp_doram_08_r1/sensitivity.py
 M tests/test_exp_doram_08_r1.py
?? docs/exp-doram-08-r1-c1/
```

- `git diff -- docs/exp-doram-08-r1/` 为空 → **R1 五份历史文档原文零修改**；
- 历史 CSV 行数未变：`exp_doram_08` 1281/81/161、`exp_doram_07` 801/161、`exp_doram_07_r1` 1201/241，合计 3927 行；
- `docs/exp-doram-08/`、`src/exp_doram_08/`、上游 VDORAM、C#/Rust 执行路径均未触碰；
- 修改严格限于任务授权的三类：R1 实现文件、R1 受影响测试、R1 受影响 CSV，外加新增 `docs/exp-doram-08-r1-c1/`。

> `git diff --check` 输出中的 CRLF 提示来自仓库既有的 `.jsonl` trace 文件与本次编辑文件的换行规范化，非空白错误；未对 trace 文件做任何修改。

## 6. 仍然存在的 ASSUMED / UNKNOWN 项

| 项 | 状态 | 说明 |
| --- | --- | --- |
| 目标系统地址域是否有界 | **UNKNOWN** | E1-B 的唯一槽位前提仍为 `CONSTRUCTED`，非上游保证 |
| `eq` 比较结果能否跨读路径与写路径复用 | **ASSUMED** | `shared` 模式假设同电路复用；无电路级证据，故 CSV 同时给 `separate` 对照 |
| `c_eq=389` 的 E1 变体 `388` | **DERIVED 变体** | 公开槽位下标放在 `FieldSub` 右操作数时 FieldNeg 走本地路径；主模型保守取 389 |
| R1CS 约束数与 `MpcCircuit→R1CS` 映射 | **UNKNOWN** | 全程未用乘法数冒充约束数 |
| 批处理 MPC 的通信轮数、在线字节数 | **UNKNOWN** | 当前串行执行器每 BeaverMulti 一个 barrier，不可外推；域元素数不等于字节数 |
| 位分解摊薄地址比较、更省的条件选择 gadget | **UNKNOWN** | 未假设存在，未计入优势 |
| `append_mults` 的真实值 | **默认为 0** | 本轮证明三模型追加项一致，但真实历史追加电路的乘法成本未取证；不影响 C1 结论（三模型同项） |
| 权重扫描点 `eq_ratio=1 / upd_ratio=100` | **ASSUMED** | 压力测试参数，非实测，CSV 已标注 |

**自检边界遵守**：未重新审计 VDORAM、未新增文献调研、未新增 ORAM 构造、未重新评估密码学假设。本轮只做两项模型勘误 + 一次有边界的最终检查。
