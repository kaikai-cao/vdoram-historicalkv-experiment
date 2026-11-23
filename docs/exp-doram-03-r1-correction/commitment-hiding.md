# commitment-hiding.md — 任务 C：Merkle commitment 随机盲化

> 2026-11-23 · 起点 `b1bfe29` · 纸面安全分析。
> 核心问题：公开 Merkle root 是否会因确定性哈希泄露低熵 bucket 状态？
> 标记：**VERIFIED** 固定源码/数学事实 · **CONSTRUCTED** 规则 · **INFERRED** 推导 · **CONDITIONAL_CONSTRUCTION** 依赖条件 · **BLOCKED** 未闭合。

---

## C0. 结论先行

- 确定性 Merkle root（C1）只提供**binding**（在哈希抗碰撞下），**不提供隐藏**。低熵 bucket 可被字典猜测。
- 公开随机盐（C2）不能解决隐藏；盐必须秘密且进入状态份额。
- **秘密 nonce 并随每次 bucket 更新刷新（C3）**是本轮唯一给出的候选构造，但仅为 `CONDITIONAL_CONSTRUCTION`：需要把 nonce 产生、认证、R1CS 绑定和 abort 语义补齐；不能说“加盐即零知识”。
- Pedersen 类承诺（C4）有明确 hiding/binding 定义，但改变哈希成本与后端假设；本轮不替换默认 MiMC。

---

## C1. 普通确定性 Merkle hash

```
leaf_h = H(addr₁,val₁,leaf₁,valid₁, …, addr_Z,val_Z,leaf_Z,valid_Z)
root   = Merkle(leaf_h₀,…,leaf_h_{2^L−1})
```

- **binding**：在 H 抗碰撞下，root 确定唯一状态；VERIFIED 源码默认 MiMC 参数，未重新评估安全裕度。
- **hiding**：**无保证**。若 bucket 可能取值集合小（例如初始化附近、低熵地址/叶子、dummy 模式），攻击者可枚举候选 bucket 并计算 leaf/root 比对。
- **可关联性**：若 bucket 内容未变，其 leaf hash 不变；根路径上的相同 sibling hash 跨步重复，产生“该 bucket 未变化”的公开关联。

判定：**不适合作为低熵状态的隐藏承诺**。它不直接破坏 ORAM 访问隐私，但公开 root 成为额外泄露面。

---

## C2. 每个 bucket 加独立随机盐（salt）

```
leaf_h = H(bucket_content, salt_bucket)
```

- 若 salt **公开**，攻击者仍可枚举 bucket 内容并用公开 salt 比对 → 不隐藏。
- 若 salt **秘密**但固定不变，重复内容仍产生相同 leaf hash → 跨步关联仍在。
- 若 salt 秘密但不受承诺约束，恶意 prover 可任意替换 salt 以匹配伪造状态 → binding 崩溃。

判定：公开盐无效；固定秘密盐只部分缓解；必须以状态份额承载并承诺，进入 C3。

---

## C3. 秘密随机 nonce，并在 Merkle leaf 中承诺（推荐候选）

```
state bucket = (Z slots, nonce_bucket)
leaf_h = H(slots₁,…,slots_Z, nonce_bucket)
nonce' = nonce + r_touched   // r 来自 MPC 共同随机，位宽 λ
```

每次 bucket 被触碰都刷新 nonce；未被触碰 bucket 的 nonce 保持不变。若希望隐藏“哪些 bucket 变化”，可对**所有** bucket 每步刷新 nonce，但成本 O(N) → 禁止；本构造只刷新路径上的 bucket，因此“有 bucket 变化但不知道是哪一个”依赖 root 伪随机与 witness 保密，**路径位置仍不公开**。

### C3.1 九个必答问题

| # | 问题 | 回答 |
| --- | --- | --- |
| 1 | 根公开时能否字典猜测低熵 bucket？ | C1 能；C3 下若 nonce 高熵且秘密，枚举 bucket 还需猜 λ-bit nonce，成功概率约 `2^{−λ}` × 候选数 → INFERRED |
| 2 | 随机盐是否必须秘密？ | **必须**。公开盐不提供 hiding |
| 3 | 盐是否进入 MPC shares？ | **必须**。作为 `[nonce]` 存在，与 bucket 一起跨步携带 |
| 4 | nonce 如何保持一致？ | 旧 nonce 由旧 root 打开绑定；新 nonce = 旧 nonce + 本步认证随机 `r`，写入新 root；verifier 只见 root |
| 5 | 旧根到新根是否泄露 bucket 是否变化？ | 若 nonce 每次触碰刷新，root 每步变化且无法从 root 直接判断内容是否变；但“存在路径更新”是每步固定事实，不泄露 leaf |
| 6 | 固定路径访问是否可关联？ | 攻击者看到 root 序列变化；由于新 nonce 随机，同一 bucket 内容的 leaf hash 不重复，关联被削弱。不能声称完全不可关联（BLOCKED：随机源绑定未闭合） |
| 7 | 如何纳入 R1CS？ | leaf hash 增加 1 preimage：`H(4Z+1)`；约束 `nonce'−nonce−r=0`；`r` 来自已认证 MPC 随机带并进入 witness 承诺 |
| 8 | 是否改变 MiMC 参数/成本？ | 参数不变；每 bucket hash 从 `260·4Z` 变 `260·(4Z+1)`，即每层 touched bucket 额外 `2·(L+1)·260` µ（旧/新两侧） |
| 9 | 如何防替换/重放 nonce？ | 旧 nonce 必须打开旧 root；新 nonce 必须等于承诺随机带派生的值，并打开新 root；缺少随机带承诺时恶意 prover 可自选 nonce → BLOCKED |

### C3.2 成本增量

每层：

```
Δµ_nonce = 2·(L_j+1)·260 + (L_j+1)      // 旧/新 leaf 各多 1 preimage + nonce 更新线性/位约束
```

示例 `N=2²⁰, Σ(L+1)=120`：额外 `2·120·260 + 120 = 62,520` µ/步（把 C3 加入推荐报价后总计约 `2,587,363` µ/步）。该数不含随机带承诺成本（UNKNOWN）。

---

## C4. Pedersen 类承诺

```
Com(bucket; r) = g^enc · h^r   （在合适群/域中实现）
```

- 有明确的 perfect/statistical hiding 与 computational binding 定义（离散对数假设）；比“MiMC + 随机盐”的安全表述更干净。
- 代价：需要群运算/椭圆曲线约束，R1CS 成本与现有 MiMC 后端完全不同；MPC 中生成 Pedersen opening 需要额外协议。
- 判定：`CONDITIONAL_CONSTRUCTION`。本轮不替换 MiMC，也不把 C4 写成已实现。

---

## C5. 四种方案对照

| 方案 | binding | hiding | 固定性泄露 | 成本 | 判定 |
| --- | --- | --- | --- | --- | --- |
| C1 确定性 Merkle | H 抗碰撞 | 无 | 有 | 最低 | 不选用作隐藏承诺 |
| C2 公开盐 Merkle | H 抗碰撞 | 无 | 有 | 低 | 不选用 |
| C3 秘密 nonce Merkle | H 抗碰撞 + nonce 状态绑定 | 条件性（λ-bit nonce 秘密） | 大幅削弱，非严格证明 | +约 62.5k µ/步 | 推荐候选，CONDITIONAL_CONSTRUCTION |
| C4 Pedersen | DL 假设 | 明确 | 可设计无关联 | 高、后端改变 | 备选，CONDITIONAL_CONSTRUCTION |

---

## C6. 必须避免的过度声称

- **不能说“加随机盐就有零知识”**：零知识是证明系统属性，承诺 hiding 是承诺属性；二者不同。
- **不能说 C3 自动隐藏路径**：公开 root 不显示路径，但 proof 实例、MPC transcript 与 abort 仍可能泄露（见 `privacy-revision.md`）。
- **不能说 nonce 可以任意由 prover 生成**：那会破坏 binding，并让恶意 prover 重放旧 nonce 制造状态替换。

---

## C7. 本轮结论

C1 被否决为隐藏承诺；C2 无效；C3 是唯一与现有 MiMC/MPC 架构相容的候选，但依赖“承诺随机带 + nonce 状态绑定 + 防重放”三个未闭合条件。故整体为 **CONDITIONAL_CONSTRUCTION**，不是 CONSTRUCTED，也不是已证明安全。
