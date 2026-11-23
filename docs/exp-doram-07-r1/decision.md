# EXP-DORAM-07-R1 — 最终决策

## 决策：`CONDITIONAL_PASS`

依据任务包第 9 节三选一规则，本轮**不是** PASS_TO_MPC_COST_MODEL，也**不是** NO_GO，判定为 `CONDITIONAL_PASS`。

### 判定理由（对照第 9 节）

**满足的条件（排除 NO_GO）：**
- ✅ 原始语义保持：E0-FullScan 与 `MemoryTraceFetchCircuitBoardGenerator` 的全历史扫描语义一致
  （每行一次地址相等、无提前退出、LowBit one-hot 选最新、无匹配返 0、step 0 零扫描、dummy Fetch 全扫），
  一手源码路径/行号/证据见 `fetch-semantics.md`。
- ✅ 三模型差分测试通过：31 项 R1 测试全过（含 12 语义、7 计数器、100 组随机差分、10 边界），
  全仓库 74 项测试通过；测试失败均已定位修正，无删除/弱化断言。
- ✅ Export 完全一致：80 cell × 5 rep 的三模型 export 逐字段一致，returns 一致，E1 不变量成立；
  1200 行 raw CSV 的 export_ok/returns_ok/invariant_ok 全为 1。
- ✅ 影子表不变量成立：E1 每步 `shadow[a]==latest_value(HistoryLog,a)` 全部成立。
- ✅ 无新增不可接受的公开泄漏/证明成本声称：本轮不进入 MPC/R1CS，明确标注三类成本边界。

**不满足 PASS_TO_MPC_COST_MODEL 的关键条件（降级为 CONDITIONAL）：**
- ⚠️ **E1 优势不稳定/有条件**：E1 相对 E0-FullScan 的总扫描优势只在 50/80 cell 成立，
  干净地依赖 `T/n ≥ 4`；在 30/80 cell（`T/n ≤ 1`）E1 反而更差（最高 55.87×）。
  不符合「多个代表性 n/T 和 workload 下**稳定**的总扫描成本优势」这一 PASS 条件。
- ⚠️ **地址域适用范围证据不足**：目标系统没有 VERIFIED 的有限地址域约束
  （地址是 253-bit 域元素，上游无 `[0,n-1]` 范围门；示例程序为 INFERRED，我们的 workload 为 CONSTRUCTED，
  目标系统全域有界为 UNKNOWN）。虽然研究问题已被严格限定为有界地址域模型，但收益仍依赖这一未证实条件。

因此符合 CONDITIONAL_PASS 的定义：「参考模型正确；E1 在有限地址域或特定 workload 下有**明显但条件性**的算法优势；
地址域或总成本收益仍依赖明确条件」。

## 具体适用条件（必须列明，不使用未验证阈值）

影子表优化**只在下列条件同时成立时**才值得继续评估：

1. **地址域有界**：所有有效内存地址属于 `[0,n-1]` 且 n 已知，且由程序逻辑或外部约束保证
   （当前证据为 CONSTRUCTED/INFERRED/UNKNOWN，非 VERIFIED）；超域地址必须能被拒止或单独处理。
2. **足够长的执行历史**：`T/n ≥ 4`（本参数矩阵的经验交叉点；T/n=1 全部失败）。
   这不是密码学保证，只是本次 80-cell 参考模型的观察，外推到其它 n/T 需重测。
3. **工作负载类型**：uniform / hot_80_20 / single_hotspot / sparse_write 在 T/n≥4 下收益明显；
   dense_write 因全表 Update（占总扫描时间约 43%）收益显著收窄（T/n=4 时扫描比 0.87–0.94），
   但在 T/n≥4 仍未翻转。
4. **成本口径限定**：优势只在「明文参考模型的抽象扫描次数与 Python 时间」层成立；
   不等价于 MPC 乘法门/通信轮数下降，不构成隐私或可验证性收益。

## 下一步（CONDITIONAL_PASS 允许的方向，非本轮任务）

若用户决定推进，唯一被本轮支持的下一步是：在**严格限定有界地址域**的前提下，
做独立的 MPC 原语成本估算（需先取得 FieldNorm/BoolAnd/SelectCompose 在 BLS12-377 secret-sharing 下的真实门数/轮数证据，
当前为 UNKNOWN）。**本轮不启动该步骤，不启动 EXP-DORAM-08，不修改上游，不改 witness 接口。**

## 保留与冻结

- EXP-DORAM-07 原有代码/CSV/文档**未修改**；原 E0 EarlyExit 数据完整保留为独立参考。
- 本轮全部新文件在 `docs/exp-doram-07-r1/`、`src/exp_doram_07_r1/`、`tests/test_exp_doram_07_r1.py`、
  `results/exp_doram_07_r1/`。
- `T ≳ 16n` 旧阈值已在本轮被修正为 `T ≳ 4n`（全历史基线），并明确为经验观察而非保证。
- 未解决/阻断项：
  1. 目标系统地址域是否有界（UNKNOWN）——影子表落地的前置条件；
  2. 电路层地址范围约束缺失——需外部约束或信任假设；
  3. E1 单扫描单元的 MPC 门数/轮数（UNKNOWN）——无法外推真实成本；
  4. 超域/NegOne 地址在 n 槽位表中的表示——需单独处理机制。
