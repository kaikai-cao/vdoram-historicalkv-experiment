# decision.md — EXP-DORAM-03-R1-Correction 最终决策

> 2026-11-23 · 起点 `b1bfe29` · 判定范围：五个技术缺口修正后，是否值得进入最小原型。
> 结论标记沿用本任务包。

---

## 0. 唯一最终决策：**HOLD**

不是 `GO_TO_MINIMAL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：本轮未发现“公开验证必须泄露秘密地址/路径”的协议矛盾；Merkle 逐路径更新仍无每步 O(N) 必然性；递归 PositionMap、stash、eviction 的完整 R1CS 均可符号化计数。任务包 §6 的 NO_GO 条件均不满足。
- **不 GO**：第 5 条（MPC 实际执行与 SNARK witness 的可执行密码学绑定）为 **BLOCKED**；第 3/4/7 条分别受挑战顺序、commitment hiding 与选择性 abort 条件限制；当前 artifact 没有兼容接口。理论路线存在不等于可实现、可证明安全。
- **理论障碍 vs 工程障碍**：Merkle 增量性与 R1CS 表示是理论层 `CONSTRUCTED`；MPC→witness 认证交接在当前 artifact 是**工程/接口 BLOCKED**，但它同时是进入 GO 的必要密码学条件，不能降级为“以后补实现”。

---

## 1. GO 判据逐条核对

| # | GO 条件 | 修正后状态 | 是否满足 |
| --- | --- | --- | --- |
| 1 | 每步无隐藏 O(N) | 路径 Merkle + 递归 posmap；若 nonce 全量刷新会 O(N)，已禁止；终态排序 O(T log²T) 属 T 维 | ✅ CONSTRUCTED |
| 2 | R1CS 完整、成本可复算 | 12 项逐项核算；推荐报价 2,524,843 µ/步（stash Merkle + B1），原 2,798,280 撤回 | ✅ CONSTRUCTED/CONDITIONAL（B1 com 接口） |
| 3 | Stash 转换 soundness 有明确协议依据 | `ρ=H(x_i)` 撤回；B1 commit-then-challenge 数学 sound，但 com(W) 接口缺失；B3 确定但贵 | ⚠️ CONDITIONAL_CONSTRUCTION |
| 4 | commitment hiding 有合理安全定义 | C1/C2 不隐藏；C3 秘密 nonce 条件性缓解；随机带绑定与防重放未闭合 | ⚠️ CONDITIONAL_CONSTRUCTION |
| 5 | MPC 执行与 SNARK witness 可执行绑定 | D1 路径约束 CONSTRUCTED；D2 端到端 BLOCKED：无 ORAM 线接口、无每 witness 输入 MAC 覆盖证明、无同执行 co-SNARK 接口 | ❌ BLOCKED |
| 6 | verifier 验证根/step/历史连续 | V1–V6 规则 CONSTRUCTED；artifact 仍无跨电路 verifier | ⚠️ 工程 BLOCKED |
| 7 | 隐私无关键访问模式泄露 | 地址/leaf/路径协议层 HIDDEN；abort、transcript timing、proof time、nonce 随机带绑定未闭合 | ❌ UNKNOWN/BLOCKED |
| 8 | 参与方与腐化模型未偷改 | 仍为任意 m、dishonest majority、active；全体合谋隐私不适用 | ✅ |

**GO 未满足：3/4/5/6/7。**

---

## 2. A–F 每项结论

- **A 成本重算**：旧 `2,798,280` 撤回。按原单哈希 stash 承诺完整重算为 **6,144,043 µ/步**；按推荐 stash-Merkle 为 **2,524,843 µ/步**；加入 C3 nonce 后约 **2,587,363 µ/步**。明细见 `r1cs-cost-revision.md`。
- **B Stash soundness**：原 `ρ=H(x_i)` 顺序错误，BLOCKED。B1（commit → challenge → 约束）数学 sound，误差约 2⁻¹⁷⁰（两挑战），但依赖 witness commitment 接口；B2 coin-toss 有偏置/abort 风险；B3 确定性匹配信息论可靠但示例约 2.60M µ（整字段编码相等口径 6.04M）。
- **C Commitment hiding**：确定性 Merkle 不隐藏；公开盐无效；推荐 C3（秘密 nonce、每次触碰刷新），但只到 CONDITIONAL_CONSTRUCTION；不能写“加盐即零知识”。
- **D 路径与绑定**：D1 secret leaf/path/sibling/递归 leaf 约束已显式 CONSTRUCTED；D2 真实 MPC 输出 shares ↔ SNARK witness shares ↔ 下一步 shares 的端到端绑定 **BLOCKED**。固定 artifact 只落盘 R1CS+witness，外部逐电路证明，verifier 无串联。
- **E 隐私**：矩阵扩为 12 项；新增 proof 时间/长度与 abort/掉线；区分协议、实现 timing、公开日志、选择性 abort 四类。选择性 abort 仍未处理。
- **F 文献/源码**：定点核查 SPDZ（CRYPTO 2012 pp.643–662；S&P 2025/789 MAC 实现风险）、Keller–Scholl（ePrint 2014/137）、VDORAM（ePrint 2025/039、固定 commit）、Path ORAM/OMap；未扩大综述。每个证据均标注“支持/不能支持”。

---

## 3. 所有 UNKNOWN / BLOCKED 汇总

| 项 | 状态 | 原因 |
| --- | --- | --- |
| witness commitment `com(W)` 与 co-SNARK transcript 顺序接口 | UNKNOWN/BLOCKED | 固定 artifact 未提供 |
| proof witness 每个输入份额的 MAC/认证覆盖 | UNKNOWN | 标准 SPDZ MAC 不等于外部 prove 输入认证；实现层另有 key leakage 风险 |
| ORAM 状态 `in_state/out_state` 线与同执行 ValueBoard witness | BLOCKED | ORAM 电路不存在 |
| 跨电路 verifier 根/step/历史串联 | BLOCKED | 本仓库未实现；外部仓库 UNKNOWN |
| C3 nonce 随机带绑定、防替换/重放 | BLOCKED | 未定义认证随机带和承诺接口 |
| 选择性 abort / 掉线是否为固定长度公开事件 | UNKNOWN | 证明失败和 prove 脚本失败未规范化 |
| 实现层 timing / proof generation time | UNKNOWN | 与 witness 内容无已证明独立性 |
| commit-then-challenge 的 ORAM-stash 直接文献实例 | UNKNOWN | 本轮只有数学推导，无固定集合 VERIFIED 实例 |
| SPDZ coin-toss 在任意方、dishonest majority 下无偏置且无 abort 泄露 | UNKNOWN | 未取得一手协议细节 |

---

## 4. 相对 R1：保留、修正、撤回

### 保留
- Merkle 增量承诺方向；Tree/递归 PositionMap/Stash/Meta 四状态表示；
- 每步无 O(N) 的结论（排除线性 posmap、整树一致性、整状态 hash）；
- stash 解析界修正 `R≥114`（2⁻⁸⁰）/ `R≥179`（2⁻¹²⁸）；
- V1–V6 verifier 串联规则；
- 整体判定 HOLD 与 narrow NO_GO 对象。

### 修正
- R1CS 总成本从单一 2,798,280 改为逐项可复算报价；推荐 2,524,843 µ/步（条件：stash-Merkle + B1）。
- 多重集检查从 `ρ=H(x_i)` 改为 commit-then-challenge；B3 作为无随机挑战备选。
- 隐私矩阵从 11 项扩展为 12 项，并显式区分四类泄露。

### 撤回
- 原 `ρ=H(x_i)` 具有 soundness 的写法；
- “witness 同源即密码学绑定”的暗示；
- 原 `2,798,280` 作为可信最终值；
- 普通确定性 Merkle root 可作为隐藏承诺的暗示；
- “加随机盐即零知识”的任何表述。

---

## 5. 下一步唯一最值得解决的技术问题

> **在任意方、dishonest-majority、active-secure 的同一 MPC 执行中，定义一个可审计接口，使 ORAM 转换输出状态份额、辅助 witness 份额、公开根打开、nonce/挑战随机带与协作 SNARK 证明输入使用同一批已认证线值；并给出 MAC 覆盖、承诺–挑战顺序与固定行为 abort 的可检查规则。**

该问题同时包含 D2 绑定、B1 挑战顺序、C3 nonce 绑定与 abort 语义，不再拆成多个平行调查分支。它闭合前不启动最小原型；若证明该接口在固定威胁模型下不可构造，才重新考虑 NO_GO。

---

## 6. 停止条件

八个文件已完成；提交推送后停止。不写 ORAM 电路、不跑 benchmark、不扩展文献、不启动原型。
