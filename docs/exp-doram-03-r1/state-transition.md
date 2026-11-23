# state-transition.md — 任务 B：一次完整状态转换

> 2026-11-23 · 起点 `b88f3db` · 纯纸面伪代码，不是实现。
> 关系：`(S_i, address_i, op_i, v_i) → (S_{i+1}, result_i)`；对应 VDORAM 每非初始 step 的 Fetch + VM step + history append。
> 标记：**VERIFIED** 固定 artifact 源码语义 · **CONSTRUCTED** 本轮协议规则 · **INFERRED** 依赖点名文献存在性 · **UNKNOWN** 未在固定证据闭合。

---

## B0. 输入/输出与秘密属性

| 对象 | 形式 | 属性 | 来源/约束 |
| --- | --- | --- | --- |
| `address_i` | `[a] = thisRegisters[0]` | 秘密份额 | VERIFIED：`ZkProgramExecutor.cs` L230；每非初始 step 都作为 Fetch 输入 |
| `op_i` | one-hot `[is_load],[is_store],[is_noop]` | 秘密份额 | CONSTRUCTED：若公开则泄露操作类型；统一跑同一电路 |
| `v_i` | `[v]` secret share | 秘密份额 | Store 写入值 |
| `leaf` / `leaf'` | 各层 `[ℓ_j],[ℓ_j']` | 秘密份额 | MPC 共同随机采样，范围 `[0,2^{L_j}−1]` |
| 路径节点 | 各层 `P_j(ℓ_j)` 的 slot shares | 秘密份额 | 通过 oblivious array 访问，不用明文索引 |
| `result_i` | `[result]` | 秘密份额 | VERIFIED 绑定点 `AddPrivate("in_mem_val", memVal)` L302 |
| `S_{i+1}, C_{i+1}` | 状态份额 + 公开根 | 状态秘密 / 根公开 | CONSTRUCTED |
| `trace_address_i` | `[a]`（内存操作）/ `NegOne`（NOOP） | 秘密份额 | VERIFIED：P3；与 `fetch_address` 是两个字段 |
| `C_i^{Hist}, C_{i+1}^{Hist}` | 历史日志承诺 | 公开 | VERIFIED 行级 hash 公开输出（MemoryTraceProve L64-83） |

固定语义（不修改）：step 0 不 Fetch，`memVal=zeroShare`；step≥1 恰好一次 Fetch，即使 NOOP 也执行完整读取路径。dummy Fetch 与真实 Fetch 的**电路形状相同**，差异仅在秘密选择位与 trace 行的秘密字段。

---

## B1. 完整伪代码（CONSTRUCTED）

```
ORAM_Step_i( S_i, [a], [op], [v] ) → ( S_{i+1}, [result], C_{i+1} ):

 0. INIT / ANCHOR
    输入: 公开 C_i=(C_i^{Tree_0..d}, C_i^{Stash_0..d}, C_i^{Top}, C_i^{Meta}, C_i^{Hist}), step_i
    C_i 由 verifier 与上一步输出核对（见 verifier-chain.md）；本步电路不再重算整状态。

 1. POS LOOKUP（递归，自顶向下）
    // 约定：第 j 层 ORAM 的数据块存的是上一层 j−1 的 χ 个 leaf label；
    //       pos_j 本身存在第 j+1 层，顶层 pos_d 在秘密寄存器中。
    [b_0] = [a]
    for j = 1 .. d: [b_j] = SecretFloorDiv([b_{j−1}], χ)   // 第 j 层块号
    top: [ℓ_d] = pos_d[b_d]
    for j = d down to 1:
        [off_{j−1}] = SecretMod([b_{j−1}], χ)           // 块内位置
        [ℓ_j]      = pos_j[b_j]                        // 由第 j+1 层/顶层提供
        [block_j]  = OblivArrayAccess(Tree_j, Stash_j, [ℓ_j], [b_j])
        [ℓ_{j−1}]  = SecretSelect(block_j, [off_{j−1}])  // χ 项秘密选择，O(χ)
        // block_j 暂存在寄存器/stash，等下层返回新 leaf 后写回（一次 access）
    输出: [ℓ_0]（主数据块当前所在叶子）
    秘密: 全部；公开: 无。成本: 每层一次 Path ORAM access + O(χ) 选择。

 2. READ PATH（主树 j=0）
    nodes_0 = OblivPathRead(Tree_0, [ℓ_0])     // (L_0+1)·Z_0 个 slot，形状固定
    stash'_0 = Stash_0 ∪ nodes_0               // 固定长度拼接，不公开命中位置
    秘密: 路径节点与 stash；公开: 无。成本: O(Z_0 L_0) shares。

 3. STASH FIND（秘密匹配）
    for s in stash'_0:
        [eq_s] = FieldEquals([addr_s],[a]) ∧ [valid_s]
    [result] = Σ_s [eq_s]·[val_s];  [found] = Σ_s [eq_s]
    秘密: eq/result/found；公开: 无。成本: O(R_0 + Z_0 L_0) 次秘密比较/选择。

 4. APPLY OP（统一形状，不分支）
    [new_val] = [is_store]·[v] + (1−[is_store])·[val_hit]
    [is_real] = [is_load] ∨ [is_store]          // NOOP 仍已执行 1–3，只丢弃 result
    [trace_addr] = [is_real]·[a] + (1−[is_real])·NegOne
    秘密: 全部；公开: 无。成本: O(1) 域运算。

 5. FRESH LEAF（MPC 共同随机）
    [ℓ_0'] = RandomLeaf(L_0)                    // Beaver/预处理随机 + 范围位约束
    然后 stash'_0 中命中 block 的 [leaf] 更新为 [ℓ_0']（用 [eq_s] 条件写）
    秘密: 叶子；公开: 无。成本: O(L_0) 位随机。

 6. POS UPDATE（递归写回）
    for j = 1 .. d:
        [block_j'] = SecretReplace(block_j, [off_{j−1}], [ℓ_{j−1}'])   // 新 leaf 来自下一层递归
        [ℓ_j']     = RandomLeaf(L_j)
        OblivArrayWriteback(Tree_j, Stash_j, [b_j], [block_j'], [ℓ_j'])
    顶层 pos_d 用 O(χ) 秘密选择写入。
    秘密: 全部；公开: 无。成本: 每层一次 Path ORAM access + O(χ)。

 7. STASH / EVICT（固定容量写回）
    for level t = 0 .. L_0:                     // 自根向叶
        for slot q = 1 .. Z_0:
            [pick] = SecretLeafInSubtree([leaf_s], t, q)   // 位比较，固定形状
            write [block_pick] via Σ over stash（秘密选择）
            rest fill dummy
    [occ_0] = Σ_s [valid_s];  R1CS 约束 [occ_0] ≤ R_0；不得公开 abort 分支。
    秘密: pick/occ；公开: 无。成本: O(Z_0 L_0 + R_0)。

 8. TREE WRITEBACK + MERKLE
    for bucket on P_0(ℓ_0): h_bucket' = H(4Z_0 preimages)
    for node from leaf parent to root: h_parent' = H(h_left,h_right)
    用同一组旧兄弟 hash 计算 C_{i+1}^{Tree_0}；各递归层 j 同法。
    公开: 所有 C_{i+1}^{Tree_j}, C_{i+1}^{Stash_j}, C_{i+1}^{Top}。
    秘密: 被承诺的 slot 内容。成本: Σ_j [(L_j+1)·H(4Z_j) + L_j·H(2) + H(4R_j)]。

 9. VM BINDING
    AddPrivate("in_mem_val", [result])          // VERIFIED L302；VM Load 消费
    [out_mem_val] 进入 privOutMemVal / 结果承诺 C_{i+1}^{result}
    秘密: result；公开: 仅承诺（若选择公开）。

10. HISTORICAL LOG APPEND（保留 VDORAM 语义）
    row_i = (global_step_counter=i, [trace_addr], [is_mem_op], [is_mem_write], [result])
    C_{i+1}^{Hist} = H(C_i^{Hist}, row_i 的 5 个字段)      // append-only 链
    dummy Fetch 同样 append 一行：trace_addr=NegOne, is_mem_op=0, result 丢弃
    秘密: row 字段；公开: C_{i+1}^{Hist}。

11. METADATA / OUTPUT
    step_{i+1} = step_i + 1; version_{i+1} = version_i + 1
    输出 ( S_{i+1} shares, [result], C_{i+1}, C_{i+1}^{Hist}, step_{i+1} )
```

---

## B2. 每步的输入/输出/秘密-公开/成本汇总

| # | 步骤 | 输入 | 输出 | 秘密属性 | 公开通信/分支 | 成本 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POS LOOKUP | `[a]`, 各层状态 | `[ℓ_0]` | 秘密索引，<t 合谋 HIDDEN | 无秘密分支；固定 d 层 | `Σ_{j≥1}(ZL + R + χ)` |
| 2 | READ PATH | `[ℓ_0]`, Tree_0 | path shares | 秘密，固定 `(L+1)Z` 形状 | 无 | `O(ZL)` |
| 3 | STASH FIND | path+stash | `[result]`, `[found]` | eq/命中位置秘密 | 无 | `O(R+ZL)` |
| 4 | APPLY OP | `[op]`,`[v]`,`[result]` | `[new_val]`,`[trace_addr]` | 全秘密 | 无统一 if | `O(1)` |
| 5 | FRESH LEAF | 随机带 | `[ℓ_0']` | 秘密随机 | 无 | `O(L)` |
| 6 | POS UPDATE | 各层 block | 新 pos 状态 | 秘密写回 | 无 | 同步骤 1 |
| 7 | STASH/EVICT | stash, path | 新 stash, 写回 blocks | pick/occ 秘密，固定 R/Z | **必须无 overflow 公开 abort** | `O(ZL+R+R²)`（R² 为唯一性检查） |
| 8 | MERKLE | touched nodes | 全部新根 | 根公开、内容秘密 | 公开根广播 | `Σ[(L+1)H(4Z)+LH(2)+H(4R)]` |
| 9 | VM BINDING | `[result]` | `in_mem_val` | result 秘密 | 若公开输出含 result 则泄露，需承诺 | `O(1)` |
| 10 | HIST APPEND | row 字段 | `C^{Hist}` | row 秘密、承诺公开 | 公开承诺 | `H(5)` |
| 11 | META | step | step+1 | step 公开 | 公开 | `O(1)` |

---

## B3. dummy/real Fetch 与执行轨迹隐藏（CONSTRUCTED / 部分 UNKNOWN）

- **形状统一**：NOOP 与真实 Load/Store 都执行 1–8；差别只在 `[op]` 秘密选择位、trace 行的秘密字段与 result 是否被 VM 使用。对网络观察者，消息数量/长度固定。
- **禁止数据相关早退**：stash 满、未命中、eviction 无候选都必须用 `select` 走完固定次数；任何 `if (secret)` 在 MPC 外产生分支即泄露。
- **历史语义**：dummy Fetch 也 append 行（trace_address=NegOne, is_mem_op=0），保持“每非初始 step 一行”的 VERIFIED 语义；ORAM 的物理叶子/路径**不进入**历史行。
- **仍未闭合（UNKNOWN）**：MPC 实现的实际通信轮次/消息长度是否严格与秘密无关，取决于具体协议与网络层；步骤 7 的 overflow 若变成公开 abort，则构成数据相关事件。固定 artifact 与点名文献没有给出“恶意 prover 选择性 abort 仍不泄露”的完整论证，见 `privacy-analysis.md`、`decision.md`。

---

## B4. 与 EXP-DORAM-03 八步伪代码的对应

| 本轮 | EXP-DORAM-03 §3.2 | 变化 |
| --- | --- | --- |
| 1 / 6 | POS-LOOKUP / REMAP | 明确递归层与每层独立根；朴素 O(N) 扫描被排除在 sublinear 构造外 |
| 2–3 | READ-PATH / STASH-FIND | 增加“秘密索引必须经 oblivious array”约束，禁止普通数组索引 |
| 4–5 | APPLY-OP / 随机 leaf | op 保持秘密 one-hot；统一电路无分支 |
| 7 | EVICT | 固定 R/Z 写回，occ/overflow 秘密且 R1CS 约束 |
| 8 | COMMIT | 从整状态 `H(Encode(S))` 改为逐路径 Merkle 增量更新；这是本轮核心 |
| 9–10 | （原 VM/Hist 绑定） | 显式绑定 `in_mem_val` 与 append-only `C^{Hist}`，保持 R1 语义 |
