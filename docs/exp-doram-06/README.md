# EXP-DORAM-06：认证随机 share → SNARK witness 跨层接口审计

## 0. 固定范围

本轮只做**跨层接口可行性审计**，不实现 adapter，不修改 C# / Rust 源码，不运行 benchmark，不重新讨论 MiMC 轮数、盐长度或 ORAM 成本，不重开 D2、跨步 verifier chain、完整 selective-abort。

- 实验仓库：`kaikai-cao/vdoram-historicalkv-experiment`
- 起始 commit：`fd8ea9e47245a10d1e46589ceb37450c120e6ec1`
- 上游仓库：`BDS-SDU/vdoram-artifacts`
- 上游固定 commit：`10c90d35464620a35ddb1e2c29d2e8725acedd52`
- 本轮只新增：`docs/exp-doram-06/` 四份文档。

审计材料为固定 commit 的源码 blob；所有结论均指向具体源码结构或数据流，不以类名、论文描述或“框架一般支持”替代当前 artifact 的证据。

## 1. 唯一工程问题

> SPDZ 风格认证随机 share 能否不丢失认证信息地进入 VDORAM 的协作证明 witness 路径，并与同一份 `W_pre,i` 绑定为私有盐 `s_i`？

拆成三个必须同时成立的环节：

1. **生成**：MPC 参与方得到认证分享的 `s_i`，任何单方不能自行指定或替换；
2. **转换**：认证分享安全地转换成协作 SNARK witness 表示，转换过程中不丢失 MAC 保护；
3. **绑定**：电路实际使用的 `s_i` 与生成的认证分享对应，并进入同一个承诺约束：
   `com_i = H(Encode(ictx_i || W_pre,i) || s_i)`。

协议上可构造与当前 artifact 可接入分开判断；接口断裂处直接记为断点，不靠增加抽象步骤假装打通。

## 2. 三句话结论

1. **存在真实 C# → Rust witness 数据流**：C# 把 `R1csCircuitWithValues` 序列化为 `*.party{k}.r1cs.json`，Rust 读取 `wire_values` 并逐 wire 转成协作域元素。
2. **该数据流只传 value share + `is_secret_share` 标志，不传 MAC / MAC key share / 认证引用；Rust CompatCircuit 证明路径被静态绑定到 additive share，而不是 SPDZ authenticated share。**
3. 因此答案不是“只缺一个 adapter”，而是**当前 artifact 的 C# 与 Rust witness 认证契约需要重做**；本轮最终决策为 **`NO_GO_CURRENT_ARCHITECTURE`**。该判定只针对当前路线，不声称 SPDZ + collaborative SNARK 理论上不可构造。

## 3. 交付导航

- `csharp-witness-path.md`：C# witness 产生路径，回答 secret wire 实际输出、additive/MAC、独立通道、session/Dispose 影响。
- `rust-authenticated-share-path.md`：Rust 协作证明输入路径，回答 JSON 如何进入 witness、`SpdzFieldShare` 来源、preprocessing、debug/cheat、序列化接口。
- `decision.md`：C1/C2/C3 候选方案、最小形式化绑定关系、五项保证的当前架构判定、最终决策与关键断点。

## 4. 判定口径

- `GO_TO_ADAPTER_SPEC`：五条件全满足——真实 C#→Rust witness 流、可用认证 share 生成路径、不公开重构的跨层传递、MAC 验证与电路 witness 绑定、无 debug-only/作弊依赖。
- `HOLD_INTERFACE_GAP`：协议可构造，但当前 artifact 缺少数据通道或认证转换。
- `NO_GO_CURRENT_ARCHITECTURE`：当前架构下必须改变证明执行契约；继续沿原路线增加复杂度不划算。

本轮选择第三项，理由见 `decision.md`。最重要断点是：**R1CS JSON witness 契约与 Rust 输入类型只定义 additive value share，MAC 信息在表示层没有位置，因而不存在 adapter 可以“保真转发”的认证对象。**

## 5. 停止标准回答

> 是只缺一个 adapter，还是实际上需要重做 C# 与 Rust 之间的 witness 认证契约？

**需要重做 witness 认证契约。** 具体要改的不是单一 JSON 字段，而是一整条执行契约：`MpcValue` 表示、MPC 运算的 MAC 维护、`R1csCircuitWithValues` 序列化 schema、Rust witness 输入类型、SPDZ 预处理/随机源、MAC 检查时机、以及电路 wire 与认证对象的安全绑定。
