# verifier-chain.md — 任务 E：公开 Verifier 跨步串联

> 2026-11-23 · 起点 `b88f3db` · 纯设计规则。
> 硬边界：**宿主层 hash 检查 ≠ verifier enforcement**；**比较 hash ≠ 自动解决所有问题**。沿用 `../exp-doram-02-r1/verifier-chain-check.md` 的 VERIFIED 结论：本 artifact 的回调只落盘、证明外部逐电路手动、verifier 无跨电路公开 IO 串联/步数/锚点检查。
> 标记：**VERIFIED** 既有源码核查 · **CONSTRUCTED** 本轮规则 · **INFERRED** 推导 · **UNKNOWN/BLOCKED** 未闭合。

---

## E0. Verifier 可见/不可见

可见（公开实例）：每一步的

```
x_i = ( C_i, C_{i+1}, step_i, step_{i+1}, C_i^{Hist}, C_{i+1}^{Hist},
        C_i^{result?}, π_i )
```

其中 `C_i` 是四元组 `(Tree_0..d roots, Stash_0..d roots, Top root, Meta root)` 的拼接；`step_i` 公开；result 内容默认秘密，只消费承诺。

不可见：地址、叶子、路径、stash occupancy、overflow flag、MPC transcript、witness shares。这些由协作 SNARK 的 t-zero-knowledge 保护，不由 root 自己保护。

---

## E1. 检查规则（CONSTRUCTED）

```
V0  初始锚点:
    C_0 == H(Encode(S_empty)) 的逐层展开:
      所有 bucket slot invalid=0、addr=val=leaf=0；所有 stash invalid=0；
      pos_d 全 0；Meta.step=0；C_0^{Hist}=H(empty)。
    // C_0 必须可公开复现，不由 prover 自由提供。

V1  相邻根串联:
    for i in 1..T:  C_i^{in of R_i} == C_i^{out of R_{i−1}}
    // 四元组逐项相等；任何一项不等则拒绝。

V2  步数连续:
    step_{i+1} = step_i + 1，且 step_0=0
    // 防跳步；只用局部 proof 无法推出全局连续性。

V3  历史日志串联:
    C_i^{Hist,in} == C_i^{Hist,out of previous}
    // 与 ORAM 根链平行的一条 append-only 链；两条链用同一 step_i 绑定。

V4  逐证明:
    Verify(pp, x_i, π_i) == 1
    // 仅证明单步 R_i 成立；不替代 V1–V3/V5。

V5  最终锚点:
    若终态公开: C_T == C_final（公开声明）；
    否则验证公开输出承诺 C_T^{result} 与程序终止声明一致。
    // 只验证单步 proof 不能保证走到正确终态。

V6  层内一致性（由 R_i 内部保证，verifier 不单独重算）:
    C1.1/C1.2/C1.6 的 Open + sibling 相等；C1.3–C1.5 的转换合法。
    // verifier 不检查“为什么”，只检查 proof；合法性在 R_i 内。
```

---

## E2. 四类正确性必须分开（不得混写）

| 层次 | 由谁保证 | 失败情形 |
| --- | --- | --- |
| **单步 R1CS 正确** | V4 + `r1cs-constraints.md` 九族约束 | 某步非法转换却通过 proof |
| **多步 proof chain 正确** | V1+V2+V3+V5 | 单步都对但换了状态/跳步/回滚/分叉 |
| **VM trace 与 ORAM state 一致** | C1.7：`in_mem_val = result`；C1.8：trace row 由同一 `[a],[op],[result]` 派生 | ORAM 算对了但 VM 用了别的值 |
| **历史记录与真实 Fetch 一致** | C1.8 + V3；dummy Fetch 也 append 一行 | 少记/多记 dummy、把物理 leaf 写进 trace |

**关键区分**：V1 的根相等只证明“下一步输入承诺 = 上一步输出承诺”；它**不证明** `S_{i+1}` 是合法转换结果，后者必须由 V4 中的 R_i 约束证明。反之，V4 的单步证明也不保证跨步连续。

---

## E3. 防跳步 / 重放 / 回滚 / 分叉 / 状态替换

| 攻击 | 本设计中的拦截点 | 剩余条件 |
| --- | --- | --- |
| 跳步 | V2 `step+1`；R1CS C1.9 | prover 不能把公开 step 改成别的 |
| 重放旧 proof | 公开输入含 `step_i` 与 `C_i`；V1/V2 不匹配 | 若同一 `(C_i,C_{i+1},step)` 在不同上下文重复，仍需外部唯一性 |
| 回滚到旧根 | V1 必须与上一步输出根相等；V5 终态锚点 | 若 verifier 无状态、接受多条独立链，需公开公告板决定哪条是主链 |
| 分叉（同一步两个 `C_{i+1}`） | 单条链只能匹配一个终态锚点 V5；但**局部验证不自动禁止**两条链同时存在 | 需 append-only 公开日志/共识层；本轮不声称已解决 |
| 状态替换 | V1 + C1.1/C1.6 打开到公开根；恶意 witness 无法同时匹配 | 依赖哈希抗碰撞与 SNARK knowledge soundness |
| VM 值替换 | C1.7 `in_mem_val=result`；C1.8 trace 同源 | 若公开输出含明文 result，隐私受额外影响（见隐私矩阵） |

**诚实声明**：仅“比较 hash”只能防最朴素的替换/跳接；回滚、分叉与“哪条链被接受”属于公开验证系统的**状态/日志层**问题，不是单 proof 的数学性质。

---

## E4. 当前 artifact 状态与新增要求

- **VERIFIED（既有核查）**：`hashThisRegisters` 初始 0、每步宿主层比较/滚动（`ZkProgramExecutor.cs` L74/L322-328/L367-371）；回调落盘（`Program.cs` L106-111/L211-214）；`SelfVerify()` 是单电路调试自检；外部 Rust `verify_proof` 是 arkworks 单 proof 验证；prove 脚本逐电路无串联逻辑。
- **本轮新增要求（CONSTRUCTED，未实现）**：V0–V5 必须成为**公开 verifier 的输入检查逻辑**，而不是执行器宿主代码；每条 proof 的实例必须显式包含相邻根与 step；历史日志承诺必须并行串联。
- **工程判定：BLOCKED**。原因不是协议矛盾，而是固定 artifact 没有这层 verifier；外部 `collaborative-zksnark-mod` 验证端是否已有同类检查 UNKNOWN（不在固定 commit 证据内）。

---

## E5. 与 D 部分绑定的接口

```
MPC 转换输出 [S_{i+1}] ──┬─► 打开 C_{i+1} ──► V1（下一步输入根）
                          ├─► 协作 SNARK witness shares ──► V4
                          └─► 下一步 AddPrivate("in_state", shares)
                                      ▲
                                      └── V1 保证这批 shares 对应 C_{i+1}
```

若缺少 V1，D1 的“同执行 witness”仍只证明单步合法，无法阻止把合法 proof 接到错误的下一步输入上；若缺少 D1，V1 只证明根连续，无法证明状态转换合法。**两者缺一不可**。
