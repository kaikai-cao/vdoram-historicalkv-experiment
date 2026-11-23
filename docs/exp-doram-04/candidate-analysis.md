# candidate-analysis.md — 四条 L2 承诺候选路线的构造、来源与适配

> 2026-11-23 · 起点 `2556ece` · 冻结接口见 `README.md`，后端事实见 `backend-facts.md`。
> 标记：**VERIFIED** 原始论文/源码一手文本直接支持 · **CONSTRUCTED** 本轮明确构造 · **INFERRED** 有依据推导 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 当前接口缺失。
> 设公开输入 `x = Encode(ictx_i ‖ W_pre,i)`（覆盖 8 字段），盲化随机数 `s_i ∉ W_pre,i`，电路域 `F = Fr(BLS12-377)`，`|F| = r ≈ 2^253`。

---

## 0. 一个必须先讲清的结构性张力

两条基本承诺路线在“域”上各有代价，无法同时原生：

| 承诺群/函数 | 消息与随机数的域 | 承诺值的域 | 在 `Fr` R1CS 内验证开口 |
| --- | --- | --- | --- |
| 代数 hash（MiMC） | `Fr`（原生） | `Fr`（一个域元素，原生） | 重算 `H(x‖s_i)=com_i`，**原生** |
| Pedersen（群 G） | 群的标量域 `Fr'` | 点的坐标域 `Fq'` | 验证 `g^x h^s=C` 需 `Fq'` 算术 |

- 若要求群**坐标域 = Fr**（点原生），则曲线定义在 `Fr` 上，其群阶 `r'` 由 Hasse 定理约 `2^253` 但 **`r' ≠ r`**（恰等于 `p` 的曲线为反常曲线，不安全）。于是标量 `x,s` 落在 `Fr'` 而非电路域 `Fr`，需域转换/范围约束 → **非原生移到标量侧**。
- 若要求群**标量域 = Fr**（标量原生，如 G1(BLS12-377) 阶为 `r`），则点坐标在 `Fq(BLS12-377)`（377 bit，`≠Fr`）→ **非原生移到坐标侧**。
- 这是曲线不能“自循环”（base field = scalar field）的直接后果；曲线循环（BLS12-377 ↔ BW6-761）只能把非原生运算推迟到另一条曲线，故用于递归而非单电路内原生验证。

**结论**：`Fr` 电路内**不存在**完全原生的群型 Pedersen；只能在“原生 hash（安全归约弱）”与“群 Pedersen（安全归约强，验证非原生）”之间取舍。这是 B1/B2/B3 分化的根源（INFERRED，依据 Hasse 定理 + ePrint 2022/586 §2 曲线链）。

---

## 1. B1 — Pedersen commitment `com = g^x · h^{s_i}`

### 1.1 构造与安全依据（VERIFIED）

- **原始文献**：T. P. Pedersen, *Non-Interactive and Information-Theoretic Secure Verifiable Secret Sharing*, CRYPTO 1991, LNCS 576, pp. 129–140, DOI `10.1007/0-387-34805-0_22`。
  - 方案：`Com(v;r) = g^v h^r`，`r ← Z_q`（`q = ord(G)`，`g,h` 为生成元且 `log_g h` 未知）。
  - 性质：**perfectly hiding**（承诺与消息统计独立）+ **computationally binding**（DL/DDH 假设）。
  - 二手权威复述（一手定义逐字）：Jokumsen et al., *Verifiable proofs for the energy supply chain*, Energy Informatics 6(Suppl 1):28 (2023), Appendix/Definition 1：「The Pedersen commitment has the following two properties. Perfectly Hiding: the commitment ← Com(v; r) is statistically independent of the value v. Binding: Assuming that DDH assumption is hard in G and the pair-wise discrete log between g and h is unknown, it is computationally hard to find o′, v′ …」；另见 Liskov, *Updatable Zero-Knowledge Databases*, LNCS 3788 §4.3（「perfectly hiding and computationally binding」）。
- **本轮判定**：Pedersen 的 hiding/binding 定义本身是 **VERIFIED**，不依赖 artifact。

### 1.2 消息编码：必须先 CRH 压缩（CONSTRUCTED / 细节 UNKNOWN）

`x = Encode(ictx‖W_pre)` 含 8 个字段（stash R=179 槽、递归多层路径等），远超一个 `Fr` 元素。Pedersen 消息空间是 `Z_q`，所以必须：

```
d = CRH(x) ∈ Fr        // 用 MiMC 链式 hash 把 x 压成一个域元素
com_i = g^d · h^{s_i}
```

- 这一步引入一个**额外 hash 的 CRH 假设**；binding 从「DL」变成「DL ∧ CRH 无碰撞」。
- 具体 `CRH` 的输入分块/轮数、是否覆盖全部 8 字段，本轮**不实现**，标 **UNKNOWN**（沿用 Correction-4「`Encode` 覆盖 8 字段为 CONSTRUCTED 规则 / 实现 BLOCKED」）。
- **关键风险**：`d = CRH(x)` 只承诺了压缩值。若 `W_pre` 中某字段不进入 `CRH`，则该字段可被替换而 `com_i` 不变 → 承诺未覆盖该字段。必须让 `CRH` 显式吸收 `ictx`（含 `attempt_i`）与 8 字段。

### 1.3 域适配三形态（用户点名必须区分）

| 形态 | 描述 | 本轮判定 |
| --- | --- | --- |
| (i) 电路内直接验证 | 在 `Fr` R1CS 内验 `g^d h^{s_i}=C`。取 G1(BLS12-377)：标量 `d,s_i∈Fr` 原生，但点 `C,g,h` 坐标在 `Fq`(377 bit) → **非原生 `Fq` 算术** | **CONDITIONAL / BLOCKED**：安全定义清楚，needs 非原生 gadget |
| (ii) 电路内非原生验证 | 用位分解模拟 `Fq` 乘法。文献代价：BN254 基域非原生乘法约 **600×**（ePrint 2024/265 §1）；PLONK 优化后椭圆曲线模拟约 **one order of magnitude**（ePrint 2025/695 摘要）；arkworks 有非原生框架（ePrint 2020/1522 §4） | **INFERRED 有界**：10×–600× 量级；本 artifact **无**该 gadget → **BLOCKED** |
| (iii) 电路外验证 + 显式桥接 | 外部 verifier 验 G1 方程；SNARK 公开输入需含同一 `com_i` 与同一 `d` 的绑定 | 见 B4；桥接本身需新证明 → **CONDITIONAL / BLOCKED** |

### 1.4 对本系统的结论

- **优点**：唯一有**标准安全定义**（perfect hiding + DL-binding）的候选；`s_i` 均匀随机时 hiding 不依赖 hash 的 RO 假设。
- **障碍**：opening verification 要么非原生（10×–600×，无 gadget），要么外部桥接（循环风险）。`s_i` 必须落在 `Fr'`（若用 G1(BLS12-377) 则 `Fr'=Fr`，原生，好）；但点坐标域 `Fq` 带来全部非原生成本。
- **改造范围**：**中等到系统级**（需新增非原生域 gadget + 曲线点运算 gadget + 域分离挑战接口）。
- **状态**：**安全定义 VERIFIED；当前后端适配 BLOCKED**。

---

## 2. B2 — Hash-based hiding commitment `com = H(x ‖ s_i)`

### 2.1 安全定义与条件（必须精确，不能写“加盐即隐藏”）

- **binding**：来自 hash 的抗碰撞（CRH）。形式化：PPT 敌手找到 `(m,r)≠(m',r')` 使 `H(m‖r)=H(m'‖r')` 的概率可忽略（ePrint 2025/1333 §2 安全游戏；ePrint 2021/478 §2 birthday bound：`2κ` bit 输出下碰撞概率 `≤ q²/2^{2κ}`）。
- **hiding**：**仅在随机预言机模型（ROM）下**成立，且**有随机量长度条件**。原始结果：
  - ePrint 2015/361（*Computationally binding quantum commitments*）Lemma 17 逐字：对 `H:X→Y`，canonical commitment `com(m)=H(m‖u)`（返回 `(c,u)`），若 `|Y| ≤ 2^{ℓ_u/8}`（`ℓ_u` = 随机量 `u` 的比特长），则对随机预言机 `H` 该承诺 **statistically hiding**。
  - ePrint 2024/1074（*Trust Nobody*）Definition 1 + 正文逐字：使用「random-oracle-based commitment scheme where the message m is concatenated to a randomness r and given in input to a random oracle」，并用 Poseidon 实例化，**明确写「We make the heuristic assumption that such instantiation of the commitment scheme is secure」**。
  - ePrint 2021/195 §2.3：`c ← H(m‖r)` 是「computationally binding (due to collision resistance) and hiding (due to pre-image resistance)」——注意这是“原像难”式弱 hiding 表述，与 ROM 统计 hiding 不等价，说明**文献用语需逐篇核对**。

### 2.2 对 `s_i` 长度的硬约束（本轮关键计算）

`H` 输出一个 `Fr(BLS12-377)` 元素 ⇒ `|Y| ≈ 2^253`。套用 Lemma 17 的条件 `|Y| ≤ 2^{ℓ_u/8}`：

```
2^253 ≤ 2^{ℓ_u/8}  ⇒  ℓ_u ≥ 2024 bit  ≈ 8 个 Fr 元素
```

- **一个 253-bit 的 `s_i` 不满足** ROM 统计 hiding 的充分条件；若只用单域元素盲化，则 canonical commitment 的 hiding **在 Lemma 17 意义下无保证**。
- 这解释了为什么“加一个随机盐”不够：**必须把 `s_i` 扩成约 8 个域元素（≈2024 bit 熵）并按此长度约束**，或改用其它有明确 hiding 归约的方案。
- 该计算为 **INFERRED**（直接套用 Lemma 17 条件 + `|Y|=2^253` VERIFIED），**不是**本轮新增安全证明。

### 2.3 与 MiMC gadget / 后端的关系

| 项目 | 结论 | 状态 |
| --- | --- | --- |
| Fr 兼容 | 完全原生：`H` 是 MiMC 链式 hash，输入/输出均 `Fr` | VERIFIED（源码） |
| 现有 gadget | MiMC 已有（65 轮，SBox=7）；`H` 封装可复用 | VERIFIED |
| opening verification | 电路内重算 `H(x‖s_i)=com_i`，`com_i` 可为公开输入，`s_i` 为私有 witness | CONSTRUCTED（规则）/ 实现需新增封装 |
| hiding 依据 | 仅 ROM + MiMC 被当作 RO 的**启发式假设**；非标准模型归约 | CONDITIONAL / 无严格归约 |
| binding 依据 | MiMC 抗碰撞（安全裕度 UNKNOWN，见 backend-facts §3） | UNKNOWN 裕度 |
| 随机源 | `s_i`（建议 ≥8 域元素）须 MPC 联合生成、MAC、不可重采样 | BLOCKED（artifact 无接口） |
| grinding | 若 prover 能重采样 `s_i` → 改 `com_i` → 改 ρ；Correction-3 的 `q_H·2^-168` 复活 | CONSTRUCTED 风险 / 执行 BLOCKED |
| 与同份 witness 绑定 | 电路内同线值重算，与 ORAM 约束共用 `W_pre,i` | CONSTRUCTED（规则层） |

### 2.4 对本系统的结论

- **优点**：唯一**原生、低成本、可立即在现有 gadget 上写出约束**的路线；`com_i` 与 ORAM 约束天然共用同一 `Fr` 线值 → witness 绑定在规则层闭合。
- **障碍**：hiding 只有 ROM + 启发式假设，**不是**标准模型安全；且需把 `s_i` 扩至 ~8 域元素才满足 Lemma 17；MiMC 安全裕度 UNKNOWN。
- **改造范围**：**局部**（新增 `H(x‖s)` 封装与 8×域元素随机带；随机源接口仍 BLOCKED）。
- **状态**：**CONDITIONAL**——工程上最接近，但 hiding 缺严格归约。

---

## 3. B3 — Curve-cycle / 内嵌曲线路线

### 3.1 原始事实（VERIFIED）

- BLS12-377 是 2-chain 的内曲线，与 BW6-761 构成曲线循环用于递归 SNARK：
  - ePrint 2022/586（*A survey of elliptic curves for proof systems*）§2 逐字：ZEXE [BCG+20] 用 BLS12-377（377-bit 基域，253-bit 子群 `r`，`2^47 | r−1`）配 Cocks–Pinch 的 CP6-782；El Housni–Guillevic [EHG20] 提出更快的 **BW6-761** 外曲线（761-bit 域），[EHG22a] 推广到任意 BLS12 上的 BW6 2-chain。
  - ePrint 2021/301（Koshelev）逐字：BLS12-377 的 G1 为 `E_b: y²=x³+b`（`b=1`），BW6-761 的 G2 亦 `b=4`；用于 recursive SNARK。
- 曲线循环的作用是：把“在电路内验证另一条曲线上的群运算”变成“在配对链的另一侧原生验证”，从而支持**递归证明组合**，不是让单电路内的群承诺免费原生。

### 3.2 三条子路线

| 子路线 | 描述 | 判定 |
| --- | --- | --- |
| B3-a 换证明曲线以适配承诺群 | 把整体 SNARK 从 BLS12-377 迁到某条曲线，使电路域 = 承诺群坐标域，从而点运算原生 | **系统级迁移**：公共参数、setup、verifier、协作证明后端全部重做；且需重新核对 MPC 与 co-SNARK 的域一致性 → **BLOCKED / 超出本轮范围** |
| B3-b 内嵌曲线（曲线定义在 `Fr` 上） | 找一条 `E/Fr(BLS12-377)` 使点坐标原生；标量域 `r'≈2^253` 但 `r'≠r`，`s_i,d` 需域转换/范围约束 | **CONDITIONAL**：Hasse 保证 `r'≈2^253`，但要 `r'=r` 会成反常曲线（不安全），故非原生移到标量侧；且 artifact 无此曲线 gadget → **BLOCKED** |
| B3-c 用 BW6-761 递归包装 | 把 Pedersen 开放验证放到 BW6-761 侧，用递归证明回传 | **系统级**：需递归证明栈；VDORAM artifact 无递归接口（verifier 只验单 proof） → **BLOCKED** |

### 3.3 对本系统的结论

- **是局部改造还是系统级迁移**：B3-a/B3-c 是**系统级迁移**，B3-b 是**中等改造**（新增内嵌曲线 gadget + 标量域适配）。均不是“换个 gadget”能完成。
- 复用 Halo2/Orchard 经验只作**设计参考**，不得当作 VDORAM 可复用代码：Orchard 用 Pallas/Vesta 循环，域与 BLS12-377 不同，gadget/公共参数不通用。
- **状态**：安全基础 VERIFIED，工程落地 **BLOCKED / 系统级**。

---

## 4. B4 — 外部承诺验证 + SNARK witness 桥接

### 4.1 必须回答的五个问题（逐条）

1. **外部承诺验证什么消息？** 只有公开摘要 `com_i` 与（可选的）公开 `d=CRH(x)`；真实 `x=W_pre` 是秘密 witnessed，外部 verifier **看不到**。
2. **SNARK 公开输入含什么？** 至少 `ictx_i`、`com_i`、`C_i`、`C_{i+1}`、`step_i`；是否含 `d` 取决于方案。
3. **外部验证结果如何绑定 SNARK 公开输入？** 唯一无循环的办法是让 `com_i`（与 `d`）同时是外部承诺验证对象**和** SNARK 公开输入，由同一字节编码绑定；但外部 verifier 若不打开承诺，只验证“公开 `com_i` 存在”——这**不证明** SNARK witness 是被承诺的 `x`。
4. **如何防止消息与 witness 不一致？** 必须额外证明 `Commit(witness; s_i) = com_i`——即**在 SNARK 内重算承诺**，或用一个独立的 equality/opening proof。若 SNARK 内重算 Pedersen → 回到 B1(ii) 非原生；若用外部 opening proof → verifier 需看到 `x,s_i`，泄露 witness。
5. **桥接是否又引入新承诺/证明，形成循环？** 是：外部 equality proof 本身要么需要一个新的 hiding 承诺（循环），要么需要递归证明（B3-c）。唯一的“无环”形态是 **SNARK 内原生重算承诺**（即 B2），此时“外部验证”退化为只验 proof，不构成独立承诺层。

### 4.2 严格结论

- **不允许**用“外部承诺验证通过”替代 witness 一致性证明（任务禁止项）。
- 若桥接 = SNARK 内同线值重算 hash 承诺：这正是 B2，**不是**独立的外部承诺路线。
- 若桥接 = 外部 Pedersen equality proof：需要额外 proof 系统接口 + 公开 `d`，且需防 `d` 与 witness 不一致 → 仍需 SNARK 内约束 `d=CRH(witness)`；总体为 B1(ii)+B4 组合，成本更高、接口更多。
- **状态**：**CONDITIONAL / BLOCKED**；不存在“无环且无需在电路内重算承诺”的外部桥接。

---

## 5. 候选小结（供 comparison.md 展开）

| 候选 | hiding 依据 | 电路内 opening | Fr 兼容 | 改造范围 | 综合状态 |
| --- | --- | --- | --- | --- | --- |
| B1 Pedersen (G1(BLS12-377)) | perfect（DL/DDH） | 非原生 10×–600×，无 gadget | 标量原生/坐标非原生 | 中等–系统级 | 安全强，后端 BLOCKED |
| B2 hash `H(x‖s)` | ROM + 启发式，需 `s_i≥~8 Fr` | 原生重算 | 原生 | 局部 | 最接近落地，hiding 仅条件 |
| B3 curve-cycle / 内嵌 | 依 B1/B2 继承 | 需递归或标量域适配 | 非原生/需迁移 | 系统级 | BLOCKED |
| B4 外部 + 桥接 | 依所选承诺 | 仍需电路内重算或额外 proof | 依桥接 | 中等–系统级 | 无环形态退化为 B2 |

**最优候选（本轮）**：安全优先为 **B1**，工程优先为 **B2**。二者都不是“已可进入原型”——B1 阻塞在非原生 gadget 与随机源，B2 阻塞在 hiding 归约与随机源。详细门槛判定见 `decision.md`。
