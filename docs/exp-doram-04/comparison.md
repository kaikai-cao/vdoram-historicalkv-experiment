# comparison.md — 统一比较、成本边界与改造范围

> 2026-11-23 · 起点 `2556ece` · 候选定义见 `candidate-analysis.md`，安全分析见 `security-analysis.md`。
> **不编造数字**：没有实测/一手约束数的格子明确写 UNKNOWN，有文献边界的写区间并标来源。

---

## 1. 统一比较表

| 维度 | B1 Pedersen (G1/BLS12-377) | B2 Hash 承诺 `H(x‖s)` | B3 Curve-cycle/内嵌 | B4 外部+桥接 |
| --- | --- | --- | --- | --- |
| **Hiding** | **Perfect**（`s_i` 域均匀 ⇒ 统计独立；Pedersen 1991 VERIFIED） | **ROM + 启发式**：需 `s_i ≥ ~2024 bit (≈8 Fr)` 满足 Lemma 17；MiMC 当 RO 无严格归约（ePrint 2015/361 Lem.17；2024/1074） | 继承 B1/B2 | 继承所选承诺 |
| **Binding** | **DL/DDH**（`log_g h` 未知）；实际为 `DL ∧ CRH`（因 `d=CRH(x)` 压缩） | **CRH**（MiMC 抗碰撞）；安全裕度 UNKNOWN | 同上 | 同上 |
| **Opening** | 外部 verifier 验 G1 方程 `g^d h^{s_i}=C`；若电路内验则需非原生 | 电路内重算 `H(x‖s_i)=com_i`，`com_i`/`s_i` 分别为公开输入/私有 witness | 递归侧验或标量适配 | 外部验承诺 + 需额外 equality/opening proof |
| **Witness binding** | 电路内验需非原生同线值；外部验无桥接 → 不成立 | 电路内同线值重算，与 ORAM 约束共用 `W_pre,i` → 规则层闭合 | 依 B1/B2 + 递归接口 | 无环形态 = B2 电路内重算；纯外部有替换空间 |
| **Fr 兼容** | **标量原生 / 坐标非原生**（`G1` 标量=`Fr`，坐标=`Fq` 377 bit） | **原生**（MiMC 输入/输出均 `Fr`） | 非原生或需换域 | 依桥接 |
| **现有 gadget** | 无 Pedersen / 无曲线 gadget（目录 19 文件，VERIFIED）；非原生组件无 | **MiMC 已有**（65 轮/SBox=7，VERIFIED）；需新增 `H(x‖s)` 封装 | 无 | 无 equality/递归接口 |
| **随机源** | 依赖 `s_i` 域均匀（∈Fr 原生）；MPC 联合生成/MAC/不可重采样 BLOCKED | 依赖 `s_i ≥8 Fr`；联合生成/MAC/不可重采样 BLOCKED | 同左 | 同左 |
| **Grinding** | 可重采样 `s_i` ⇒ 复活 `q_H·2^-168`；防护执行 BLOCKED | 同左；`s_i` 更长不自动防 grind | 同左 | 同左 |
| **公共输入新增** | `ictx_i`、`com_i`、`C_i`、`C_{i+1}`、`step_i`、公开 `d=CRH(x)`（若外部验） | `ictx_i`、`com_i`、`C_i`、`C_{i+1}`、`step_i`（`d` 可不公开） | 依子路线 | 更多：承诺对象 + bridge 公开值 |
| **额外成本** | 非原生乘法 **10×–600×**（ePrint 2025/695 摘要 / 2024/265 §1），**具体约束数 UNKNOWN**；`CRH` 约束数 UNKNOWN | `H(x‖s)` 的 MiMC 约束 = `260·k`（k=preimage 数，Correction-2 INFERRED）；`s_i` 扩 8× ⇒ 输入更多；**精确总数本轮未算** | **UNKNOWN**（系统级） | **UNKNOWN**（需额外 proof） |
| **改造范围** | **中等–系统级**：新增非原生域 + 点运算 gadget + CRH + 随机源 | **局部**：新增 `H(x‖s)` 封装 + 8×域元素随机带；随机源仍 BLOCKED | **系统级**（B3-a/c）/ 中等（B3-b） | **中等–系统级** |
| **安全前提未解** | BLS12-377 G1 上实例化细节、非原生 gadget、`s_i` 随机源 | MiMC RO 假设、安全裕度、`s_i` 熵长度、随机源 | 曲线/公共参数迁移、`s_i` 随机源 | equality proof 接口、递归、`s_i` 随机源 |
| **综合状态** | **CONDITIONAL / BLOCKED**（安全强，后端阻塞） | **CONDITIONAL**（最接近落地，hiding 条件化） | **BLOCKED**（系统级） | **BLOCKED**（无环退化为 B2） |

---

## 2. 成本边界（不编造，只给有来源的界）

### 2.1 已知可复算项

| 项 | 公式/来源 | 状态 |
| --- | --- | --- |
| MiMC hash 约束 | `H(k) = 260·k` 乘法约束（65 轮 × SBox=7 的 4 乘法 + 加法链；Correction-2 §E1 INFERRED） | INFERRED（源码轮数可复算） |
| B2 承诺重算 | 若 `Encode` 用 k 次 preimage 的 MiMC，`s_i` 扩 8 域元素增加 ≈8 个 preimage ⇒ 增量 ≈ `260×8 = 2080` 乘法约束量级 | INFERRED（口径来自既有模型；本轮未重算总成本，按范围禁止） |
| B1 域大小 | `Fr(BLS12-377)` 253 bit（源码 + ePrint 2022/1396 VERIFIED） | VERIFIED |

### 2.2 只有区间、无精确值

| 项 | 界 | 来源 | 状态 |
| --- | --- | --- | --- |
| 非原生域乘法开销 | 约 **10×–600×**（相对原生） | ePrint 2025/695 摘要（PLONK 优化后 one order of magnitude）；ePrint 2024/265 §1（BN254 基域 600×） | INFERRED 有界，非本后端实测 |
| `CRH(x)` 压缩 8 字段约束数 | 依赖字段总位宽与分块，未定义 | — | UNKNOWN |
| B1 Pedersen 完整电路内验证约束数 | 依赖非原生实现选择，artifact 无 gadget | — | UNKNOWN / BLOCKED |
| B3 系统级迁移成本 | 依赖目标曲线与公共参数 | — | UNKNOWN |

> 任务红线：不为表格完整编造数字。上表 UNKNOWN 格保持 UNKNOWN。

---

## 3. 改造范围分级

| 级别 | 含义 | 对应候选 |
| --- | --- | --- |
| **局部** | 在现有 BLS12-377+Plonk 后端加少量 gadget/witness 字段，不改曲线/公共参数/verifier | B2（`H(x‖s)` 封装 + 8×域元素随机带） |
| **中等** | 需新增实质性 gadget（非原生域、内嵌曲线、CRH 压缩）但仍在同一证明系统内 | B1 部分、B3-b |
| **系统级** | 换证明曲线 / 公共参数 / setup / verifier / 协作后端，或引入递归证明栈 | B3-a、B3-c、B1 若走递归 |

---

## 4. 关键权衡一句话

- **要安全依据强** → B1（perfect hiding + DL binding），但电路内 opening 需非原生（10×–600×，无 gadget）且随机源 BLOCKED。
- **要当前能落地** → B2（原生 MiMC，局部改造），但 hiding 只有 ROM 启发式假设，且必须把 `s_i` 扩到 ~8 域元素、随机源仍 BLOCKED。
- **两者共同的硬阻塞**：`s_i` 的 MPC 联合生成 + MAC + 不可重采样在固定 artifact 中无接口 → grinding 未消除。这是**承诺构造之外**、但决定承诺能否安全使用的必要条件。

---

## 5. 与 GO 门槛的对应

| GO 条件 | B1 | B2 |
| --- | --- | --- |
| 具体承诺构造 | 有（Pedersen + CRH） | 有（`H(x‖s)` + 扩熵） |
| hiding/binding 明确依据 | 有（VERIFIED 假设） | hiding 条件化（ROM 启发式） |
| opening verification 完整 | 规则有，实现 BLOCKED（非原生） | 规则有，实现 CONDITIONAL |
| 同份 witness 绑定接口闭合 | BLOCKED（非原生同线值无 gadget） | CONSTRUCTED 规则 / CONDITIONAL 实现 |
| 当前后端可实现或改造有界 | 改造系统级，成本 UNKNOWN | 局部改造，成本有量级界 |
| `s_i` 随机源与 grinding 处理 | BLOCKED | BLOCKED |

无一候选满足全部 GO 条件 → 见 `decision.md`。
