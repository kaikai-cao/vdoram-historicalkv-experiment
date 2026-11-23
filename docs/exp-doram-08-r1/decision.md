# EXP-DORAM-08-R1 — 最终决策

起始 commit：`2b5e47fc725a78f3c48ef91168c4efa6b1bb4a82`
固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
前置：`EXP-DORAM-08 = CONDITIONAL_PASS`；`EXP-DORAM-06 = NO_GO_CURRENT_ARCHITECTURE`（C#→Rust witness 无 SPDZ MAC/auth 契约，本轮不改变）。

## 最终决策：`CONDITIONAL_PASS`

（四选一：`PASS_TO_MPC_MICROBENCHMARK` / **`CONDITIONAL_PASS`** / `NO_GO_COST_ADVANTAGE` / `BLOCKED_SOURCE_EVIDENCE`）

理由：三项勘误均有源码/构造证据支持（排除 `BLOCKED_SOURCE_EVIDENCE`）；修正后 E1 在源码权重下仍有真实 Fetch 原语优势（排除 `NO_GO_COST_ADVANTAGE`）；但该优势依赖有界地址域、`T/n>2`、以及 `c_eq≫c_upd` 的权重结构与未证的 eq 复用，不满足"无条件进入微基准"的 `PASS`。

---

## Q7 逐问回答

### 1. 修正后 E1 是否仍有 Fetch 原语优势？

**有，但收窄且附条件**。源码推导基线（`c_eq=389, c_upd=2`）：

- E1-B 在 10/16 cell 更省，精确等于 `T/n≥4` 的 cell；
- `T/n≤1` 的 cell 全部反劣（最坏 64×）；
- 优势来自结构差异（E1 每步扫固定 n 槽 vs E0 扫递增历史 s），且省掉 E0 的每行 LowBit：E1-B 无 LowBit，E1-A 保留。

R1 修正**削弱但未消除**优势：`c_upd` 从 1→2、`step0 STORE` 强制 separate 使高 STORE + separate 在边界 cell `n=16,T=64` 翻转（ratio=1.0017）；但只读/低 STORE 与 shared 更新下优势稳定。

### 2. E1-A 与 E1-B 哪个更值得微基准？

**E1-B（唯一槽位，无 LowBit）**。理由：

- E1-B 比 E1-A 每 Fetch 省 `(3n−2)` 次秘密乘法（`n=1024` 时全程省 12,571,650 次），且 STORE/追加成本相同；
- 前提是影子表不变量成立（每地址恰一槽、域有界 `addr∈[0,n−1]`），此时 eq 向量天然 one-hot，LowBit 冗余（构造证明见 construction-comparison.md §2）；
- 若该前提不成立（重复地址/域外地址/恶意 witness），E1-B 正确性失效，须退回 E1-A。因前提=CONSTRUCTED（目标系统地址域有界=UNKNOWN），**微基准应先在明确有界的受控域内做 E1-B**，E1-A 作为对照。

### 3. 结果是否依赖地址域有界？

**是，强依赖**。EXP-DORAM-08-R1 地址域审计结论：地址为 BLS12-377 253-bit 域元素、上游无范围约束门（VERIFIED）；示例程序限界=INFERRED；实验 workload 限界=CONSTRUCTED；**目标系统全域有界=UNKNOWN**。E1-B 的"唯一槽位"与 E1 的"固定 n 槽"都建立在"所有有效地址∈[0,n−1]"之上。若目标系统地址可超出该域，影子表方案（A 和 B）都不成立。必须写明：**影子表目前只适用于有界地址域工作负载模型，不能宣称可直接替代原始 VDORAM 的任意域地址语义。**

### 4. 是否值得进入最小 MPC 微基准？

**有条件值得**：仅批准"严格限定有界域下的最小化原语权重微基准"，目的是验证唯一仍主导的不确定性——`c_eq=389`（秘密求逆 p−2 的 386 次 Beaver 是否如源码所推）以及 `SelectCompose`/条件更新的实际原语计数。**不批准**完整 E1 电路或端到端 MPC：后端缺 SPDZ MAC/auth 契约（EXP-DORAM-06），且 R1CS 约束数、批处理轮数均为 UNKNOWN，端到端结论无法可审计地得出。

### 5. 当前 VDORAM 后端是否可直接承载？

**否**。当前 C# `MpcExecutor` 是串行无 MAC 的 additive-share 执行器（L160 TODO 未并行、无 SPDZ 认证），C#→Rust R1CS JSON 路径为 `MF::from_add_shared`、无 MAC 字段（EXP-DORAM-06 VERIFIED）。直接承载 E1 需要：有界地址范围约束/外部信任、eq 跨读写复用的电路实现、以及认证随机源与 MAC 通道。**这些都不在本轮范围内，也不改变 EXP-DORAM-06 的 NO_GO 结论。**

---

## 已证实的结论（VERIFIED / DERIVED）

- `c_upd_shared=2`、`c_upd_separate=c_eq+2`（R1-1，逐层 gadget 链 VERIFIED）；
- R0 的 `c_upd=1` 漏计 `FieldNeg(old_j)` 的 1 次 Beaver（勘误）；
- E1-B 域内唯一命中、域外返回 0、无需 LowBit 的代数正确性（构造 DERIVED，前提=有界域）；
- step 0 无 Fetch（`ZkProgramExecutor.cs` L205-206 VERIFIED）→ step 0 STORE 强制 separate；
- 每 step 0 STORE 多付 `n·389`（CSV 隔离验证，与公式一致）；
- E1-A − E1B = `(T−1)(3n−2)`（构造 + CSV 双验证）；
- E0 闭式 `393·T(T−1)/2 − 2(T−1)` 与逐步求和相等（测试验证）。

## 条件成立的结论（CONSTRUCTED / ASSUMED）

- E1-B 的 `390n` / E1-A 的 `393n−2` 读取成本（gadget VERIFIED，构造 DERIVED，前提有界域）；
- eq 跨读/写复用（shared 模式）——ASSUMED，E1 非上游电路，无源码证明；
- `c_eq_e1=388` 的公开操作数优化——DERIVED 变体，未实测；
- E1 在 `T/n>2` 的理论交叉——参数化推导，非经验阈值反推。

## 未知项（UNKNOWN）

- 目标系统地址域是否有界（影子表落地前置）；
- R1CS 约束数与 `MpcCircuit→R1CS` 映射：UNKNOWN（不得用乘法数代替）；
- 批处理/并行执行下的通信轮数（当前串行 barrier 数不可外推）；
- 在线字节数（域元素编码长度未核实）；
- 是否有未取到的更省条件选择 gadget（UNKNOWN，未假设存在）；
- 位分解摊薄 n 路比较的可行性（无一手证据，不计入任何优势）。

## 阻断项

1. **后端契约**：缺 SPDZ MAC/auth（EXP-DORAM-06），无法直接承载；
2. **地址域证据**：全域有界=UNKNOWN，E1-B/E1 落地前必须解决；
3. **eq 复用**：shared 模式无电路证据，须在微基准中先验证。

## 下一阶段允许 / 明确不做

- **允许**：严格限定有界域下、E1-B 的最小化原语权重微基准（验证 `c_eq=389`、`c_upd=2`、`SelectCompose` 计数），可含 E1-A 对照。
- **明确不做**：完整 E1 电路实现、端到端 MPC、修改 VDORAM 上游/C#→Rust witness 接口、把符号模型升级为论文性能结论、自动启动 EXP-DORAM-10、位分解比较路线（无证据）。
