# design.md — EXP-DORAM-07 双结构方案设计与边界分析

> 基线：上游 `BDS-SDU/vdoram-artifacts` @ `10c90d35464620a35ddb1e2c29d2e8725acedd52`
> 实验：`kaikai-cao/vdoram-historicalkv-experiment` @ `c545ddcb9a14853811e2333b132a75f1592f8566`
> 标注：**M1** 已在参考模型验证 · **D1** 仅从算法结构推导 · **D2** 尚未在 MPC 中验证 · **D3** 尚未纳入公开证明

---

## 0. 候选方案（任务 §4）

| 方案 | 结构 | Query | Update | Export |
| --- | --- | --- | --- | --- |
| E0 | 单一 append-only 历史日志 | 逆序扫历史行，首匹配返值，未匹配返 0（O(当前历史长度)） | 仅追加历史行 | 完整 5 列历史 |
| E1 | 影子表 `Shadow[0..n-1]` + 同一份 append-only 历史日志 | 固定扫 `n` 个槽位，相等选择（O(n)） | 固定扫 `n` 个槽位，相等写（O(n)）+ 追加历史行 | 完整 5 列历史（与 E0 逐字段一致） |

E1 的两条铁律（任务 §4.2）：

1. **不使用秘密索引或字典直接查找**。参考模型的 `for j in range(n): if j == addr:` 是相等选择的明文模拟，目的是体现“固定长度全域扫描”，不是 O(1) dict 查找。
2. **历史日志与 E0 同规则追加**，不删、不合并、不覆盖；被覆盖旧值仍保留。

不变量（任务 §4.3）：每步结束后 `Shadow[a] == latest_value(HistoryLog, a)`，其中 `latest_value` 取该地址最后一条 `is_mem_write=1` 行的值，无写返 0。**该不变量每步在测试中校验（M1），不是 R1CS 约束（D3）。**

---

## 1. 正确性与隐私边界八问（任务 §8）

### Q1. 为什么 E1 的 Export 可以保持原历史日志不变？ — M1 + D1

E1 的 `add()` 与 E0 调用**同一个** `make_trace_row`，按同一规则构造 5 列行，并追加到**独立但同构**的 `history` 列表。影子表的写入是**旁路**：它不改变 trace 行的任何字段，也不增删行。因此：

- 行数、列值、顺序、哨兵（`NegOne`）规则两模型完全相同；
- 每行承诺用同一 `row_commitment` 计算；
- benchmark 中每个 cell 都以 `export_fields()` 逐字段比对，800 个原始运行全部一致（`export_ok=1`）。

上游对应：`ZkProgramExecutor.cs` L389-408 的 `AddMemoryTrace` / `AddHashMemoryTrace` 只依赖 VM 的 `out_trace_*` 输出，与是否存在影子表无关（D1）。

### Q2. 影子表错误是否可能影响最终历史证明？ — D1 / 部分 D2

- **不会直接改变历史证明的输入**：Prove 电路消费的是 5 列 trace + 承诺（源码 `MemoryTraceProveCircuitBoardGenerator.cs` L60-79），影子表不在其中。影子表发生错误但历史行正确时，历史证明仍然通过（D1）。
- **但会造成“查询结果 vs 历史最新值”不一致**：若影子表错误，`Load` 返回的 `mem_val` 可能不是 `latest_value`，而该值被写入 Load 历史行；Prove 的值完整性约束（源码 L167-193：同地址非写行的值须相等）可能因此失败。即影子表错误**间接**可能使历史证明不通过（D2：未在 MPC 中验证约束链）。
- 本轮用每步不变量检查把这类错误在参考模型中即时拦截（M1）。

### Q3. 影子表状态与历史日志的关系如何表达为状态不变量？ — M1 / D3

形式化：设 `H_t` 为前 `t` 步历史行序列，`W_t[a]` 为第 `t` 步后影子表槽位 `a` 的值，则

```
∀t, ∀a ∈ [0,n-1]:  W_t[a] = latest_write_value(H_t, a)
latest_write_value(H, a) = mem_val of last row r ∈ H with
                           r.is_mem_write = 1 ∧ r.mem_addr = a,  else 0
```

- 归纳基础：`H_0 = ∅`，`W_0[a] = 0`，成立。
- 归纳步：STORE 以同一 `(addr, value)` 同时更新 `W` 与追加写行；LOAD/NOOP 都不改 `W` 且不追加写行（NOOP 的 trace 地址是 `NegOne`），故等式保持（M1：100 组差分 + 全矩阵每步校验）。
- **这不是公开证明**：不变量目前只是 Python 断言（D3）。

### Q4. 若未来要把影子表纳入 R1CS，需要约束哪些状态转换？ — D2 / D3

需新增（仅列约束族，不实现、不声称已构造）：

1. 每步 `Shadow` 与 `History` 最新写值的相等约束（Q3 不变量逐槽位展开，O(n) 约束/步）；
2. `out_trace_mem_val`（LOAD）与 `SelectCompose(Shadow, addr)` 的相等约束；
3. STORE 的 `Shadow'` 更新约束：仅 `j=addr` 槽改变，其余保持不变（`[j==addr]` 选择）；
4. 与现有 `in_mem_val` 命名线的对接（源码 L298 `AddPrivate("in_mem_val", memVal)`）。

这些约束尚未写出电路，也未估算 R1CS 约束数（D2/D3）。本轮禁止把抽象计数器当成约束数。

### Q5. 全域扫描是否避免了秘密索引访问？ — D1 / D2

- 结构上：E1 对 `[0,n-1]` 每个槽位都执行 `j == addr` 相等判断，**访问位置不依赖 `addr` 的值**，循环上界固定为 `n`。因此不存在“按秘密值选择内存地址”的数据相关访存（D1）。
- 但参考模型用 Python `if j == address` 实现相等选择，其**执行时间仍是数据相关的**（命中槽位后才写入）。在 MPC 中该 `if` 必须替换为算术选择器 `eq · new + (1-eq) · old`，且相等判断要由秘密比较原语完成（D2）。本轮**未实现**该算术化。

### Q6. 是否仍然泄露 n、T、操作频率或公开控制流？ — D1（是）

**是，全部泄露。**

- `n` 决定扫描长度，是公开参数；
- `T` 是执行步数，公开；
- 操作类型序列（LOAD/STORE/NOOP）、调用次数（`query_count`/`update_count`/`fetch_count`）在 trace 中是公开的；
- 本轮不改变上游 trace 已公开这些字段的事实（源码 `is_mem_op`/`is_mem_write` 每行承诺，见语义审计 §1.6/1.9）。

影子表方案**不提供**对访问频率或控制流的隐藏。

### Q7. 是否有数据相关的提前退出、条件分支或内存访问？ — M1 + D1 / D2

- **E0**：有。参考模型 `for row in reversed(history): if match: return` 是**数据相关提前退出**（命中越新越快）。这是 EXP-DORAM-01 的明文高效实现，本轮忠实保留、未故意降速。注意：上游 Fetch 电路（源码 L52-63）是**全行** `FieldEqualsGadget` + `LowBitGadget`，并**无**提前退出；E0 的提前退出只是明文参考模型的捷径（D1）。
- **E1 的 Query/Update**：循环上界固定 `n`，无提前退出，槽位索引是循环变量而非秘密值（D1）。Python 层面 `if j == addr` 是数据相关分支，但在 MPC 目标实现中须改为恒定算术选择（D2，本轮未做）。
- 因此，把 E0 与 E1 的 Python 耗时直接比较，**混入了“明文早停 vs 固定全扫”的实现差异**；这是参考模型比较，不是 MPC 比较（见 decision.md 边界声明）。

### Q8. 多方执行时，相等判断和选择需要哪些 MPC 原语？ — D1 / D2

- 相等判断 `[addr == j]`：需要秘密比较/相等原语（上游有 `FieldEqualsGadget`，见 `docs/source-audit.md` §1.5，基于 `LowBit` + 位分解 + Beaver）。
- 选择：算术选择器 `[eq]·v1 + (1-[eq])·v0`；Load 输出 `SelectCompose` 类原语（上游已有 `SelectComposeGadget`）。
- 更新保持“其他槽不变”：同一选择器的写变体。
- 这些原语在上游源码层面存在（D1），但**本轮未连接、未在 MPC 中执行、未计通信轮数与乘法门数**（D2）。不能从 Python 计数推出 MPC 成本。

### Q9. 该方案是否改变 VDORAM 的参与方隐私假设？ — D2

**本轮不改变任何参与方假设；也不能声称已满足。** 上游的隐私门限、参与方数、恶意/半诚实模型由原系统决定（本轮未核查其参数，记为 D2）。影子表只是数据结构的增加；一旦要在 MPC 中执行 E1，上述 Q5/Q7/Q8 的算术化与 MAC/witness 契约问题必须重新审计——这与 EXP-DORAM-06 的结论（当前 C#/Rust witness 认证契约需重做）一致，本轮不触碰。

---

## 2. 明确不声称

- 不声称 E1 具备 obliviousness、恶意安全或公开可验证性；固定长度扫描 ≠ 完整 obliviousness（Q5/Q7）。
- 不声称 Python 字典/数组速度代表 MPC 性能；抽象计数器不是 MPC 乘法门、通信轮数或 R1CS 约束数。
- 不声称影子表已纳入 R1CS（Q3/Q4 为 D3）。
- 不修改上游源码、不接入 ORAM、不改 Rust/C# witness 契约、不碰 EXP-DORAM-01..06。
