# stash-soundness.md — 任务 B：Stash 多重集守恒的 Soundness 修正

> 2026-11-23 · 起点 `b1bfe29` · 纸面协议分析。
> 目标：判断原稿 `ρ=H(x_i)` 多重集指纹是否 sound，并比较 B1/B2/B3。
> 标记：**VERIFIED** 可复现数学/固定源码 · **CONSTRUCTED** 本轮规则 · **INFERRED** 推导 · **CONDITIONAL_CONSTRUCTION** 依赖条件 · **BLOCKED** 未闭合。

---

## B0. 原稿结论

原稿把 `ρ = H(x_i)`（仅由公开实例派生）作为随机线性累加器挑战。**该写法不成立，撤回。** 原因不是“Fiat–Shamir 不行”，而是**顺序错了**：挑战必须在 witness 固定并承诺之后派生；只由公开 input 派生的 ρ 在 prover 选择 witness 前已完全已知，随机化多重集检查的 soundness 论证失效。

---

## B1. 为什么“公开先定 ρ”不安全

原检查试图证明：

```
Σ_{u∈Old} ρ^{enc(u)} = Σ_{v∈New} ρ^{enc(v)}
```

若 prover 在看到 ρ 后仍能选择 witness，则它面对的是**已知系数**的单个域方程。只要能在允许的编码集合内找到两个不同多重集使多项式差为零，即可伪造。即使受 `enc<2^169` 限制、直接找根不一定容易，安全性已不再来自 Schwartz–Zippel 的“随机点避根”论证，而是退化为“prover 能否解出已知多项式方程”——不能用 128-bit 安全假设覆盖。

具体攻击面：

1. 已知 ρ 后，prover 可先选差额多项式 `D(z)=Σρ^{enc(old)}−Σρ^{enc(new)}`，再反向挑字段值使差为零；
2. 若 ρ 的乘法阶落在允许编码范围内，可令 `enc₁=enc₂+ord(ρ)` 造成不同元组同指纹；
3. 若后端对 `ρ` 复用或域分离不严，跨步/跨电路重放差额更容易。

因此原 `ρ=H(x_i)` 写法标 **BLOCKED（顺序错误）**，不能继续作为 soundness 依据。

---

## B2. 正确的 Fiat–Shamir 顺序（候选 B1）

```
1. MPC / prover 先确定完整 witness W_i（含 stash、path、eviction 辅助线）。
2. 对 witness 生成绑定承诺 com(W_i)，并把 com(W_i) 加入 transcript。
3. ρ₁,ρ₂ = H("stash-multiset" || x_i || com(W_i) || domain-separator)。
4. 才在 R1CS 中约束 Σρ_k^{enc(old)} = Σρ_k^{enc(new)}，k=1,2。
```

- **安全假设**：`com` binding；H 建模为 RO / FS 安全；ρ 在 F 中近似均匀；`enc` 无碰撞； Schwartz–Zippel。
- **soundness 误差**：差多项式次数 `d≤max enc < 2^169`，`|F|≈2^254`，单挑战 `≤2^-85`；两个独立挑战约 `≤2^-170`（CONSTRUCTED 计算）。若把 value 位宽 B 提高，需重新核算 `d<|F|`。
- **成本**：每挑战旧/新两侧各 Q 个 `ENC` 指数；两个挑战 `4QE` 乘法（见 `r1cs-cost-revision.md` A2.11）。承诺 `com(W)` 的成本另计，当前 artifact 未提供该接口 → **CONDITIONAL_CONSTRUCTION**。
- **恶意参与方**：承诺绑定后不能在看到 ρ 后改 witness；但可在看到 ρ 后 **abort**。这不破坏 knowledge soundness（没有假证明被接受），但构成可用性/选择性 abort 泄露面，见 `privacy-revision.md`。

---

## B3. MPC coin-tossing / distributed challenge（候选 B2）

```
各方先 commit r_i；
所有 commitment 收齐后 open r_i；
ρ = H(r_0 || ... || r_{m−1} || x_i)；
再用 ρ 约束多重集累加器。
```

- **安全假设**：至少一方诚实且不泄露其 r_i 直到打开；commitment binding + hiding；哈希安全。
- **抗性**：ρ 在承诺阶段不可预测；但最后打开者可 rushing bias（看到他人 r 后选择是否开），且任何参与方都可在看到 ρ 后拒绝继续 → 选择性 abort 仍需要处理。
- **额外通信**：至少两轮（commit/open）× m 方，并有 abort 处理轮；比 B1 的 transcript hash 更重。
- **R1CS 成本**：累加器同 B1；commit/open 验证若进入证明另计。
- **任意参与方**：协议层支持任意 m，但 dishonest-majority 下“无条件防偏置”需要额外假设或公平coin-toss；本轮标 UNKNOWN/BLOCKED。
- **适用性**：可配合 collaborative SNARK，但要求 proof transcript 包含 coin-toss 记录；固定 artifact 无此接口。

---

## B4. 确定性逐槽 permutation / matching（候选 B3）

不使用随机指纹，直接约束旧集合到新集合存在一个保持 `(addr,val,leaf,valid)` 的置换：

```
对 Q 个旧槽 s 与 Q 个新槽 t 引入 one-hot 匹配位 m_{s,t}；
Σ_t m_{s,t}=1, Σ_s m_{s,t}=1；
m_{s,t}=1 ⇒ old_s = new_t（四个字段逐项相等）；
invalid slot 的字段固定为规范值 0。
```

- **安全假设**：信息论组合约束，不依赖随机挑战；one-hot 与相等约束 sound。
- **抗性**：恶意 prover 无法用随机碰撞；可做重复/丢失/换值攻击均被匹配等式拒绝。
- **额外通信**：无 coin-toss；但 witness 增加 `Q²` 匹配位。
- **R1CS 成本**：匹配矩阵 one-hot 校验 `Q(Q−1)` µ + 每对每字段条件等式 `4Q²` µ；示例十层总计 **2,600,580** µ。若改用整字段 ℓ-bit 编码相等（`Q(Q−1)/2·(2L−1)`/层），则为 **6,040,110** µ；两种口径都高于 B1 的 1,381,640 µ（CONSTRUCTED 计算）。
- **任意参与方 / collaborative SNARK**：支持；不引入随机挑战偏置问题。固定形状，故通信模式仍固定。

---

## B5. 三方案对照

| 项 | B1 commit-then-challenge FS | B2 MPC coin-toss | B3 确定性匹配 |
| --- | --- | --- | --- |
| 安全假设 | com binding + RO/FS + enc 无碰撞 | ≥1 诚实 + commitment + coin-toss 防偏置 | 仅 one-hot/相等约束 |
| 恶意 prover 抗性 | 承诺后不能改 witness；可 abort | 难预测但可能被偏置/abort | 最强，无随机误差 |
| 额外 MPC 通信 | 需要 com(W) 接口，通信 UNKNOWN | commit/open ≥2 轮 | 无 |
| R1CS 成本（示例） | 1,381,640 µ（不含 com） | 同 B1 + coin-toss 验证 | 2,600,580 µ（编码相等口径 6,040,110 µ） |
| 任意参与方 | 是（若 com 支持） | 是（防偏置 UNKNOWN） | 是 |
| collaborative SNARK 适配 | CONDITIONAL（需 transcript 顺序） | CONDITIONAL（需记录 coin-toss） | CONSTRUCTED |
| 选择性 abort | 未解决 | 未解决 | 不因挑战而新增 |

---

## B6. 整体编码、重复、无效与空 slot（必须回答）

1. **必须整体编码**：只编码 `addr` 会让 prover 在相同地址上换 `val/leaf` 或制造重复仍通过。使用 `enc = addr + 2^L·val + 2^{L+B}·leaf + 2^{2L+B}·valid`，并约束各字段位宽，保证 `<p` 且单射。
2. **重复元素**：累加器保持**带重数**的多重集；从初始合法状态出发，若出现重复则必然伴随另一端少一个元素，指纹失败。B3 更直接禁止一对一之外的匹配。
3. **无效/空 slot**：`valid=0` 时强制 `addr=val=leaf=0`；`valid` 为 bit；空槽全部同一 `enc=0`，因此多个空槽的重数一致，不影响 active 多重集。
4. **位宽**：`L=20,B=128` 时 `enc` 位数 169 < BN254 scalar 域 254，安全余量存在；若换域或增大 B，必须重新检查。

---

## B7. 本轮结论

- 原 `ρ=H(x_i)` 写法：**撤回 / BLOCKED**。
- 推荐：**B1 作为成本主报价，B3 作为无随机挑战的保守备选**；两者都属于 `CONDITIONAL_CONSTRUCTION`，因为当前 artifact 没有 witness commitment 或匹配辅助线的现成接口。
- B2 支持任意方，但偏置与 abort 未闭合，不作为首选。
- 无论 B1/B2/B3，**选择性 abort 泄露**仍未解决；它属于执行轨迹隐私，不因多重集 soundness 修正自动消失。
