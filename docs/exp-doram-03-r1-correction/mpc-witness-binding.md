# mpc-witness-binding.md — 任务 D：秘密路径绑定与 MPC–SNARK witness 绑定

> 2026-11-23 · 起点 `b1bfe29` · 本轮最重要文档。
> 标记：**VERIFIED** 固定源码/论文直接证据 · **CONSTRUCTED** 显式约束规则 · **INFERRED** 推导 · **CONDITIONAL_CONSTRUCTION** 依赖未实例化接口 · **BLOCKED** 无法证明。
> 硬规则：**不把“同源 witness”当作密码学绑定；若不能证明 MPC 输出 shares 与 SNARK witness shares 一致，就保留 BLOCKED。**

---

## D1. 秘密 leaf 与 Merkle 路径绑定（显式 R1CS）

### D1.1 变量与约定

- 访问叶子 `[ℓ]`，位分解 `ℓ = Σ_{k=0}^{L−1} 2^k b_k`，`b_k∈{0,1}`（`BIT(L)`，`µ=L`）。
- 路径从根 depth 0 到叶 depth L；第 t 层方向位 `d_t = b_{L−1−t}`（若采用 MSB-first 路径索引；实现固定一种约定即可）。
- 第 t 层左右子 hash 为 `h_{t+1}^{L}, h_{t+1}^{R}`；兄弟 hash 由方向位选择：

```
sib_t = d_t · h_{t+1}^{R} + (1−d_t) · h_{t+1}^{L}
child_t = d_t · h_{t+1}^{L} + (1−d_t) · h_{t+1}^{R}
```

这里每个字段选择 1 个 `FieldMul`，共 `2` µ/层；`d_t` 已是 bit，不额外校验。

### D1.2 旧根认证（展开 `Open`，不是黑箱）

对 `t = L−1 … 0`：

```
h_t^{old} − H(child_{t+1}^{old}, sib_t) = 0
h_0^{old} − C_i^{Tree} = 0
h_L^{old} − H(slots^{old}_{bucket(ℓ)}) = 0
```

其中 `slots^{old}_{bucket(ℓ)}` 是被访问 bucket 的 4Z 个字段 witness；`bucket(ℓ)=ℓ` 由路径方向位唯一确定。该 bucket 的索引必须满足：

```
Σ_{t=1}^{L} 2^{L−t} d_t − ℓ = 0
```

### D1.3 新根更新与 siblings 复用

```
h_L^{new} − H(slots^{new}_{bucket(ℓ)}) = 0
h_t^{new} − H(child_{t+1}^{new}, sib_t) = 0     // 同一个 sib_t
h_0^{new} − C_{i+1}^{Tree} = 0
```

**同一个 `sib_t` 变量同时出现在旧/新路径**，这是“未触碰节点未改变”的可检查约束；若 prover 为新旧路径提供不同 sibling，则可通过另一个状态替换攻击。

### D1.4 递归 leaf 一致性

对递归层 j，令 `off_{j−1}=b_{j−1} mod χ`，从 pos-map block 中读出：

```
ℓ_{j−1} = Σ_{r=1}^{χ} Eq(off_{j−1}, r) · block_j[r]
```

写入新值：

```
block_j'[r] = Eq(off_{j−1}, r)·ℓ'_{j−1} + (1−Eq(off_{j−1}, r))·block_j[r]
```

R1CS 必须使用**同一个** `ℓ_{j−1}` 变量作为：①本层 pos-map 读出的值；②下一层 Merkle 路径的 leaf；③eviction 的前缀比较基准。禁止用“另一个副本”表示同一 leaf。

### D1.5 被修改 bucket 与状态转换一致

- `slots^{new}_{bucket(ℓ)}` 必须等于 eviction/writeback 输出的 Z 个 slot；
- 每个 slot 的 4 个字段 `(addr,val,leaf,valid)` 逐项线性等于 eviction 选择结果；
- `valid` 为 bit；dummy slot 字段规范为 0。

若任一等式缺失，恶意 prover 可证明一个“路径合法但写入内容任意”的转换。

### D1.6 D1 判定

**CONSTRUCTED（约束层）**：上述规则把 leaf bit、路径方向、sibling 选择、旧认证、新更新、递归 leaf、bucket 内容全部显式化，不依赖 `Open()` 黑箱。
**未闭合**：它只证明“给定 witness 的路径关系正确”，不证明 witness 来自真实 MPC 执行；这是 D2。

---

## D2. 真实 MPC 执行与 witness 绑定

### D2.1 四个必须区分的对象

| 对象 | 含义 | 当前 artifact 证据 |
| --- | --- | --- |
| MPC 实际读写 | 在 ORAM 电路中执行的 path read/stash/eviction | **ORAM 电路不存在**，UNKNOWN |
| MPC 输出 shares | `[S_{i+1}]`, `[result]`，由外层执行器持有并跨步 | registers 模式 VERIFIED；ORAM 状态 INFERRED（R1 核查） |
| SNARK witness shares | 协作证明消费的 wire values 分片 | R1CS 从 ValueBoard 生成并落盘 VERIFIED；外部 prove 消费方式 UNKNOWN |
| 下一步状态 shares | 下一步 `AddPrivate("in_state")` 的份额 | 机制可复用 INFERRED；ORAM 专用输入线未实现 |

### D2.2 完整流程草案（CONDITIONAL_CONSTRUCTION / BLOCKED）

```
输入：外层持有认证状态份额 ⟨S_i⟩；公开 C_i, step_i；秘密输入份额 ⟨a⟩,⟨op⟩,⟨v⟩

1. 输入认证检查
   - 对 ⟨S_i⟩ 做 SPDZ MAC/open 检查，确认未被替换；
   - 打开 C_i，与 verifier 上一步接受值比较（公开检查）。
   输出：认证通过的状态份额；公开 C_i。

2. 单一 MPC session 内执行 ORAM 转换
   - 电路同时产生主输出 ⟨S_{i+1}⟩, ⟨result⟩ 与辅助线 ⟨aux_i⟩
     （path slots, sibling hashes, eq bits, eviction picks, nonce 随机带, 多重集输入）。
   输出：同一 ValueBoard 上的全部线值份额。

3. 根计算与公开打开
   - 在同一 session 内由这些线值计算 C_{i+1}^{Tree/Stash/Top/Meta/Hist}；
   - authenticated open 得到公开根。
   输出：公开 C_{i+1}。

4. R1CS 实例生成
   - x_i = (C_i, C_{i+1}, step_i, step_{i+1}, C_i^{Hist}, C_{i+1}^{Hist})；
   - witness 直接取第 2 步 ValueBoard 的对应线值，不重新输入份额。

5. 协作 Prove
   - Prove(pp, x_i, w_0..w_{m−1}) 在同一 session/同一份已认证线值上执行；
   - transcript 与 π_i 记录，abort 形成固定长度公开事件。

6. 输出认证与跨步携带
   - 对 ⟨S_{i+1}⟩ 做 MAC 检查；外层变量 thisState = 这批输出份额；
   - 下一步 AddPrivate("in_state", thisState)。

7. 公开 verifier
   - Verify(pp,x_i,π_i)=1；V1–V6 检查根/step/历史连续。
```

**关键一致性点**：第 4 步 witness 必须是第 2 步第 6 步的**同一批线值**。若证明阶段重新接收 shares，则流程退化为独立证明阶段，必须额外定义份额认证与承诺开启；当前没有。

### D2.3 八个必答问题

| # | 问题 | 回答 |
| --- | --- | --- |
| 1 | Keller–Scholl SPDZ 中认证计算输出如何进入 co-SNARK？ | 论文层 CompatCircuit 说“MPC 中间份额直接作为 co-SNARK witness”（VERIFIED 定义层面，VDORAM p4-5）；本 artifact 只有 R1CS+witness 落盘、外部逐电路证明（VERIFIED），ORAM 实例的输出→prove 接口不存在（BLOCKED） |
| 2 | 辅助线是否必须同一 MPC execution 产生？ | 本轮路线下**必须**；否则需要份额认证/承诺开启的独立交接，当前 UNKNOWN |
| 3 | SPDZ MAC 检查是否覆盖 proof witness 每个输入份额？ | 标准 SPDZ 对认证份额与输出开值做 MAC 检查，但“外部协作证明的每个 witness 输入都带 MAC 并被检查”**不是自动结论**；2025/789 还给出实现层 MAC key 泄露攻击（VERIFIED 其存在），故标 UNKNOWN/BLOCKED |
| 4 | 恶意方能否提交另一组合法 witness？ | 若 prove 独立接收 shares：能，除非有认证/承诺绑定；若 witness 就是同一 ValueBoard 线值且 active MPC 未中止：不能在不偏离协议的情况下替换。后者依赖接口存在 → CONDITIONAL |
| 5 | witness–公开根绑定是否足够？ | **不足够**。根绑定保证 witness 对应公开状态；执行输出认证保证该状态是 VM/下一步实际使用的状态。两者缺一不可 |
| 6 | 下一步状态 shares 是否与本步证明输出相同？ | 仅当第 4 步 witness 与第 6 步输出来自同一线值集合时可证明；当前无 ORAM 专用实现 → INFERRED/CONDITIONAL |
| 7 | proof 失败 / MPC abort / 掉线如何处理？ | 必须定义固定长度、固定轮次的公开 abort 事件，并证明 abort 不与秘密相关；当前未定义 → BLOCKED（隐私侧） |
| 8 | 是否仍支持任意方、dishonest majority、active？ | 协议理论上 Keller–Scholl/SPDZ 支持（VERIFIED）；但 compatible co-SNARK witness 接口与本 artifact 未实例化 → CONDITIONAL，不写成已具备 |

### D2.4 源码证据边界（VERIFIED）

- `MpcValue` 是 `Field Value + bool IsSecretShare` 的纯值对象，可跨 session 持有（R1 已核）；
- `ZkProgramExecutor` 用 `in_this_reg_i` / `out_reg_i` 传递寄存器份额，`in_mem_val` 绑定 Fetch 结果（L297/L302/L375-376）；
- R1CS+witness 由 `RaiseR1csCircuitWithValuesGenerated` 交给回调，回调落盘 JSON（Program.cs L106-111/L211-214）；
- `SelfVerify()` 只验单电路；外部 Rust client 逐电路手动证明；verifier 无跨电路串联（`verifier-chain-check.md` §1-4）；
- 这些证据支持“份额可跨步承载 + R1CS witness 来自同一执行 ValueBoard”，**不支持**“ORAM 输出 shares 已被密码学绑定到协作证明 witness”。

### D2.5 本轮判定

- **D1 路径约束：CONSTRUCTED**（§D1 显式 R1CS）。
- **D2 端到端绑定：BLOCKED**。缺少：①ORAM 状态 shares 的显式输入/输出线；②从同一 ValueBoard 生成 co-SNARK witness 的可执行接口；③对 proof witness 每个输入份额的 MAC/认证覆盖证明；④固定行为 abort 语义。
- 若把 CompatCircuit 论文层范式视为已实例化，则最多是 **CONDITIONAL_CONSTRUCTION**，不是 CONSTRUCTED。固定 commit 中没有该接口，因此不能进入 GO。
