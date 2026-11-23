# EXP-DORAM-04 — L2 承诺构造与 SNARK 电路兼容性评估

> 2026-11-23 · 起点 commit `2556ece2fd040978ad89fd9ed61bd1bc15243947`
> 固定上游：`BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 本轮只研究承诺构造；不写代码、不跑 benchmark、不重算 ORAM 成本、不启动原型。

---

## 1. 研究问题

**能否找到一种有明确安全依据、能落地到当前 SNARK 后端、且能绑定同一份 ORAM witness 的 L2 承诺构造？**

要求把四件事分开：①理论安全 ②后端兼容 ③witness 绑定 ④随机源可执行。只有四者同时成立才值得进入最小协议原型。

---

## 2. 冻结接口（不得重定义，沿用 Correction-4）

```
ictx_i   = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)
W_pre,i  = (old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i)   // 8 字段
s_i      = commitment_blinding_randomness        // ∉ W_pre,i
com_i    = Com(Encode(ictx_i ‖ W_pre,i); s_i)
rho_k    = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context)
```

约束：`s_i ∉ W_pre`；`r_tape,i ∈ W_pre`；`com_i` 覆盖 `ictx` 与全部 8 字段；`s_i` 不公开；承诺打开与 ORAM 约束用同一份 witness；不允许重采样 `s_i` 筛选挑战；七阶段顺序不变。

---

## 3. 文件导航

| 文件 | 内容 |
| --- | --- |
| `backend-facts.md` | 当前 SNARK 曲线/域/R1CS/hash gadget/公开输入接口的证据；**纠正电路域为 BLS12-377 Fr（非 BN254）** |
| `candidate-analysis.md` | B1 Pedersen、B2 hash 承诺、B3 curve-cycle/内嵌、B4 外部+桥接的构造、原始来源、域适配与限制 |
| `security-analysis.md` | 七个安全边界问题逐项分析：binding / grinding / hiding / attempt 绑定 / C_i 绑定 / 8 字段覆盖 / 外部桥接替换空间 |
| `comparison.md` | 统一比较表、成本边界（不编造数字）、改造范围分级 |
| `decision.md` | 最终 GO/HOLD/NO_GO、最优候选、三大未解决问题、下一项最小证据任务 |

---

## 4. 主要结论

- **最终决策：HOLD**。无协议级矛盾故不 NO_GO；GO 六条件无一候选同时满足故不 GO。
- **最重要的新发现**：固定 artifact 的电路域是 **`Fr(BLS12-377)`，253 bit**——既有报告继承的“BN254、254 bit”错误。一手证据 `ArithConfig.cs` + ePrint 2022/1396 + 可复算算术。连带把 B1 soundness `2^-170 → ≈2^-168`、grinding `q_H·2^-168`。证明系统主路径为 **Plonk + BLS12-377**（不是 Groth16）。
- **结构性张力**：`Fr` 电路内不存在完全原生的群型 Pedersen——标量原生则坐标非原生，坐标原生则标量非原生（曲线不能自循环）。故 B1（安全强、后端阻塞）与 B2（原生、hiding 条件化）各有取舍。
- **B2 关键计算**：`|Y|≈2^253` 套 ePrint 2015/361 Lemma 17 的 `|Y|≤2^{ℓ_u/8}` ⇒ `s_i` 需 ≥2024 bit ≈ 8 个 `Fr` 元素才满足 ROM 统计 hiding；单域元素盐不够。
- **最优候选**：安全优先 B1（Pedersen，perfect hiding + DL binding）；工程优先 B2（`H(x‖s_i)` + 8×域元素熵，原生 MiMC，局部改造）。都不满足全部 GO 条件。

---

## 5. 与 R1 / Correction 系列的关系

- **保留**：Correction-4 的冻结接口、三随机量角色分离、七阶段顺序、`Encode` 覆盖 8 字段规则、D2/verifier chain/选择性 abort 的 BLOCKED 状态。
- **修正**：电路域（BN254→BLS12-377）、soundness 单位、证明系统（Plonk）、Pedersen 兼容性（一刀切不可用→三形态有界分析）、hash hiding（启发式→ROM Lemma 17 精确条件）。
- **撤回**：「电路域 BN254 / `|F|≈2^254`」及相关派生；「Pedersen 绝对不可行」；「`H(x‖s)` 有标准 hiding」的暗示。

---

## 6. 未解决问题（详见 decision.md §3）

1. `s_i` 的认证联合生成 + MAC + 不可重采样接口（两方案共同、最高优先）。
2. B1 电路内 opening 的非原生化（10×–600× 有界，无 gadget）与 `CRH` 定义。
3. B2 hiding 的严格归约（ROM 启发式、MiMC 裕度 UNKNOWN、`s_i` 熵长度）。

遗留 D2、跨步 verifier chain、选择性 abort 保持 BLOCKED，影响端到端但本轮未触碰。

---

## 7. 停止条件

六份文件完成并提交推送后停止；不追加原型、不新开文献调研、不重算 ORAM 成本。
