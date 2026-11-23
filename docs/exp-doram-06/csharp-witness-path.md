# A. C# witness 产生路径审计

证据均来自 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52` 的固定源码 blob。行号为该 blob 行号。

## A.1 调用链结论

真实调用链为：

```text
IMpcExecutor.Compute(...)
  -> MpcExecutor.Compute(...)
  -> CircuitExecuteResult.ValueBoard : List<MpcValue?>
  -> CircuitBoardExecutorWrapperBase.GetR1csCircuitWithValues()
  -> R1csCircuitWithValues.WireValues : IReadOnlyList<MpcValue>
  -> ZkProgramExecutor.OnR1csCircuitWithValuesGeneratedAsync(name, r1cs)
  -> JsonSerializerHelper.Serialize(stream, r1cs, ...)
  -> *.party{MyID}.r1cs.json
```

链路闭合，且没有旁路认证通道。

## A.2 逐步证据

### 1. `IMpcExecutor.Compute`

`CompatCircuit/CompatCircuitCore/Computation/IMpcExecutor.cs:6-7`：

```csharp
Task<CircuitExecuteResult> Compute(
    MpcCircuit mpcCircuit,
    IReadOnlyDictionary<int, Field> publicInputValueDict,
    IReadOnlyDictionary<int, MpcValue> privateInputValueShareDict);
```

私有输入类型已经是 `MpcValue`，因此要看 `MpcValue` 到底携带什么。

### 2. `MpcValue`

`CompatCircuit/CompatCircuitCore/MultiPartyComputationPrimitives/MpcValue.cs:5-16`：

```csharp
public record MpcValue {
    public required Field Value { get; init; }
    public required bool IsSecretShare { get; init; }
    ...
    public Field AssumeNonShare() => this.IsSecretShare ? throw ... : this.Value;
}
```

`MpcValue` 只有两个字段：

- `Value`：一个域元素；
- `IsSecretShare`：是否是秘密分享值。

**没有** MAC share、MAC key share、`randomness_id`、`attempt_i`、承诺实例 ID、所有者或认证引用。`AssumeNonShare()` 只是类型断言，不是认证检查。

### 3. `MpcExecutor.Compute`

`MpcExecutor.cs:403-502` 的 share 输入版本：

- 初始化 `valueBoard` 时，公开输入/常量写为 `IsSecretShare=false`（`:453-461`）；
- 私有输入必须是 `IsSecretShare=true`，否则抛错（`:463-469`）；
- 计算结束后返回 `CircuitExecuteResult { ValueBoard = this.valueBoard }`（`:502`）。

`MpcExecutor.cs:514-648` 的明文输入版本会调用 `FieldSecretSharing.MakeShares` 生成分享（`:579-596`），再通过 `MpcSharedStorage` 发送 share（`:598-627`）。

`CompatCircuit/CompatCircuitCore/MultiPartyComputationPrimitives/SecretSharing/FieldSecretSharing.cs:5-25` 明确是全阈值加法秘密分享：

```csharp
// Full threshold secret sharing
for (int i = 0; i < partyCount - 1; i++) {
    Field rand = this.FieldFactory.Random();
    value -= rand;
    shares.Add(rand);
}
shares.Add(value);
```

没有 SPDZ 风格的 `γ = α·x` MAC share。公开/重构路径 `ExposeFieldValues` 通过广播 share 后 `RecoverFromShares` 得到明文（`MpcExecutor.cs:690-730`），也没有 MAC 检查。

因此：C# MPC 在线阶段维护的是**未认证加法 share**。

### 4. `CircuitExecuteResult.ValueBoard`

`CompatCircuit/CompatCircuitCore/Computation/CircuitExecuteResult.cs:6-24`：

```csharp
public required List<MpcValue?> ValueBoard { get; init; }
```

`PublicOutputs` 只检查 wire 不是 secret share，否则报错；没有任何 MAC 相关字段或验证。

### 5. R1CS witness 构造

`CompatCircuit/CompatCircuitProgramming/CircuitElements/CircuitBoardExecutorWrapperBase.cs:24-25`：

```csharp
public R1csCircuitWithValues GetR1csCircuitWithValues() =>
    this.ExecuteResult is null
        ? throw ...
        : R1csCircuitWithValues.FromR1csCircuit(this.R1csCircuit, wireValues: this.ExecuteResult!.ValueBoard);
```

`CompatCircuit/CompatCircuitCore/CompatCircuits/R1csCircuits/R1csCircuitWithValues.cs:5-20`：

```csharp
public required IReadOnlyList<MpcValue> WireValues { get; init; }
...
if (this.WireValues.Any(value => value.IsSecretShare)) {
    throw new InvalidOperationException("This method is only possible when all values are not secret shares.");
}
```

`SelfVerify()` 只能验证“全部为明文值”的本地 R1CS 满足性；它不能在 share 模式运行，更不会验证 MAC。

### 6. `ZkProgramExecutor` 与 JSON 序列化

`CompatCircuit/CollaborativeZkVm/ZkPrograms/ZkProgramExecutor.cs` 在多处调用 `RaiseR1csCircuitWithValuesGenerated`：

- 指令取指电路：`:186-187`
- zkVM 每步执行电路：`:410-411`
- 最终 MemoryTraceProver 电路：`:585-586`
- 等待所有序列化任务完成：`:593-594`

`CompatCircuit/CollaborativeZkVm/Program.cs:202-211` 的 `run-mpc-zkvm` 回调：

```csharp
OnR1csCircuitWithValuesGeneratedAsync = (string name, R1csCircuitWithValues r1cs) => {
    using Stream stream = File.Open(
        Path.Combine(outputFolder.FullName,
            $"{instanceName}.{name}.party{mpcConfig.MyID}.r1cs.json"),
        FileMode.Create, FileAccess.Write);
    JsonSerializerHelper.Serialize(stream, r1cs, JsonConfig.JsonSerializerOptions);
}
```

单方路径同样只写 `*.single.r1cs.json`（`Program.cs:97-108`）。

固定仓库中的示例 `collaborative-zksnark-mod/mpc-snarks/CompatCircuit-examples/demo.party0.r1cs.json` 显示 wire 条目形态为：

```json
{ "value": "...", "is_secret_share": false }
```

没有 MAC 字段。

## A.3 六个必答问题

| 问题 | 回答 |
|---|---|
| 每个 secret wire 实际输出什么？ | `MpcValue { Field Value, bool IsSecretShare }`。`Value` 是该参与方的加法 share；`IsSecretShare=true` 表示它是 share 而非明文。 |
| 是否包含 additive share？ | 是。`MpcExecutor` 用全阈值加法分享与 Beaver 乘法；`Value` 是本地加法份额。 |
| 是否包含 MAC share？ | 否。`MpcValue` 无 MAC 字段，C# MPC 也没有 `γ=α·x` 维护逻辑。 |
| 是否包含 MAC key share 或认证引用？ | 否。无 `α` share、无 `randomness_id`、无 `commitment_instance`、无 circuit wire 绑定 ID。 |
| 是否存在独立于 JSON 的认证信息通道？ | 未发现。`run-mpc-zkvm` 的唯一输出动作是把 `R1csCircuitWithValues` 序列化到 JSON；网络层 `MpcSharedStorage` 只传加法 share、公开值/输入 share 和 online/completed 标志。 |
| `MpcSharedStorage.Dispose()` / session 切换是否影响这些数据？ | `MpcSharedStorage.cs:34-51` 只注销 session 并清空内部 `partyOnline`、`partyCompleted`、`exposedBoolShareVectors`、`exposedBigIntegerShareVectors`。已经写入 `MpcValue`/JSON 的加法 share 不受影响；但这些数据本来就不含 MAC，故不存在“认证信息被 Dispose 丢失”的问题——认证信息从未产生。 |

## A.4 额外发现：debug reshare 路径不能充当安全转换

`Program.cs:255-379` 的 `run-fake-r1cs-reshare` 会读取各方 R1CS JSON，`RecoverFromShares` 重构秘密，再 `MakeShares` 重新分享；命令描述明确为 “Only for debugging purpose”。

`Program.cs:382-478` 的 `run-fake-verify` 同样先重构秘密再 `SelfVerify()`。

这两条路径证明当前 artifact 的 JSON witness 是纯加法 share；它们**不能**作为“不公开重构的认证 share 转换”证据，且被任务包明确禁止作为方案依赖。

## A.5 C# 侧结论

C# 侧能够产生并保存真实 witness share，但对象是**未认证加法 share**。从 `MpcValue` 到 `R1csCircuitWithValues.WireValues` 再到 JSON，表示层始终只有 `(Field, bool)`。因此 SPDZ 认证随机 share 若在 C# 前端生成，必须先改变 C# witness 表示和 MPC 运算维护规则；这不是仅修改序列化格式即可解决。
