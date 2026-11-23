# decision.md — EXP-DORAM-03-R1-Correction-2 最终决策

> 2026-11-23 · 起点 `bc6d774` · 仅就三项有限修正与固定 GO/HOLD/NO_GO 门槛作判定。
> D2（MPC–SNARK 真实接口）按任务包要求**保持 BLOCKED**，本轮未尝试解决。

---

## 0. 唯一最终决策：**HOLD**

不是 `GO_TO_MINIMAL_PROTOTYPE`，也不是 `NO_GO`。

- **不 NO_GO**：没有发现不可消除的协议矛盾；公开验证不需要公开秘密地址或 leaf；D1 左右顺序修正后路径关系闭合；eviction 逐项展开后仍是 `O(RZL·D)` 级、无每步 O(N)；成本上升属于约束补全，不是结构性不可接受。
- **不 GO**：GO 门槛中「witness commitment 具备明确 hiding 与 binding 依据」和「nonce 生命周期闭合」两条未满足；`com(W_i)` 与随机带接口在固定 artifact 中不存在；非原生 Pedersen 无实现。理论表达完整 ≠ 可进入原型。
- **注意**：任务包明确允许 D2 保持 BLOCKED，但 GO 的其余条件仍必须全部满足；本轮恰恰有两条不在 D2 范围内的条件未闭合。

---

## 1. GO 门槛逐条核对

| # | GO 条件 | 本轮状态 | 满足 |
| --- | --- | --- | --- |
| 1 | D1 路径关系完整且无方向错误 | 撤回 swapped sibling；固定 MSB-first、`d=0` 左 / `d=1` 右、`H(h^L,h^R)`；L=3 左右分支手工核对 | ✅ CONSTRUCTED |
| 2 | eviction 选择逻辑完整 | 逐位 XOR + AND 聚合、valid gating、exclusion、one-hot、sel⇒elig、dummy、4 字段选择全部展开 | ✅ CONSTRUCTED |
| 3 | R1CS 成本无已知结构性漏项 | 逐层可复算；新增 PATHSEL/ADDRBIT/RECBIT；撤回 `PREFIX(t)=t` | ✅ CONSTRUCTED/CONDITIONAL（后端倍率 UNKNOWN） |
| 4 | witness commitment 有明确 hiding 与 binding 依据 | 确定性 MiMC 只 binding；nonce+MiMC hiding 无规约；Pedersen 有定义但无实现/域不匹配 | ❌ CONDITIONAL/BLOCKED |
| 5 | B1 challenge 顺序完整 | 七步 transcript 与域分离已给出；依赖 4 的 com 接口，且选择性 abort 未解决 | ⚠️ CONDITIONAL |
| 6 | nonce 生命周期闭合 | 生成/认证随机带、防替换/重放、abort 四块未闭合 | ❌ BLOCKED |
| 7 | 无新的协议级矛盾 | 未发现 | ✅ |

**未满足：4、6；部分依赖：5。** 按门槛不得选 GO。

---

## 2. 三项修正结论

### 任务 A — Merkle 路径（`merkle-path-correction.md`）

- 旧稿 `sib_t = d_t·h^R + (1−d_t)·h^L` 在 `d=1` 走右的约定下等于 `child_t`，**撤回**。
- 新约定：`ℓ=Σ2^k b_k`（MSB-first 路径位 `d_t=b_{L−1−t}`）；`d=0` 左、`d=1` 右；sibling 数组根→叶；父节点恒 `H(h^left,h^right)`，固定顺序。
- 给出任务指定的 `(child,sibling)` 公式与等价的“单 sibling witness 重建左右输入”公式；旧/新路径共用同一 `sib`，off-path 不变是结构性的。
- `L=3` 两案例（ℓ=2 左→右→左；ℓ=5 右→左→右）手工核对通过。
- 递归 PositionMap：`χ=4 → off` 2 bit、one-hot `3χ µ`、读 `χ µ`、写 `χ µ`；同一 `ℓ_{j−1}` 绑定 pos-map 读出 / 下层路径 leaf / eviction 前缀基准。约束层 **CONSTRUCTED**。

### 任务 B — Eviction 成本（`eviction-cost-correction.md`）

- 撤回 `PREFIX(t)=t`；给出朴素 `R·L(L+2)` 与共享链 `4RL` 两种精确计数，后者为主报价。
- 每层公式：
  - `µ_evict(shared) = (9Z+3)RL + 4ZL`
  - `µ_evict(naive)  = [L+9Z+1]·RL + 4ZL`（示例十层 1,005,950 µ）
- `Z=4,R=179,L=20…2` 逐层合计：上轮 `659,615` → **shared `769,670`**、naive `1,005,950`；差值来自 AND 聚合、四个 gating、dummy 候选与 4 字段选择。
- 全电路总计 **2,635,246 µ/步**（含 C3 nonce **2,697,766 µ/步**）；上轮 `2,524,843` → +110,403。另一口径（stash 单哈希承诺）为 `6,254,446`，与上轮 `6,144,043` 同差。
- 无隐藏 O(N)：所有求和仅遍历 `R,Z,L,D`。

### 任务 C — 承诺安全模型（`commitment-security-model.md`）

- 定义完整 `W_i` 与隐藏/绑定/公开分类；区分状态根、见证承诺、随机带承诺三层。
- 三种方案：确定性 MiMC 无 hiding；nonce+MiMC 仅启发式；Pedersen-like 有 perfect hiding 但无域相容实现。统一方案只能列 **CONDITIONAL_CONSTRUCTION**。
- B1 transcript 七步完整；challenge 不可预测依赖 ROM + binding com；com hiding 缺失；选择性 abort 未被顺序解决。
- C3 nonce 生命周期：刷新/保留规则 CONSTRUCTED；生成、认证随机带、防替换/重放、abort 均为 **BLOCKED**。

---

## 3. 最小阻塞项（只留两条）

1. **承诺与随机带的可实现 hiding+binding 接口**：在固定威胁模型下，为 `com(W_i)` 与 nonce 随机带给出明确安全定义、域相容实现、认证生成方式和公开 transcript 绑定；否则 B1 挑战与 C3 nonce 都只能是条件构造。
2. **D2 端到端绑定与固定行为 abort（既有 BLOCKED，本轮未解）**：同一 MPC 执行中 ORAM 输出份额、辅助 witness 份额、公开根与协作证明输入使用同一批已认证线值；proof 失败/掉线形成与秘密无关的固定长度事件。

两条中第 1 条是本轮新增的未闭合项，第 2 条是前序遗留项。二者闭合前不启动最小原型；若证明第 1 条在固定威胁模型下不可构造，才重新评估 NO_GO。

---

## 4. 相对上一轮（Correction）的保留、修正与撤回

### 保留
- Merkle 增量方向、四状态表示、每步无 O(N)、`R≥114/179`、V1–V6、整体 HOLD；
- stash B1/B3 分析与 `ρ=H(x_i)` 撤回结论；
- D2 BLOCKED 与隐私四类泄露区分。

### 修正
- D1 方向位/左右选择/父节点顺序；
- eviction 前缀与选择计费（含 dummy 与字段选择）；
- 总成本 `2,524,843 → 2,635,246`（nonce 版 `2,587,363 → 2,697,766`）；
- 承诺模型从“C3 候选 + 顺序规则”合并为三层统一模型。

### 撤回
- 旧稿 swapped sibling 与 `H(child,sibling)` 写法；
- `PREFIX(t)=t` 及 eviction `659,615` 作为可信值；
- 任何“com(W) 天然 hiding”“加随机盐即零知识”“commit-then-challenge 已完成安全协议”的表述。

---

## 5. 停止条件

六份文件完成；提交推送后停止。不写 ORAM 电路、不跑 benchmark、不扩展文献、不启动原型。
