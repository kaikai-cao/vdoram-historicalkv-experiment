# README — EXP-DORAM-03-R1-Correction-4

> 2026-11-23 · 起点 `6586dd28d3d7f4dce8d51815c96f4ea4be7eba9c`
> 固定 VDORAM 上游 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 范围：**只修承诺消息、承诺盲化随机数、状态更新随机带的角色混淆与接口一致性**。不扩展 ORAM、不重算成本、不写代码、不跑 benchmark、不启动原型。

---

## 1. 唯一目标

Correction-3 中 `r_i` 同时是 `W_pre,i` 内部字段与承诺 opening randomness。本轮把三个对象彻底分离：

```
W_pre,i = (old_state, new_state, path, siblings, stash, eviction_aux, nonce, r_tape,i)   // 被承诺的消息
s_i     = commitment_blinding_randomness                                               // 承诺盲化随机数
r_tape,i= 状态更新随机带（属于 W_pre,i，派生 r_t 刷新 nonce）

com_i   = Com(Encode(ictx_i ‖ W_pre,i); s_i)
rho_k   = H(domain_k ‖ ictx_i ‖ com_i ‖ transcript_context),  k = 1,2
W_post,i= (A_k,B_k)，由 (W_pre,i, rho) 唯一确定
ictx_i  = (protocol_version, program_id, circuit_id, step_i, C_i, attempt_i)
```

`s_i ∉ W_pre,i`、不进 ORAM 状态、不作 ρ 种子；`r_tape,i ∈ W_pre,i`、被 `com_i` 覆盖、不作独立 ρ 种子；`r_t` 在电路中绑定到 `nonce' = nonce + r_t`。依赖图无环。

---

## 2. 文件导航（六份）

| 文件 | 内容 |
| --- | --- |
| `witness-transcript.md` | 角色混淆撤回、三对象最终定义、依赖图、I1–I7 无环检查、`s_i`/`r_tape,i` 属性表 |
| `transcript-order.md` | 七阶段（输入/输出/可见者/可修改者/失败行为/传递信息）、五个必答问题、FS 与 grinding 角色说明 |
| `commitment-interface.md` | 层模型修正（L3 并入 L2）、三类承诺逐项核查、四条禁止推断、witness 绑定结论 |
| `randomness-lifecycle.md` | `s_i` vs `r_tape,i` 对照表、独立性/联合生成/偏置、失败作废、跨步复用、固定长度 abort 不足 |
| `decision.md` | GO 门槛逐条、最终决策、三种阻塞源定位、相对 Correction-3 的保留/修正/撤回 |

---

## 3. 主要结论

- **角色分离**：完成（CONSTRUCTED）。`W_pre,i` 8 字段不含 `s_i`；`s_i` 独立盲化；`r_tape,i` 属消息并绑定 nonce 更新。
- **七阶段 transcript**：与角色分离自洽；阶段 2 分别产生 `W_pre,i` 与 `s_i`，阶段 3 锁定 `com_i`，阶段 4 派生 ρ，阶段 6 验证打开关系与约束，阶段 7 才推进状态。
- **承诺与 witness 绑定**：电路内同线值约束在规则层成立；外部承诺桥接无接口 → BLOCKED。`Encode` 必须覆盖全部 8 字段。
- **承诺候选**：确定性 MiMC 无 hiding；随机化 MiMC 仅启发式；Pedersen 有 hiding/binding 但 `Fr` 后端不兼容且 artifact 无 gadget。**L2 BLOCKED**，本轮不强行选定。
- **随机源与 grinding**：联合生成 + MAC + 不可重采样 + `attempt_i` 作废在规则层完整；artifact 无认证随机带，执行层 BLOCKED。固定长度 abort 不足以解决选择性 abort。
- **最终决策**：**HOLD**。

---

## 4. 阻塞定位

1. **承诺构造（首要）**：无同时满足 hiding、binding、opening verification 与 `Fr` 兼容的具体 L2 候选。
2. **MPC 随机源**：`s_i`/`r_tape,i` 的认证联合生成、MAC、防重采样、失败作废无接口；直接支撑 grinding 与 nonce 隐私。
3. **SNARK witness 绑定**：规则层已写清；外部承诺路径需先选定承诺方案才能闭合。
4. 遗留：D2 同执行绑定、跨步 verifier chain、选择性 abort 均保持 BLOCKED。

---

## 5. 边界

- 不修改 Correction-3 及更早报告；不修改上游；不写代码；不跑 benchmark；不重算 Merkle/Eviction 成本；不扩展 ORAM 文献。
- 不把纸面构造标为 VERIFIED；无法从固定源码证实的接口标 BLOCKED / UNKNOWN。

---

## 6. 停止条件

六份文件完成；提交推送、核对本地/远端 SHA 与工作区 clean 后立即停止。不追加任务、不启动原型。
