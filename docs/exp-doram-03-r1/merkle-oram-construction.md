# merkle-oram-construction.md — 任务 A：Merkle-Path ORAM 显式状态构造

> 2026-11-23 · 起点 `b88f3db` · 仅纸面构造。
> 标记：**VERIFIED** 固定 artifact 源码/点名文献直接证据 · **CONSTRUCTED** 本轮给出的可检查规则 · **INFERRED** 有依据推导 · **UNKNOWN** 未在固定证据中闭合。
> 符号：`F` = proof 后端标量域（VDORAM 的 Fp 侧；与 Z2ⁿ 侧通过已 VERIFIED 的 daBit/edaBit 混合域机制交互，本轮不展开）；`N` 逻辑块数；`Z` bucket 容量；`R` stash 容量；`χ` 递归 position-map 的每块 position 数；`L_j=⌈log₂ N_j⌉`；`D` 总层数；`[·]` additive share；`H` Merkle 哈希；`H(k)` 表示 k-preimage MiMC-Hash 的乘法约束数。

---

## A0. 构造目标与关键限制

要检验的不是“Merkle tree 能不能哈希”，而是下面这条链能否同时成立：

```
每步只重算 O(log N) 节点  →  R1CS 只用 O(polylog N) witness 打开旧/新根
        →  verifier 只检查公开根串联  →  MPC 访问模式仍隐藏
```

结论先行：

- **Tree 部分**：Merkle 更新确实是增量式；一次访问只触碰一条路径，重算 `L+1` 个 bucket hash 与 `L` 个内部 hash（CONSTRUCTED）。
- **秘密索引**：若 position map 用 `N` 项线性扫描，则单步回到 O(N)，Merkle 的增量性被抵消；因此必须递归化（CONSTRUCTED 规则 / INFERRED 任意方实现依据）。
- **递归代价**：总路径长度 `Σ_j L_j = O(log²N / log χ)`，仍是 polylog，不是 O(N)（CONSTRUCTED 符号核算）。
- **Stash**：固定容量、固定形状可做；但 EXP-DORAM-03 的 `R=89/≈100` 数值错误，按任务给定解析界修正为 `R≥114`（2⁻⁸⁰）/ `R≥179`（2⁻¹²⁸）。理论界不能直接当实现安全参数。

---

## A1. Tree

### A1.1 显式编码（CONSTRUCTED）

- 逻辑块 `a ∈ [0,N−1]`；叶子编号 `leaf ∈ [0,2^L−1]`，`L=⌈log₂N⌉`。
- bucket 固定在深度 `L`，共 `2^L` 个；每个 bucket 恰 `Z` 个 slot；空 slot 用 `valid=0` 的 dummy 填充。
- slot = `(addr, val, leaf, valid)`，四个域元素；`val` 若超过一个域元素，用 `⌈B/log₂ p⌉` 个域元素表示，本文按 1 个符号计数（不改变渐近结论）。
- bucket hash：`h_bucket = H(addr₁,val₁,leaf₁,valid₁, …, addr_Z,val_Z,leaf_Z,valid_Z)`，即 4Z 个 preimage 的链式 MiMC-Hash。
- 内部节点：`h_parent = H(h_left, h_right)`；`C^Tree = h_root`。
- `C^Tree` 的含义：整棵树全部 bucket 内容的抗碰撞绑定；不加密、不承诺“谁访问了它”，根值本身是公开域元素。

**哈希具体化（VERIFIED/INFERRED）**：固定 artifact 的 `MimcHashGadget` 以 key=0 链式调用 `MimcEncryptGadget`；默认 `roundConstants` 恰 65 个、`SBox=7`（源码快照 `MimcEncryptGadget.cs` L16-20，`MimcHashGadget.cs` L24-32，VERIFIED）。`x⁷` 在 R1CS 中需 4 次乘法（addition chain `x²=x·x, x³=x²·x, x⁶=x³·x³, x⁷=x⁶·x`），故每次 encrypt 260 个乘法约束，k-preimage hash 为 `H(k)=260k`（INFERRED 由源码轮数直接计数；不含线性约束）。本轮**不选用 Poseidon**：若后续替换 `P128Pow5T3`，必须先固定域、rate/capacity、full/partial rounds 与 MDS 常量；固定证据内未给出这些参数，标 UNKNOWN，不能只写“使用 Poseidon”。

### A1.2 一次访问的读写路径（CONSTRUCTED）

给定秘密叶子 `[leaf]`：

1. **读路径**：路径 `P(leaf)` 含 `L+1` 个 bucket（根到叶）。MPC 不能按明文索引“取第 leaf 个 bucket”——那会用 `[leaf]` 决定物理读取位置，直接泄露。做法是把整棵树视为 secret-shared 数组，用 Keller–Scholl 的 oblivious array 秘密索引逐层取出路径节点（VERIFIED 存在性：L2，polylog overhead，任意 m 方、dishonest majority、active secure）；若退化为“对所有节点做秘密谓词选择”，则为 O(N) 扫描，**不得宣称增量**。
2. **block 选择**：对路径上每个 slot 计算 `[eq] = Eq([addr_slot],[a]) ∧ [valid]`，明文形状固定为 `(L+1)·Z` 次比较；命中位置对 <t 合谋方隐藏。
3. **更新**：命中 block 内容为 `[val]` 时被 `[eq]` 条件覆盖；Store 写入 `[v]`，Load 读出旧 `[val]`；dummy 访问也走完整路径与比较，只丢弃 result。
4. **eviction/writeback**：自根向叶，每个 bucket 从 stash 中挑“leaf 落在该 bucket 子树”的 block 填入，剩余填 dummy；每 bucket 固定写 Z 个 slot，无数据相关分支。
5. **Merkle 更新**：重算 `L+1` 个 touched bucket hash，再自底向上重算 `L` 个父节点；未触碰兄弟节点直接复用旧 authentication path 中的 hash。

### A1.3 增量性判据

- 更新 touched 节点数：`(L+1)+L = 2L+1`，与 N 无关地 polylog。
- R1CS 只接收被触碰路径节点 + 兄弟 hash 作为 witness；**不接受整棵树作为 witness**，否则退回 O(N·Z)。
- 若任何人要求“对整棵树做全局一致性重算”，成本 O(N·Z) 是真实成本，必须写入复杂度（`complexity-accounting.md`），不能藏在“Merkle”名目下。

---

## A2. 递归 PositionMap

### A2.1 分层结构（CONSTRUCTED）

令 `N₀=N`，`N_{j+1}=⌈N_j/χ⌉`，`χ≥2`（本轮示例 χ=4）。令 `d = min{j : N_j ≤ χ}`，即顶层 leaf 数组小到可放在参与方共同持有的寄存器份额中。总层数 `D=d+1`：j=0 是数据 ORAM，j=1..d 是递归 position-map ORAM。

- 第 j 层的 ORAM 有 `Tree_j`（`2^{L_j}` 个叶子，`L_j=⌈log₂N_j⌉`）、`Stash_j`、bucket 容量 `Z_j`。
- 第 j 层的数据块 `b_j ∈ [0,N_j−1]` 存 `χ` 个 leaf label；对 j=0，数据块是用户 block `(addr,val,leaf,valid)`；对 j≥1，数据块是上一层 `χ` 个 block 的 leaf。
- `pos_j[b_j]` 给出 `b_j` 在第 j 层树中的 leaf；`pos_j` 本身作为第 j+1 层的数据存储；顶层 `pos_d` 是 O(χ) 个秘密寄存器值。

### A2.2 完整递归访问流程（CONSTRUCTED）

一次逻辑访问 `[a₀]`：

```
[leaf₀] = ReadPos([a₀])          // 经递归层获得
Tree access at layer 0 with [leaf₀] → ([result], updated block)
[leaf₀'] ← FreshRandomLeaf()     // MPC 共同随机，范围 [0,2^{L_0}−1]
WritePos([a₀], [leaf₀'])         // 经递归层写回
```

其中 `ReadPos`/`WritePos` 展开为：

```
// 约定：第 j 层 ORAM 的数据块存上一层 j−1 的 χ 个 leaf label；
//       pos_j 存在第 j+1 层；顶层 pos_d 在秘密寄存器中。
b_0 = a_0
for j = 1 .. d: b_j = floor(b_{j−1}/χ)   // 各层块号，可由位分解秘密计算
从顶层取 [leaf_d] = pos_d[b_d]，然后自顶向下：
for j = d down to 1:
    off_{j−1} = b_{j−1} mod χ            // 秘密 offset
    // 用上一层给出的 [leaf_j] 对第 j 层 ORAM 做一次 access
    block_j  = OblivPathRead_j(Tree_j, Stash_j, [leaf_j], [b_j])
    [leaf_{j−1}] = SecretSelect(block_j, [off_{j−1}])   // χ 项秘密选择，O(χ)
    // block_j 暂存；等下层返回新 leaf 后，在同一 access 的写回阶段更新：
    block_j' = SecretReplace(block_j, [off_{j−1}], [leaf_{j−1}'])
    [leaf_j'] = FreshRandomLeaf(L_j)
    OblivPathWriteback_j(Tree_j, Stash_j, [b_j], block_j', [leaf_j'])
top: pos_d 用 O(χ) 秘密选择把 b_d 的表项更新为 [leaf_d']。
```

每层只做**一次** Path ORAM access（读出旧 leaf 与写回新 leaf 合并），不是“读一次再写一次”的两次访问；若实现拆成两次，成本需按 2 倍计入。递归层数 `d=⌈log_χ N⌉`，每层深度递减，`L_j ≈ log₂N − j·log₂χ`。

### A2.3 递归承诺

每层独立维护 `C_j = (C_j^{Tree}, C_j^{Stash})`，顶层维护 `C^{Top}=H(pos_d entries)`。每步更新所有层：对每层 j，重算 `2L_j+1` 个节点 hash；总 hash 数

```
Σ_{j=0}^{d} (2L_j+1) = O( Σ_j log N_j ) = O( (log₂N)² / (2 log₂χ) + log N )
```

这就是本文对“递归是否偷偷引入 O(N)”的回答：**没有**，只要每层都用秘密索引的 Path ORAM 而不是线性扫描。注意总存储仍是 `Σ_j N_j·Z_j·4 = O(N·Z)`，sublinear 指**每步更新/证明成本**，不是总状态大小。

---

## A3. Stash

### A3.1 容量与参数修正（本轮必须修正 EXP-DORAM-03）

任务给定解析界：`Pr[|S| > R] ≤ 14·0.6002^R`（Z=4 情形，沿用 EXP-DORAM-03 L1 引用）。取 log₂：

```
log₂(14·0.6002^R) = log₂14 + R·log₂0.6002 ≈ 3.807355 − 0.736485 R
```

要求：

| 目标 | 不等式 | R 下界 | 最小整数 R |
| --- | --- | --- | --- |
| ≤ 2⁻⁸⁰ | 3.807355 − 0.736485R ≤ −80 | R ≥ 113.794 | **114** |
| ≤ 2⁻¹²⁸ | 3.807355 − 0.736485R ≤ −128 | R ≥ 178.968 | **179** |

校验：`R=89 → 2^-61.74`，`R=100 → 2^-69.84`，`R=104 → 2^-72.79`，`R=114 → 2^-80.15`，`R=179 → 2^-128.02`。

**因此 EXP-DORAM-03 §3.1/§3.4 的“Z=4: R≈89 达 2⁻⁸⁰；Z=5: R≈100 达 128-bit”不成立。** 另需注明来源冲突：`docs.rs/oram` 页面写明 “With Z = 4 … SO = 89 suffices for 2^{-80} overflow probability”，并称来自原论文 Figure 3 的**实验/保守估计**；该数字不是由本文采用的解析界推出的（VERIFIED 页面文本；解析界数值计算 CONSTRUCTED）。本轮按任务要求使用解析界，故取 114/179，并把“理论界 ≠ 实际 MPC/SNARK 安全参数”作为硬声明：具体实现的 S-box、hash 抗碰撞、预处理失败概率仍需另定。

### A3.2 槽位表示与秘密操作（CONSTRUCTED）

- 每层 stash 固定 `R` 槽，slot = `(addr, val, leaf, valid)`；`valid=0` 为 dummy。
- **occupancy 是秘密**：`[occ] = Σ_j [valid_j]`，永不公开；所有扫描/写回固定跑满 R 槽。
- 命中查找：对每槽 `[eq_j]=Eq([addr_j],[a])∧[valid_j]`，`[result]=Σ[eq_j][val_j]`；O(R) 次秘密比较/选择，R 是安全参数级常数而非 N。
- insert/remove：用 `[eq_j]` 条件更新 slot，不移动数组元素；eviction 同理用条件写回，避免秘密交换导致的分支。
- **overflow**：R1CS 强制 `[occ] ≤ R`（若按 leaf 分组还需各组不超容量）；超出时**不得**产生一个公开 abort 分支（见 `privacy-analysis.md`）。诚实执行下溢出概率由 §A3.1 保证可忽略；恶意 prover 若构造溢出 witness 则不满足约束，验证失败。

### A3.3 stash root

`C^{Stash}_j = H(addr₁,val₁,leaf₁,valid₁, …, addr_R,val_R,leaf_R,valid_R)`，k=4R 的 MiMC-Hash；每次 stash 更新后重算一次（不是按 slot 逐个 Merkle 化），成本 `H(4R)=1040R` 乘法约束。

---

## A4. Metadata

| 字段 | 编码 | 公开? | 承诺归属 |
| --- | --- | --- | --- |
| `step_i` | 域元素，VM 全局步计数 | **公开** | R_i 公开输入；verifier 强制 +1 |
| `accessCount_i` | 域元素，实际 ORAM/VM Fetch 次数 | 公开但确定：`step_i−1`（step 0 除外） | R_i 公开输入，不额外泄露 |
| `version_i` | 域元素，状态根版本号 | 公开，等于 `step_i` | 与根绑定，防替换 |
| `[a_i]`, `[op_i]`, `[v_i]` | VM 输入份额 | 秘密 | 仅在 witness |
| `[leaf]` / `[leaf']` | 各层叶子份额 | 秘密 | 仅在 witness |
| `[occ_j]` / overflow flag | 秘密份额 | **秘密** | 进入 stash root；不进公开输入 |
| `C_i^{Hist}` / `C_{i+1}^{Hist}` | 历史日志承诺 | 公开 | verifier 串联 |
| `C_i^{result}` | 若结果不公开，用承诺 | 承诺公开、内容秘密 | 与 `in_mem_val` 绑定 |
| 初始化 `S_0` | 全 invalid、leaf=0、stash 空 | 公开可复现 | `C_0` 作为 verifier 锚点 |

**关键区分**：公开的是 step/accessCount/version 与各 root；秘密的是地址、叶子、路径、操作类型、stash occupancy 与 overflow flag。Merkle root 单向隐藏状态内容，但**不是零知识证明**；隐私来自 collaborative SNARK 的 t-zero-knowledge 与 MPC 的 `<t` 安全，不是来自 root 本身。

---

## A5. 方案 A / B 在此构造中的位置

- **方案 A（秘密分享 Path ORAM 状态）**：上述 A1–A4 直接给出 A 的完整状态；秘密索引走递归层；任意方安全依赖 Keller–Scholl（VERIFIED 存在性）。
- **方案 B（任意方 MPC-ORAM 子协议 + 公开证明层）**：把上述每层 `ORAM_Access_j` 视为黑盒子协议；公开证明层消费该子协议的公开根与 witness。B 的状态表示与 A 同构；差异在 witness 生成/绑定方式，见 `mpc-snark-binding.md`。

**本轮没有引入第三种 ORAM 架构。** Merkle 是承诺工具，递归 PositionMap 是 Path ORAM 标准组件，二者组合的增量性与成本在本目录内给出可检查规则，不等于已有实现或已有文献先例（后者见 `literature-evidence.md`）。
