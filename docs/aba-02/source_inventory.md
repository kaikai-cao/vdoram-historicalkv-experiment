# ABA-02 阶段 A：固定 commit 源码清单

## 1. 来源与边界

- 上游仓库：`BDS-SDU/vdoram-artifacts`
- 固定 commit：`10c90d35464620a35ddb1e2c29d2e8725acedd52`
- 本轮只读取该 commit 的源码（经 GitHub API 只读 blob，源码带上游原始行号）；未修改上游、未修改 C#/Rust 执行器。
- 本地源码快照：`D:/tmp/aba01/src/`（文件名为上游路径以 `__` 连接），每行号均指上游文件。

## 2. 程序生成器（源码存在）

固定 commit 的 `CompatCircuit/CollaborativeZkVm/ZkPrograms/Examples/` 下共 11 个 `IZkProgramExampleGenerator` 实现：

| 生成器文件 | CodeName | Load/Store 静态指令 |
| --- | --- | --- |
| `BubbleSortProgramGenerator.cs` | `BubbleSort` | 6 |
| `ReverseInputProgramGenerator.cs` | `ReverseInput` | 2 |
| `SlidingWindowProgramGenerator.cs` | `SlidingWindowAlgorithm` | 4 |
| `FibonacciProgramGenerator.cs` | `FibonacciNumberAlgorithm` | 0 |
| `RangeQueryProgramGenerator.cs` | `RangeQuery` | 0 |
| `EuclideanProgramGenerator.cs` | `EuclideanAlgorithm` | 0 |
| `GreaterThanZkProgramGenerator.cs` | `NumberComparison` | 0 |
| `BinarySearchProgramGenerator.cs`（未在 `ZkProgramExamples` 注册） | 见源码 | 2 |
| `SetIntersectionProgramGenerator.cs`（未注册） | 见源码 | 4 |
| `LongestContinuousIncreasingSubsequenceProgramGenerator.cs`（未注册） | 见源码 | 0 |
| `DivideByTwoProgramGenerator.cs`（未注册） | 见源码 | 0 |

`IZkProgramExampleGenerator.cs` L1–L4：接口仅 `GetZkProgram()`。`ZkProgramExample.cs` L5–L12 规定每个示例含 `ExamplePublicInputs`、`ExamplePrivateInputs`、`ExamplePublicOutputs`、`GlobalStepsNoMoreThan`；L14–L35 `GetZkProgramInstances()` 把这些**固定示例输入**与 opcodes 打包成实例，不做任何范围检查。

## 3. 注册入口

`ZkPrograms/Examples/ZkProgramExamples.cs` L6–L15 静态注册表，仅 7 个生成器：

```text
L7  GreaterThanZkProgramGenerator
L8  ReverseInputProgramGenerator
L9  BubbleSortProgramGenerator
L10 EuclideanProgramGenerator
L11 FibonacciProgramGenerator
L12 RangeQueryProgramGenerator
L13 SlidingWindowProgramGenerator
L15 Examples = ...ToDictionary()   （以 program.Name 为键）
```

BinarySearch、SetIntersection、LCIS、DivideByTwo **不在此注册表中**。

## 4. 执行入口与测试

| 文件 | 关键行 | 作用 |
| --- | --- | --- |
| `CollaborativeZkVmTest/ZkProgramExamplesTest.cs` | L14–L54 `TestZkProgramWithMemoryTrace()` 构造 `ZkProgramInstance` 并 `await Execute()`（L46）；L56–L143 具体测试 | 单方执行证据 |
| 同上 | L59–L66 ReverseInput n=4；L70–L78 BubbleSort inputLength=4；L82–L90 DivideByTwo；L93–L143 GreaterThan | 直接 `new generator()` 调用，不经过注册表 |
| `CollaborativeZkVmExperiment/Program.cs` | L484–L515 `exp-4-gen-zk-program-instance` 注册 8 个 `ExperimentFour*` 生成器 | 实验四实例生成 |
| 同上 | L491–L500 | exp4_bubble / fib / increasing / range / slide / binary / intersection / greater |
| 同上 | L545–L649 `run-mpc-zkvm`、L651–L756 `run-mpc-zkvm-thread` | 读取实例文件并进入 `ZkProgramExecutor.Execute()`（L611/L725） |
| `ExperimentFourZkProgramGeneratorBase.cs` | L6–L18 | 完全复用示例的 Opcodes/Example*Inputs/GlobalStepsNoMoreThan，只覆写 `CodeName` |
| `ZkPrograms/ZkProgramExecutor.cs` | L109–L116 | `GlobalStepNoMoreThan` 仅在执行时 `globalStepCounter > limit` 抛异常；不进入电路约束 |
| `ZkVmCircuits/ZkVmOpType.cs` | L44–L50 | Load/Store 的 memory address = Reg0，NegOne 为保留地址 |
| `ZkVmCircuits/ZkVmExecutorCircuitBoardGenerator.cs` | L126–L131、L426–L437、L500–L509、L988 | `in_public_input` 为公共输入线；PrivateInput/PublicInput 写入 Arg0 寄存器；Load/Store 用 Reg0 作地址；NegOne 保留地址返回 0 |
| `CompatCircuitCore/Arithmetic/FieldFactory.cs` | L24、L30–L35 | `NegOne = p−1`；`New(BigInteger)` 仅做 mod p 归一 |

## 5. 结论

- 固定 commit 中“程序存在”与“注册”“实际执行”是三个不同集合，详见 `workload_inventory.md`。
- 没有任何源码把 `Nmax`（容量上界）作为程序参数、公共输入或电路约束；`GlobalStepsNoMoreThan` 是步长上限，不是地址域上界。
- 所有固定 commit 引用均指向 `10c90d35`；本轮未把示例程序的边界推广到整个 VM。
