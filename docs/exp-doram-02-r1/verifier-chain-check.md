# verifier-chain-check.md — EXP-DORAM-02-R1 补充：回调链与 verifier 检查核查

> 日期：2026-11-23 · 固定 commit `10c90d3`。
> 触发：研究负责人独立核查指出 R1 文档两处措辞过强——(1) "hash 承诺链同时防替换/跳步/回滚"；(2) "自动成为协作证明关系"。要求核实回调调用方与 verifier 检查逻辑，**不做原型、不做完整审计**。

## 0. 一句话结论

**研究负责人的两点收紧全部成立（VERIFIED）。** 执行器层的跨步 hash 检查是**宿主代码检查**；回调只把每电路 R1CS+witness **落盘为 JSON** 并（单方）`SelfVerify()`；协作证明是**外部 Rust 工具逐电路手动运行**；本仓库内**未发现** verifier 对跨电路公开输出做串联、步数连续性或初始/最终状态锚点检查。因此"防回滚""自动进入 collaborative SNARK"两处措辞必须收紧为"机制/接口层面可用，公开证明层保证待核实/本仓库未提供"。

## 1. 回调的实际调用方（VERIFIED）

`OnR1csCircuitWithValuesGeneratedAsync` 的两个真实赋值点均在 `CompatCircuit/CollaborativeZkVm/Program.cs`：

- **单方** L106-111：回调做两件事——
  1. `File.Open(..."{instanceName}.{name}.single.r1cs.json")` + `JsonSerializerHelper.Serialize(...)`：把电路+witness 序列化落盘；
  2. `r1cs.SelfVerify()`：本地自检。
- **多方** L211-214：回调**只做落盘**——`File.Open(...".party{MyID}.r1cs.json")` + Serialize，**连 SelfVerify 都没有**。

**即：回调 = 序列化到磁盘（+单方自检），不是"提交给协作 zkSNARK 证明器"。** 原 R1 文档"RaiseR1csCircuit... 证明入口 → 自动成为协作证明关系"的表述过强。

`MultiPartyZkVmTest.cs` L74 的赋值是 `( _, _ ) => { }`（测试里直接丢弃），进一步说明该回调语义就是"给外部消费者留的落盘钩子"。

## 2. `SelfVerify()` 检查什么（VERIFIED）

`CompatCircuitCore/CompatCircuits/R1csCircuits/R1csCircuitWithValues.cs` L22-38：

- L23-25：若任一 `WireValues` 仍是 secret share 则抛异常（只适用于已恢复秘密的调试场景）；
- L27-31：逐条验证乘法约束 `left * right == result`；
- L33-37：逐条验证加法约束 `left + right == result`。

**它只验证"单个电路的 R1CS 约束在给定 witness 下成立"**，与跨电路状态、步数、承诺链完全无关。且 `Program.cs` L390 明言 `run-fake-verify` 命令是 *"Verifying R1CS constraints by reconstructing secrets. **Only for debugging purpose.**"*——它先 `RecoverFromShares`（L443-446）把秘密重组再验证，是调试工具，**不是零知识 verifier**。

## 3. 协作证明是外部独立手动步骤（VERIFIED）

`CompatCircuit/Experiments/scripts/prove-scripts/collaborative-zksnark-mod.md`：

- L42-48：从**另一个仓库** `https://codeup.aliyun.com/.../collaborative-zksnark-mod.git` 克隆并 `cargo build --release --bin client`——证明器不在本 artifact 仓库的 C# 执行链路里；
- L50-67：`manually prove a circuit`——逐电路手动命令，`circuit_name=MemoryTraceProverCircuit-16`，各方 client 读 `*.party{ID}.r1cs.json`；
- L69-78：`prove-r1cs-multiparty.sh` / `prove-r1cs-single.sh` 脚本化同一过程。

`prove-r1cs-multiparty-inner.py`：`start_processes(party_count, r1cs_name, r1cs_path, ...)`（L33）对每个 r1cs 文件独立启动各方 client（L48-55），脚本内**无**跨电路 hash 串联、无 `previous/next/step/chain/verify` 逻辑（全文件 grep 无命中）。

`collaborative-zksnark-mod/groth16/src/verifier.rs` L27-61 是 arkworks 标准 `verify_proof(pvk, proof, public_inputs)`——只验证**单个 proof 相对该电路公开输入**的配对等式，无跨电路状态逻辑。

## 4. 逐项回答研究负责人要求的四点

| # | 要求核实的点 | 核查结果 | 标记 |
| --- | --- | --- | --- |
| 1 | `OnR1csCircuitWithValuesGeneratedAsync` 实际调用方 | `CollaborativeZkVm/Program.cs` L106-111（单方，落盘+SelfVerify）、L211-214（多方，仅落盘）；测试 L74 丢弃。回调是落盘钩子，不是证明提交。 | VERIFIED |
| 2 | verifier 对每电路公开输入/输出的检查 | 本仓库 C# 端只有 `SelfVerify()`（单电路约束+witness 自检，调试用途 `run-fake-verify`）；Rust 端 `verify_proof` 为 arkworks 标准单 proof 配对验证。 | VERIFIED |
| 3a | 跨步骤 hash 是否被验证端强制串联 | **本仓库未发现**。执行器宿主代码 L322-328/L367-371 有检查，但公开证明侧无 `previous output hash == next input hash` 的 verifier 逻辑；证明脚本逐电路独立。 | VERIFIED（本仓库范围内） |
| 3b | 初始状态锚点 / 步数连续性检查 | **本仓库未发现** verifier 侧实现。`hashThisRegisters` 初始为 0（L74）、`globalStepCounter` 递增（L116/L122）均为执行器逻辑；`Program.cs` 只打印 `GlobalStepCounter`（L125/L222），无拒绝跳步的验证端检查。 | VERIFIED（本仓库范围内） |
| 4 | 措辞修订 | 已修订 `state-carrying-feasibility.md` §0/§2/§4/§5/§6 与 `decision-revision.md`；整体 HOLD 不变。 | VERIFIED |

## 5. 边界声明

- "本仓库未发现" ≠ "VDORAM 论文声称的机制不存在"。论文层面对公开可验证性有设计描述（见 `docs/exp-doram-02/paper/EXCERPTS.md`），但**本 artifact commit 的代码**未展示跨电路 verifier 串联；外部 `collaborative-zksnark-mod` 是独立仓库（codeup.aliyun.com），其内容不在本固定 commit 的证据范围内（UNKNOWN）。
- 这不构成对"任意方公开可验证 ORAM 状态机"的 NO_GO——恰相反，它明确了需要新增哪一层约束（verifier 侧跨电路公开 IO 串联 + 步数/锚点检查），整体研究问题继续 **HOLD**。

## 6. 新增证据文件（均在 source-evidence/）

实际保留 9 个（均带 PATH/BLOB SHA 文件头）：

- `MpcValue.cs`（R1 主轮已引）、`CollaborativeZkVm/Program.cs`（回调调用方 L106-111/L211-214）、`R1csCircuitWithValues.cs`（`SelfVerify()` L22-38）、`CollaborativeZkVmTest/MultiPartyZkVmTest.cs`（测试 L74 丢弃回调）。
- `groth16/src/verifier.rs`（arkworks 标准 `verify_proof` L27-61）。
- `Experiments/scripts/prove-scripts/{collaborative-zksnark-mod.md, prove-r1cs-multiparty-inner.py, prove-r1cs-multiparty.sh, print-results-inner.py}`（外部证明桥接与逐电路脚本）。
