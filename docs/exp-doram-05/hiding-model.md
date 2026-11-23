# hiding-model.md — 私有盐 Hash Commitment 的 hiding 定义修正

> 2026-11-23 · 起点 `ca26127f156d43c7f09c19435e34a627e1bf3f80` · 冻结接口见 `README.md`。
> 标记：**VERIFIED** 原始论文/固定源码一手文本直接支持 · **CONSTRUCTED** 本轮构造的游戏/规则 · **INFERRED** 由明确前提推导 · **CONDITIONAL** 依赖未实例化假设 · **UNKNOWN** 无可靠证据 · **BLOCKED** 接口缺失。
> 本轮只处理 `com = H(x‖s)` 且 `s` 不公开的 hiding 定义；不重做四条路线比较、不重算 ORAM 成本。

---

## 0. 冻结对象

```
x_i   = Encode(ictx_i ‖ W_pre,i)        // 8 字段 + 6 个 ictx 字段，低熵分量存在
s_i   = commitment_blinding_randomness  // 不属于 W_pre,i，不公开
com_i = MiMCCommit(x_i, s_i)            // 本轮按 B2 写作 H(x_i‖s_i)
rho_k = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)
```

本轮要回答的唯一问题：**公开 `com_i` 时，`s_i` 不公开，究竟能给出什么 hiding 保证？**

---

## 1. 三类对象必须严格区分

| 类别 | 构造 | 提交阶段 verifier 看到 | opening | 低熵消息的 hiding |
| --- | --- | --- | --- | --- |
| **A 公开盐** | `com = (H(x‖s), s)` | `c` **和** `s` | 公开 `x`（`s` 已在） | **FAIL**：枚举候选 `x'` 验 `H(x'‖s)=c` 即可 |
| **B 私有盐（本轮 B2）** | `com = H(x‖s)`，`s` 秘密且不向 verifier 打开 | 仅 `c` | 无外部 opening；`s_i` 只作 SNARK 私有 witness，电路内重算见 §4 | ROM 下计算 hiding，见 §3 |
| **C 标准承诺** | `com = Commit(x;s)`, `Open(com,x,s)=1` | `c` | 向 verifier 揭示 `(x,s)` | 依具体方案（Pedersen perfect；hash-based ROM） |

**关键结论 1（CONSTRUCTED，逻辑必然）**：若 A 中 `s` 与 `c` 一同公开，则对低熵 `x` 不可能有 hiding —— 攻击者枚举小消息空间并对每个 `x'` 计算 `H(x'‖s)` 与 `c` 比对即可。因此任何声称「`H(x‖s)`  statistically hiding」的引理，其 hiding 断言**必然是关于 `c` 单独、而 `s` 在承诺阶段保密**的情形。

**关键结论 2（本轮 B2 的定位）**：我们的构造既不是 A（`s_i` 不公开），也不是完整意义上的 C（verifier 永不收到 `(x_i,s_i)` opening）。它是 **B 的变体**：随机化哈希作为承诺，opening 在 SNARK 内部完成，外部 verifier 只检查 `com_i` 与证明一致。是否称之为"承诺"取决于定义；其 *binding* 来自 H 的抗碰撞，*hiding* 来自 `s_i` 的秘密性与 H 的 RO 行为（§3）。

---

## 2. 对 EXP-DORAM-04 所引 Lemma 17 的核查

### 2.1 已核实部分（VERIFIED）

- **论文身份**：Dominique Unruh, *Computationally binding quantum commitments*, Cryptology ePrint Archive **2015/361**，EUROCRYPT 2016 重大修订版（最后一次修订 2022-12-19）。URL `https://eprint.iacr.org/2015/361`。论文主题为**量子敌手**下的 collapse-binding 承诺。
- **canonical commitment 定义**（论文正文逐字，经 ePrint 全文索引取得）：
  > "The most obvious construction is to send `c:=H(m ‖ u)` for uniformly random `u` of suitable length. We call this the 'canonical commitment'. The canonical commitment is easily seen to be classical-style binding if `H` is collision-resistant, and it is statistically hiding if `H` is a random oracle."
- **逐字解读（INFERRED）**：承诺值是 `c = H(m‖u)`；`u` 是 **opening information**，在承诺阶段**保密**、在 open 阶段才揭示。这与 §1 的结论 1 一致 —— 若 `u` 随 `c` 一起公开，"statistically hiding" 对低熵 `m` 不成立。因此该引理描述的是 **B 类（私有盐）**在承诺阶段的行为，不是 A 类。

### 2.2 未核实部分（UNKNOWN）—— 必须撤回的引用

- EXP-DORAM-04（`candidate-analysis.md` §2.1、`security-analysis.md` §1.3、`decision.md` §3）写「Lemma 17 **逐字**：对 `H:X→Y`，`com(m)=H(m‖u)`（**返回 `(c,u)`**），若 `|Y| ≤ 2^{ℓ_u/8}` 则 statistically hiding」，并据此算得 `ℓ_u ≥ 2024 bit ≈ 8 个 Fr`。
- 本轮尝试核对原文：ePrint PDF 与所有存档/作者主页镜像均被 Cloudflare 拦截（`Just a moment...` 页面），无法取得 Lemma 17 的逐字文本、`|Y| ≤ 2^{ℓ_u/8}` 这一具体不等式、或其证明。**该"逐字"引用本身未获一手证实 → UNKNOWN。**
- 进一步的三重不匹配（INFERRED）：
  1. **承诺输出语义不匹配**：Unruh 的承诺值是 `c`，`(c,u)` 是「承诺+开启」的完整 transcript，不是承诺对象；EXP-DORAM-04 的"返回 `(c,u)`"表述若意为 `u` 随承诺公开，与 §2.1 的 hiding 断言内部矛盾。
  2. **敌手模型不匹配**：Unruh 处理的是**量子敌手 + collapse-binding**；本系统冻结威胁模型是"少于阈值的经典合谋方 + 公开 verifier"，未要求后量子 collapse 性质。
  3. **充分条件 ≠ 必要条件**：即便该不等式真实存在，它也是 RO 下统计 hiding 的**充分**条件，不是"达到 128-bit hiding 所必需的盐长"。

**撤回声明**：EXP-DORAM-04 的"私有盐需 ≥2024 bit / 8 个 Fr"结论 **WITHDRAWN**。它既未经原文核实，也把公开随机性方案的充分条件错误移植到私有盐接口。下文用可自行复算的安全游戏替代。

---

## 3. 私有盐的正确 ROM 安全游戏与界限（CONSTRUCTED / INFERRED）

### 3.1 游戏 `G_hide[A, ℓ_s, κ]`

```
参数：输出域 Y，|Y| = 2^κ（本系统 κ = 253，因 H 输出一个 Fr 元素）
     盐空间 S，|S| = 2^{ℓ_s}（ℓ_s = k·253 bit，k = s_i 的 Fr 元素个数）
挑战者：b ← {0,1};  s ← S;  com = H(x_b ‖ s);  把 com 给 A
攻击者 A（PPT，至多 q 次自适应随机预言机查询，看不到 s）：
      (x'_j, s'_j) ← H(...),  j=1..q;  输出 b'
A 胜：b' = b；优势 Adv = |Pr[b'=b] − 1/2|
假设：H 为随机预言机；x_0, x_1 由 A 选择（可低熵，可只差一比特）
```

### 3.2 界限推导（INFERRED，标准 RO 论证）

- 事件 `E`：A 查询了**真实点** `(x_b ‖ s)`。若 `¬E`，A 得到的所有 RO 答案都在非真实点，`com` 是其在未查询点的独立均匀输出 —— `(com, answers)` 的联合分布与 `b` 无关，故 `Pr[b'=b | ¬E] = 1/2`。
- `Pr[E] ≤ q / |S| = q·2^{-ℓ_s}`（每次猜测命中秘密 `s` 的概率）。
- 假预像（`(x_{1-b}‖s')` 恰命中 `com`）对两个候选消息**同等可能**，只影响 binding 不影响 hiding 优势（binding 界限另见 `rom-analysis.md`）。
- 得：**`Adv_hide ≤ q·2^{-ℓ_s}`**。

**数值**（取 `q = 2^128` 的保守查询预算）：

| `k`（`s_i` 的 Fr 元素数） | `ℓ_s` (bit) | `Adv ≤ q·2^{-ℓ_s}` | 判定 |
| --- | --- | --- | --- |
| 1 | 253 | `2^{-125}` | 约 125-bit，略低于 128-bit 目标 |
| 2 | 506 | `2^{-378}` | 远超 128-bit |
| 4 | 1012 | `2^{-884}` | 过量 |
| 8 | 2024 | `2^{-1896}` | 远过量（EXP-DORAM-04 的量级） |

### 3.3 统计 hiding（无界 A）的另一条界（INFERRED，占用/覆盖论证）

若要求对**无界** A（可查询全空间）成立，需 `{H(x‖u) : u∈S}` 几乎覆盖 `Y`，此时 `H(x‖U)`（U 均匀）与 `Y` 上均匀的统计距离约 `2^{(κ−ℓ_s)/2}`，故
`ℓ_s ≥ κ + 2λ`；`κ=253, λ=128 ⇒ ℓ_s ≥ 509 bit ≈ 2.01 个 Fr`。
与 §3.2 的计算 hiding 界同量级：**2 个 Fr 元素已足够**，8 个 Fr 过量约 6 倍。

### 3.4 消息熵的作用（直接回答任务问题）

- **公开盐（A）**：低熵消息可被枚举 → hiding 完全失效。
- **私有盐（B）**：`Adv` 上界 `q·2^{-ℓ_s}` **不含消息熵项** —— 隐藏来自秘密的 `s`，而非消息本身的熵。因此即使 `x` 是单比特 op 类型，只要 `s` 均匀且保密，`x` 仍隐藏。
- 唯一失效路径：`s` 被泄露、被重用、或可被单方重采样（见 `randomness-protocol.md`）。

---

## 4. "能否用于 SNARK witness 内部重算" 的接口性质（CONSTRUCTED）

- 电路内约束 `com_i − H(W_pre,i 的线值 ‖ s_i 线值) = 0` 是 `Fr` 上的原生约束；`com_i` 可作公开输入，`s_i` 作私有 witness（backend-facts §2/§4 VERIFIED 接口）。
- 因此 `com_i` 同时对 **binding**（H 抗碰撞）和 **hiding**（`s_i` 私有 + RO 行为）负责，且与 ORAM 约束共用同一份 `W_pre,i` 线值 —— witness 一致性在规则层闭合（延续 Correction-4）。
- **但这不是对 verifier 的零知识 opening**：verifier 看不到 `s_i`，也看不到 `x_i`，只看到 `com_i` 与 ZK 证明。hiding 的最终成立还依赖 SNARK 本身是 ZK（本轮不重新证明协作 SNARK 的 t-zero-knowledge，标 UNKNOWN，沿用既有边界）。

---

## 5. 本页最终结论

| 问题 | 结论 | 标记 |
| --- | --- | --- |
| Lemma 17 是否适用 | 其 hiding 断言针对**保密 `u`** 的 canonical commitment（与 B 相符）；Exact lemma/`2^{ℓ_u/8}` 未核实；EXP-DORAM-04 的"8 Fr"撤回 | UNKNOWN / WITHDRAWN |
| 私有盐能否给出可证明 hiding | **受限 ROM hiding**：`Adv ≤ q·2^{-ℓ_s}`，有明确安全游戏 | CONSTRUCTED / INFERRED |
| 盐长要求 | 128-bit 计算 hiding 需 `ℓ_s ≳ 256 bit`（1 Fr 约 125-bit，2 Fr 充分）；统计 hiding 需 `κ+2λ ≈ 509 bit`（约 2 Fr） | INFERRED |
| 消息低熵是否致命 | 私有盐下不致命；公开盐下致命 | INFERRED |
| 落到 MiMC 实例化 | RO 行为仅为启发式假设（见 `rom-analysis.md`） | CONDITIONAL |

**四选一结论**：抽象 RO 层为「**受限的 ROM hiding**（选项 2）」，有显式安全游戏与界限；一旦以 MiMC 实例化，退化为「**启发式 hiding**（选项 3）」，因 MiMC 既非可证明 RO，其 65 轮参数亦低于素数域设计推荐（见 `rom-analysis.md`）。**不能**声称标准模型可证明 hiding。
