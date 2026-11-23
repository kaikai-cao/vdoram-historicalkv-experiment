# rom-analysis.md — MiMC 实例化的安全边界

> 2026-11-23 · 起点 `ca26127` · 固定上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`。
> 标记：**VERIFIED** 固定源码/原始论文一手文本 · **INFERRED** 由明确前提推导 · **CONDITIONAL** 依赖假设 · **UNKNOWN** 证据不足 · **BLOCKED** 接口缺失。
> 本轮只分析 MiMC 作为 `H(x‖s)` 的实例化安全性，不重算 MiMC 约束成本（那在 `cost-model.md` 只给承诺相关部分）。

---

## 0. 固定 artifact 中的 MiMC 事实（VERIFIED）

来源：`CompatCircuit/CompatCircuitProgramming/Gadgets/MimcEncryptGadget.cs`、`MimcHashGadget.cs`（固定 commit 源码快照）。

| 项 | 值 | 证据 |
| --- | --- | --- |
| 轮数 | **65 轮** | `DefaultRoundConstantStrValues` 65 个常量（源码逐字，correction-2 §E1、exp-doram-04 backend-facts §3 已定点复核） |
| SBox | **`x^7`** | `DefaultSBox = 7`；每轮 `FieldAddGadget(3)` + `FieldConstPowGadget(7)` |
| key | `key = 0`（`MimcHashGadget`） | 链式调用 `MimcEncryptGadget`，输出**一个** `Field` |
| 域 | `Fr(BLS12-377)`，`\|F\| = r ≈ 2^253`，位宽 253 | `ArithConfig.cs` 模数 hex `12ab655e…0001`（exp-doram-04 一手纠正，VERIFIED） |
| 输出长度 | 单个域元素 ≈ 253 bit | 源码输出类型 `Field` |
| 复用形态 | `H(k)` 对 k 个输入链式压缩为 1 个 `Fr` | `MimcHashGadget` 结构 |

---

## 1. MiMC 是否有可引用的抗碰撞安全分析？（任务 B 问题 1）

**结论：有一般性分析，但对本实例没有可引用的具体安全位 → UNKNOWN。**

- 原始设计论文：Martin Albrecht, Lorenzo Grassi, Christian Rechberger, Arnab Roy, Tyge Tiessen, *MiMC: Efficient Encryption and Cryptographic Hashing with Minimal Multiplicative Complexity*, ePrint 2016/492（ASIACRYPT 2016）。
  - 素数域 MiMC-p/p 的推荐轮数（逐字）：「The number of rounds for constructing the keyed permutation is `r = ceil(log p / log_2 3)`」（针对 `x^3`）。其安全性论证基于**代数次数随轮数增长，最终使多项式次数达到/超过域阶**，从而抵抗插值/Gröbner 攻击。
- 对一般指数 `d`，设计准则同样要求 `d^r` 达到域规模量级；文献常用 `r ≈ ceil(log p / log_2 d)`（ePrint 2023/1872 §4.1 逐字给出 `r = ceil(n·log_d 2)`）。
- **攻击侧现状**：
  - ePrint 2020/182（Eichseder 等）给出 GF(2^n) 上全轮 MiMC 的代数攻击，但逐字声明「our attack does not affect the security of MiMC over **prime fields**」→ 本实例是素数域，**该攻击不适用**。
  - ePrint 2019/812（改进的插值攻击）打破的是 MiMC-129/129（GF(2^n) 形态）38 轮，并称「full 82 rounds are necessary」→ 同为二进制域，**不直接适用**素数域实例。
  - ePrint 2019/426（Grassi 等，Marvellous 设计框架）逐字指出：对 arithmetization-oriented 密码，**Gröbner 基攻击是关键顾虑**，依赖"parasitical solutions 数量大"作为安全论证「is a new security argument as well as a **risky** one」；并明确说「the question whether there is a systematic argument for Gröbner basis security ... we answer this question positively」，但这是**设计框架**，不等于对 artifact 具体 65 轮参数的审计。
- **判定**：存在可引用的一手分析框架，但没有任何一手来源给出「65 轮、`d=7`、`Fr(BLS12-377)` 的具体碰撞安全位」。→ **具体安全位 UNKNOWN**，不得凭 253-bit 输出直接声称 128-bit 抗碰撞。

---

## 2. 现有 65 轮参数能否支持所需安全位？（任务 B 问题 2）

**计算（INFERRED，基于设计准则）**：

```
域规模 p ≈ 2^253（Fr(BLS12-377)）
指数 d = 7,  log2(7) ≈ 2.8074

设计推荐轮数（若按素数域 MiMC 准则 r = ceil(log p / log2 d)）：
    d=3:  ceil(253 / 1.5850) = 160 轮
    d=7:  ceil(253 / 2.8074) =  91 轮
artifact 实际：65 轮

已达成代数次数上界： 7^65 = 2^(65·log2 7) = 2^182.5  <  2^253 = p
```

- **判读（INFERRED）**：按设计准则，本实例的轮数比 `d=7` 的推荐值 **少约 26 轮**（91 → 65），其多项式次数仅到 `2^182.5`，未达到域阶 `2^253`。这意味着"次数饱和→抗插值/Gröbner"的**设计论证前提在本参数下不成立**。
- **不能据此直接宣称已破**：GF(2^n) 上的具体攻击不迁移到素数域（§1），且 65 轮对 hash 形态未必等同于对 keyed permutation 的安全要求。但**安全裕度没有被任何一手证据确立**。
- **状态**：`65 轮 d=7` 是否达到 128-bit 抗碰撞 —— **UNKNOWN**；设计准则给出的是"应≥91 轮"的反向指示，标 INFERRED，不写成"已证明不安全"。

---

## 3. 把 MiMC 当随机预言机用于 hiding 属于什么假设？（任务 B 问题 3）

**结论：这是一个显式的启发式假设（heuristic / RO-instantiation assumption），不是可证明归约 → CONDITIONAL。**

- `hiding-model.md` §3 的界限 `Adv ≤ q·2^{-ℓ_s}` 成立的前提是 `H` 为**真随机预言机**（未查询点输出独立均匀）。
- 真实实例是 `MiMCCommit(x,s)`：一个 65 轮、低度数（`x^7`）、`key=0` 的确定性函数。它**在结构上与 RO 不同**：
  - 它是**低代数度**的（次数 `2^182.5`），RO 没有这种结构；
  - 它是**无密钥**的确定性置换链，任何人都可离线计算全表（虽然域大）；
  - 它没有可证明的"不可区分于 RO"归约。
- 把 §3 的 RO 界限用于 MiMC，等价于假设"对该应用而言 MiMC 表现足够像 RO"。这是 **Nisan–Wigderson 式启发式实例化**，须显式标注，**不能**写成"hiding 已被证明"。
- 一手佐证：ePrint 2024/1074（*Trust Nobody*）对 Poseidon/RO-based commitment 明确写「We make the **heuristic assumption** that such instantiation of the commitment scheme is secure」（exp-doram-04 candidate-analysis §2.1 已逐字引用）。本轮不新增文献，沿用该既有证据。

---

## 4. 抗碰撞 与 RO 行为 是两种不同的安全要求（任务 B 问题 4）

| 要求 | 用于 | 具体含义 | 对本实例的状态 |
| --- | --- | --- | --- |
| **抗碰撞（CRH）** | binding | 难找 `(x,s)≠(x',s')` 使 `H(x‖s)=H(x'‖s')` | 具体安全位 UNKNOWN（§1–2）；只有"依赖 CRH"的形式保证 |
| **RO 行为** | hiding | 未查询点输出独立均匀，使 `s` 的秘密性转化为 hiding | 仅启发式假设（§3） |
| **collapse-binding（量子）** | 本系统不需要 | Unruh 2015/361 的量子安全定义 | 冻结威胁模型未要求 → 不适用 |

**关键点**：即便 MiMC 被证明抗碰撞，**也不能**推出它有 RO 式 hiding；反之亦然。抗碰撞是"两张不同输入难以同输出"，RO 行为是"输出对未查询输入不可预测且均匀" —— 后者严格更强。把两者混用是 hiding 论证的常见错误，本轮明确分开。

---

## 5. 随机量长度足够时，MiMC 是否仍有结构性安全缺口？（任务 B 问题 5）

**结论：有，且独立于盐长 → CONDITIONAL / UNKNOWN。**

1. **代数结构缺口**：次数仅 `2^182.5`（§2），未饱和；Gröbner 基攻击对 arithmetization-oriented 密码是"关键顾虑"（ePrint 2019/426）。这是哈希函数本身的结构问题，**加长盐不能修复**。
2. **无密钥确定性**：`key=0`，无隐藏随机置换；RO 区分器若基于代数结构存在，加盐只能提高穷举成本，不改变结构可区分性。
3. **输出域窄**：输出仅一个 `Fr`（253 bit），抗碰撞的通用上界是生日界 `~2^126.5`，达不到严格 128-bit；且这是通用上界，实际因代数结构可能更低。
4. **grinding 交互**：`com_i` 进入 Fiat–Shamir 挑战派生（冻结接口）；若 `s_i` 可被重采样，攻击者可反复改 `com_i` 改挑战（Correction-3/4 已记录 `q_H·2^{-168}`）。这是随机源问题（`randomness-protocol.md`），但与 MiMC 结构叠加时，任何"输出非均匀"偏差都会被 grinding 放大。

---

## 6. 本页最终结论

| 任务问题 | 结论 | 标记 |
| --- | --- | --- |
| 可引用的抗碰撞分析？ | 有设计/攻击框架，无针对 65 轮 d=7 Fr 实例的具体安全位 | UNKNOWN |
| 65 轮够不够？ | 设计准则 `ceil(253/log2 7)=91`，实际 65，次数 `2^182.5<p`；裕度未确立 | INFERRED / UNKNOWN |
| MiMC 当 RO 属于什么假设？ | 显式启发式实例化假设 | CONDITIONAL |
| CRH vs RO 是否不同要求？ | 是，严格不同，不可互推 | INFERRED |
| 盐长足够是否消除结构缺口？ | 否；低代数度、无密钥、窄输出、grinding 叠加均独立于盐长 | CONDITIONAL |

**不得声称**：凭 253-bit 输出宣称 128-bit 抗碰撞；凭"加盐"宣称 MiMC 已达 RO；凭 GF(2^n) 攻击不适用宣称素数域实例安全。三条边界均如实标 UNKNOWN/CONDITIONAL。
