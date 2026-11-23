# ABA-02 最终决策

## 决策

**`GO_WITH_ADDED_INPUT_CONSTRAINTS`**

## 判定理由

固定上游 `10c90d35` 中确有真实注册且有执行证据的有限结构工作负载：BubbleSort（注册 `ZkProgramExamples.cs` L9，测试 `ZkProgramExamplesTest.cs` L70–L79，实验四 `Program.cs` L492）、ReverseInput（注册 L8，测试 L57–L67）、SlidingWindow（注册 L13，实验四 L496）。三者的 Load/Store 地址可由程序结构推出随 n（或 n,k）有界，ABA-01-C1 已为 BubbleSort 建立可独立检查的静态证书。

但**有限地址域不是当前系统的既有能力**：

- 固定 commit 中没有任何 `Nmax` 容量参数、没有 `1≤n≤Nmax` 约束、没有地址上界电路；
- 真实调用参数是硬编码小示例（测试 n=4、示例 n=5/4/6/10、实验四继承），调用方无法声明 Nmax；
- `GlobalStepsNoMoreThan` 只是执行时步长阈值（`ZkProgramExecutor.cs` L114–L116），不是输入范围或地址约束。
- `n=0` 在 BubbleSort/ReverseInput 中仍会在守卫前访问 mem[0]，需接口层禁止。

因此不能判 `GO_BOUNDED_WORKLOAD`（那要求边界已由上游约束），也不应判 `NO_GO`（确有真实工作负载且结构可界化）。判 `GO_WITH_ADDED_INPUT_CONSTRAINTS`，并明确：这是**新增构造**，不是现有能力。

## 必须新增的约束（明确影响）

| 约束 | 加在哪里 | 影响 |
| --- | --- | --- |
| 公共 `Nmax` | 证明语句/电路公共参数（新） | 上游无此参数；需修改执行电路接口 |
| `1≤n≤Nmax` | 电路公共输入约束（新） | 消除 n=0 缺陷；使 ABA-01-C1 的 `n≥1` 假设落地为电路事实 |
| `Nmax<p`（需要时 `Nmax²<p`） | 语句常量 | 保证线性/乘法地址无域回绕；BubbleSort 无乘法，SlidingWindow 的 `R0±k` 需逐项证明 |
| `addr<n` 或 `addr≤Nmax−1` | 每步 Load/Store 的电路内约束（新） | 把静态证书与真实执行地址关联；当前 VM 电路无此约束 |
| `k≤n`（SlidingWindow） | 公共输入约束（新） | 防止 L20–L22 之外的非法分支与 `R0−k` 下溢 |

在加入这些约束之前，ABA-01-C1 的 PASS 只是**静态规则成立**，不是系统已具备有界地址域。

## 证据分层

- **VERIFIED（源码直接证据）**：注册表 7 个程序；测试对 ReverseInput/BubbleSort/GreaterThan/DivideByTwo 的实际 `Execute()`；实验四 8 个生成器与运行入口；BubbleSort n=5/测试 n=4 硬编码；`GlobalStepsNoMoreThan` 仅抛错；地址线用 Reg0；LessThan 位分解；Field 253 位。
- **CONSTRUCTED（本轮/前序构造，非上游）**：ABA-01 静态分析器、ABA-01-C1 结构化证书与独立检查器；`(program_id,Nmax,n,constraints)` 接口设计；EXP-DORAM-07/08 参考模型与成本公式。
- **INFERRED（基于结构推导）**：BubbleSort/ReverseInput 地址随 n 有界的条件性结论；SlidingWindow 地址可达有界的推断；成本模型与三程序“形状兼容”的映射。
- **UNKNOWN**：真实历史运行的性能数据（固定 commit 仓库中无 benchmark 数值文件可核验）；`c_eq=389` 的执行侧实测；Prove/R1CS 侧成本；后端 SPDZ MAC/auth 路径；BinarySearch/SetIntersection/LCIS 的逐地址审计；实际部署是否使用这些示例 n 值。

## 后续是否值得启动小规模原型

**条件性值得，但本轮不启动。** 门槛（按优先级）：

1. 取得目标系统真实地址域证据（是否确为有界、界限由谁提供），而不是沿用示例 n；
2. 先把 `1≤n≤Nmax`、`Nmax` 公共参数与 `addr<n` 加入电路级语句，处理 `n=0`；
3. 在上述约束落地后，才考虑小规模执行绑定原型（BubbleSort 优先），并只在 Fetch 相验证原语权重；
4. 不做：SlidingWindow/SetIntersection 新证书、HistoricalKV 替换、固定槽位存储实现、MPC 微基准、新一轮 ORAM 文献调研。

EXP-DORAM-06 的 `NO_GO_CURRENT_ARCHITECTURE` 不因本轮改变；EXP-DORAM-08 的成本模型不得被称为真实 MPC 性能优势。

本轮结束即停止。
