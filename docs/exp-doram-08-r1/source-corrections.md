# EXP-DORAM-08-R1 — 三项源码勘误（先源码证据，后公式）

固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
起始 commit：`2b5e47fc725a78f3c48ef91168c4efa6b1bb4a82`（本轮未改任何 EXP-DORAM-08 原文件）

## 0. 方法与定位说明

本轮**不重新开展源码大审计**，只对三项勘误做定向核对。证据来源两类：

| 来源 | 定位 | 行号状态 |
| --- | --- | --- |
| 本地快照 `docs/source-snapshot/` | 文件路径 + 快照内行号（文件头含 BLOB SHA） | **VERIFIED**（可直接复核） |
| 固定 commit 的 raw gadget 文本 | 固定 commit + blob SHA（下表）+ 方法名 + 语句顺序 | 内容 **VERIFIED**；**精确行号 UNKNOWN**（传输通道折叠空行，不伪造行号） |

blob SHA（来自 `data/_tree2.json.tmp`，固定 commit 树）：

| 文件 | blob SHA |
| --- | --- |
| `FieldNegGadget.cs` | `cdf945d10051…` |
| `FieldSubGadget.cs` | `ed993455bbfd…` |
| `FieldMulGadget.cs` | `6e775d7a5968…` |
| `FieldAddGadget.cs` | `94e89eb058f2…` |
| `FieldEqualsGadget.cs` | `fbd6c0074f8c…` |
| `SelectComposeGadget.cs` | `dc19cb7a6f35…` |
| `LowBitGadget.cs` | `de6c11c7f7bb…` |
| `FieldNormGadget.cs` | `13c898c41250…` |
| `FieldInverseGadget.cs` | `e11ef3daa6a0…` |
| `MpcExecutor.cs`（本地快照） | `30b7eeb0…`，L191/L312-351/L736-755 可复核 |
| `ZkProgramExecutor.cs`（本地快照） | L205-206 可复核 |

执行器关键分支（本地快照，VERIFIED）：

- **L191**：`containNoSecretShares = inputValueTags.All(tag => !tag.IsSecretShare)`。
- **L312-330 Addition**：含秘密 → 逐 share 本地相加（L323-327），**0 次 BeaverMulti**。
- **L331-351 Multiplication**：全公开 → 本地乘（L334-339，0 乘法）；含秘密 → 对每个后续因子 `BeaverMulti`（L345），**每个因子 1 次秘密乘法**。
- **L352-376 Inversion**：全公开 → `InverseOrZero()`；含秘密 → 对 `p−2` 比特平方乘（L365-370）。
- **L736-755 BeaverMulti**：每次消费 1 个 `FieldBeaverTripleShare{X,Y,XY}` + 1 次 `ExposeFieldValues` barrier。

---

## R1-1：STORE 条件更新成本

**拟议 E1 更新式**：`new_j = old_j + eq_j · (value − old_j)`

### 逐层源码链（不按类名推断）

| 步骤 | gadget（blob） | 展开 | 秘密乘法（输入含秘密时） |
| --- | --- | --- | --- |
| `value − old_j` | `FieldSubGadget` `ed993455` | `FieldNeg(subtrahend)` + `FieldAdd(minuend, negSub)` | 见下 |
| └ `FieldNeg(old_j)` | `FieldNegGadget` `cdf945d1` | `FieldMulGadget(NegOne, old_j)`；源码注释 “TODO: After Neg operation is implemented…，now just multiply with negOne” | **old_j 秘密 → 1**；old_j 公开 → 0（走 L334-339 全公开本地乘） |
| └ `FieldAdd(value, −old_j)` | `FieldAddGadget` `94e89eb0` | `OperationType.Addition` | **0**（L322-327 本地 share 加） |
| `eq_j · (value−old_j)` | `FieldMulGadget` `6e775d7a` | `OperationType.Multiplication`，两秘密因子 | **1**（L345 BeaverMulti） |
| `old_j + prod` | `FieldAddGadget` | Addition | **0** |

### 结论（VERIFIED 链 → DERIVED 计数）

`value − old_j` 中 `old_j` 是槽位内秘密 share（影子表值为秘密），故 `FieldNeg(old_j)` 确实进入 Beaver 路径（`containNoSecretShares=false`，L191/L341-348），**不是免费的线性运算**。

- **每槽共享 eq 的更新乘法数 `c_upd_shared = 1 (FieldNeg) + 1 (FieldMul) = 2`** — DERIVED（每个叶子 VERIFIED）。
- **每槽独立重算 eq 的更新乘法数 `c_upd_separate = c_eq + 2`** — DERIVED（重算一次 FieldEquals + 上述 2 次）。

用户给出的候选 `c_upd_shared=2`、`c_upd_separate=c_eq+2` **得到源码支持**。

### 修正前后差异

| 项 | EXP-DORAM-08（R0） | R1 修正 | 依据 |
| --- | --- | --- | --- |
| `c_upd`（shared） | `1` | **`2`** | R0 只计了 `eq_j·delta` 的 1 次 FieldMul，漏计 `value−old_j` 中 `FieldNeg(old_j)` 的 1 次 Beaver（本轮 VERIFIED） |
| `c_upd_separate` | `c_eq + 1` | **`c_eq + 2`** | 同上 |

线性加法（顺带核对，不遗漏）：`value−old_j` 的 FieldAdd 1 次 + 最终 `old_j+prod` 的 FieldAdd 1 次 = **每槽更新 2 次线性加法**（R0 未单列更新线性项，本轮补上）。

### 是否存在更省的专门条件选择 gadget？

取到的 gadget 目录中**未发现**专门的 “条件更新/CMUX” gadget；`SelectComposeGadget` 是加权和 `Σ sel_i·val_i`（k 次 FieldMul + (k−1) 次 FieldAdd），用于读取选择，直接套用到逐槽更新不会低于 2 次乘法/槽。**是否存在未取到的更省路径 = UNKNOWN**，本轮不假设存在。

### c_eq 是否仍为 389 — 一个必须记录的细节

`FieldEqualsGadget` 源码（`fbd6c007`）把两个输入**原样**传给 `FieldSubGadget`：

```
GetInputWireNames() => ["left", "right"];
ins1 = new FieldSubGadget().ApplyGadget(inputWires, ...)   // FieldSub(left, right)
ins2 = new FieldNormGadget().ApplyGadget([difference], ...)
ins3 = new BoolNotGadget().ApplyGadget([normBit], ...)
```

而 `FieldSubGadget` 只对 **`subtrahend=right`** 做 `FieldNeg`。

- **E0**：`FieldEquals(trace_addr_i, fetch_addr)`，两操作数均为私有输入 share（R0 §2，L21-47）→ `FieldNeg(fetch_addr 秘密)=1` → `c_eq=1+387+1=389`（与 R0 一致，**仍成立**）。
- **E1**：`eq_j = [addr == j]`，j 为**公开槽位下标**。
  - 若按 `FieldEquals(addr, j)` 调用（j 在 right）：`FieldNeg(j 公开)` 走 L334-339 全公开本地乘 → **0 乘法**，`c_eq_e1 = 0 + 387 + 1 = 388`（DERIVED）。
  - 若按 `FieldEquals(j, addr)` 调用（addr 在 right）：`FieldNeg(addr 秘密)=1` → `c_eq_e1 = 389`。

为避免高估 E1 优势，**主成本模型保守取 `c_eq_e1 = 389`**（与 R0、E0 同口径），并把 388 作为“公开操作数优化”变体在敏感性中单列（标 DERIVED，非实测）。**两种都不写成 VERIFIED 的端到端结论。**

---

## R1-2：E1 是否需要 LowBit

### 源码作用

- `LowBitGadget` `de6c11c7`（经 `LowBitWithCarry`）把 raw 相等位向量压成 one-hot：k 个 `BoolNot` + 2(k−1) 个 `BoolAnd`(=FieldMul) = **3k−2 次秘密乘法**。
- `SelectComposeGadget` `dc19cb7a`：`for i in 0..k` 无条件执行 `FieldMul(sel_i, val_i)`，再做 (k−1) 次 `FieldAdd` → **k 次秘密乘法 + (k−1) 次线性加法**；**即使全部 sel=0 也执行全部 k 次乘法**（源码循环无 break/常量折叠）。

### E0 与 E1 的结构差异

- **E0 历史表**：同一地址可多次写入 → 多条历史行的 `eq` 同时为 1 → 必须 `LowBit` 选最新匹配（E0 逆序扫描 + LowBit 取 one-hot）。
- **E1 固定槽位表**：槽位 j 的地址就是公开常量 j（构造定义），`eq_j = [addr == j]`：
  - `addr ∈ [0,n−1]`：恰有一个 j 使 eq_j=1（槽位下标互异）；
  - `addr ∉ [0,n−1]`（含 NegOne/dummy）：全部 eq_j=0。

因此 eq 向量**天然是 one-hot 或全零**，`LowBit` 在 E1 中是冗余操作。代数正确性证明见 `construction-comparison.md`。

### 候选公式核对（保守 c_eq=389）

| 构造 | 组成 | 每 Fetch 秘密乘法 |
| --- | --- | --- |
| **E1-A**（保守，含 LowBit） | n×FieldEquals + LowBit(n) + n×SelectCompose | `389n + (3n−2) + n = 393n − 2` |
| **E1-B**（唯一槽位，无 LowBit） | n×FieldEquals + n×SelectCompose | `389n + n = 390n` |

用户候选 `fetch_A(n)=393n−2`、`fetch_B(n)=390n` **在保守 c_eq 下得到源码与代数支持**。若采用 R1-1 记录的公开操作数优化（c_eq_e1=388），则 `fetch_A=392n−2`、`fetch_B=389n`；本轮主表用保守值，优化变体单列。

### 适用范围硬约束

E1-B 的“唯一槽位”性质**依赖有界地址域 `[0,n−1]`**，这是**我们构造 E1 时的 CONSTRUCTED 假设**，不是 VDORAM 上游已保证的事实。EXP-DORAM-07-R1 的地址域审计结论：目标系统全域有界 = **UNKNOWN**。因此 E1-B 只能标为**有界域构造**；域外地址在 E1-B 中返回默认值 0（代数证明见另文），但“域外地址在目标系统中是否可能出现且应返回什么”仍属 UNKNOWN。

---

## R1-3：step 0 STORE 边界

### 源码证据

`ZkProgramExecutor.cs`（本地快照，VERIFIED）：

- **L205-206**：`if (globalStepCounter == 0) { memVal = zeroShare; ... }` → step 0 **不构造 Fetch 电路**，直接用零 share。
- **L209**（step>0 分支）：才 `new MemoryTraceFetchCircuitBoardGenerator(globalStepCounter)`，逐行比较产生 eq 位。

结论：step 0 没有执行地址比较，**不存在可复用的 eq 结果**。

### 选定语义：方案 A（推荐，本轮实现）

- step 0 不执行 Fetch（遵循上游特判）；
- step 0 **允许 STORE**；
- step 0 STORE **必须独立计算地址比较**，使用 `c_upd_separate = c_eq + 2`；
- 成本函数接收**具体 STORE step 集合**，不再只接收 W 数量后假设所有 STORE 都能复用 eq。

方案 B（禁止 step 0 STORE）未被选中：上游并未禁止 step 0 写入（STORE 由 opcode 决定，与 Fetch 特判无关），强行禁止会引入无证据的约束。

### 修正前后差异

| 项 | EXP-DORAM-08（R0） | R1 修正 |
| --- | --- | --- |
| step 0 STORE（share_eq=True） | 只付 `c_upd`（错误地复用不存在的 eq） | 强制 `c_upd_separate`（本轮实现为：step 0 无论 share_eq 标志如何都按 separate 计费） |
| 成本函数入参 | `W: int` + `share_eq: bool` | `store_steps: set[int]`（显式集合）+ `share_eq`，step 0 单独判定 |

**注意**：step>0 STORE 是否真的能复用本步 Fetch 的 eq，仍取决于电路实现（同一比较结果是否被 STORE 路径引用）。当前无上游源码证据（E1 是我们构造的，非上游电路）→ 标 **ASSUMED**；本轮同时建模 `share_eq=True/False` 两种，默认成本表两种都给。

---

## 本节停止条件检查

三项勘误的源码链（FieldNeg/FieldSub/FieldMul/FieldEquals/SelectCompose + 执行器分支 + step 0 特判）全部取得并核对； gadget 精确行号因传输折叠标 UNKNOWN，未伪造。未扩大到新 gadget 大审计。可以据此建立成本模型（Phase 2）。
