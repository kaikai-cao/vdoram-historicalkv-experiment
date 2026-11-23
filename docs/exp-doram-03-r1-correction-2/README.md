# EXP-DORAM-03-R1-Correction-2 — 路径约束、Eviction 成本与承诺安全修正

> 2026-11-23 · 起点 `bc6d774921b89fb19e9d809d21f4757545039a51` · 只做纸面修正，不写代码、不跑 benchmark、不启动原型。

## 本轮目标

只修正上一轮独立审查发现的三个问题，并把构造推进到可作出下一阶段决策的程度：

1. **D1**：Merkle 路径方向位、左右子节点和父节点哈希顺序；
2. **A**：Eviction 前缀比较与候选选择的完整 R1CS 成本；
3. **B1 + C3**：witness commitment 与秘密 nonce 的隐藏性、绑定性、重放安全统一模型。

**最终决策：HOLD**（见 `decision.md`）。D2（MPC–SNARK 真实接口）按任务包要求保持 **BLOCKED**，本轮未尝试解封，也未用流程图把它标成已解决。

## 固定基线

- Repository：`kaikai-cao/vdoram-historicalkv-experiment`
- Local：`D:\Research\vdoram-historicalkv-experiment`
- 上游 VDORAM commit：`10c90d35464620a35ddb1e2c29d2e8725acedd52`
- 前序报告：`docs/exp-doram-03-r1-correction/`（本轮不修改）
- 语义不变：step 0 无 Fetch；此后每步恰好一次 Fetch（含 dummy）；Fetch 地址 `thisRegisters[0]`；`fetch_address` 与 `trace_address` 分离；非内存 op 的 trace 为 `NegOne`；初始 map 空、未出现地址 Load 返回 0；每步一条历史事件；地址域 `[0,n−1]`。
- 威胁模型不变：correctness 对全部 prover 恶意成立；privacy 仅在 `<t` 合谋时承诺；全体合谋不保证隐私。

## 文件导航

| 文件 | 内容 |
| --- | --- |
| `merkle-path-correction.md` | 固定位序、`child/sibling` 正确公式、旧/新根约束、`L=3` 左右分支手工核对、递归 PositionMap 变量一致性 |
| `eviction-cost-correction.md` | 前缀相等电路两种实现、候选选择逐项约束、逐层成本表、全电路总计与口径 |
| `commitment-security-model.md` | `W_i` 定义、三种承诺方案、B1 transcript 七步、C3 nonce 生命周期、统一（条件性）方案 |
| `evidence.md` | 五项定点源码/性质核查，每条含来源、位置、直接支持、不能支持、状态 |
| `decision.md` | GO 门槛逐条核对、最终 HOLD、最小阻塞项、与前序差异 |

## 主要结论

- **D1**：旧稿在特定约定下把 `sib_t` 算成了 `child_t`，且用无序的 `(child,sibling)` 作哈希输入；已撤回并给出完整固定顺序公式与手算核对。
- **成本**：`PREFIX(t)=t` 撤回。共享前缀链每层 `(9Z+3)RL+4ZL`；示例 eviction `659,615 → 769,670 µ`。全电路 `2,524,843 → 2,635,246 µ/步`；含 C3 nonce 为 `2,697,766 µ/步`。
- **承诺**：确定性 MiMC 只 binding；nonce+MiMC 仅启发式 hiding；Pedersen-like 定义清晰但域/后端不匹配、artifact 无实现。统一方案为 `CONDITIONAL_CONSTRUCTION`。
- **B1 与 nonce**：七步 transcript 与域分离给出；challenge 不可预测依赖 ROM + binding com；nonce 的生成/认证随机带/防重放/abort 仍 BLOCKED；选择性 abort 不因顺序修正而消失。
- **证据**：固定 gadget 目录（19 个文件）无 Commitment/Pedersen/Poseidon/Merkle 实现；co-SNARK 接口只落盘 R1CS+witness 并外部逐电路证明，无 com/challenge/认证 witness 暴露。

## 与上一轮（Correction）的差异

- **修正**：路径左右顺序、父节点哈希输入顺序、前缀相等与 eviction 选择计费、承诺模型合并。
- **新增**：PATHSEL `220 µ`、ADDRBIT `20 µ`、RECBIT `108 µ`；dummy 候选与 4 字段选择的完整计数。
- **撤回**：swapped sibling 公式；`PREFIX(t)=t`；`eviction=659,615` 与 `总成本=2,524,843` 作为最终可信值。
- **保持不变**：Merkle 增量方向、每步无 O(N)、`R≥114/179`、V1–V6、`ρ=H(x_i)` 撤回、D2 BLOCKED、整体 HOLD。

## 未解决问题

1. `com(W_i)` 与 nonce 随机带的可实现 hiding+binding 接口（本轮新增的最小阻塞项）；
2. D2 同执行 witness 认证交接与固定行为 abort（遗留 BLOCKED，本轮不扩范围）；
3. 后端每乘法门的 auxiliary 约束倍率、MiMC 安全裕度（沿用上轮 UNKNOWN，本轮不重查）。

完成并提交推送后停止；不启动原型、不追加实验。
