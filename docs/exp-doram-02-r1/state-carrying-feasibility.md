# state-carrying-feasibility.md — EXP-DORAM-02-R1：State-Carrying Feasibility Check

> 日期：2026-11-23 · 起点 commit `039aa45` · 聚焦验证，**不重做完整审计、不实现 ORAM、不跑 benchmark、不重新下载全部源码**。
> 唯一研究问题：**能否仿照 VDORAM 的 registers 跨步传递方式，让 ORAM 的秘密状态份额跨越 MPC session、在下一步作为新电路输入，并把状态转换纳入 collaborative zkSNARK 的证明关系？**

## 0. 一句话结论

**机制层面：可以（VERIFIED for registers / INFERRED for ORAM）。** VDORAM 的 `thisRegisters` 份额由外层执行器持有、跨 session 传递、每步作为 `in_this_reg_{i}` 输入、输出份额 `out_reg_{i}` 写回，并以公开 hash 承诺链约束连续性——ORAM 状态份额可依**同一模式**承载。**EXP-DORAM-02 中"session 注销 → 份额全部销毁 → ORAM 状态无法跨步"的推理被撤回（见 §3）。**

**仍未验证：ORAM 状态表示规模、转换电路构造、承诺更新与 SNARK 约束、任意方兼容（UNKNOWN，见 §6）。** 这不是"不可能"，而是"尚未解决"。

---

## 1. 核查的源码证据（固定 commit `10c90d3`）

| 文件 | 关键行 | 证明内容 | 标记 |
| --- | --- | --- | --- |
| `ZkProgramExecutor.cs` | L73 | `List<MpcValue> thisRegisters = ...ToList()` — 份额列表由**外层执行器**声明并持有 | VERIFIED |
| `ZkProgramExecutor.cs` | L142/L213/L250/L481/L536 | 每个阶段/每步调用 `NextExecutor()` — 每个电路一个新 session | VERIFIED |
| `ZkProgramExecutor.cs` | L297 | `AddPrivate($"in_this_reg_{i}", thisRegisters[i])` — 上一步输出份额作为下一步电路**私有输入** | VERIFIED |
| `ZkProgramExecutor.cs` | L302 | `AddPrivate("in_mem_val", memVal)` — Fetch 输出绑定进 VM（ORAM `result_i` 的对应点） | VERIFIED |
| `ZkProgramExecutor.cs` | L230 | `AddPrivate("in_mem_addr", thisRegisters[0])` — Fetch 输入地址用 reg0 | VERIFIED |
| `ZkProgramExecutor.cs` | L375-376 | `privOutRegisters = GetOutput($"out_reg_{i}"); thisRegisters = privOutRegisters;` — 输出份额**写回外层变量** | VERIFIED |
| `ZkProgramExecutor.cs` | L363-365 | `thisProgramCounter = privOutProgramCounter` — pc 份额同模式 | VERIFIED |
| `ZkProgramExecutor.cs` | L322-328 | `out_hash_this_registers` vs `hashThisRegisters` 一致性检查 — **输入侧承诺校验** | VERIFIED |
| `ZkProgramExecutor.cs` | L367-371 | `hashThisRegisters = out_hash_next_registers` — **输出侧承诺更新为下一步输入** | VERIFIED |
| `ZkProgramExecutor.cs` | L415/L590 / L23/L45-48 | `RaiseR1csCircuitWithValuesGenerated(...)` → `OnR1csCircuitWithValuesGeneratedAsync` — 每个电路的 R1CS+witness 落盘交给协作证明 | VERIFIED |
| `MpcValue.cs`（本轮新增证据，blob `0932697ce7fc`） | 全 17 行 | `record MpcValue { Field Value; bool IsSecretShare; }` — **纯值对象，零 session/storage 引用** | VERIFIED |
| `MpcExecutorFactory.cs` | L44-50 | `NextExecutor()` 先确认上个 executor `Completed`，再 `_prevMpcShareStorage?.UnregisterSession()`，再新建 storage+executor | VERIFIED |
| `MpcSharedStorage.cs` | L47-55 `Dispose()` | 只清 `_partyCompleted`/`_partyOnline`/`_exposedBoolShareVectors`/`_exposedBigIntegerShareVectors` — **全是通信缓冲，无 MpcValue 份额** | VERIFIED |

（路径前缀：`CompatCircuit/CollaborativeZkVm/ZkPrograms/`、`CompatCircuit/CompatCircuitCore/MultiPartyComputationPrimitives/`、`CompatCircuit/CompatCircuitCore/Computation/MultiParty/`；快照见 `docs/source-snapshot/` 与 `docs/exp-doram-02/source-evidence/`。）

## 2. registers 的实际跨 session 传递机制（源码实证）

```
外层 Execute() 作用域（跨所有 step 存活）             每个 step 一个 MPC session
─────────────────────────────────────────           ──────────────────────────────
thisRegisters: List<MpcValue>  (L73)
hashThisRegisters: Field       (L74)
        │                                              NextExecutor() (L250)
        │  AddPrivate("in_this_reg_{i}", thisRegisters[i])  (L297) ──────► 新 session
        │  AddPrivate("in_this_program_counter", ...)       (L293) ──────► 电路输入
        │                                                    Compute()
        │  一致性检查: out_hash_this_registers == hashThisRegisters (L322-328)
        │  ◄──────────────── GetOutput("out_reg_{i}") (L375)
        ▼
thisRegisters = privOutRegisters                (L376)   写回外层变量
hashThisRegisters = out_hash_next_registers     (L370)   承诺链滚动到下一步
RaiseR1csCircuitWithValuesGenerated(...)        (L415)   本步 R1CS+witness 入协作证明
```

**要点（VERIFIED）**：
1. 份额载体是 `MpcValue`——一个 `Field` + 一个 bool 标志的**纯值对象**，不持有 session 引用（`MpcValue.cs`）。
2. 份额**从未**存放在 `MpcSharedStorage` 里；后者只是各方之间的**消息/暴露份额交换缓冲**。`Dispose()` 清的是四个通信字典，不包括 `MpcValue`。
3. `NextExecutor()` 注销的是上一个**通信 session ID**，与外层持有的份额无关。
4. 跨步连续性不是靠"份额活着"自动成立，而是靠 `hashThisRegisters` 链：每步先校验**输入状态 hash 等于上一步承诺的输出 hash**（L322-328），再把输出 hash 滚动为下一步输入承诺（L367-371）。这同时防替换、跳步、回滚。

## 3. 关键纠正：撤回原推理

| EXP-DORAM-02 原表述 | R1 核查后判定 | 修订表述 |
| --- | --- | --- |
| "session 销毁份额 → ORAM 状态无法跨 step 保存"（decision.md 依据2、protocol-audit §Q4、state-binding §D） | **不接受原推理（研究负责人独立核查 + 本轮源码实证）** | `UnregisterSession()` → 旧 session 的**通信状态**被注销；秘密份额是外层执行器持有的 `MpcValue` 值对象，可像 registers 一样跨 step 传递。**当前缺的是 ORAM 状态传递与证明的专用接口/电路，不是份额不能存活。** |
| "无专用 ORAM/secret-index 原语 → 理论障碍" | **收紧**（负责人第 2 点） | VERIFIED：无现成高效秘密索引接口（`SelectComposeGadget` 是固定候选线性组合）。但现有比较/乘法/加法原语**理论上可组合**出 O(N) 秘密索引电路——这是**成本与构造问题（UNKNOWN）**，不是不可绕过的理论禁止。 |
| "2-3 方 DORAM 限制 → NO_GO" | **收紧**（负责人第 3 点） | VERIFIED：论文 p9 记录作者因任意方目标放弃当时高效 DORAM。但这是**现有方案**的限制，不推出"任意方 ORAM 不存在"或"Path ORAM 必然限方"。作为**直接插件**仍 NO_GO；一般问题 HOLD。 |

> 三种香槟式结论的边界必须分开：**(a)** MPC 内部正确计算状态（份额能被电路算出来）；**(b)** SNARK 验证状态转换关系（转换本身是 R1CS 可证）；**(c)** 外部协议保证连续性与不可回滚（hash 承诺链 + 每步校验）。registers 三者具备；ORAM 的 (a) 机制可推广、(b)(c) 需新增电路与承诺但模式存在，成本与构造 UNKNOWN。

## 4. 数据流与电路接口（本轮要求的图）

```
   S_i shares (MpcValue[], 外层持有, 类比 thisRegisters)
        │
        │  AddPrivate("in_state_{j}", S_i[j])   ← 新增输入线（类比 L297 in_this_reg_i）
        │  AddPrivate("in_mem_addr", reg0)      ← Fetch 用 reg0 (L230, 已 VERIFIED)
        ▼
   ┌─────────────────────────────────┐
   │  ORAM transition circuit        │  ← 新增电路（本轮不实现）
   │  (路径读/写 + stash + pos map)  │
   └─────────────────────────────────┘
        │
        ├──► result_i ──► AddPrivate("in_mem_val", result_i) ──► VM (L302 已 VERIFIED 钩子)
        │
        ├──► S_{i+1} shares ──► 写回外层变量 (类比 L376 thisRegisters = ...)
        │
        └──► H(S_{i+1}) 公开承诺 ──► hashThisState = out_hash_next_state (类比 L370)
                    │
                    ▼
         下一步: 校验 out_hash_this_state == hashThisState (类比 L322-328)
                    │
                    ▼
         本步 R1CS+witness ──► OnR1csCircuitWithValuesGeneratedAsync (L415/L23)
                    │
                    ▼
         collaborative zkSNARK 验证「状态转换关系」而非仅独立承诺
```

**接口清单（相对 registers 的新增项）**：

| 接口 | registers 现状（VERIFIED） | ORAM 需要（本轮设计，INFERRED） | 状态 |
| --- | --- | --- | --- |
| 份额载体 | `List<MpcValue>`，`MpcValue` 为纯值对象 | 同类型，`S_i` 为 MpcValue 列表 | 机制可复用 |
| 电路输入线 | `in_this_reg_{i}`（L297） | `in_state_{j}`（新） | 需新增 symbols |
| 电路输出线 | `out_reg_{i}`（L375） | `out_state_{j}`（新） | 需新增 symbols |
| 结果绑定 | `in_mem_val`（L302） | 复用同一钩子 | 已存在 |
| 输入地址语义 | `in_mem_addr = reg0`（L230） | fetch_address = reg0，trace_address = NegOne（R1 已分离） | 已存在 |
| 承诺校验 | `out_hash_this_registers`（L322-328） | `out_hash_this_state`（新，同 gadget） | 模式可复用 |
| 承诺滚动 | `hashThisRegisters = out_hash_next_registers`（L370） | `hashThisState = out_hash_next_state`（新） | 模式可复用 |
| 证明入口 | `RaiseR1csCircuitWithValuesGenerated`（L415） | 同一入口 | 已存在 |

## 5. 机制推广判定（逐条标注）

| 子问题 | 判定 | 依据 |
| --- | --- | --- |
| ORAM 份额能否像 registers 一样由外层持有、跨 session？ | **INFERRED（强）→ 可行** | `MpcValue` 是纯值对象、无 session 引用；registers 已实证此模式（L73/L297/L376）。ORAM 份额同为 field 元素，无类型障碍。 |
| 能否作为下一步电路输入？ | **INFERRED（强）→ 可行** | `AddPrivate` 接受任意 `MpcValue`（L297/L302/L549 已用于 registers/memVal/trace）；增 `in_state_j` 线即可。 |
| 能否把状态转换纳入 collaborative zkSNARK 证明关系？ | **INFERRED → 模式存在** | 每个电路的 R1CS+witness 经 `OnR1csCircuitWithValuesGeneratedAsync` 入协作证明（L415/L23/L45-48）；ORAM 转换电路若按同一 wrapper 构造，其 R1CS 自动进入。**但"转换正确"必须由该电路自身的 R1CS 约束表达，非仅加一个独立承诺**（原报告此点仍成立，见 §6.1）。 |
| 能否防状态替换/跳步/回滚？ | **INFERRED → 模式存在** | registers 用 hash 承诺链达成（L322-328/L367-371），ORAM 复用同 gadget 需承诺可增量更新且覆盖全状态——覆盖性与成本见 §6.4。 |
| 现有框架是否"具备实现路径访问的全部原语"？ | **UNKNOWN（收紧）** | 无专用秘密索引（VERIFIED），但可用比较+乘法组合；是否足够且成本可接受未验证。 |

## 6. 仍未知 / 需注意的部分（诚实边界）

1. **承诺 ≠ 转换证明（VERIFIED 约束事实）**：`hashThisState` 链只能绑定"输入状态 = 上一步输出承诺"，**不能单独证明转换合法**；转换合法必须由 ORAM 转换电路自身的 R1CS 约束保证（原报告 §State Binding 此点正确，保留）。本轮不推翻它，只撤回"份额无法跨步"。
2. **状态规模导致电路宽度膨胀（INFERRED）**：若 `S` 含完整 position map（O(N) 条目）+ stash + 树节点，每步需 O(N) 条 `in_state_j`/`out_state_j` 线，witness 与 R1CS 规模随 N 增长。这是**效率问题**，非"跨步不可能"——但可能抵消 ORAM 相对线性扫描的收益，需实测或符号成本确认。
3. **秘密索引与 ORAM 构造（UNKNOWN）**：可用现有原语组合 O(N) 秘密索引，但能否构造出保持 ORAM 复杂度优势、且任意方兼容的转换电路，本轮未验证（负责人第 2 点）。
4. **承诺覆盖性与增量更新（UNKNOWN）**：需一个覆盖全 ORAM 状态、可每步更新、且更新本身可证的承诺方案；registers 的 hash gadget 是否直接适配大状态未验证。
5. **参与方模型（UNKNOWN，负责人第 3 点）**：现有 2-3 方 DORAM 与目标冲突是 VERIFIED 论文事实；任意方、dishonest-majority、全体合谋下公开可验证的 ORAM 状态机是否存在，未被证明不可能，也未被证明可行。

## 7. 本轮明确不做

- 不实现 Path ORAM、不写 ORAM 电路代码；
- 不跑 benchmark、不引入新性能对比；
- 不重新下载全部源码（仅新增 `MpcValue.cs` 一个证据文件）；
- 不把"机制可推广"写成"ORAM 已可行"，不把"成本未知"写成"不可能"。

## 8. 移交决策

见 `decision-revision.md`：整体判定修订为 **HOLD**；NO_GO 严格限定为"直接移植现有 2–3 方 DORAM 且不修改 VDORAM 执行/证明契约"这一 narrower 对象。唯一最关键待验证问题见该文档 §3。
