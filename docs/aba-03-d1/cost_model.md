# ABA-03-D1 / Phase E：符号成本模型（不填虚构数值）

> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35…`；起点 `f3933474…`。只读设计评估，不实现电路、不运行 benchmark。
>
> 本文只给**符号表达式与成本类别**。所有具体约束数、乘法门数、时间、字节数一律 `UNKNOWN`：本轮没有电路实现，也没有 gadget 级可靠来源。任务明确要求不做虚构数值 benchmark。

---

## 0. 记号与定义

| 符号 | 含义 |
| --- | --- |
| `T` | 总执行步数（含 step 0） |
| `M` | 真实内存事件数（`is_mem_op=1` 的步，即 Load/Store 数） |
| `D = T − 1 − M` | dummy Fetch 数（step≥1 的非内存步；step 0 无 Fetch） |
| `L` | `bit_length(Nmax)`，范围检查位宽；要求 `2^L ≤ p` |
| `C_step` | 每步基础执行成本（VM 电路现状，不因本改造改变） |
| `C_real` | 每个真实访问步新增成本（范围检查 + 三值相等） |
| `C_dummy` | 每个 dummy 步新增成本（哨兵语义 + 事件分类） |
| `C_prog` | 程序身份相关一次性成本（P1-A 表比较或 P1-B digest） |
| `C_commit` | 承诺一次调用成本（若方案含承诺） |
| `C_recursive` | 递归/组合验证成本（若方案含递归） |

**总量骨架**（仅结构，不代表任何实测）：

```
C_total(T, M) = T · C_step + M · C_real + (T − 1 − M) · C_dummy + C_prog
               (+ 方案相关项：C1 公开字段 / C2 T·C_commit / C3 C_recursive)
```

`C_step` 是现状基线，不是本改造新增；本改造的新增成本集中在 `C_real`、`C_dummy`、`C_prog` 及方案相关项。数值全部 `UNKNOWN`。

---

## 1. 五类成本必须分开（不得相互等同）

| 成本类别 | 本文如何处理 | 与他人的关系 |
| --- | --- | --- |
| R1CS/PLONK 约束数量 | 用符号项表示，数值 `UNKNOWN` | ≠ MPC 乘法数；≠ 通信轮次 |
| MPC 乘法与通信轮次 | 单独列出；受 additive-only 限制（见 `../exp-doram-06/rust-authenticated-share-path.md` B.5/B.6），数值 `UNKNOWN` | ≠ 约束数；≠ 时间 |
| proof 生成时间 | `UNKNOWN`（依赖实现/硬件/并发） | ≠ verifier 成本 |
| verifier 验证成本 | `UNKNOWN`（标准 `verify_proof` 为 pairing 等式，`verifier.rs:32-43/61`，本改造新增公开输入会改变其规模） | ≠ prove 时间 |
| 公开输入/数据规模 | 用字段数符号表示，字节数 `UNKNOWN` | 与隐私直接相关 |

**明确的错误等价**（延续既有冻结结论）：约束数 ≠ 乘法数 ≠ 通信轮次 ≠ Python 时间 ≠ 真实性能。本文不重犯。

---

## 2. 按方案的成本维度清单

### 2.1 方案 C1：直接公开地址

| 成本维度 | 符号/类别 | 数值 |
| --- | --- | --- |
| 新增 public inputs 数量 | 每步每 proof 约 5 字段 `(step, pc, opcode, is_mem_op, addr)` → `O(T)` 量级 | 具体数 `UNKNOWN` |
| 新增 private witness 数量 | 无需新私有 witness（把已有私有值提升为公开） | `UNKNOWN` |
| 新增等式约束数量 | 范围检查（位分解 L + Boolean L + 比较）、三值相等、分类来自 opcode 的断言；`C_real` 含范围+相等，`C_dummy` 含哨兵+分类 | `UNKNOWN` |
| 新增哈希/承诺调用数量 | 若不做承诺则 0；P1-A 表比较为 verifier 侧，非电路哈希 | `UNKNOWN` |
| 非原生域运算 | 无（公开字段与范围检查在 Fr 内） | 无 / `UNKNOWN` |
| 递归验证成本 | 无 | 无 |
| 每步与总步数关系 | `C1_add = M·C_real + D·C_dummy`，公开字段 `O(T)` | — |
| M 与 D 关系 | `D = T − 1 − M` | — |
| 额外证明轮次/MPC 交互 | 公开输入增加不改变每步 prove 结构；是否增加 MPC 交互取决于公开值注入方式 | `UNKNOWN` |

### 2.2 方案 C2：共享隐藏承诺

| 成本维度 | 符号/类别 | 数值 |
| --- | --- | --- |
| 新增 public inputs 数量 | 每步公开 `com_i`（+ 分类字段，若需）：`O(T)` 个承诺字段，但地址不公开 | `UNKNOWN` |
| 新增 private witness 数量 | 承诺随机数 `r_i`（每步 1 或按设计）；`O(T)` | `UNKNOWN` |
| 新增等式约束数量 | 承诺重算（VM 侧 + Fetch 侧各一次）+ 范围/相等约束；`T·C_commit + M·C_real + D·C_dummy` | `UNKNOWN` |
| 新增哈希/承诺调用数量 | `2T`（两电路各算一次）+ 程序承诺（若 P1-B）；MiMC gadget 已在 Fr 使用（`:1013`） | 调用次数符号；门数 `UNKNOWN` |
| 非原生域运算 | 若用 MiMC 类域内承诺：无；若用 Pedersen：需群运算/其他域，域兼容 `UNKNOWN` | `UNKNOWN` |
| 递归验证成本 | 无（除非与 C3 组合） | 无 |
| 每步与总步数关系 | `C2_add = T·C_commit + M·C_real + D·C_dummy + C_prog` | — |
| M 与 D 关系 | `D = T − 1 − M`；承诺对所有步计算（含 dummy） | — |
| 额外证明轮次/MPC 交互 | `r_i` 若由 MPC 认证随机生成，新增交互轮次；当前 additive-only 无 MAC（见 exp-doram-06） | `UNKNOWN` |

### 2.3 方案 C3：证明组合 / 递归

| 成本维度 | 符号/类别 | 数值 |
| --- | --- | --- |
| 新增 public inputs 数量 | 顶层 statement 公开字段（程序身份、实例锚点、承诺等）；具体数量未定 | `UNKNOWN` |
| 新增 private witness 数量 | 递归验证 witness（子 proof、VK 等） | `UNKNOWN` |
| 新增等式约束数量 | 递归电路内部验证两份子 proof 的约束；规模取决于组合方式 | `UNKNOWN` |
| 新增哈希/承诺调用数量 | 递归内哈希/FRI/pairing 验证相关；未定 | `UNKNOWN` |
| 非原生域运算 | PLONK 递归通常需跨域模拟（BLS12-377 Fr 与内层域），固定 commit 未见相关 gadget 证据 | `UNKNOWN` |
| 递归验证成本 | `C_recursive`（新增大项，可能主导） | `UNKNOWN` |
| 每步与总步数关系 | 取决于是否逐步递归或批量组合；未定 | `UNKNOWN` |
| M 与 D 关系 | 未定 | `UNKNOWN` |
| 额外证明轮次/MPC 交互 | 需改造 `mpc_prove_and_verify_compat_circuit`（`plonk.rs:293-315`）；当前无递归分支（`client.rs:36-65`） | `UNKNOWN` |

---

## 3. 与现有可复用项的边界

- **可复用（源码支持）**：公开输入通道（`InstructionFetch...cs:126-156`、`plonk.rs:143-161`）；标准 `verify_proof`（`verifier.rs:27-61`）；MiMC gadget（`:1013`）；逐行 opcode 选择骨架（`:158-213`）；逐行哈希（`:215-235`）。
- **不可直接复用 / 需新增**：整程序承诺、跨电路共享承诺、事件计数与顺序约束、独立 verifier 与固定 vk、递归/组合接口（均见 `ABA-03-C2`、`design_options.md`）。
- **additive-share / proof 接口是否构成独立阻断项**：从成本角度，若 C2 需要认证随机而当前无 MAC，可能新增显著 MPC 交互；是否达到「阻断」级别需 `UNKNOWN`（依赖具体承诺方案与 MPC 协议选择），本文不下定论。

---

## 4. 本文明确不声称的事

- 不提供任何约束数/乘法门数/时间/字节的具体数字。
- 不声称 R1CS/PLONK 映射已实现、Halo2 电路已实现、协同后端可用、真实 trace 已绑定。
- 不把符号骨架 `C_total` 当成实测成本模型或性能预测。
- 不把「可复用 gadget」当成「整体方案成本已知」。
