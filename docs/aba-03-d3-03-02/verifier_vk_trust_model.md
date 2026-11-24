# ABA-03-D3-03-02 / Phase 3：Verifier 与 VK Trust Model 审计

> 实验仓起点：`62ec3827bc89fb495daf68735ab93d1ea0b1e7c0`；固定上游 `10c90d35…`。
>
> 性质：审计现有证明验证路径并设计候选 verifier 模型；不实现 verifier / VK 分发 / 电路，不解除 HOLD。
>
> 标签：`VERIFIED` / `CONSTRUCTED` / `INFERRED` / `UNKNOWN` / `BLOCKED` / `CONDITIONAL INFERENCE`。
>
> 证据来源：`../aba-03-c2/verifier_interface_audit.md` §A1–A8、§4；`../aba-03-d3-01/verifier_independence.md` §1/§3；`../aba-03-d1/leakage_and_security.md` D6（勘误 C1）；`trust_boundary_inventory.md` §0。

---

## 0. 当前固定实现的 verifier 状态（`VERIFIED`）

| 事项 | 证据 | 标签 |
| --- | --- | --- |
| 同一函数内 setup→prove→reveal→verify | `plonk.rs:293-315` | `VERIFIED` |
| VK 由 `test_rng()` 现场生成 | `plonk.rs:302-304` | `VERIFIED` |
| public inputs 全部来自 prover JSON | `plonk.rs:97-110,143-161,203-247` | `VERIFIED` |
| `verify_proof(pvk, proof, public_inputs)` 只做长度 + pairing 等式 | `verifier.rs:27-61` | `VERIFIED` |
| 固定 commit 无独立 verifier / verify-only 主体 | `client.rs:36-65`（Computation 枚举全为 prove-and-verify）；`proof.rs` verify 仅在 `#[cfg(test)]` | `VERIFIED`（限固定 commit） |
| 外部部署是否存在独立 verifier / 固定 VK / 可信分发 | 现有证据未覆盖 | `UNKNOWN` |
| 接受 prover 自提 VK 且无可信锚定 → 可能 setup 重选 | 两前提同时成立的推论，非已执行攻击 | `CONDITIONAL INFERENCE` |

**边界声明（不得违反）**：现场 setup 是源码事实 ≠ 外部固定 VK 能力已被证实不支持；public input 通道存在 ≠ verifier 已检查；标准 `verify_proof` 存在 ≠ 独立 verifier 主体存在。VK 状态沿用 D1-C1 分级（本轮不改）。

**本轮核心判断（`VERIFIED` + `INFERRED`）**：当前所谓"验证"发生在 prover 进程内部，用 prover 生成的 VK、prover 提供的 public inputs 检查 prover 自己的 proof 是否自洽。因此**当前没有 verifier-trusted 的任何东西**——既没有可信 VK，也没有可信 statement。任何"verifier 检查"目前都是 prover 自测。

---

## 1. Model A：Verifier 固定 VK 与 statement

| 问题 | 回答 | 标签 |
| --- | --- | --- |
| VK 由谁生成和分发？ | 候选：由可信 setup/ceremony 生成，经可信通道分发给 verifier 并固定；prover 不得现场生成。当前无此机制（现场 `test_rng()`） | `CONSTRUCTED`；现状 `VERIFIED` 缺失 |
| verifier 如何知道 VK 对应预期 circuit？ | 需 VK↔circuit↔program 的绑定关系（`vk_id` 或注册表）；单有 VK 不能保证它对应预期程序 | `CONSTRUCTED` |
| prover 能否自行替换 VK？ | 若 verifier 预固定 VK 且不从 prover 取，则不能；此为 Model A 的定义性前提。当前路径 prover 侧生成 VK，故当前"能"（现场生成） | `CONSTRUCTED`（目标）/ `VERIFIED`（现状相反） |
| public input 是否由 verifier 或调用方固定？ | Model A 要求：至少预期 opcode table、public input、`final_step` 有 verifier 期望值；否则固定 VK 只保证"验的是固定电路"，不保证 statement 符合应用预期 | `CONSTRUCTED` |
| 是否存在 setup/VK 替换问题？ | 若 VK 真正预固定，则排除 prover 重选 setup 的路径；这是 Model A 相对当前路径的核心收益 | `INFERRED` |

**Model A 最小接口（`CONSTRUCTED`）**：独立 verifier 主体 + 固定 VK（`vk_id`）+ verifier 固定预期 statement（opcode table P1-A-1、public input、execution_id、`final_step`）。仍需 program↔VK 绑定、execution 锚点；这些不是 Model A 自动提供。

---

## 2. Model B：Verifier 固定 VK，但部分 statement 由 prover 提供

| 问题 | 回答 | 标签 |
| --- | --- | --- |
| 哪些字段可以由 prover 声明？ | 原则上：不影响"语义归属"的辅助值可声明；但 program identity、execution_id、T 属于语义归属字段（见下） | `CONSTRUCTED` |
| 哪些字段必须 verifier 重新取得/校验？ | `program_id`/opcode table、`execution_id`、`final_step`、public input——这些决定"验的是什么"，必须由 verifier 固定或可信取得（`execution_anchor_statement.md` §2） | `INFERRED` |
| program / execution_id / T 是否允许 prover 单独决定？ | **不允许**（否则 prover 可自选程序语义、声称任意执行身份、截断 T）；若允许，则回到 self-declared 问题 | `INFERRED` |
| 是否出现"proof 对自选 statement 有效但不满足应用预期"？ | **是**：`verify_proof` 只验证 proof 相对给定 public inputs 自洽。若 prover 提供 statement，proof 可对其自洽通过，而该 statement 不是 verifier/应用想要的——这是 Model B 的核心风险 | `INFERRED`（基于 `verifier.rs:27-61`） |

**Model B 判定（`INFERRED`）**：仅固定 VK 而不固定 statement，只解决"用哪把密钥验"，不解决"验的是不是预期请求"。因此 Model B **不足以**单独构成可信 verifier；必须向 Model A 的"statement 也由 verifier 固定/校验"收敛。

---

## 3. Model C：Verifier 通过可信注册表取得 VK 与 program identity

| 问题 | 回答 | 标签 |
| --- | --- | --- |
| 注册表信任根是什么？ | 候选：一个可信维护的 `(program_id, circuit_digest, vk_id, vk)` 映射；信任根是注册表的写入授权与分发完整性 | `CONSTRUCTED` |
| 谁能更新 VK/program 映射？ | 必须限定为可信治理主体；若 prover 能更新，则等价于 Model C 退化到"接受 prover 自提 VK"→ `CONDITIONAL INFERENCE` 风险回归 | `INFERRED` |
| 是否需要版本号/撤销/升级规则？ | 需要：`protocol_version`（域分离）、程序升级对应新 VK、`vk_id` 版本化；否则旧 VK/proof 可在升级后重放 | `CONSTRUCTED` |
| 注册表本身是否成为新信任假设？ | **是**：注册表是可信第三方，是新增信任根；它不消除信任，只把信任从 prover 转移到注册表治理方 | `INFERRED` |

**Model C 最小信任假设**：注册表写入权仅可信治理方持有；verifier 经可信通道读取并记录 `(program_id→vk)`；prover 无法影响映射。这**改变了当前信任模型**（当前无注册表），属于新增信任根。

---

## 4. 三种模型对照

| 模型 | VK 来源 | statement 来源 | 是否需新信任根 | 能否抵抗 prover 替换 program/T/execution_id | 当前证据 | 标签 |
| --- | --- | --- | --- | --- | --- | --- |
| A 固定 VK + 固定 statement | verifier 预固定 | verifier 固定/校验 | 需固定 VK 分发（可视为配置，非第三方） | 能（前提：statement 字段齐全） | 未实现 | `CONSTRUCTED` |
| B 固定 VK + prover statement | verifier 预固定 | prover 提供 | 同上 | **不能**（statement 自报） | 部分接近现状但 VK 也非固定 | `INFERRED` |
| C 可信注册表 | 注册表 | 注册表 + verifier 固定 | **是**（注册表治理方） | 能（前提：写入权受控） | 未实现 | `CONSTRUCTED` |

**不要求设计完整 PKI/部署系统**（任务边界）；上表只给最小信任假设。

---

## 5. VK 与 program identity 的绑定关系

- **VK identity ≠ program identity**：固定 VK 只保证验证的是某一固定电路（R1CS/PLONK 结构），不保证该电路对应预期 opcode table/program。当前 `plonk.rs:293-315` 的 VK 由 `test_rng()` 生成，与任何程序身份都无绑定（`VERIFIED`）。
- **需显式绑定**：`(vk_id ↔ program_id/circuit_digest)` 映射必须由 verifier 固定或注册表维护；否则 prover 可换一套电路+VK 形成另一套自洽证明（前提性推论：`CONDITIONAL INFERENCE`，非已执行攻击）。
- **与 P1-A 的分工**：P1-A-1（逐项比 opcode table）解决"程序语义"，VK 固定解决"用哪把密钥验"，两者是**并列且都必须**的 verifier 侧前置，不可互相替代（`verifier_independence.md` §0/§4）。

---

## 6. 最小独立 verifier 必要接口（`CONSTRUCTED`）

1. **输入**：proof、public inputs、固定 VK（或经注册表取得）、verifier 固定/可信取得的 statement 期望值（opcode table、public input、execution_id、`final_step`）、`vk_id`/`program_id`。
2. **检查**：① VK 是否本次预期（比对固定/注册值）；② public inputs 中 opcode table/public input 是否等于期望值；③ execution_id 是否为本请求 verifier 生成值；④ `final_step` 是否等于可信 T 或受约束推导；⑤ `verify_proof(vk, proof, public_inputs)`。
3. **不做**：不接收 prover 现场生成的 VK 作为可信 VK；不把 prover 提供的 opcode table 当成已验证期望值；不把 host 哈希检查当作 proof 检查。
4. **仍缺（本轮不解决）**：statement 完整（B4）、地址同一性（P2）、承诺层、R5–R8 电路约束——这些不在 verifier 接口层能单独闭合。

---

## 7. 本阶段结论

- 当前固定实现的 verifier 状态：无独立主体、VK 现场生成、public inputs 来自 prover、只做自洽验证（`VERIFIED`）。
- 三种模型中：**Model A（固定 VK + 固定 statement）是最小可行方向**；Model B（只固定 VK）不足以抵抗 statement 自报；Model C（可信注册表）可行但新增信任根。
- 无论哪种模型，都必须补齐 VK↔program 绑定和 verifier 固定 statement；这些是**改变信任模型**的工作，不是复用现有接口。
- 关键判据复核：若 verifier 最终仍从 prover 取得 VK 或 statement，则结论是**阻断**，而非接口可行。当前现状即如此 → 支撑 `decision.md` 的 `BLOCKED_BY_TRUST_MODEL` 判断。
