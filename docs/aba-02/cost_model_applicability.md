# ABA-02 阶段 E：对 EXP-DORAM-08 成本模型的适用性映射

只做适用性判断，不修改任何成本公式、CSV 或模型代码（EXP-DORAM-08-R1-C1-P1 冻结）。

## 1. 模型假设回顾（来自 EXP-DORAM-08-R1-C1-P1）

- 固定槽位 `[0,Nmax−1]` 的影子表/Fetch 模型，缺席槽返回 0；
- E0 每行一次 `FieldEquals`（`c_eq`），每步 Fetch；step 0 STORE 无 Fetch；
- E1 只扫 n 个槽，优势在 `n<0.5T`（E1-A）或 `n<(393T−4)/780`（E1-B），且 `c_eq≫c_upd`、相等判断可跨读写复用；
- 成本是**源码推导的 Fetch 相秘密乘法计数**，不是实测时间，Prove/R1CS 侧为共同项且 UNKNOWN。

## 2. 逐程序映射

| 程序 | 固定槽位 `[0,Nmax−1]` | 缺席返回 0 | 动态插入/迁移 | dummy Fetch | eq 复用 | 分类 |
| --- | --- | --- | --- | --- | --- | --- |
| BubbleSort | 条件满足：`1≤n≤Nmax` 是外部约束，地址 R0∈[0,n−1]（ABA-01-C1） | BubbleSort 每个地址 0..n−1 都被写后读，缺席槽不被访问；影子表 Nmax 中 n..Nmax−1 是否需返回 0 取决于 E1 实现，当前无该语义证明 | 无插入/删除/迁移（R1 递减仅缩小上界） | 程序每条 Load/Store 都是真实访存，无 dummy | 每步可尝试共享 eq，但 ABA-01-C1 证书不证明跨读写复用 | `MODEL_COMPATIBLE_WITH_EXTRA_CONSTRAINTS` |
| ReverseInput | 条件满足：输入/输出地址 ∈[0,n−1]，但需 `n≥1` 与减法无下溢证明 | 同 BubbleSort | 无 | 无 dummy | 未做静态证书，未知 | `MODEL_COMPATIBLE_WITH_EXTRA_CONSTRAINTS` |
| SlidingWindow | 条件性：`R0±k` 地址有界需 `1≤k≤n≤Nmax` 与整数无回绕证明，当前无证书 | 窗口滑动会重复访问已写地址；缺席语义未分析 | 无结构迁移，但地址表达式复杂 | 无显式 dummy | 未知 | `MODEL_COMPATIBLE_WITH_EXTRA_CONSTRAINTS`（需专门静态规则与更强约束） |
| Fibonacci / RangeQuery / Euclidean / GreaterThan / DivideByTwo | 无 Load/Store，槽位模型空输入 | 不适用 | 不适用 | 不适用 | 不适用 | `MODEL_INCOMPATIBLE`（无地址域优化对象） |
| BinarySearch / SetIntersection / LCIS | 未主注册、未做逐地址分析 | 未知 | SetIntersection 可能有多列表迭代 | 未知 | 未知 | `UNKNOWN`（本轮不扩展） |

## 3. 程序特定成本（模型未计入）

- **BubbleSort** 的固定 43 条指令含比较/交换分支；Fetch 相乘法数只覆盖地址相等判断，不含 `LessThan`/`Not`/`Add`/`Sub`/`PublicOutput` 等 op 的电路成本（EXP-DORAM-08 已声明这些不在 Fetch 模型内）。
- **SlidingWindow** 的 `R0−k`/`R0+k`（L43/L45）与字段累加和可能需要额外无回绕约束，属于模型外的程序特定成本。
- **ReverseInput** 的输出地址减法 `R4−R2`（L11）需要 n≥1 的整数解释，属于模型外。
- **所有程序** 的真实 Load/Store 次数随 n 动态增长，但成本模型以“每步一次 Fetch”抽象，未与具体程序的循环结构逐指令对齐。

## 4. 适用性结论

- EXP-DORAM-08 的 Fetch 相模型与 BubbleSort/ReverseInput/SlidingWindow 在语义上**形状兼容**（固定槽位、无插入迁移、无 dummy），但依赖当前不存在的 `1≤n≤Nmax` 等公共约束；因此分类为 `MODEL_COMPATIBLE_WITH_EXTRA_CONSTRAINTS`，不是 `MODEL_COMPATIBLE`。
- 无访存程序完全不适用该模型。
- **不得把 Python 参考模型或 Fetch 相源码计数说成真实 MPC 性能优势**：`c_eq=389` 未经执行侧实测，Prove/R1CS 侧为共同项且 UNKNOWN，当前后端缺 SPDZ MAC/auth（EXP-DORAM-06），且本轮未做任何微基准。
- 模型适用性的前提是“先有真实有界工作负载”；本轮证据表明该前提目前只部分满足（见 `decision.md`）。
