# decision.md — EXP-DORAM-05 最终判定

> 2026-11-23 · 起点 `ca26127f156d43c7f09c19435e34a627e1bf3f80` · 仅就本轮六份文件作判定。
> 本轮只回答两个问题：(1) `com_i=H(x_i‖s_i)`、`s_i` 不公开能给出什么 hiding；(2) `s_i` 能否有可执行的认证随机源接口。D2、跨步 verifier chain、完整选择性 abort 按范围保持 BLOCKED。

---

## 0. 唯一最终决策：**HOLD**

不是 `GO_TO_B2_MINIMAL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：没有发现协议级矛盾。私有盐在 ROM 下有可证明的计算 hiding（`Adv≤q·2^{-ℓ_s}`，`hiding-model.md` §3），认证随机源在协议层可正确构造（SPDZ F_PREP，`randomness-protocol.md` §2 R3），公开验证仍不需要公开秘密地址/路径。盐长与路由问题都是可解决的工程/密码学任务，不是不可消除的冲突。
- **不 GO**：GO 六条件中，条件 ③（`s_i` 可执行认证联合生成接口）、④（随机量不可单方选择/重采样）在 artifact 层 BLOCKED；条件 ②（MiMC 实例化假设与裕度）未闭合（65 轮 < 设计推荐 91 轮，安全位 UNKNOWN）。不能把协议层 CONSTRUCTED 当成 artifact 可执行。

---

## 1. GO 六条件逐条核对

| GO 条件 | 状态 | 依据 |
| --- | --- | --- |
| ① 私有盐有清楚可引用的 hiding 定义或 ROM 界 | **满足（受限 ROM）** | `hiding-model.md` §3 显式游戏 `Adv≤q·2^{-ℓ_s}`；Lemma 17 具体引用 UNKNOWN、"8 Fr"撤回，但替换为可复算界限 |
| ② MiMC 实例化假设准确标注、安全裕度未夸大 | **部分满足** | `rom-analysis.md` §1–2 明确标 UNKNOWN：65 轮 d=7 低于推荐 91 轮，次数 `2^182.5<p`；RO 仅启发式（§3）。假设标注准确，但裕度本身 UNKNOWN，未"闭合" |
| ③ `s_i` 有可执行的认证联合生成接口 | **不满足（BLOCKED）** | `randomness-protocol.md` §2 R3：`AuthShare` 类型存在，但 `F_PREP.Rand` 接口与一次性台账 artifact 无 → BLOCKED |
| ④ 随机量不可单方选择/重采样/任意偏置 | **不满足（BLOCKED）** | 协议层 R3 可保证，执行层无 MAC→witness 通道；选择性 abort 偏置仍 UNKNOWN（§3/§6） |
| ⑤ 同一份 `W_pre,i` 在承诺与 ORAM 约束中绑定 | **规则满足 / 实现 UNKNOWN** | `hiding-model.md` §4：电路内同线值重算，CONSTRUCTED；完整实现属 D2，BLOCKED |
| ⑥ 承诺成本可用现有 gadget 计算或新增明确有界 | **部分满足** | `cost-model.md`：`260=4×65` 与 `Δμ=260·k` 可复算；但 `L_x/C_enc/C_tag` 未冻结，完整总数仅符号公式（`k=2` 增量 +520 µ 明确） |

**汇总**：完全满足 1 项，部分满足 2 项，规则满足实现 UNKNOWN 1 项，未满足/BLOCKED 2 项 → **HOLD**。

---

## 2. 两个核心问题的最终答案

### 问题 1：私有盐到底给出什么 hiding？

- **抽象 RO 层**：受限但**可证明**的计算 hiding。`Adv ≤ q·2^{-ℓ_s}`（`q` 次查询，`ℓ_s` 盐位数）；`x` 低熵不致命，隐藏来自秘密 `s`。统计 hiding 需 `ℓ_s ≥ κ+2λ ≈ 509 bit`（约 2 Fr）。
- **EXP-DORAM-04 的 Lemma 17 / "8 Fr"**：**WITHDRAWN**。Unruh 2015/361 的 canonical commitment 承诺值只是 `c`、`u` 保密；Exact lemma 与 `|Y|≤2^{ℓ_u/8}` 本轮未能从一手 PDF 核实（Cloudflare），且"返回 `(c,u)`"表述与 hiding 断言内部矛盾。**2 Fr 已足够，8 Fr 过量约 6 倍**。
- **MiMC 实例化层**：退化为**启发式 hiding**；MiMC 无 RO 归约，65 轮 d=7 次数仅 `2^182.5`，安全位 UNKNOWN。
- **定位**：不能再写"标准模型可证明 hiding"，也不必退回"完全无保证"。准确表述是"ROM 下可证明、实例化后启发式"。

### 问题 2：能否设计可执行的认证随机源接口？

- **协议层**：能。`randomness-protocol.md` §2 R3 基于 SPDZ `F_PREP.Rand` + IT-MAC 生成 `[s_i]`，配一次性 `randomness_id` 台账 + `attempt_i` 绑定 + 失败作废，四个概念（随机性/认证/不可重采样/作废）分别定义。
- **artifact 层**：**BLOCKED**。`AuthShare{val,mac}` 类型存在，但无 `F_PREP.Rand` 对外接口、无一次性消费台账、无 MAC→协作证明 witness 的衔接（后者属 D2）。若强行用 R2（承诺-揭示），abort 偏置残留。
- **不能声称已实现**：与任务令一致，接口是 CONSTRUCTED 设计，不是 artifact 现状。

---

## 3. 最重要的修正（相对 EXP-DORAM-04）

### 撤回（WITHDRAWN）
- 「私有盐必须 `s_i ≥ 8 个 Fr`（≈2024 bit）」—— 无一手证实，且是公开盐充分条件的错误移植；`k=2` 已足够。
- 「Lemma 17 逐字给出 `|Y|≤2^{ℓ_u/8}`、canonical commitment 返回 `(c,u)`」—— Exact 文本未核实，"返回 `(c,u)`"与 hiding 断言内部矛盾。
- 「凭 253-bit 输出即 128-bit 抗碰撞」—— 65 轮 d=7 安全位 UNKNOWN。

### 修正（REVISED）
- hiding 论证从"引用 Lemma 17"改为**显式 ROM 安全游戏 + 可复算界限** `Adv≤q·2^{-ℓ_s}`。
- 公开盐 / 私有盐 / 标准承诺三类**严格区分**；明确低熵消息在公开盐下致命、私有盐下不致命。
- `s_i` 随机量从"规则 CONSTRUCTED"细化为**生成/认证/不可重采样/作废四概念分离** + R1/R2/R3 三路线比较。
- 成本从"8 域元素"驱动改为 `Δμ=260·k`，指出 `k=8` 无额外 RO 安全收益。

### 保留（RETAINED）
- 冻结 `ictx_i / W_pre,i / s_i / com_i / rho` 接口与七阶段顺序；
- `s_i ∉ W_pre,i`、`r_tape,i ∈ W_pre,i` 且两者独立、不作 ρ 种子（Correction-4）；
- D2、跨步 verifier chain、选择性 abort 保持 BLOCKED；
- 电路域 `Fr(BLS12-377)`、MiMC 65 轮 SBox=7、Plonk 主路径（EXP-DORAM-04 一手纠正）；
- grinding `q_H·2^{-168}` 的量级与"`attempt_i` 不消除 abort 泄露"的结论。

---

## 4. 最多三个尚未解决的问题（按阻塞优先级）

1. **认证随机源的 artifact 接口（最高优先，BLOCKED）**：需要把 SPDZ `F_PREP.Rand`（认证随机 share）+ 一次性消费台账暴露给承诺阶段，并让 MAC 覆盖送进协作证明的 witness 份额。这是 GO 条件 ③④ 的共同阻塞；缺它则 grinding 与重采样无法在协议层被真正阻断。属 `randomness-protocol.md` §2 R3 / §4。
2. **MiMC 作为 `H(x‖s)` 的实例化安全裕度（UNKNOWN）**：65 轮 d=7 低于素数域设计推荐 91 轮，次数 `2^182.5<p`；无 RO 归约、无 128-bit 抗碰撞证明。需要一手密码分析结论（针对本参数/本域）才能把 hiding 从启发式升级。属 `rom-analysis.md` §1–3。
3. **`W_pre,i` 在承诺与 ORAM 约束中的实现级一致性（UNKNOWN，属 D2）**：规则层 CONSTRUCTED，但认证份额→协作证明 witness 的衔接未闭合；`Encode`/chaining 未冻结使完整承诺成本只能给符号公式。属 `hiding-model.md` §4、`cost-model.md` §6。

> 三项之外不另列。选择性 abort 的完整安全性、跨步 verifier chain 属既有 BLOCKED，本轮按范围未触碰，不作为新发现的问题。

---

## 5. 下一步（本轮不执行）

唯一最值得先做的最小证据任务：**在固定 artifact 上确认/新增 `F_PREP.Rand` 认证随机接口，并冻结 `Encode` 分块与 MiMC chaining 规则**，从而同时闭合 GO ③（随机源）、GO ⑥（成本可精确化），并为 GO ② 的 MiMC 裕度评估提供参数。该任务的答案决定 B2 是否值得进入最小协议原型；在此之前不启动原型。

---

## 6. 停止条件

六份文件完成；不写代码、不跑 benchmark、不重算 ORAM/Merkle/Eviction/Stash 成本、不重开四条路线比较、不重新研究 D2/verifier chain/选择性 abort；提交推送并核对本地/远端 SHA 后立即停止。
