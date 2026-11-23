# decision.md — EXP-DORAM-02 最终决策

> ⚠️ **修订提示（2026-11-23）**：本文整体判定已被 `docs/exp-doram-02-r1/decision-revision.md` 修订为 **HOLD**；本文"依据2（session 销毁份额 → 无法跨 step）"整条撤回，依据1/3 收紧为仅对"直接移植现有 2-3 方 DORAM"成立。本文保留为 EXP-DORAM-02 的历史执行记录，不再作为当前决策依据。请以 R1 修订文档为准。

> 决策日期：2026-11-23 · 起点 commit `068d2507` · 严格按任务包 §7 三选一规则。

## 决策：**NO_GO**

**NO_GO 对象（严格遵守全局硬边界：具体贡献 NO-GO ≠ 整体研究问题 NO-GO）**：

> 在**当前 VDORAM 框架内**引入 Path ORAM 替代线性扫描 HistoricalKV、并把每步 ORAM 状态转换接入现有公开协作式 SNARK 的这条**具体技术路线**。

**核心研究问题的状态：HOLD（未关闭）**：

> "能否为 VDORAM 构造一个既能任意参与方下分布式隐藏访问、又能公开验证状态转换的 ORAM 状态机"——本轮**未证明其不可能**，只是证明**当前框架内这条路走不通**。它需要全新的协议设计，超出本轮边界。

## 一、决策依据（三条，均为结构性、论文/源码直接支持）

### 依据 1：参与方数量与研究目标结构性冲突（VERIFIED，论文 p9/p14）

论文原文（p9）：现有高效 DORAM 只支持 *"insubstantial number of parties"*，与 VDORAM *"arbitrary number of provers beyond just two or three"* 目标 *"does not align"*；作者因此明确选择 *"one linearly-scanned oblivious array"*。Table III（p14）把 `≥1 provers` 列为 VDORAM 独有能力。**命中任务包 NO_GO 条件"必须限制参与方数量而原目标要求任意参与方"。**

### 依据 2：无法跨 step 维护和绑定 ORAM 状态（VERIFIED/BLOCKED）

- 现有跨 step 状态只有 pc/registers/trace（源码 L70-74/L358-376/L393-412），无 ORAM 状态槽。
- `MpcExecutorFactory.NextExecutor()` L50 每步前注销上一 session；`MpcSharedStorage.Dispose()` L47-55 清空份额——session 是短命通信容器，不保留状态。
- SNARK 只验证现有 RAM 状态转换；ORAM 状态转换无电路、无可验证 R1CS 关系；加独立 `H(S_{i+1})` 承诺不能证明转换合法。
- 无 `H(S)` 链 → 状态替换/跳步/重放/回滚均无防护。

**命中任务包 NO_GO 条件"无法跨 step 维护和绑定 ORAM 状态"。**

### 依据 3：秘密索引原语缺失（VERIFIED）

MPC 原生只有 4 操作（Add/Mul/Inv/BitDecomp）；`SelectComposeGadget` 是编译期固定候选的线性组合，非 secret-index 数组访问；全树搜索无 ORAM/swap/secret-index 源文件。O(N) 线性实现秘密索引将退化为现有线性扫描，无 ORAM 收益。

## 二、为什么不是 GO_TO_PROTOTYPE

GO 的六个条件（任务包 §7）逐条对照：

| GO 条件 | 是否满足 |
| --- | --- |
| ① 地址空间及动态 map 语义明确 | 部分满足（固定域明确；但无需动态 map） |
| ② Position Map/Stash/Path RW 都有可实现 MPC 路径 | **否**（秘密索引缺失、状态无法持久化） |
| ③ MPC 状态跨 step 持久化 | **否**（session 销毁、无通道） |
| ④ 可信状态转换证明与连续绑定 | **否**（无可验证 ORAM 转换关系、无 H(S) 链） |
| ⑤ ORAM 威胁模型与参与方模型兼容 | **否**（2-3 方 vs 任意方冲突） |
| ⑥ 复杂度无抵消收益的结构性障碍 | **否**（递归 pos map + 每步状态承诺 + 未知常数） |

六项中四项明确不满足 → 不满足 GO。

## 三、为什么不是 HOLD（对本路线）

任务包 HOLD 定义要求"存在值得继续解决的具体技术缺口，但现有证据不足以判定可行或不可行"。本路线**已有充分证据判定不可行**：

- 参与方冲突不是"待验证"，而是论文作者已论证并据此做出设计决策的事实（p9）；
- 状态绑定阻断不是"证据不足"，而是源码明确显示无状态通道、session 明确销毁份额、SNARK 明确无可验证关系；
- 再投入原型实现只会制造"能运行但无法接入 VDORAM 公开证明"的 ORAM 模拟器——正是任务包开篇要避免的结果。

因此本具体路线判 NO_GO，而非 HOLD。（更一般研究问题另记 HOLD，见开头边界声明。）

## 四、若 nonetheless 要推进该研究方向——唯一最关键的待验证问题

按任务包"不得列出无穷无尽未来工作"的要求，只给**一个**问题：

> **能否构造一个 ORAM 状态机，使"每一步状态转换 `S_i → S_{i+1}`"本身成为 collaborative zkSNARK 可验证的 R1CS 关系，同时不限制参与方数量（保持 dishonest-majority、任意 m 方、全体合谋下公开可验证）？**

- 这是 Q2-Q5 四个阻断的共同根：若此问题有解，状态绑定、持久化、SNARK 验证、威胁模型兼容可一并解决；若无解，其余都无需再试。
- 它**不是**"实现一个 Path ORAM 原型"——那只是底层数据结构；它需要新的协议层设计（状态承诺链 + 可验证转换关系 + n 方兼容）。
- 当前证据集对该问题为 **UNKNOWN**：既未证明可行，也未证明不可能。

**建议**：若研究负责人决定继续，先做一个**纸面协议设计**（不写 ORAM 代码），只回答上面这一个问题；在其有肯定答案前，不启动任何 Path ORAM 原型工程。

## 五、本轮已确认可保留的成果（避免否定全部工作）

| 成果 | 状态 |
| --- | --- |
| 双结构 HistoricalKV 语义保持（E1/R1） | VERIFIED，仍成立 |
| 5 列历史 + 逐行承诺可保留（对应论文 `Export()`） | VERIFIED，仍成立 |
| `in_mem_val` VM 输入钩子与 session 链（source-audit） | VERIFIED，仍成立（仅钩子，非完整接入） |
| 地址域可映射固定 Path ORAM（修正负责人预判①） | VERIFIED，仍成立 |

本轮不是"白做"：它把"ORAM 接入 VDORAM"从一个抽象设想，精确收敛到**一个**可判定的协议层问题（§四），并在投入昂贵原型前识别了两条论文级结构性障碍。

## 六、决策纪律声明

- 未为得到 GO 弱化威胁模型；未因已有 Path ORAM 工作直接 NO_GO（逐项核对安全模型/动态 map/状态绑定/适配）。
- 未用"有待进一步研究"代替决策：本路线明确 NO_GO，一般问题明确 HOLD。
- 未扩展研究范围；未重跑 benchmark；未实现 ORAM；未改上游。
- 交付后停止，等待研究负责人独立核查。
