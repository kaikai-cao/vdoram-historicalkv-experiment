# EXP-DORAM-08-R1-C1-P1：最终决策

## 最终决策：`PASS_COST_MODEL_PARAMETERIZATION`

> 候选：`PASS_COST_MODEL_PARAMETERIZATION` / `BLOCKED_INCONSISTENCY`。
> 选择前者：`e0_total_closed()` 的 LowBit 硬编码已改为参数化表达式，默认参数结果零变化，非默认参数下逐步/闭式/交叉条件通过针对性测试与反向验证一致。

---

## 1. 本补丁证明了什么

只证明一件事：E0 闭式成本模型现在与逐步模型、`cross_threshold_n()` 共享同一套 LowBit 参数定义。

- 修正前：`e0_total_closed()` 用 `K = c_eq + c_sel + 3`，而 `cross_threshold_n()` 用 `K = c_eq + c_sel + lowbit_not + lowbit_and`。默认 `1+2=3` 掩盖了不一致。
- 修正后：两处统一为参数化 `K`；`b = lowbit_and` 不变。
- 非默认 `CostParams(lowbit_not=4, lowbit_and=5)`（K=399, b=5）下，`T ∈ {0,1,2,5,17}` 逐步等于闭式；`T ∈ {17,65,67,128}` 两变体全整数 n 范围内，交叉条件与真实成本不等式符号一致。
- 反向验证：旧硬编码会在上述非默认用例中失配，说明新测试具备有效捕获能力，而非同义反复。

## 2. 未证明 / 明确不声称

- **不是真实 MPC 性能验证。** 单元测试与符号一致性不测量任何执行时间、通信量或后端吞吐；`c_eq=389`、`c_upd_shared=2` 等仍是源码推导假设，未由执行侧实测确认。
- 不证明 E1 在真实 MPC 后端具有性能优势。地址域有界性、`eq` 跨读写复用、`c_eq ≫ c_upd` 三个前提仍未证实。
- 不解除 EXP-DORAM-06 的当前架构 `NO_GO_CURRENT_ARCHITECTURE`：后端缺 SPDZ MAC/auth 契约、C#→Rust witness 路径缺口依旧。
- 不涉及 R1CS 约束数、真实网络字节数、批处理轮数；不修改任何 CSV 或既有文档。

## 3. 关闭口径

本补丁完成后，EXP-DORAM-08-R1-C1 的成本公式勘误线正式关闭：

- 不再追加新的成本公式修正；不启动 MPC 微基准；不进入 EXP-DORAM-09；不重新调研 ORAM 文献。
- 后续研究重心转向真正影响可行性的三项：**地址域证据**、**执行侧权重**、**后端认证接口**。
- C1 的 `CONDITIONAL_PASS` 结论保持不变：本补丁只在模型实现层面消除参数硬编码，不改变优势区间、阈值数值或任何实验数据。
