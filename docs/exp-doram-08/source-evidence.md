# EXP-DORAM-08 — 源码原语证据矩阵

固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
本地快照：`docs/source-snapshot/`（R1 之前建立，带 `BLOB SHA` 头）；远程 gadget 通过固定 commit 的 raw 文本取得。

## 0. 取证方法与可追溯性限制

| 来源 | 定位方式 | 行号状态 |
| --- | --- | --- |
| 本地快照的电路/执行器文件 | 文件路径 + 快照内行号（文件头含 BLOB SHA） | **VERIFIED**（可直接复核） |
| 远程 gadget 文件 | 固定 commit + `BLOB SHA`（见下表）+ 类/方法名 + 语句顺序 | 内容 **VERIFIED**；**精确行号 UNKNOWN** |

远程 raw 文本经传输通道后空行/换行被折叠，无法逐行还原 GitHub 行号。为不伪造行号，本文对 gadget 一律以 **blob SHA + 方法内语句顺序** 定位；本地快照文件才给出行号。blob SHA 是 Git 内容寻址的强定位，足以独立复核。

椭圆曲线/域：`ArithConfig.cs` blob `3f7b4fa0…`，域为 BLS12-377 标量域，**p 为 253 bit**（R1 已核；本轮 `ArithConfig` 远程文本同样折叠行号）。取
`p = 0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001`。
`p-2` 的 bit 长度 = 253，popcount = 133，**秘密求逆 = 133 + 253 = 386 次 Beaver 乘法**（依据 `MpcExecutor.cs` L365-370）。

## 1. gadget 调用链（逐层展开，不按类名推断）

| gadget (blob SHA 前 8) | 展开后的底层操作 | 秘密乘法次数（输入含秘密时） |
| --- | --- | --- |
| `FieldAddGadget` `94e89eb0` | `OperationType.Addition` ×(k-1) | 0（本地加法） |
| `FieldNegGadget` `cdf945d1` | `FieldMul(−1, x)`；源码注释 “TODO: After Neg operation is implemented…” | **1**（与公开常数 −1 相乘仍走 Beaver） |
| `FieldSubGadget` | `FieldNeg` + `FieldAdd` | **1** |
| `BoolNotGadget` `4b736179` | `FieldSub(1, x)` → `FieldNeg` + `FieldAdd` | **1** |
| `FieldMulGadget` `6e775d7a` | `OperationType.Multiplication` ×(k-1) | **1**（2 因子时） |
| `FieldInverseGadget` `e11ef3da` | `OperationType.Inversion` ×1 | **386**（秘密路径；公开路径本地 `InverseOrZero`） |
| `FieldNormGadget` `13c898c4` | `FieldInverse` + `FieldMul(x, x⁻¹)` | **387** |
| `FieldEqualsGadget` `fbd6c007` | `FieldSub` + `FieldNorm` + `BoolNot` | **389** |
| `BoolAndGadget` `0bf09fd0` | 直接委托 `FieldMulGadget` | **1** |
| `LowBitWithCarryGadget` `7de9e9a8` | k 个 `BoolNot` + 2(k−1) 个 `BoolAnd` | **3k−2** |
| `LowBitGadget` `de6c11c7` | 委托 `LowBitWithCarry`，丢弃 carry | **3k−2** |
| `SelectComposeGadget` `dc19cb7a` | k 个 `FieldMul(selᵢ,valᵢ)` + (k−1) 个 `FieldAdd` | **k** |

**关键纠正（防过度声称）**：`BoolAndGadget` 名字像布尔门，但实际委托 `FieldMulGadget`，在 MPC 执行器中走 `BeaverMulti`（域 Beaver 三元组 + 域元素公开），**不是**布尔 Beaver 三元组；`FieldNeg`/`BoolNot` 虽然只和公开常数相乘，但只要另一操作数秘密，`containNoSecretShares == false`（`MpcExecutor.cs` L191）即走 Beaver 路径，**不是免费的线性运算**。

## 2. Fetch 电路实际构造（`MemoryTraceFetchCircuitBoardGenerator.cs`，blob `8232e2b8…`）

- L52-63：`for (row = traceCount-1; row >= 0; row--)` 每行调用一次 `FieldEqualsGadget`；**无 break**。
- L65-71：一次 `LowBitGadget(traceCount)` 作用于全部行的 raw 选择位。
- L73-74：反转低比特选择位为升序。
- L79-89：`foreach (col in ColumnNamesToBeFetched)`；`ColumnNamesToBeFetched = ["mem_val"]`（L14），故**只有 1 列**，一次 `SelectComposeGadget(traceCount)`。
- L21-47：所有 trace 单元与 `in_mem_addr` 均为 `Wire.NewPrivateInputWire`；执行器 L470-472 强制私有输入必须是秘密 share，故上表全部“输入含秘密”分支成立。

设当前可见历史行数 `t ≥ 1`：

```
FieldEquals 行扫描   t × 389 = 389 t
LowBit(3t-2)                  =   3t - 2
SelectCompose(1 列)           =   t
------------------------------------------
Fetch 秘密乘法总数  M_FETCH(t) = 393 t - 2
线性加法总数        A_FETCH(t) = 2t (eq) + t (BoolNot in LowBit) + (t-1) (SelectCompose) = 4t - 1
```

`t = 0` 时 `M_FETCH(0) = 0`（step 0 特判，无 Fetch）。

## 3. MPC 执行器证据（`MpcExecutor.cs`，blob `30b7eeb0…`，本地快照有精确行号）

| 原语 | 行号 | VERIFIED 事实 |
| --- | --- | --- |
| 分发 | L160-161 | `for opID` **严格串行**；L156 注释 `TODO: optimize this by parallelizing` → 当前实现无批次并行 |
| 秘密判定 | L191 | `containNoSecretShares = inputValueTags.All(tag => !tag.IsSecretShare)` |
| Addition | L312-330 | 本地 share 加法；**0 通信、0 Beaver** |
| Multiplication | L331-351 | 全公开→本地；含秘密→逐因子 `BeaverMulti`（L345） |
| Inversion | L352-376 | 全公开→`InverseOrZero()`；含秘密→对 `p-2` 比特平方乘，每位 1–2 次 `BeaverMulti`（L365-370） |
| `BeaverMulti` | L736-755 | 每调用消费 **1 个 `FieldBeaverTripleShare`**（L738-742），1 次 `ExposeFieldValues([dA,dB])`（L748）→ **1 个 barrier 轮**；在线暴露 2 个域元素/方 |
| `ExposeFieldValues` | L696-734 | `SetExposedBigIntegerShareVector` 后 `Until(...)` 等齐所有方 → 明确通信轮 |
| 输入/输出 | L482-488, L381-395 | 上线同步 1 轮；公开输出暴露，数量依电路 |

`FieldBeaverTripleShare`（blob 未本地缓存，raw 取得）含 `X, Y, XY` 三个 `Field` → **预处理 3 域元素 / Beaver 乘法**。

**所以**：在当前执行器中 1 次秘密乘法 ⟹ 1 次 Beaver 三元组消费 + 1 个在线 barrier 轮；但这是**当前实现的 VERIFIED 性质**，不是一般定理。未来若实现批处理（L156 TODO），乘法数可不变而轮数下降。反过来，R1CS 约束数**不能**由乘法数推出（Fetch 生成的是 `MpcCircuit`；R1CS 来自另一条 `MemoryTraceProve` 路径）。

## 4. 证据矩阵（严禁用约束数冒充乘法数）

| 原语 | R1CS 约束 | MPC 秘密乘法 | 公开常数乘法 | 线性加法 | 在线轮数 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| `FieldAdd` | UNKNOWN | 0 | 0 | 1 | 0 | VERIFIED（L312-330） |
| `FieldNeg` | UNKNOWN | 1 | 1（网格级 −1） | 1 | 1 | VERIFIED（gadget + L331-351） |
| `FieldSub` | UNKNOWN | 1 | 1 | 1 | 1 | DERIVED |
| `BoolNot` | UNKNOWN | 1 | 1（网格级 1） | 1 | 1 | DERIVED |
| `FieldMul` | UNKNOWN | 1 | 0 | 0 | 1 | VERIFIED |
| `FieldInverse` | UNKNOWN | 386 | 0 | 0 | 386 | VERIFIED + DERIVED（p−2 计数） |
| `FieldNorm` | UNKNOWN | 387 | 0 | 0 | 387 | DERIVED |
| `FieldEquals` | UNKNOWN | **389** | 2 | 2 | **389** | DERIVED（全链 VERIFIED） |
| `BoolAnd` | UNKNOWN | 1 | 0 | 0 | 1 | VERIFIED |
| `LowBit(k)` | UNKNOWN | 3k−2 | 0 | k | 3k−2 | DERIVED |
| `SelectCompose(k)` | UNKNOWN | k | 0 | k−1 | k | VERIFIED |
| Fetch 全电路 (t 行) | **UNKNOWN** | **393t−2** | 3t−1（网格级，全部走 Beaver） | 4t−1 | **393t−2 + O(1)** | DERIVED |
| 预处理（每秘密乘法） | UNKNOWN | — | — | — | — | VERIFIED：1 `FieldBeaverTripleShare` = 3 域元素 |
| 在线通信（每秘密乘法） | UNKNOWN | — | — | — | — | VERIFIED：2 域元素/方；字节数 UNKNOWN |

“公开常数乘法”一列指**电路层的常数操作数**；执行器对“常数×秘密”仍调用 Beaver（L334-349 的 `containNoSecretShares` 为 false），故不得当作免费。R1CS 约束列全部 UNKNOWN：本轮未取得 `MpcCircuit → R1CS` 的编译映射源码，也没有实测证明系统；不得填推测数字。

## 5. E1-ShadowState 的原语结构（Q2）

E1 不是上游电路，需自建。用**同一套 gadget** 实现 n 槽位时：

- `eq(j, addr)`：j 为**公开常量**（槽位下标），addr 为秘密。字段差 `j − addr` 仍为秘密 → `FieldNorm` 仍走秘密求逆 → **389 次秘密乘法/槽**，与 E0 每行**完全同价**。执行器没有“公开−秘密比较”的快捷路径（L352-376 只看 `containNoSecretShares`）。
- read-select：`LowBit(n)` + `SelectCompose(n)`，与 Fetch 同构 → `393n − 2`。
- write-select：`new[j] = old[j] + eq_j·(v − old[j])`。若复用同一步 read 的 `eq_j` → **n 次秘密乘法**；若独立重算 eq → `389n + n`。是否可复用取决于电路实现，**当前无源码证据** → 标 ASSUMED，两种都建模。
- 历史追加：与 E0 相同的 5 列 trace 行，Go to `MemoryTraceProveCircuitBoardGenerator.cs`（L64-83 每行一次 MiMC(7 preimage)）。E0/E1 追加的行完全相同 → **Prove/R1CS 侧成本相同，不构成 E1 优势**。

另一条可能路线（对秘密 addr 做一次 bit decomposition，再与公开 j 逐位比较）可摊薄 n 个槽的比较成本，但**不在上游源码中**，其安全性/成本无证据 → UNKNOWN，本轮不计入任何优势。

## 6. Rust 后端范围（任务限定“与成本证据直接相关”）

- `collaborative-zksnark-mod/mpc-algebra/src/share/field.rs`：`FieldShare::mul` 用 `BeaverSource::triple`，`inv` 用 `inv_pair`（1 乘 + 1 开）；`batch_mul` 可批量开。`mod.rs`：`BeaverSource` trait，`PanicBeaverSource` 会 panic。
- 该 crate 是**证明侧代数 crate**，不是 `CompatCircuit` Fetch 的执行路径；EXP-DORAM-06 已证 C#→Rust R1CS JSON 走 `MF::from_add_shared`，不带 SPDZ MAC。
- 因此**不得**用 Rust `inv_pair` 的便宜求逆去降低上表 386 的估计：那是另一个执行上下文，会犯跨上下文替代错误。Rust 侧秘密乘法的实际轮数/字节数在本轮标 **UNKNOWN**。

## 7. 停止条件检查

关键 gadget（7 个 + 5 个叶子）与 MPC 执行路径全部取得，内容 VERIFIED；R1CS 映射与 Rust 在线通信为 UNKNOWN，已按要求标注且未补猜测。可以继续建立符号成本模型；但在有证据前，不得把任何成本写成实测值。
