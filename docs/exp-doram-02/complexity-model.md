# complexity-model.md — 符号化复杂度模型

> 目标：比较"VDORAM 现有线性扫描 HistoricalKV"与"假设引入 Path ORAM + 状态绑定"的符号成本。
> 不编造常数；无法从源码/论文得到的参数标 UNKNOWN。论文轮数来自 `paper/EXCERPTS.md` p10 §IV-E（VERIFIED）。
> 标注：VERIFIED / INFERRED / UNKNOWN。

## 0. 符号定义

| 符号 | 含义 | 来源/取值 |
| --- | --- | --- |
| `T` | VM 执行步数（= 内存访问次数） | 论文 p10；R1 trace 的 T |
| `N` | ORAM 逻辑容量 / 地址空间大小 | 论文 p8 Fig.5（`n`）/ p10（容量 p） |
| `B` | bucket 大小（每 bucket 槽位数） | ORAM 标准参数，本仓库 UNKNOWN |
| `Z` | 每 bucket 的块数 | 任务包定义，本仓库 UNKNOWN |
| `L` | 树高 `⌈log₂ N⌉` | 标准 Path ORAM，INFERRED |
| `S` | stash 容量 | 本仓库 UNKNOWN |
| `l` | 域位宽 `⌈log₂ p⌉` | 论文 p10（视为小常数） |
| `m` | prover 数量 | 论文 p14（任意 ≥1） |

## 1. 现有 VDORAM 线性扫描成本（VERIFIED，论文基线）

论文 p10 §IV-E 明确给出（VERIFIED，逐字核对）：

| 阶段 | 通信轮数 |
| --- | --- |
| 输入分发 | `m·N` 广播 |
| 指令 fetch（T 次，每次 O(I) 线性扫描） | `O(T·I)` |
| **Memory fetch（T 次，每次 O(T) 线性扫描）** | **`O(T²)`** |
| 指令执行 | `O(T)` |
| trace 排序（Bitonic） | `O(T log²T)` |
| trace 验证 | `O(T)` |

gadget 成本（p10，VERIFIED）：Addition 0 轮；Mul 1 轮；inversion-or-zero `l+4` 轮；**全位分解 `19l+2` 轮**。

**关键**：`O(T²)` 来自"每步对全部历史做 EqualityCheck + 选最新"（论文 ΠHistoricalKV，p9），与 R1 实测的 E0 扫描行数 ∝ T 累积、查询成本随 T 超线性增长一致（R1 报告 §6）。

## 2. 假设引入 Path ORAM 的成本（INFERRED，常数 UNKNOWN）

### 2.1 Position Map 空间与访问成本

| 项 | 符号估计 | 标注 |
| --- | --- | --- |
| 非递归 pos map 空间 | `N · L` 位，秘密共享 → 每方 `N·L` 份额 | INFERRED |
| 递归 pos map | 多层，总空间约 `O(N)`（几何级数），但每层需独立跨 step 状态 | INFERRED |
| 单次 pos 查询 | 非递归 O(1) 秘密数组访问；本仓库无 secret-index gadget，退化 O(N) 线性扫描 | VERIFIED（无原语）/ INFERRED |

**注意**：若用 `SelectComposeGadget` 实现 pos 查询（O(N) 候选线性组合），主 ORAM 的"O(1) 位置查询"优势被抵消，退化为线性扫描——与 §1 基线同类。递归 pos map 每层又需跨 step 状态，把 `state-binding-analysis.md` 的 BLOCKED 复制多层。

### 2.2 单次 Path Read/Write 本地计算量

标准 Path ORAM 每步：读 L 层路径，每层扫 Z 个 bucket 行，每行做秘密 tag 比较 + 选择 + stash 插入/重排（S 槽）。

| 操作 | 每步本地门/比较数量级 | 通信轮数估计 |
| --- | --- | --- |
| 路径读取 | `L·Z` 行 × (比较 + 选择) | `O(L·Z·l)`（每行一次位分解级比较） |
| stash 查找/重排 | `S` 槽 × (比较 + 选择) | `O(S·l)` |
| 回写/重加密 | `L·Z` 行；需随机 leaf/dummy 重随机化 | `O(L·Z)` 轮（乘/加） |
| 合计（单次访问） | — | `O((L·Z + S)·l)` 轮，INFERRED |

### 2.3 单步 ORAM 状态承诺更新成本

按 `state-binding-analysis.md`，需要每步 `H(S_i)` 公开承诺并 SNARK 约束转换：

| 项 | 估计 | 标注 |
| --- | --- | --- |
| 承诺对象大小 | pos map `N·L` 位 + 树 `2^L·Z` 块 + stash `S` 块 | INFERRED |
| 单步 hash 成本 | MiMC 逐元素（论文用 MiMC 对 trace 行 hash，p10）→ `O((N·L + 2^L·Z + S)/block)` 次 hash | INFERRED，常数 UNKNOWN |
| SNARK 约束增长 | 需把 `S_i→S_{i+1}` 展开为 R1CS；规模随状态大小线性 | INFERRED / BLOCKED（无实现） |

**关键**：这是题目 §5 特别要求不能遗漏的开销——**状态承诺不是免费的**，若每步承诺整个 ORAM 状态，成本可能抵消路径访问收益。

### 2.4 T 步累计与结构对比

| 方案 | T 步通信轮数（符号） | 标注 |
| --- | --- | --- |
| 现有线性扫描 | `O(T²)`（memory fetch 主导） | VERIFIED（论文 p10） |
| Path ORAM（仅主路径，不含递归/承诺） | `O(T·(L·Z + S)·l)` | INFERRED |
| 加递归 pos map | 乘递归层数（约 L 层递减规模） | INFERRED |
| 加每步状态承诺 | 再加 `O(T·状态大小)` 的 hash + SNARK 约束 | INFERRED / BLOCKED |

### 2.5 与 O(T²) 的关系（是否存在值得实现的空间）

- 结构上有 `T·(L·Z+S)·l` vs `T²`：当 `T ≫ (L·Z+S)·l` 时 ORAM  asymptotically 更优。
- **但不能据此宣称优势**，因为：
  1. `L·Z·S` 的实际值与递归层成本全 UNKNOWN，常数可能很大；
  2. 每步状态承诺/公开证明开销（§2.3）可能把收益吃掉；
  3. dummy ORAM 操作（非内存步也跑路径）使**每步**都付路径成本，而现有线性扫描每步也付 O(T)——两者都"每步付"，比较取决于单步成本常数；
  4. 论文刻意选择线性扫描的理由是**参与方数量与证明简洁性**（p9），不是不懂 ORAM——说明在该设计目标下 O(T²) 是可接受的权衡。
- 净判定：**存在理论渐近空间，但没有证据表明净收益为正**；UNKNOWN。

## 3. 与原 HistoricalKV 工作量的对应（R1 交叉验证）

R1 实测（报告 §6，VERIFIED）：N=512,T=1024 时 E0 扫描约 159,816 行、查询 3.76ms；E1 查找 1,023 次、查询 0.073ms。这与论文 O(T²) 线性扫描模型定性一致（扫描量随 T 超线性）。但要强调：

- E1 是普通字典（无隐私、非 ORAM），其 O(1) 查询**不能**作为 Path ORAM 成本上界——ORAM 每步要路径读写 + stash + 状态承诺，远高于字典查找。
- 真实比较须在"相同 Fetch 工作负载 + 相同隐私保证"下测 ORAM，而非字典。

## 4. 参数清单（全部 UNKNOWN，禁止编造）

| 参数 | 状态 |
| --- | --- |
| bucket size B、每桶块数 Z | UNKNOWN（本仓库无 ORAM） |
| stash 容量 S 及 overflow 界 | UNKNOWN |
| 递归层数与每层开销 | UNKNOWN |
| 秘密索引原语的实际通信量 | UNKNOWN（原语不存在） |
| 每步状态承诺的 MiMC hash 次数 | UNKNOWN（需新设计） |
| ORAM 重随机化所需随机数生成成本 | UNKNOWN |
| 网络字节数 / 证明大小 | UNKNOWN（无 benchmark） |

## 5. 证据索引

- `paper/EXCERPTS.md` p10 §IV-E（gadget 轮数、O(T²) memory fetch、容量 p、隐私声明）、p9（ΠHistoricalKV 线性扫描、Bitonic padding）、p5（MiMC/证明只查状态完整性）。
- R1 报告 `../experiment-report.md` §6（E0 扫描行数超线性，实测）。
- `path-read-write-analysis.md` §1/§5（原语成本、无 secret-index）、`position-map-analysis.md` §2（递归）、`state-binding-analysis.md` §2.3（状态承诺开销）。
