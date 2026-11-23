# protocol-compatibility-audit.md — EXP-DORAM-02 总体协议与源码兼容性审计

> 仓库 `kaikai-cao/vdoram-historicalkv-experiment` · 起点 commit `068d2507`
> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52` · 论文 NDSS'26 / eprint 2025/039
> 本轮：纯协议与源码审计，未实现 ORAM、未跑 benchmark、未改上游。
> 标注：VERIFIED / INFERRED / UNKNOWN / BLOCKED。源码证据 `source-evidence/` + `../source-snapshot/`（带 PATH/BLOB SHA）；论文原文 `paper/EXCERPTS.md`（PDF 页码）+ `paper/vdoram-ndss2026.pdf`。

## 0. 唯一研究问题与总答案

**问题**：能否在 VDORAM 的 MPC 框架中维护跨 VM 步骤更新的 Current-State ORAM，且每步状态转换能被公开协作式 SNARK 验证、绑定 VM 执行与 Historical Log，同时不破坏分布式访问模式隐私？

**总答案**：**在当前 VDORAM 框架内，这条路线走不通（NO_GO，针对该具体路线）。** 两个独立的结构性障碍同时成立，均为论文/源码直接支持，非调参或工程优化可绕过：

1. **参与方数量冲突**：论文明确说明现有高效 DORAM 仅支持 2-3 方，与 VDORAM"任意数量 prover"核心目标冲突，这正是作者放弃 DORAM、改用线性扫描的原因（p9，VERIFIED）。
2. **无法跨 step 维护和绑定 ORAM 状态**：现有框架只有 pc/registers/trace 的跨 step 闭环，无 ORAM 状态槽；MPC session 用完即销毁份额；没有可被 SNARK 验证的 ORAM 状态转换关系（`state-binding-analysis.md`，BLOCKED）。

**边界声明（遵守全局硬边界）**：此 NO_GO 针对"在现有 VDORAM 电路中引入 Path ORAM 替代线性扫描 HistoricalKV"这一**具体路线**，不等于"公开可验证分布式 ORAM 状态机"这一更一般研究问题被证明不可能——后者需要全新的协议设计（n 方、dishonest-majority、可公开验证状态转换），已超出本轮边界，记为 **HOLD**。详见 `decision.md`。

## 1. 五个必答问题（不得合并）

| # | 问题 | 答案 | 标注 |
| --- | --- | --- | --- |
| 1 | MPC 能否计算 ORAM 状态转换？ | 底层原语（加/乘/逆/位分解 + 比较/选择/hash）足以表达加法共享上的转换，**但**没有秘密索引数组访问原语，也无 ORAM 状态对象；跨 session 份额被销毁 | VERIFIED（原语）/ BLOCKED（索引与持久化） |
| 2 | 状态能否跨 VM 步骤持久化？ | 现有只有 pc/registers/trace 通过电路输入输出闭环；`NextExecutor()` 每步前 `UnregisterSession()` 上一个，`MpcSharedStorage.Dispose()` 清空份额；ORAM 状态无通道 | VERIFIED（现状）/ BLOCKED（ORAM 状态） |
| 3 | 公开证明能否验证状态转换正确性？ | 能验证现有 RAM 状态（pc/R/M/halt）转换；ORAM 状态转换无电路、无可验证关系，加一个独立 `H(S_{i+1})` 承诺不足以证明转换合法 | VERIFIED（现有范围）/ BLOCKED（ORAM） |
| 4 | 新状态能否被绑定到下一步、阻止替换/回滚？ | registers 有 hash 连续检查闭环；ORAM 无 `H(S)` 链，状态替换/跳步/重放/回滚均无防护 | VERIFIED（现有）/ BLOCKED（ORAM） |
| 5 | 是否满足 VDORAM 参与方与隐私威胁模型？ | 高效 DORAM 限 2-3 方，违背"任意 prover"目标；半诚实 ORAM 无可验证性；全体合谋破坏 correctness 的假设要求 ORAM 转换也可公开验证 | VERIFIED（论文 p2/p4/p9/p14）/ BLOCKED |

**五问独立结论**：没有一问得到无条件的"支持 ORAM"结论。问题 1（底层原语）部分肯定，问题 2-5 全部命中结构性阻断。

## 2. 四组件判定汇总

| 组件 | 判定 | 关键点 |
| --- | --- | --- |
| Position Map | **BLOCKED（当前）/ INFERRED（另起 n 方）** | 本仓库不存在；地址域固定 `[0,n−1]`（这一关可过）；无秘密索引原语；递归会复制状态绑定障碍 |
| Stash | **BLOCKED（当前）/ UNKNOWN（参数）** | 无 stash/树结构；原语可做固定形状扫描；无跨 step 通道；overflow 界与 S 全 UNKNOWN |
| Path Read/Write | **BLOCKED（秘密索引）/ UNKNOWN（成本）** | 比较/选择/hash 原语具备；秘密索引数组访问缺失；dummy path 需新设计；轮数 O((L·Z+S)·l) 常数未知 |
| State Binding | **BLOCKED（核心）** | 无 ORAM 状态槽、session 销毁份额、无可验证转换关系、无 H(S) 承诺链——**最关键系统性障碍** |

## 3. 八项验收标准逐条回答

| # | 验收问题 | 回答 | 标注 |
| --- | --- | --- | --- |
| 1 | VDORAM memory address 能否直接映射 Path ORAM？ | **能**（地址是固定密集域 `[0,n−1]`，与固定容量数组 Path ORAM 相容）。修正负责人初步担忧：动态 key 不是第一阻断 | VERIFIED（论文 p8 Fig.5） |
| 2 | Position Map 是否成为新主要瓶颈？ | **是，但不是唯一**。它无现成结构、无秘密索引原语、递归复制状态绑定障碍；与状态绑定并列为两大瓶颈 | VERIFIED（缺失）/ INFERRED |
| 3 | MPC 框架是否具备路径访问全部原语？ | **不具备**。具备比较/选择/位分解/hash/位运算；缺秘密索引数组访问与条件交换 | VERIFIED（原语清单与全树搜索） |
| 4 | ORAM 状态如何跨 step 保存？ | **当前无法保存**。只能靠电路输入输出闭环（registers 模式）；ORAM 状态规模随 N 线性且无输出线契约；session 销毁份额 | BLOCKED |
| 5 | SNARK 如何验证每步状态转换？ | **当前不能验证 ORAM 状态**。只验证现有 RAM 状态转换；ORAM 需新定义 R1CS 转换关系并接入电路 | VERIFIED（范围）/ BLOCKED |
| 6 | 如何阻止下一步用旧状态或伪造状态？ | registers 用 hash 连续检查；ORAM 无 H(S) 链、无 step 绑定，替换/跳步/重放/回滚均可发生 | VERIFIED（现有）/ BLOCKED |
| 7 | 原 VDORAM 隐私与参与方假设是否仍成立？ | **若强行接入 2-3 方 DORAM 则不成立**（违背任意 prover 目标）；隐私阈值 t 与合谋模型本身保留，但 ORAM 状态转换隐私未证 | VERIFIED（论文 p4/p9/p14） |
| 8 | 与 O(T²) 相比是否有值得实现的复杂度空间？ | 渐近上有（`T·(L·Z+S)·l` vs `T²`），但递归 pos map + 每步状态承诺 + dummy 操作 + 未知常数可能抵消；无净收益证据 | INFERRED / UNKNOWN |

## 4. 三个最高风险的处理（与负责人预期对照）

| 负责人预判风险 | 审计结论 | 是否命中 |
| --- | --- | --- |
| ① 动态地址空间 | 地址固定 `[0,n−1]`，不构成门槛；动态 KV map 不需要 | **未命中**（预期需修正） |
| ② 跨步状态与证明绑定 | 命中，且是**唯一最关键系统性障碍**；缺的是可证明约束的状态机而非 ORAM 读写接口 | **命中（核心）** |
| ③ 威胁模型兼容 | 命中；论文作者已因任意参与方目标放弃 DORAM；2-3 方 ORAM 与目标直接冲突 | **命中** |

## 5. 关键源码/论文证据摘要（可复核）

### 源码（固定 commit，带行号）

- `ZkProgramExecutor.cs` L70-74：跨 step 状态初始化（pc/registers + 公开 hash）。
- `ZkProgramExecutor.cs` L205-236：每步 Fetch（step 0 zeroShare）、L230 `in_mem_addr = reg0`、L302 `in_mem_val = memVal`。
- `ZkProgramExecutor.cs` L322-328 / L355-376：hash 连续检查 + registers/pc 跨 step 更新（唯一闭环）。
- `ZkProgramExecutor.cs` L393-412 / L580-586：trace 追加 + hash-count 比对。
- `MpcExecutorFactory.cs` L45-67：L50 注销上一 session、L52 递增 sessionID、L57 注释预处理 enumerator 不可交错。
- `MpcSharedStorage.cs` L47-55：Dispose 清空全部 share 向量。
- `MpcSharedStorageSessionManager.cs` L95-111：UnregisterSession 移除状态。
- `SelectComposeGadget.cs` L16-44：`Σ cᵢvᵢ`，编译期固定候选数，非秘密索引。
- `ZkVmExecutorCircuitBoardGenerator.cs` L990-1000：`out_trace_mem_addr` 非内存 op = NegOne；L1013-1017 MiMC 行承诺。
- 全树搜索（1497 条目）：无 ORAM/position/leaf/bucket/stash/secret-index/swap 源文件（0 命中）。

### 论文（NDSS'26 官方 PDF，页码）

- p2：半诚实 DORAM 无可验证性；恶意 DORAM 内部可验证 ≠ 公开可验证。
- p4 §III-A：威胁模型（0 prover 对 correctness 诚实；≥t prover 对 privacy 诚实；dishonest-majority MPC）。
- p5-6：协作 zkSNARK (m,t) 定义；"只检查 RAM 状态完整性"的设计哲学。
- p8 Fig.5：`FHistoricalKV` 地址域 `addr ∈ [0,n−1]`、`Export()` 导出全部历史；2-party Circuit ORAM / 3-party RAM 举例。
- p9：现有 DORAM 只支持少数方、与任意 prover 目标冲突；改用单线性扫描 array；ΠHistoricalKV；Bitonic padding。
- p10 §IV-E：gadget 轮数；memory fetch `O(T²)`；隐私声明（访问次数 = 周期数）。
- p11 Definition IV.1：安全定义；I/O 与 T 公开例外。
- p14 Table III：`≥1 provers` 是 VDORAM 独有能力。

## 6. 本轮边界遵守声明

- 未重新跑 E0/E1/R1 benchmark；未引入新的 Python 字典对比；未实现 Path ORAM；未启动 Halo2。
- 未把 MPC 比较/选择原语等同于已支持 ORAM（明确需秘密索引，缺失）。
- 未把 SNARK 状态承诺等同于自动保证状态真实/连续/不可回滚（三层严格区分）。
- 未弱化威胁模型；未因已有 Path ORAM 工作直接下结论（逐项检查安全模型/动态 map/状态绑定/适配差异）。
- 未扩展成 ORAM 文献综述；所有结论针对固定 commit 与本论文。

## 7. 与 E0/E1/R1 的衔接

- 本轮**不修改** E0/E1 实现与 R1 历史数据；只新增 `docs/exp-doram-02/`。
- E1 已证明"历史日志可保留证明所需 5 列 + 承诺"（对应论文 `Export()` 需求），这一结论在本轮仍成立（VERIFIED）。
- 本轮新增结论：历史侧可保留，但**ORAM 状态侧无法绑定**——双结构路线只完成了一半。
