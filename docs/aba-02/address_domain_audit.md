# ABA-02 阶段 C：逐程序地址域审计

固定 commit：`10c90d35464620a35ddb1e2c29d2e8725acedd52`。行号均指该 commit 源文件。

## 1. 判定标尺

- **BOUNDED**：现有电路/输入约束已把每次 Load/Store 地址限制在 `[0,Nmax−1]`，Nmax 是受约束的公共参数。
- **CONDITIONALLY_BOUNDED**：静态结构可推出地址随 n 有界，但 `1≤n≤Nmax` 或等价范围约束**当前不存在**，需要新增；且未提供 Nmax 公共参数。
- **UNBOUNDED**：地址直接来自任意输入/动态状态，无结构可推出有限上界。
- **UNKNOWN**：证据不足。
- 另对无 Load/Store 的程序标 `NO_MEMORY_ACCESS`（不属于上述四类，表示地址域模型不适用）。

关键区分：**静态 PC 数量 ≠ 动态访问次数**；**循环由 n 控制 ≠ n 已被约束**；**地址由 R0 产生 ≠ R0 ∈ [0,n−1]**。

## 2. 有内存访存的注册程序

### 2.1 BubbleSort（`BubbleSortProgramGenerator.cs`）

| 项目 | 内容 |
| --- | --- |
| 输入参数 | 公共输入 n（L19 `PublicInput 1`），私有数组 n 个元素（L21）；真实调用 n=4（测试 L73）、示例 n=5（L76）、实验四继承 n=5 |
| 地址来源 | R0（VM 地址线，`ZkVmOpType.cs` L44–L50）；R0 由 L2/L15/L17/L21/L23/L27/L29/L33/L35 的 Set/Move/比较写覆盖 |
| Load/Store | 静态 6 条：PC4 Store、PC16/18 Load、PC22/24 Store、PC36 Load；动态次数随 n 与交换次数增长（O(n²)） |
| 地址生成 | 输入循环 R0=0..n−1（L2/L5）；内层取 R2/R3（L15/L17/L21/L23，R3=R2+1 L12）；输出循环 R0=0..R8−1（L35/L38/L9） |
| 循环守卫 | L6–L8（R0<R1）、L13–L14（R3<R1）、L30–L31（0<R6）、L39–L41（R0<R8） |
| 边界 | n=0：输入循环跳过一次 Store? 否——L4 Store 在守卫 L6 之前，n=0 仍访问 mem[0]；n=1 可运行；n=Nmax 依赖外部约束 |
| 有限域风险 | R1 递减 L32（Sub mod p）；R3=R2+1 L12，R8=n 副本 L9；只有 `1≤n` 且 `n<Nmax`、`Nmax²<p` 时整数解释成立 |
| 当前约束 | Field 元素规范（Field.cs）；LessThan 253 位分解；`GlobalStepsNoMoreThan=43×n²` 仅是执行抛错阈值（Executor L114–L116），**不是地址/输入约束** |
| 缺失约束 | 公共 `Nmax`、`1≤n≤Nmax`、`Nmax<p`（BubbleSort 无乘法，是否需要 `Nmax²<p` 需按实际乘法审计，ABA-01 保守加入） |
| 结论 | **CONDITIONALLY_BOUNDED**（结构可证，但约束缺失；ABA-01-C1 的 PASS 依赖外部 `1≤n≤Nmax`） |

ABA-01-C1 复核：程序已注册（L9）、有测试执行证据（测试 L70–L79）；`1≤n≤Nmax` **不能**从真实调用参数获得（调用只给 n=4/5 或随机 n，且无 Nmax）；`n=0` 未出现在示例调用中但程序语义缺陷仍在；用户/测试调用者可控的最大数组长度不存在——只有 `GlobalStepsNoMoreThan` 这个步长阈值（L79），不进入执行电路公共输入或受约束位置（Executor L114–L116）。

### 2.2 ReverseInput（`ReverseInputProgramGenerator.cs`）

| 项目 | 内容 |
| --- | --- |
| 输入参数 | 公共 n（L18），私有 n 个元素（L20）；测试 n=4（L61） |
| 地址来源 | R0；输出循环 L11 `R0 = R4 − R2`，R4=L9 `R1−1`，R2 从 0 递增（L14） |
| Load/Store | 静态 2 条：PC4 Store、PC12 Load；动态各 n 次 |
| 地址生成 | 输入 R0=0..n−1（L2/L5）；输出 R0=(n−1)−R2，R2=0..n−1（L9–L14） |
| 循环守卫 | L6–L8（R0<R1）、L15–L17（R2<R1） |
| 边界 | n=0：L4 Store 先于守卫执行（同 BubbleSort 缺陷）；R4=R1−1 在 n=0 时下溢到 p−1 |
| 有限域风险 | L9 `R1−1` mod p；L11 减法 mod p；无乘法；需 `n≥1` 保证 R4 是规范整数 n−1 |
| 当前约束 | 同 BubbleSort：无 n 范围、无 Nmax |
| 缺失约束 | `1≤n≤Nmax`、`Nmax<p`、输出地址 `(n−1)−R2 ≥ 0` 的整数解释 |
| 结论 | **CONDITIONALLY_BOUNDED**（结构与 BubbleSort 类似，但本轮未做完整静态证书；地址含减法，新增约束需求更强） |

### 2.3 SlidingWindowAlgorithm（`SlidingWindowProgramGenerator.cs`）

| 项目 | 内容 |
| --- | --- |
| 输入参数 | 公共 n（L18）、公共 k（L19）；示例 n=6,k=3（L60）；私有 n 个值（L26） |
| 地址来源 | R0；多循环：输入 PC8–PC13（R0+=1）、首窗口 PC16–PC21（R0+=1，范围 <k）、滑动 PC24–PC52（R0 先 PC43 `R0−=k`，PC45 `R0+=k`，PC51 `R0+=1`） |
| Load/Store | 静态 4 条：PC27 Store、PC34/42/44 Load；动态次数随 n,k 与滑动步数增长 |
| 地址生成 | 计数器 + `R0±k` 混合；守卫 L20–L22（n≥k）、L24–L25（R0<n）、L32–L33（R0<k）、L40–L41（R0<n） |
| 边界 | n=0/k=0：无显式检查；k>n 时 L20–L22 跳到错误分支；R0−k 在字段中可能下溢 |
| 有限域风险 | L43 Sub、L45 Add、L51 Add 均为 mod p；`R0−k` 的整数非负依赖未证明；累加和 R3 是字段加法（溢出语义，非整数和） |
| 当前约束 | 无 n/k 范围、无 `k≤n` 的电路约束（L20–L22 只是运行时分支） |
| 缺失约束 | `1≤k≤n≤Nmax`、`Nmax<p`；对 `R0−k` 与 `R0+k` 的整数无回绕证明；地址与最大值的关联 |
| 结论 | **CONDITIONALLY_BOUNDED**（结构比 BubbleSort 复杂，需专门静态证明；当前无证书） |

## 3. 无内存访存的注册程序

| 程序 | Load/Store | 说明 | 结论 |
| --- | --- | --- | --- |
| FibonacciNumberAlgorithm | 0 | 纯寄存器迭代（FibonacciProgramGenerator.cs L15–L33），n 是私有输入（L15），`GlobalStepsNoMoreThan=1000` 固定（L37），无地址线 | `NO_MEMORY_ACCESS` |
| RangeQuery | 0 | 流式读取两个私有输入/人（RangeQueryProgramGenerator.cs L19–L34），公共 n 先 `Mul R1, R1, 2`（L18）后循环，R0 是计数器但不作地址 | `NO_MEMORY_ACCESS` |
| EuclideanAlgorithm | 0 | 两私有数，寄存器取模迭代（EuclideanProgramGenerator.cs L14–L25） | `NO_MEMORY_ACCESS` |
| NumberComparison (GreaterThan) | 0 | 两私有数比较（GreaterThanZkProgramGenerator.cs L15–L19） | `NO_MEMORY_ACCESS` |
| DivideByTwo（测试执行，未注册） | 0 | 单私有字段除 2 | `NO_MEMORY_ACCESS` |
| BinarySearch / SetIntersection / LCIS（实验四包装，未主注册） | 2/4/0 | 源码存在且实验四注册（`Program.cs` L494/L497/L498），但本轮只做证据登记；LCIS 无访存 | `UNKNOWN`（未做逐地址分析，本轮不扩展） |

对 `NO_MEMORY_ACCESS` 程序，固定槽位地址域模型根本不适用——它们没有需要压缩的 Load/Store 地址。

## 4. 有限域分析（C2）

- 实际 Field 为 BLS12-377 标量域（253 位，`ArithConfig.cs` / `FieldFactory.cs` L24 `NegOne=p−1`）。
- 所有寄存器值是规范 Field 元素 `[0,p−1]`；但**这不是整数范围约束**：`R1−1` 在 n=0 时变为 p−1，`R0+k` 可能回绕。
- LessThan（253 位分解）提供规范整数比较；`GlobalStepsNoMoreThan`（Executor L114–L116）只限制步数不限制地址。
- `Nmax<p` 与 `Nmax²<p`：只有 BubbleSort/ReverseInput 的线性地址推导需要 `Nmax<p`；SlidingWindow 的 `R0±k` 与 RangeQuery 的 `n×2`（L18 `Mul`）出现乘法/减法，是否需 `Nmax²<p` 需逐程序按实际乘法审计，不机械套用。
- 结论：三个有访存程序都**缺乏**当前生效的 `n≤Nmax` / `Nmax` 公共参数约束；整数无回绕依赖外部假设。

## 5. 总体判断

- 真实注册且有执行证据的程序中，**只有 BubbleSort/ReverseInput/SlidingWindow** 存在内存地址压缩问题；其余注册程序没有 Load/Store。
- 这三个程序的地址界都是**条件性**的：结构可由静态分析推出，但 `1≤n≤Nmax`、`Nmax<p`（及可能的 `Nmax²<p`）当前不是系统接口的一部分。
- 因此 ABA-01 的有限地址域证明对应的是**真实存在但未被有界化的示例程序**，不是一个已有 Nmax 接口的真实部署工作负载。
