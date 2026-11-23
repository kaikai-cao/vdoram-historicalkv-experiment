# commitment-interface.md — 承诺方案最低安全接口与 nonce/随机带生命周期

> 2026-11-23 · 起点 `ee75b79` · 仅纸面安全接口定义。
> 标记：**VERIFIED** 固定源码/可复现算术 · **CONSTRUCTED** 本轮规则 · **INFERRED** 标准结论 · **CONDITIONAL** 依赖未实例化条件 · **UNKNOWN** 证据不足 · **BLOCKED** 未闭合。
> 硬规则：Merkle root 可验证 ≠ Merkle root hiding；不能因为 root 存在就宣称 witness 承诺已具备 hiding。

---

## 1. 三层承诺必须分开

| 层 | 对象 | 要求 | 公开可见 | 当前依据 |
| --- | --- | --- | --- | --- |
| L1 状态 Merkle root | `C_i^{Tree/Pos/Stash/Meta/Hist}` | **binding**（确定状态）；不强制 hiding | 是 | MiMC 链式 hash，65 轮 SBox=7（**VERIFIED**，Correction-2 §E1） |
| L2 `W_pre,i` hiding commitment | `com_i = Com(Encode(ictx_i‖W_pre,i); r_i)` | **binding + hiding**（B1 挑战与 witness 隐私） | 仅 `com_i` | **BLOCKED**：固定 artifact 无此接口（§E2） |
| L3 随机带 / nonce 承诺 | `com(r_tape)`、bucket nonce | binding + hiding；抗替换/重放 | 仅承诺值 | **BLOCKED**：认证随机带→nonce 接口不存在 |

**不得混用**：L1 只保证“状态没被改”，不保证“看不到状态”。低熵 bucket 在确定性 root 下可被字典枚举（Correction-2 `commitment-hiding.md` §C2.1）。L2 的 hiding 不能从 L1 推出。

---

## 2. 三类承诺方案对照

设 `x = Encode(ictx_i‖W_pre,i)`，`r` 为随机量，电路为 BN254 `Fr` 上的 R1CS。

### 2.1 确定性 MiMC/hash `com = H(x)`

- **binding**：MiMC 抗碰撞假设下成立（参数 **VERIFIED**，安全裕度 **UNKNOWN**）。
- **hiding**：**无**。低熵 `x` 可被枚举比对；相同 `x` 跨步产生相同 `com` → 可关联。
- **字典攻击**：可行（若 `x` 熵低于安全参数）。
- **随机数**：无；无可保密对象。
- **域兼容**：完全兼容 `Fr`，MiMC gadget 已有（**VERIFIED**）。
- **verifier 看到**：`com` 值；若在电路内核验，则 `com` 作为公开输入，电路重算 `H(x)`。
- **跨 step 绑定**：可通过 `ictx_i` 编码前缀实现；但 binding 不代表 hiding。
- **artifact 可复用实现**：MiMC hash gadget 有；**承诺接口无**（**VERIFIED**，§E2）。
- **判定**：可用于 **L1**，**不可**用于 L2/L3（`BLOCKED`）。

### 2.2 带秘密随机性的 hash commitment `com = H(x, r_i)`

- **binding**：依赖 `r_i` 被承诺且不可替换；若 prover 自选且可重采样 `r_i`，binding 与 FS soundness 同时退化（见 `transcript-order.md` §4.6）。
- **hiding**：**启发式**。随机化 CRH 使字典攻击需同时猜 `r_i`，但从 MiMC 抗碰撞**推不出**标准 hiding 规约。Correction-2 已标 `CONDITIONAL_CONSTRUCTION`。
- **字典攻击**：成本升至约 `2^λ`（`λ = r_i` 位宽）；不是信息论 hiding。
- **随机数生成/保密**：`r_i` 必须秘密、进入 MPC 份额、进入 R1CS preimage 与位宽约束；当前 artifact 无认证随机带接口 → **BLOCKED**。
- **域兼容**：兼容 `Fr`，可用现有 MiMC。
- **verifier 看到**：仅 `com`；`r_i` 作为 witness 在电路内参与 hash 重算，不公开。
- **跨 step 绑定**：`r_i` 每步独立；`com` 输入含 `ictx_i`，可跨步区分。
- **artifact 可复用实现**：hash 有，承诺封装无（**VERIFIED**）。
- **判定**：`CONDITIONAL`，缺 hiding 规约与认证随机源，不能选为已定义方案。

### 2.3 Pedersen-like `com = g^x h^r`

- **binding**：离散对数假设下计算 binding（明确安全定义，**INFERRED** 标准结论）。
- **hiding**：`r` 均匀时 perfect/statistical hiding（明确安全定义）。
- **字典攻击**：信息论不可行。
- **随机数生成/保密**：`r` 必须域均匀且秘密；需证明其生成不可偏置、不可重采样。
- **域兼容**：**不匹配**。承诺值在 G1（坐标域 `Fq`），电路在 `Fr`；在 `Fr` 电路中验证 `g^x h^r = C` 需 `Fq` 非原生算术；改用 `Fr`-基域内曲线仍需 artifact 不存在的曲线 gadget（Correction-2 §E4 **INFERRED** / §E2 **VERIFIED**）。
- **verifier 看到**：G1 元素（2 个 `Fq` 坐标）；若承诺验证进电路，需非原生域约束。
- **跨 step 绑定**：每步独立 `r` → 不可关联；需把 `ictx_i` 编码进 `x`。
- **artifact 可复用实现**：**无**（gadget 目录 19 文件中无 Pedersen/Commitment，**VERIFIED**）。
- **判定**：安全定义最强，但**当前 artifact 无可用实现且域不匹配** → `CONDITIONAL`。

### 2.4 对照表

| 项 | 确定性 MiMC | `H(x,r_i)` | Pedersen-like |
| --- | --- | --- | --- |
| binding 依据 | CRH（裕度 UNKNOWN） | CRH + `r_i` 不可替换 | DL（明确） |
| hiding 依据 | **无** | 启发式，无规约 | perfect/statistical |
| 字典攻击抵抗 | 无 | 需同时猜 `r_i` | 信息论不可行 |
| `r` 保密要求 | — | 必须秘密 + 认证 | 必须秘密 + 认证 |
| `Fr` 域兼容 | 是 | 是 | 否（非原生 `Fq`） |
| verifier 可见 | `com` | `com`（`r` 不公开） | G1 元素 |
| 跨 step 绑定 | 靠 `ictx` 前缀 | 靠 `ictx` + 独立 `r_i` | 靠 `ictx` + 独立 `r` |
| artifact 实现 | hash 有、承诺无 | hash 有、承诺无 | 无 |
| 适用层 | **L1** | L2/L3 条件候选 | L2/L3 条件候选 |

**结论**：不存在一个在固定 artifact 上同时满足 hiding、binding、后端兼容且有现成实现的方案。L2/L3 维持 **BLOCKED**，不强行选定（**CONSTRUCTED** 判定）。

---

## 3. Nonce / 随机带生命周期表

| 阶段 | 必须明确的内容 | 本轮规则 | 状态 |
| --- | --- | --- | --- |
| 生成 | 谁生成、熵来源、是否联合生成 | `r_i`、`r_tape` 由同一 MPC 执行的认证随机带产生，不由单个 prover 本地采样 | **BLOCKED**（D2，artifact 无接口） |
| 分发 | 是否秘密分享、是否认证 | 以 `<nonce>`、`<r_i>`、`<r_tape>` 份额分发；SPDZ MAC 覆盖每个份额 | **BLOCKED**（MAC 覆盖 proof witness 输入未证） |
| 使用 | 绑定哪个 step、哪个 commitment | `r_i` 绑定 `ictx_i` 并进入 `com_i`；`r_t` 由 `r_tape` 派生并以 `step_i` 域分离 | CONSTRUCTED（规则）/ BLOCKED（生成） |
| 持久化 | 哪些 nonce 跨 step 保留 | 未触碰 bucket 保留旧 nonce；触碰 bucket 在本步刷新。全量刷新是 O(N)，禁止 | CONSTRUCTED |
| 更新 | bucket 更新后 nonce 如何处理 | `nonce' = nonce + r_t`（域内），受位宽约束；旧 nonce 开旧根，新 nonce 开新根 | CONSTRUCTED（算术）/ BLOCKED（`r_t` 来源） |
| 重放 | 如何拒绝旧 nonce 与旧 commitment | 旧 nonce 必须打开当前 `C_i`；`com_i` 输入含 `ictx_i`（step/root/version/circuit）；重放旧 proof 因锚点失配被拒 | CONDITIONAL（依赖 L1/L2 binding） |
| abort | 挑战前后退出怎么办 | 需要固定长度、固定轮次的公开 abort 事件，且与秘密无关；当前未定义 | **BLOCKED** |

### 3.1 具体攻击面逐项分析

1. **nonce 被恶意参与方替换**：若 nonce 是认证份额且旧 nonce 必须打开 `C_i`，替换会导致旧根认证失败（**CONSTRUCTED**）。但“证明 witness 的每个输入份额都被 MAC 覆盖”在 artifact 中未证（**BLOCKED**），所以只能算条件防御。
2. **同一个 nonce 用于不同 witness**：nonce 是 `W_pre,i` 的一部分并进入 `com_i`（`ictx_i` 前缀）；同一 nonce 配不同 witness 会产生不同 `com_i`，但 prover 若能自由选 nonce 仍可筛选；防筛选依赖认证随机源（**BLOCKED**）。
3. **同一个 commitment 用于不同 step**：`com_i` 的输入编码含 `step_i`、`C_i`、版本与电路 ID；跨步重用会与 verifier 重算的 `ictx` 不符（**CONSTRUCTED**）。若实现省略 `ictx` 前缀，则此项失效 → **BLOCKED**。
4. **参与方看到 challenge 后选择性 abort**：`commit-then-challenge` 顺序**不能**消除此泄露。它只保证没有假证明被接受；中止本身仍可编码“这个 witness 对我不利”。需要固定行为 abort 规则；当前 **BLOCKED**。不得把“有 abort 流程”写成“选择性 abort 已消除”。
5. **多次提交筛选有利 challenge**：等价于 grinding，`q_H·ε` 降低有效 soundness（见 `transcript-order.md` §4.6）。需要 `r_i`/`r_tape` 不可由单方重采样（**BLOCKED**）或增加挑战数（**CONDITIONAL**）。

### 3.2 固定行为 abort 的最低要求（未实现）

- 中止事件必须固定长度、固定轮次、固定公开字段；
- 中止不得携带 witness、nonce、挑战函数的中间值；
- 中止后状态锚点保持不变，下一步从同一 `C_i` 重新实例绑定；
- 上述规则与 MPC 认证随机带、co-SNARK 证明流程的接口需要在同一执行中定义；当前 artifact 不具备（**BLOCKED**，D2）。

---

## 4. 交付判定

| 接口 | 状态 |
| --- | --- |
| L1 状态 Merkle root | VERIFIED（MiMC 参数）+ INFERRED（成本），可用于 binding |
| L2 `com(W_pre,i)` hiding+binding | **BLOCKED**（无同时满足 hiding/binding/后端兼容的已定义方案） |
| L3 随机带 / nonce 承诺与认证生成 | **BLOCKED** |
| 跨步 nonce 保留 / 刷新算术 | CONSTRUCTED |
| 防替换 / 防重放 | CONDITIONAL（依赖 L1/L2 binding 与认证份额） |
| 选择性 abort / grinding | **BLOCKED / UNKNOWN** |

**不因本轮把任何一项升级为 VERIFIED。** 承诺接口的最低安全要求尚未在固定 artifact 上闭合；这是进入最小协议原型前必须解决的阻塞项之一。
