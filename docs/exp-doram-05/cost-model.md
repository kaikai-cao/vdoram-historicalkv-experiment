# cost-model.md — B2 承诺相关成本（不含 ORAM 本身）

> 2026-11-23 · 起点 `ca26127` · 冻结接口见 `README.md`。
> 标记：**VERIFIED** 固定源码直接支持 · **CONSTRUCTED** 本轮记账口径 · **INFERRED** 由源码结构推导 · **UNKNOWN** 缺确定规则 · **BLOCKED** 无接口。
> 范围：只算 `com_i = MiMCCommit(x_i, s_i)` 的承诺成本增量。**不重算** Path ORAM / Merkle / Eviction / Stash 成本（Correction-2 已冻结）。**不编造**精确总数。

---

## 0. 为什么只能给符号公式

任务输入 `x_i = Encode(ictx_i ‖ W_pre,i)` 的**具体分块规则**与 MiMC 链式 `chaining` 的**精确吸收方式**在固定 artifact 中均未定义（`Encode` 覆盖 8 字段是 CONSTRUCTED 规则 / 实现 UNKNOWN，见 correction-4、backend-facts §5）。因此按任务令，本页只给**参数化公式 + 由源码可精确读取的单点成本**，并明确哪些是符号量。

---

## 1. `Encode` 的字段顺序与分块规则（CONSTRUCTED 待定 / 具体长度 UNKNOWN）

按冻结接口，需吸收的字段共 14 个逻辑项：

```
ictx_i    (6):  protocol_version, program_id, circuit_id, step_i, C_i, attempt_i
W_pre,i   (8):  old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i
```

- **建议顺序（CONSTRUCTED，待审计）**：`domain_tag ‖ ictx_i（按上序，各 1 域元素，C_i 为 1 个 Merkle root 域元素） ‖ W_pre,i（按上序，各字段先摊平为固定长度 Fr 序列）`。
- **摊平长度符号**：
  - `L_state`：old/new state 摊平长度；`L_path`：路径 + siblings（树深 `L`）；`L_stash`：stash（容量 `R` 槽 × 每槽字段数）；`L_evict`：eviction_aux；`nonce, r_tape`：各 1 或若干域元素。
  - 记 `L_x = 6 + L_state^old + L_state^new + L_path + L_stash + L_evict + 1 + 1`（域元素数）。
- **长度前缀**：每变长字段需固定上界 + 长度标记，否则不同字段拼接可碰撞（任务要求域分离与去重）。这部分约束数计入 `Encode` 开销 `C_enc`，符号保留。
- **状态**：字段清单 CONSTRUCTED；`L_x` 具体值 **UNKNOWN**（依赖未冻结的摊位/树摊平编码）。

---

## 2. MiMC 链式哈希的输入分块（VERIFIED 结构 / 记账口径 CONSTRUCTED）

一手源码事实（`MimcHashGadget.cs` / `MimcEncryptGadget.cs`，fixed commit；correction-2 §E1、backend-facts §3 已核）：

- `MimcHashGadget`：对 `preimageCount` 个输入**逐个链式**调用 `MimcEncryptGadget`，输出 **1 个** `Fr` 元素。
- 每轮：`FieldAddGadget(3)`（线性/加法，非乘法约束）+ `FieldConstPowGadget(7)`（`x → x^7`，需 **4 次域乘法**：`x², x³=x²·x, x⁶=x³², x⁷=x⁶·x`）。
- 轮数 65 → 每个输入元素约 `65 × 4 = 260` 个乘法约束。

**记账口径（CONSTRUCTED / INFERRED，沿用 correction-2）**：

```
H(m) 处理 m 个输入域元素：   μ_H(m) ≈ 260 · m        （乘法约束；加法/线性不计入 μ）
```

- 该 `260` 来自"4 乘/轮 × 65 轮"的源码结构推导（INFERRED），**不是** artifact 实测；backend-facts 已将 `H(k)=260k` 标为 INFERRED。
- **不能**简化为"65 轮 × 4 乘法 = 完整承诺成本"：还需计入输入吸收（§1 的 `L_x` 分块）、链式调用次数、域分离 `domain_tag`、以及最终输出与公开输入的对齐（§4）。

---

## 3. `s_i` 候选长度档位与增量成本（INFERRED 公式 / 档位由 hiding 界定）

设 `s_i` 含 `k` 个 `Fr` 元素（`k = 1,2,4,8`），与 `x_i` 一同进入链式哈希。承诺输入域元素总数：

```
m = L_x + k        （+ domain_tag 等常数项，符号记 C_tag）
μ_com(k) ≈ 260 · (L_x + k + C_tag) + C_enc
```

**相对"无盐基线" `(k=0)` 的增量**（可直接从口径复算，不依赖 `L_x` 具体值）：

| `k`（Fr 元素） | 盐位数 `ℓ_s` | 增量乘法约束 `Δμ = 260·k` | 对应 hiding（见 hiding-model §3.2，q=2^128） |
| --- | --- | --- | --- |
| 1 | 253 | **+260** | `2^{-125}`（略低于 128-bit） |
| 2 | 506 | **+520** | `2^{-378}`（充分） |
| 4 | 1012 | **+1040** | 过量 |
| 8 | 2024 | **+2080** | 过量（EXP-DORAM-04 旧值量级，已撤回为"必需"） |

**关键结论**：从计算 hiding 角度，`k=2` 已足够（`Adv≤2^{-378}`），`k=8` 的额外 `1560` 约束**没有安全收益**。EXP-DORAM-04「必须扩到 8 个 Fr」不再作为成本驱动因素（该结论已撤回）。为何仍可能选更大 `k`：见 `rom-analysis.md` 的 MiMC 结构缺口与统计 hiding 边际 —— 但那不是 RO 界限推出的"必需"。

---

## 4. 哪些可精确读取、哪些只能符号估算

| 项 | 可精确？ | 依据 |
| --- | --- | --- |
| 每输入元素乘法数 `260 = 4×65` | **可**（源码结构 INFERRED） | `FieldConstPowGadget(7)` 4 乘 × 65 轮 |
| 输出为 1 个 `Fr` | **可**（VERIFIED） | `MimcHashGadget` 输出类型 |
| `Δμ = 260·k` | **可**（口径推导） | §3 |
| `L_x`（Encode 摊平长度） | **否** → 符号 | 摊平规则未冻结 |
| `C_enc`（长度前缀/域分离约束） | **否** → 符号 | 编码未定 |
| 完整 `μ_com` 总数 | **否** → 符号公式 | 依赖 `L_x, C_enc, C_tag` 未定 |
| MiMC 安全裕度对约束数的反馈 | **否** → UNKNOWN | 65 轮裕度未立（rom-analysis §2） |

---

## 5. 承诺成本之外但本轮必须点明的接口成本（不作数）

- **承诺打开验证**：若 `com_i` 在电路内重算（`com_i − H(x‖s_i)=0`），成本即 §2–3 的 `μ_com`；`com_i` 可作 `AddPublic`（VERIFIED 接口）。无额外 gadget。
- **随机源成本**（`generate_authenticated_blinding` + MAC + 台账）：属 `randomness-protocol.md`，其 MPC 通信与预处理成本 **UNKNOWN / BLOCKED**（artifact 无接口），本页不编造数字。
- **协作 SNARK witness 生成**：属 D2，BLOCKED，本轮不碰。

---

## 6. 本页最终结论

- 承诺相关的**可复算核心**是 `μ_com(k) ≈ 260·(L_x + k + C_tag) + C_enc`，其中 `260=4×65` 来自固定源码结构（INFERRED），`Δμ=260·k` 精确可复算。
- **`k=2`（+520 µ）已达 128-bit 计算 hiding**；`k=8` 多花的 1560 µ 无 RO 层面的安全收益。
- `L_x, C_enc, C_tag` 未冻结 → **不给精确总数**（任务令），只给参数化公式与所需参数清单。
- 完整承诺成本能否精确化，取决于先冻结 `Encode` 分块与 chaining 规则 —— 这是下一步可做的具体工作，不是本轮结论。
