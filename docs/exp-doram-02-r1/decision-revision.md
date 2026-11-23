# decision-revision.md — EXP-DORAM-02-R1 修订决策

> 日期：2026-11-23 · 本文**修订并取代** `docs/exp-doram-02/decision.md` 的整体判定；原决策文档作为历史执行记录保留不改（非破坏式）。
> 触发：研究负责人独立核查发现"session 注销 → 份额销毁 → 状态无法跨步"为过度推断；本轮 R1 源码实证确认该质疑成立。

## 1. 修订后的决策：**HOLD**（整体）

**判定对象**：在 VDORAM 框架内引入"跨 VM step 持续更新、状态转换可被公开协作式 SNARK 验证、任意参与方下隐藏访问模式"的 Current-State ORAM 状态机——**这条研究方向整体判定为 HOLD**，未被证明不可行，也未被证明可行。

**为什么从 NO_GO 改为 HOLD**：
EXP-DORAM-02 判 NO_GO 依赖三条依据，其中**依据2整条被撤回**、**依据1与依据3被收紧**：

| 原依据 | R1 后状态 |
| --- | --- |
| 依据2：session 销毁份额 → 无法跨 step 绑定状态 | **整条撤回**。份额是外层持有的 `MpcValue` 纯值对象，跨 session 存活；registers 已实证（L73/L297/L376）；hash 承诺链机制存在（L322-328/L367-371）。缺的是 ORAM 专用接口/电路，不是份额不能存活。 |
| 依据1：2-3 方 DORAM 与任意方目标冲突 | **收紧为 narrower NO_GO**。仅对"直接移植现有 2-3 方 DORAM"成立；不推出任意方 ORAM 不存在。 |
| 依据3：无专用秘密索引原语 | **收紧为 UNKNOWN**。无现成接口 VERIFIED，但可用现有原语组合，成本未验证，非理论禁止。 |

NO_GO 三依据倒了一条、另两条缩窄，已不足以支撑"整个方向明确不可行"的判定 → 改 HOLD。

## 2. NO_GO 的严格限定（仍然成立的 narrower 对象）

**NO_GO（此对象成立）**：

> **直接移植现有 2–3 方 DORAM（如 Circuit ORAM / 3-party RAM），且不修改 VDORAM 的执行契约与公开证明契约，作为 HistoricalKV 线性扫描的插件替代。**

理由（仍为 VERIFIED）：
- 论文 p9 原文：现有高效 DORAM 只支持 *"insubstantial number of parties"*，与 VDORAM *"arbitrary number of provers beyond just two or three"* 目标 *"does not align"*——作者据此选线性扫描；Table III（p14）把 `≥1 provers` 列为 VDORAM 独有能力。
- 命中任务包 NO_GO 条件"必须限制参与方数量而原目标要求任意参与方"——**但仅对"直接移植现成方案"这一具体做法成立**。

**HOLD（一般对象）**：任意方、dishonest-majority、公开可验证状态转换的 ORAM 状态机——未被排除。

## 3. 唯一最关键的待验证问题（HOLD 的收敛点）

按任务包"不得列无穷未来工作"的要求，只给**一个**问题：

> **能否构造一个 ORAM 转换电路，使"每步状态转换 `S_i → S_{i+1}`"本身成为 collaborative zkSNARK 可验证的 R1CS 关系——状态份额按 registers 模式（外层持有、跨 session、逐步输入输出）承载，承诺链按 `hashThisState` 模式滚动，且不限制参与方数量（保持任意 m 方、dishonest-majority、全体合谋下公开可验证）？**

- 这是 R1 中 (b) SNARK 验证转换 + (c) 连续绑定 + 参与方兼容三者的共同根；若此问题有肯定答案，方向即可进入原型设计；若否定，则真正 NO_GO。
- **补充限定（2026-11-23 verifier 核查）**：此问题还须包含"verifier 强制串联每步公开状态 hash（previous output = next input）、拒绝跳步、检查初始/最终锚点"这一子项——`verifier-chain-check.md` 确认本仓库只提供执行器宿主层 hash 检查与逐电路落盘/手动证明，**未提供**该验证端串联。因此它明确属于待验证问题的一部分，而非已知可复用能力。
- 它**不是**"写一个 Path ORAM 数据结构"——那只是底层组件；它需要协议层设计（状态转换 R1CS 关系 + 大状态承诺 + n 方兼容）。
- 当前证据为 **UNKNOWN**：registers 的承载/承诺/证明**模式存在**（INFERRED），但 ORAM 状态规模、秘密索引成本、承诺覆盖性、参与方兼容均**未验证**。

**建议**：若继续，先做**纸面协议设计**（不写 ORAM 代码），只回答上面这一个问题；有肯定答案前不启动 ORAM 原型工程。

## 4. 已确认可保留的成果（不受修订影响）

| 成果 | 状态 |
| --- | --- |
| 双结构 HistoricalKV 语义保持（E1/R1） | VERIFIED，仍成立 |
| 5 列历史 + 逐行承诺可保留 | VERIFIED，仍成立 |
| `in_mem_val` 钩子 + registers 跨 session 链 | VERIFIED，仍成立（R1 进一步实证份额跨 session） |
| 地址域固定 `[0,n-1]`，可映射固定 Path ORAM | VERIFIED，仍成立（负责人预判①未命中） |
| 无现成高效秘密索引接口 / 现有 DORAM 参与方限制 | VERIFIED，仍成立（但不再作为整体 NO_GO 依据） |
| 承诺不能单独证明转换合法 | VERIFIED，仍成立（R1 §6.1 保留） |

## 5. 对三个预判的最终对照（负责人表格对齐）

| 判断 | 负责人独立结论 | R1 后本项目结论 |
| --- | --- | --- |
| 地址域固定 `[0,n−1]` | 接受 | VERIFIED，一致 |
| 当前无专用 ORAM/secret-index 原语 | 接受 | VERIFIED，一致（但成本问题非理论禁止） |
| 现有 DORAM 参与方限制 | 接受 | VERIFIED，一致（限"直接插件"NO_GO） |
| 当前无 ORAM 状态转换证明 | 接受 | VERIFIED，一致 |
| session 注销导致状态无法跨步 | **不接受原推理** | **已撤回原推理，与负责人一致** |
| 当前框架内无法实现 ORAM 状态机 | 尚未证明 | **UNKNOWN，一致（不宣称已证明不可能）** |
| 直接用现有 2–3 方 ORAM 作插件 | NO_GO | NO_GO，一致 |
| 任意方、公开可验证 ORAM 状态机 | HOLD | HOLD，一致 |

## 6. 决策纪律

- 未为得到 GO 弱化威胁模型；未把"机制可推广"写成"ORAM 已可行"。
- 未用"有待进一步研究"代替决策：整体明确 HOLD，narrower 对象明确 NO_GO，并给出唯一收敛问题。
- 未重跑 benchmark、未实现 ORAM、未大规模改旧文档（原 decision.md 保留为历史记录）。
- 本 R1 到此停止，等待研究负责人独立核查。
