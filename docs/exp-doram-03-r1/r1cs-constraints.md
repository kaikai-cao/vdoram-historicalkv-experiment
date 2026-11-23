# r1cs-constraints.md — 任务 C：R1CS 约束构造与参数化核算

> 2026-11-23 · 起点 `b88f3db` · 纯纸面设计，不写电路代码。
> 公开关系：`R_i(C_i, C_{i+1}, step_i, C_i^{Hist}, C_{i+1}^{Hist}; witness_i)=1`。
> 标记：**VERIFIED** 固定源码/点名文献证据 · **CONSTRUCTED** 本轮约束规则 · **INFERRED** 由源码参数计数推导 · **UNKNOWN** 未在固定证据闭合。

---

## C0. 关系与 witness 划分

```
Public x_i = ( C_i^{Tree_0..d}, C_i^{Stash_0..d}, C_i^{Top}, C_i^{Meta},
               C_{i+1}^{Tree_0..d}, C_{i+1}^{Stash_0..d}, C_{i+1}^{Top}, C_{i+1}^{Meta},
               C_i^{Hist}, C_{i+1}^{Hist}, step_i, step_{i+1} )

Private witness_i =
  [a], [op] one-hot, [v], [result],
  for each layer j:
    old/new touched bucket slots, old/new stash slots,
    old/new authentication siblings for every node on P_j(ℓ_j),
    [ℓ_j], [ℓ_j'], [b_j], [off_{j−1}], recursive block old/new,
    eviction pick bits, [occ_j], fresh-random bits,
  HistoricalLog row fields, result commitment opening.
```

**witness 是 secret-shared 输入**（VERIFIED 范式：VDORAM 论文 p4-5 “using these secret shares as witnesses”，`EXCERPTS.md` L99-103）；协作 SNARK 用 `(m,t)` 关系，<t 合谋 t-zero-knowledge。公开根由 MPC 打开，是实例的一部分，不是 witness。

---

## C1. 九族约束（CONSTRUCTED）

记 `Open(C, frag, auth)` 表示“用认证路径 auth 把片段 frag 绑定到根 C”：逐层检查 `h_parent = H(h_child, h_sibling)`，最终等于 C。

### C1.1 旧根打开（Commitment opening）

对每层 j：

```
Open(C_i^{Tree_j}, slots_i(P_j(ℓ_j)), auth_i^j) = 1
Open(C_i^{Stash_j}, stash_i^j, ·) = 1        // stash 一次性全哈希，auth 为空
Open(C_i^{Top}, pos_i^d, ·) = 1
```

约束旧 witness 片段确实属于旧公开根；**不提供整棵树**，否则 O(N)。

### C1.2 Merkle authentication

对每个被触碰 bucket：

```
h_bucket = H(addr_1,val_1,leaf_1,valid_1, …, addr_Z,val_Z,leaf_Z,valid_Z)
```

对路径上每个内部节点：

```
h_parent - H(h_left,h_right) = 0
sibling_old = sibling_new   // 未触碰兄弟必须复用同一 hash，防止“顺便改别处”
```

这条相等约束是增量性的核心：它把“只改一条路径”形式化，而不是靠口头声明。

### C1.3 ORAM transition（主层 j=0）

对每个 slot s：

```
eq_s·(addr_s − a) = 0
eq_s·(valid_s)    = eq_s                 // eq 只在 valid slot 上为 1
Σ eq_s ≤ 1                                // 至多一个命中
result = Σ eq_s·val_s
new_val_s = eq_s·v + (1−eq_s)·val_s       // Store 条件写入，Load/NOOP 保持
```

eviction：

```
pick_{t,q,s}·(leaf_s ∉ subtree(t,q)) = 0   // 位分解后的范围约束
written_bucket_{t,q} = Σ_s pick_{t,q,s}·slot_s + (1−Σ_s pick)·dummy
```

所有 `pick` 是秘密比特；无明文 if。

### C1.4 PositionMap transition

对递归层 j=1..d（含顶层寄存器）：

```
b_j     = floor(b_{j−1}/χ),  b_0 = a
off_{j−1} = b_{j−1} − χ·b_j,  0 ≤ off_{j−1} < χ
selected = Σ_{r=1}^{χ} Eq(r,off_{j−1})·block_j[r]
block_j'[off_{j−1} ← ℓ_{j−1}'] = Σ_r Eq(r,off_{j−1})·(r == off_{j−1} ? ℓ' : block_j[r])
ℓ_{j−1}' ∈ [0, 2^{L_{j−1}}−1]            // 位分解范围约束
pos_j[b_j] = ℓ_{j−1}'                      // 秘密写入，由上层 Open 绑定
```

注意每层都要同时满足 C1.1/C1.2/C1.3 的**小型 Path ORAM 实例**；不能只约束主树。

### C1.5 Stash transition（不丢失/不重复/不伪造）

1. **多重集守恒**：取 Fiat–Shamir 挑战 `ρ = H(x_i)`（在 witness 固定后派生），对每个 stash：

```
Σ_{s∈old_stash ∪ read_path} valid_s·ρ^{addr_s}
  = Σ_{s∈new_stash ∪ write_path} valid_s·ρ^{addr_s}
```

并同样对 `(addr,val,leaf)` 三元组做一次独立随机线性累计，防止只保地址不保值。

2. **唯一性**：对 active slot 做两两不等约束（R 是常数）：

```
∀ s≠t:  valid_s ∧ valid_t ⇒ addr_s ≠ addr_t
```

可由 `Eq(addr_s,addr_t)` 与 `valid_s·valid_t·Eq = 0` 实现，成本 O(R²) 次比较，与 N 无关。

3. **无溢出**：`Σ_s valid_s ≤ R`，且 overflow flag 不进入公开实例；若不成立则关系不满足，验证失败。

### C1.6 New commitment

```
Open(C_{i+1}^{Tree_j}, slots_{i+1}(P_j(ℓ_j')), auth_{i+1}^j) = 1
Open(C_{i+1}^{Stash_j}, stash_{i+1}^j, ·) = 1
Open(C_{i+1}^{Top}, pos_{i+1}^d, ·) = 1
```

与 C1.2 的 sibling 相等约束合起来，保证**只有**被访问路径和 stash 改变。

### C1.7 VM binding

```
in_mem_val = result                         // VERIFIED 命名线 L302
out_mem_val 由 VM 电路消费；若 result 不公开，公开只有 C^{result}=H(result, step_i)
```

### C1.8 HistoricalLog binding

```
row_i = (step_i, trace_address_i, is_mem_op_i, is_mem_write_i, result_i)
trace_address_i = is_mem_op_i·a_i + (1−is_mem_op_i)·NegOne
is_mem_write_i = is_store_i
C_{i+1}^{Hist} = H(C_i^{Hist}, row_i[0..4])  // append-only 链
```

dummy Fetch 也满足同一约束（trace_address=NegOne、is_mem_op=0）；ORAM 物理 leaf/path 不进入 row。

### C1.9 Metadata transition

```
step_{i+1} = step_i + 1
version_{i+1} = version_i + 1
accessCount_{i+1} = accessCount_i + 1       // step 0 特例另写常量约束
C_i^{Meta}, C_{i+1}^{Meta} 与上列公开值一致
```

---

## C2. 哈希与具体参数（不得只写 Poseidon）

### C2.1 本轮选择：VDORAM 已有 MiMC（VERIFIED 源码参数）

- `MimcHashGadget` 以 key=0 链式调用 `MimcEncryptGadget`；默认轮常量 **65 个**、`SBox=7`（`MimcEncryptGadget.cs` L16-20、`MimcHashGadget.cs` L24-32）。
- 每轮 `x⁷`：addition chain 需 4 次乘法；每 encrypt = 65×4 = **260 个乘法约束**；k-preimage hash `H(k)=260k`（INFERRED 计数，未含线性约束与常量线）。
- 域兼容性：MiMC 在 `F_p` 上运算，与 VDORAM 的 arithmetic witness 侧一致；`Z2ⁿ` 侧通过 daBit/edaBit 转换（VERIFIED 论文 p4-5），本轮不改混合域接口。
- 抗碰撞安全性沿用 artifact 默认参数，**本轮未重新做密码分析**；若实现要声称 128-bit，需要单独评估，标 UNKNOWN。

### C2.2 Poseidon / P128Pow5T3

**本构造不依赖 Poseidon。** 若以后替换，必须至少固定：标量域、state width `t=rate+capacity`、`α=5` 的 S-box、full/partial rounds、MDS 矩阵与轮常量，并说明与 `F_p` 的兼容性；固定证据集内没有给出这组完整参数（`docs.rs/ark-poseidon` 查询返回 crate 不存在；点名文献未给出本构造所需参数化），因此写“使用 Poseidon/P128Pow5T3”在本轮只能标 UNKNOWN，不能作为已定参数。

### C2.3 单次访问的 hash 计数（CONSTRUCTED）

对每层 j：

| 项目 | 次数 | 每次乘法约束 | 小计 |
| --- | --- | --- | --- |
| Merkle 父节点：旧路径认证 + 新路径重算 | `2L_j` | `H(2)=520` | `1040 L_j` |
| touched bucket hash：每条路径 `L_j+1` 个 bucket | `L_j+1` | `H(4Z_j)=1040Z_j` | `1040 Z_j (L_j+1)` |
| stash root | 1 | `H(4R_j)=1040R_j` | `1040R_j` |
| top register root（仅顶层） | 1 | `1040χ` | `1040χ` |
| 历史日志 append | 1 | `H(5)=1300` | `1300` |

总计（不含 ORAM 算术约束）：

```
C_hash = Σ_{j=0}^{d} [1040 L_j + 1040 Z_j (L_j+1) + 1040 R_j] + 1040χ + 1300
```

递归 PositionMap 增加的约束就是上式中 `j=1..d` 的同类项，加上每层 O(χ) 选择、O(Z_j L_j) eviction 与 O(R_j²) 唯一性；**没有隐藏的全量扫描项**。

---

## C3. 参数化估算示例（CONSTRUCTED，不是实测）

取 `N=2²⁰`，`χ=4`，`Z_j=4`，`R_j=179`（按任务给定解析界的 2⁻¹²⁸ 值），则：

- 层数 `j=0..9`，`D=10`，`L_j = 20,18,16,…,2`，`Σ L_j = 110`；
- 旧认证 + 新重算父 hash 次数 `2ΣL = 220`，bucket hash 次数 `Σ(L+1)=120`，stash root 次数 `D=10`；
- hash 乘法约束：

```
2·110·520  +  120·4160  +  10·(1040·179)
= 114,400 + 499,200 + 1,861,600
= 2,475,200
```

- ORAM 算术约束（每层 `2ZL_j + R_j + R_j²`，取 Z=4）：

```
Σ_j (8L_j + 179 + 179²) = 880 + 1,790 + 320,410 = 323,080
```

- **合计约 2,798,280 个乘法约束/步**（不含加法/线性约束、预处理、协作证明通信）。若采用论文/文档的经验值 `R=89`，hash 与 stash 唯一性成本都会显著下降，但本轮不采用该值作为 128-bit 参数（见 `merkle-oram-construction.md` §A3.1）。

**这不是实测证明时间**，只说明：成本是 `polylog N` 的函数，不含 O(N) 项；但常数很大，sublinear 不代表 practical。证明生成、通信与公共输入规模见 `complexity-accounting.md`。

---

## C4. 必须避免的三种伪增量

1. **只算路径 hash，却用 O(N) 秘密索引取 leaf** → 单步回到 O(N)，必须在递归层用 oblivious array（C1.4）。
2. **只算新根，却不做旧根认证** → 恶意 prover 可用任意状态替换，C1.1/C1.6 必须同时存在。
3. **只比较根，却不做转换约束** → 承诺链只保证连续性，不保证合法性；C1.3–C1.5 不可省（沿用 EXP-DORAM-03 §5.3 已收紧结论）。

---

## C5. 仍未闭合的约束层事项（UNKNOWN / BLOCKED）

- 协作 SNARK 后端是否能以 sublinear witness 高效证明上述关系（尤其递归多层 stash 唯一性 O(D·R²) 与 MiMC hash 量），固定 artifact 与点名文献没有实例；标 UNKNOWN。
- Fiat–Shamir 挑战 `ρ` 的具体派生与域分离需要与证明系统绑定；本轮只给出规则，未固定实现。
- `Open(C, frag, auth)` 的抗碰撞依赖 MiMC 默认参数；未重新做 128-bit 抗碰撞评估（UNKNOWN）。
- 约束是否满足 VDORAM 的 mixed-domain（Fp + Z2ⁿ）全部需求（尤其 op/地址位分解来源），沿用 artifact 已 VERIFIED 的 daBit/edaBit 接口，本轮未验证新电路的域转换成本。
