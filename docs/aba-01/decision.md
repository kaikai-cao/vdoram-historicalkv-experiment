# ABA-01：最终决策

## 最终结论：`PASS_STATIC_ADDRESS_PROOF`

> 四个候选：`PASS_STATIC_ADDRESS_PROOF` / `PARTIAL_STATIC_PROOF` / `BLOCKED_ADDRESS_PROOF` / `INVALID_PROGRAM_ASSUMPTION`。
> 选择 `PASS_STATIC_ADDRESS_PROOF`，并附加两个不可省略的边界：`n ≥ 1` 是**本轮显式加入的输入约束**，不是上游电路已有约束；本结论**不等于**端到端 R1CS 绑定已完成。

---

## 1. 程序级地址域是否严格推出

**是（在明确约束下）。** 在 `1 ≤ n ≤ Nmax`、`Nmax < p`、`Nmax² < p` 下，固定 commit 的 Bubble Sort 全部 6 条 Load/Store（PC 4/16/18/22/24/36）执行时地址 `R0 ∈ [0,n−1] ⊆ [0,Nmax−1] < p`。

推导链条：输入循环 PC2 置 0、PC5 +1、PC6–8 以 `R0<n` 守卫；排序内层 PC12 `R3=R2+1`、PC13–14 以 `R3<R1` 守卫、PC26 `R2=R3`、PC32 受 `R6>0` 守卫递减 R1（可证 `R1≥1`，无下溢）；输出循环 PC35 置 0、PC38 +1、PC39–41 以 `R0<R8=n` 守卫。交换分支（PC21–25）与不交换分支（跳 PC26）复用同一已守卫的 R2/R3 地址，没有新地址计算。

## 2. 现有 VDORAM 电路已有的约束

1. 所有 Field 值规范在 `[0,p−1]`，p = BLS12-377 标量域、BitSize=253（`ArithConfig.cs` L10/L13，`Field.cs` L14–L21）。
2. Load/Store 的地址线与内存 trace 地址取**执行时 R0**，不是证明者可自由指定的辅助输入（`ZkVmExecutorCircuitBoardGenerator.cs` L224–L227、L925–L1007）。
3. Add/Sub 的 mod p 语义（`Field.cs` L35–L43；电路 L534–L560）。
4. LessThan 用 253 位分解 + `BitsLessThanGadget` 做规范整数比较；JumpIfZero 用 FieldNorm + BoolNot + SelectCompose（电路 L466–L497、L660–L695）。
5. 位分解经 `AddBitDecompositionProof` 插入证明电路并把公开输出约束为 0（`CompatCircuitConverter.ToMpcCircuitAndR1csCircuit` 路径；未逐门审计内部）。

## 3. 新增构造（本轮，均未接入真实电路）

1. 明确的公开输入约束 `1 ≤ n ≤ Nmax`、`Nmax < p`、`Nmax² < p`——**当前源码没有**。
2. 逐访存点的静态地址域证书与独立结构检查器（`src/aba_01/`），由程序与 CFG 分析生成，绑定 `sha256` 程序哈希。
3. 若未来要做端到端证明，还需把上述范围约束与 `addr<n` 加入 per-step R1CS（本轮**不做**）。

## 4. 证书是否绑定真实执行

**否。** 证书绑定的是固定指令序列（程序哈希、指令数、每条 Load/Store 的 PC 与 R0 定义链）和静态推导结论；检查器独立验证 schema、哈希、范围声明与访存点覆盖，但不重跑分析器，也不读取运行时寄存器或内存 trace。因此不能声称“证书保证 VM 实际执行满足地址域”。静态分析成功 ≠ 密码学证明成功。

## 5. 边界与未解决问题

- `n = 0`：上游程序在守卫之前仍执行 `Store mem[0]` 与 `Load mem[0]`，与 `[0,n−1]=∅` 矛盾。本轮如实记录并把它作为失败输入排除；若目标系统允许 `n=0`，本决策应改判 `INVALID_PROGRAM_ASSUMPTION`。
- 位分解与 `Not` 的布尔性为 ASSUMED（`Not` 文档明言不检查输入布尔；本程序只接 LessThan 输出）。
- R6 计数无显式上界约束，依赖 `Nmax² < p` 假设。
- 未修改 HistoricalKV、未做 ORAM/MPC 设计或性能优化、未推广到 Sliding Window / Set Intersection、未开始 R1CS 电路集成。

## 6. 下一步是否值得做 R1CS 绑定原型

**条件性值得，但本轮不启动。** 只在满足以下前提后才建议开一个独立、最小范围的绑定原型：① 目标系统能给出严格有界地址域证据（否则 `n≤Nmax` 只是假设）；② 先把 `1≤n≤Nmax` 加入公开输入约束并验证；③ 明确处理 `n=0` 的程序语义问题。在此之前，优先事项仍是地址域证据、执行侧权重与后端认证接口（EXP-DORAM-06 的当前架构 `NO_GO_CURRENT_ARCHITECTURE` 不变）。

**本轮结束后立即停止**，不扩展到其他程序、不做性能评估、不进入下一轮研究。
