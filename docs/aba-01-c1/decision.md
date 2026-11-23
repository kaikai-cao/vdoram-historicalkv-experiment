# ABA-01-C1：最终决策

## 决策

**`PASS_STATIC_CERTIFICATE_RULES`**

## 判定依据（六项全部满足）

1. **原始固定程序 PASS**：`BUBBLE_SORT` 在 `1≤n≤Nmax=16`、`Nmax²<p` 下分析器 `PASS`，独立检查器 `verify_certificate(..., require_pass=True).ok=True`；6 条 Load/Store 全部 `R-INPUT`/`R-INNER`/`R-OUTPUT` 规则通过。
2. **M1–M10 均不能错误通过**：10 类关键状态/控制流变异全部 `UNKNOWN` 或 `FAIL`，证书不可能返回 PASS；尤其 M1（`Set R2,p−1`，域回绕使守卫失效）被专门断言为 `UNKNOWN`，伪造 PASS 也被检查器拒绝。
3. **证书篡改全部拒绝**：13 项结构化字段/绑定字段篡改与文本伪造测试全部被独立检查器拒绝，包括 `address_def_pc`、`address_source_register`、`guard_pc`、`loop_head`、`proof_rule`、区间、PC、bound register、source path、program hash、instruction count、field prime，以及“只改文本不改关系”的伪造。
4. **独立检查器不调用分析器**：mock `analyze()` 抛异常后 `verify_certificate()` 仍独立完成检查；规则从绑定程序指令与数据流推导，不信任证书文本。
5. **全部测试通过**：原有 22 项 + 新增 26 项 = `tests.test_aba_01` 48 项；全仓库 `unittest discover` 198 项；`git diff --check` 干净。
6. **文档与指令数一致**：`cfg.py` 注释与 `docs/aba-01/{source_semantics,certificate_format,validation}.md` 统一为 43 条指令、PC 0–42；证书样例与新 schema/analyzer version 一致。

## 必要边界声明

- 本结论只针对**固定 Bubble Sort** 与本轮定义的**有限证明规则**；分析器/检查器不是通用静态分析器或形式化验证器。
- **静态证书规则验证成功，不代表证书绑定了真实 VM 执行，更不代表端到端 R1CS 证明已完成。** 检查器不读取运行时寄存器/内存 trace，不把 `1≤n≤Nmax` 写成电路输入约束，也不证明 MPC/协同 SNARK 安全性。
- `n=0` 仍属程序语义缺陷（守卫在首次访存之后）；本轮继续把 `n≥1` 作为显式外部输入约束，未声称电路已强制。
- ABA-01 原结论 `PASS_STATIC_ADDRESS_PROOF` 保持；C1 只是把“人工推导 + 原型分析器”推进到“有限规则下可独立检查的结构化静态证书”，不自动启动 R1CS 绑定原型。

## 未解决问题

- 目标系统地址域是否严格有界、执行侧权重、后端 SPDZ MAC/auth 接口仍未解决；EXP-DORAM-06 的 `NO_GO_CURRENT_ARCHITECTURE` 不变。
- LessThan 的 253 位分解仅标 `ASSUMED`，未逐门审计；`bool_not` 仅由 LessThan 输入约束保证。
- 尚未把 `n` 范围约束与 `addr<n` 加入每步 R1CS 执行关系；是否值得做 R1CS 绑定原型需取得地址域证据后再决定。

按任务停止条件：本轮到此停止，不启动 R1CS 绑定原型、不推广其他程序、不改 HistoricalKV、不启动 MPC 微基准。
