# ABA-03 验证记录

## 1. 基线

| 项 | 值 | 结果 |
| --- | --- | --- |
| 分支 | `main` | 符合 |
| 起始 HEAD | `06535962fdecd62534bc0bea1bccfc50b05ebce6` | 精确吻合 |
| 起始 `origin/main` | `06535962fdecd62534bc0bea1bccfc50b05ebce6` | 与 HEAD 一致，工作区 clean |
| 上游 artifact | `BDS-SDU/vdoram-artifacts@10c90d35464620a35ddb1e2c29d2e8725acedd52` | 本轮只读引用，未下载/修改 |

Phase 0 未触发停止条件；未执行 stash / reset / rebase / 覆盖操作。

## 2. 证据来源与行号口径

- 无头原始 blob：`D:/tmp/aba01/src/*.cs`，行号即原始行号。
- 带头快照：`D:/Research/vdoram-historicalkv-experiment/docs/source-snapshot/*.cs`，头部 4 行（`SOURCE` / `PATH` / `BLOB SHA` / 空行）；`MemoryTraceProveCircuitBoardGenerator.cs` 的原始行号 = 快照行号 − 4。
- 实验侧静态证书材料：`src/aba_01/cfg.py`、`docs/aba-01/certificate_format.md` 等，本轮只读。
- 本轮**没有**重新下载上游源码；本地 `D:/tmp/aba01/` 无 `.git`，commit 归属无法在本轮独立重验，已在 `source_trace_audit.md` 标 `BLOCKED`。

## 3. 交叉核验的源码抽样

以下位置由主会话直接读取，与三份并行只读审计结论一致：

| 文件（原始行号） | 核验内容 |
| --- | --- |
| `ZkVmExecutorCircuitBoardGenerator.cs:215-249` | `inMemValWire` 私有输入；`inMemAddrWire = inRegisterWires[0]`（`:227`）；opcode 表私有输入与逐行哈希注释（`:247-248`） |
| `ZkVmExecutorCircuitBoardGenerator.cs:920-1024` | `out_mem_val/out_mem_addr`（`:929-961`）、`out_trace_*`（`:968-1007`）、公开 `out_hash_mem_trace`（`:1009-1018`） |
| `ZkProgramExecutor.cs:195-239` | step0 跳过 Fetch（`:201-203`）；`AddPrivate("in_mem_addr", thisRegisters[0])`（`:225-226`） |
| `ZkProgramExecutor.cs:140-194` | `opcode_table_*` 整表 `AddPublic`（`:147-157`）；哈希连续性外部检查（`:170-181`） |
| `ZkProgramExecutor.cs:338-357` | `out_mem_addr` 被读取后未使用；`:348` 注释称“Load 时 reg0、否则 0”，与电路实际（Store 时 reg0、否则 NegOne，`:941-961`）不一致。本轮以电路代码为准，视该注释为过期 |
| `InstructionFetchCircuitBoardGenerator.cs:120-169` | opcode 表公开输入（`:126-156`）、PC 逐行选择（`:158-169`） |
| `BubbleSortProgramGenerator.cs:10-79` | 43 条指令、6 个访存 PC、R15/R1/R0/R8 初始化、示例 n=5、步数阈值 |
| `MemoryTraceProveCircuitBoardGenerator.cs`（快照 `L1-18` / `L58-85` / `L158-219`） | 4 行抓取头；逐行 trace 哈希公开输出；原始 `L164-165` 忽略 `is_mem_op` 的注释；原始 `L205-212` 公开 `out_is_satisfied` |
| `Field.cs:1-35` | `Field` 只校验 `0≤value<p`，无整数序 |
| `src/aba_01/cfg.py:1-60` | 固定 commit、路径、`p` 十六进制、253 bit、canonical JSON / sha256 |
| `docs/aba-01/certificate_format.md:1-40` | 静态证书边界声明与字段表，明确未接入 R1CS/运行时 trace |

## 4. 三份并行审计的一致性

- VM 指令/地址审计、Fetch/trace 审计、程序/证书审计均独立确认：`reg0` 是唯一地址源；dummy 地址为 `p−1`；step0 无 Fetch；Prove 电路不接收 pc/opcode；静态证书与运行时解耦；上游无整程序承诺。
- 分歧：无实质分歧。仅 `ZkProgramExecutor.cs:348` 的过期注释与电路行为不同，已按电路代码处理。
- 所有审计均为只读，未修改任何文件。

## 5. 范围与自检命令

撰写完六份授权文档后执行：

```text
git status --short        -> ?? docs/aba-03/
git diff --name-only      -> 无输出（六份均为未跟踪新文件）
git diff --check          -> 无输出（clean）
ls docs/aba-03            -> 六个 .md 文件
```

范围核验：除 `docs/aba-03/` 六个新增文件外，没有任何既有文件被修改；没有新增脚本、测试、CSV、数据、电路代码或分支。

## 6. 测试

**未运行代码测试。** 本轮没有代码改动，任务明确禁止新增脚本/测试与运行代码测试。

## 7. 结论对应

- `source_trace_audit.md`：Phase A 源码事实与证据标签。
- `constraint_spec.md`：Phase B 变量、字段/整数语义、no-wrap、B1/B2/B3。
- `trace_binding_analysis.md`：Phase C 两种方案、比较、最小候选与 HOLD 理由。
- `attack_cases.md`：Phase D 十个反例，均标为未实际执行。
- `decision.md`：Phase F 最终决策 `HOLD` 与解除条件。

提交与推送结果以最终汇报为准；本文件不声称任何已执行但尚未核验的同步状态。
