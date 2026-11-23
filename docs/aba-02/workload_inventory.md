# ABA-02 阶段 B：真实程序集合与执行证据

固定 commit：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。行号均指该 commit。

## 1. 三张清单

### 清单一：源码中存在的程序（11 个）

`CompatCircuit/CollaborativeZkVm/ZkPrograms/Examples/` 下所有 `IZkProgramExampleGenerator` 实现：

1. `BubbleSortProgramGenerator.cs`
2. `ReverseInputProgramGenerator.cs`
3. `SlidingWindowProgramGenerator.cs`
4. `FibonacciProgramGenerator.cs`
5. `RangeQueryProgramGenerator.cs`
6. `EuclideanProgramGenerator.cs`
7. `GreaterThanZkProgramGenerator.cs`
8. `BinarySearchProgramGenerator.cs`
9. `SetIntersectionProgramGenerator.cs`
10. `LongestContinuousIncreasingSubsequenceProgramGenerator.cs`
11. `DivideByTwoProgramGenerator.cs`

实验目录另有 `ExperimentFourZkPrograms/`、`ExperimentTwoThreeZkPrograms/` 的包装生成器（复用上述程序，仅覆写 CodeName，见 `ExperimentFourZkProgramGeneratorBase.cs` L6–L18）。

### 清单二：主程序注册的程序（`ZkProgramExamples.cs` L6–L15，7 个）

| 生成器 | CodeName | 注册行 |
| --- | --- | --- |
| `GreaterThanZkProgramGenerator` | NumberComparison | L7 |
| `ReverseInputProgramGenerator` | ReverseInput | L8 |
| `BubbleSortProgramGenerator` | BubbleSort | L9 |
| `EuclideanProgramGenerator` | EuclideanAlgorithm | L10 |
| `FibonacciProgramGenerator` | FibonacciNumberAlgorithm | L11 |
| `RangeQueryProgramGenerator` | RangeQuery | L12 |
| `SlidingWindowProgramGenerator` | SlidingWindowAlgorithm | L13 |

`BinarySearch`、`SetIntersection`、`LCIS`、`DivideByTwo` **不在清单二**。任务中“至少检查 Euclidean”与注册集合一致；任务提到的 `DivideByTwo` 实际未注册但在测试中执行，如实记录。

### 清单三：有执行证据的程序

测试入口 `ZkProgramExamplesTest.cs`（单方 `Execute()`，L46）：

| 程序 | 证据位置 | 输入 | 证据等级 |
| --- | --- | --- | --- |
| ReverseInput | L57–L67 `TestReverseInputZkProgram` | n=4（L61） | `VERIFIED_EXECUTED` |
| BubbleSort | L70–L79 `TestBubbleSortZkProgram` | inputLength=4（L73），随机元素（L75） | `VERIFIED_EXECUTED` |
| DivideByTwo | L82–L90 | 随机 Field（L84） | `VERIFIED_EXECUTED`（直接 new，未注册） |
| GreaterThan | L93–L143 两个测试 | 随机/边界 Field（L107–L124） | `VERIFIED_EXECUTED` |

实验入口 `CollaborativeZkVmExperiment/Program.cs`：

| 程序 | 证据位置 | 证据等级 |
| --- | --- | --- |
| BubbleSort / Fibonacci / LCIS / RangeQuery / SlidingWindow / BinarySearch / SetIntersection / GreaterThan | L491–L500 exp-4 生成器列表；L503–L510 导出实例；L545–L649 / L651–L756 运行器调用 `Execute()` | `VERIFIED_EXECUTED`（实例生成 + 运行入口存在；实际历史运行数据不在本仓库固定 commit 可核验范围） |

注意：实验四生成器的输入完全来自示例生成器（`ExperimentFourZkProgramGeneratorBase.cs` L6–L18），例如 BubbleSort 仍是 `n=5` 的硬编码示例（`BubbleSortProgramGenerator.cs` L76）、SlidingWindow `n=6,k=3`（L60）、RangeQuery `n=10`（L36）。实验四没有参数化的大 n 或容量上界。

## 2. 综合证据等级表（优先调查程序）

| 程序 | 源码存在 | 主程序注册 | 执行证据 | 证据等级 |
| --- | --- | --- | --- | --- |
| BubbleSort | 是（L9 生成器） | 是（L9） | 测试 L70–L79；实验四 L492 | `VERIFIED_EXECUTED` |
| ReverseInput | 是 | 是（L8） | 测试 L57–L67 | `VERIFIED_EXECUTED` |
| SlidingWindow | 是 | 是（L13） | 实验四 L496；无单方测试 | `VERIFIED_EXECUTED`（实验入口）/ 单方未测 |
| Fibonacci | 是 | 是（L11） | 实验四 L493 | `VERIFIED_EXECUTED`（实验入口） |
| RangeQuery | 是 | 是（L12） | 实验四 L495 | `VERIFIED_EXECUTED`（实验入口） |
| Euclidean | 是 | 是（L10） | 无测试、无实验四条目 | `VERIFIED_REGISTERED` |
| GreaterThan | 是 | 是（L7） | 测试 L93–L143；实验四 L499 | `VERIFIED_EXECUTED` |
| BinarySearch | 是 | **否** | 实验四 L497（通过包装生成器） | `SOURCE_ONLY`（主程序未注册）/ 实验入口存在 |
| SetIntersection | 是 | **否** | 实验四 L498 | 同上 |
| LCIS | 是 | **否** | 实验四 L494 | 同上 |
| DivideByTwo | 是 | **否** | 测试 L82–L90 | `SOURCE_ONLY`（主程序未注册）/ 测试执行 |

## 3. 与任务给定列表的差异

- 任务列出 `SlidingWindow`、`Fibonacci`、`RangeQuery`、`Euclidean`、`GreaterThan` 等：均在固定 commit 中，且除 Euclidean 外都出现在实验四或测试中。
- `DivideByTwo` 未注册但在测试中执行；`BinarySearch`、`SetIntersection`、`LCIS` 未在主注册表，但出现在实验四（重命名包装）。按任务要求“以真实源码为准”，这些只作为“源码存在 + 实验入口存在”记录，**不误报为主程序注册**。
- 没有名为 `RangeQuery` 之外的“区间查询”变体；没有名为 `GreaterThan` 的生成器（实际为 `GreaterThanZkProgramGenerator`，CodeName `NumberComparison`）。

## 4. 关键判断

- ABA-01 的 Bubble Sort **既是注册程序，又有测试执行证据**，是“真实工作负载候选”。但真实调用参数是**硬编码小示例**（测试 n=4、示例 n=5、实验四继承 n=5），没有任何调用方传入可声明的 `Nmax`。
- 程序存在 ≠ 注册 ≠ 执行；本轮对每项标注了证据等级，未把实验入口存在等同于“历史性能数据已核验”。
