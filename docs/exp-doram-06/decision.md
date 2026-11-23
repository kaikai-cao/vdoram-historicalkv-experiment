# C/D/E. 跨层绑定方案与最终决策

## 0. 唯一最终决策：`NO_GO_CURRENT_ARCHITECTURE`

本轮判定：

```text
NO_GO_CURRENT_ARCHITECTURE
```

含义只限于当前 artifact 路线：**要让 SPDZ 认证随机 share 成为 VDORAM 协作证明中的私有盐 `s_i`，必须重做 C# 与 Rust 之间的 witness 认证契约，而不是只补一个 adapter。**

这不等于证明“SPDZ authenticated share + collaborative SNARK witness”在协议层不可构造；本轮没有发现理论不可能性。NO-GO 的对象是当前 C# 前端 / Rust 后端 / JSON witness 表示这一具体架构。

## 1. GO_TO_ADAPTER_SPEC 五条件核验

| 条件 | 当前结果 | 依据 |
|---|---|---|
| 1. 找到真实 C# → Rust witness 数据流 | 满足 | `R1csCircuitWithValues` → JSON → `to_plonk_circuit_multi_party()`，见 `csharp-witness-path.md` / `rust-authenticated-share-path.md`。 |
| 2. 找到可用的认证 share 生成路径 | 不满足 | C# 无 MAC；Rust SPDZ `from_add_shared` 依赖 `mac()` cheat，无 `F_PREP.Rand`。 |
| 3. 找到不公开重构的跨层传递方案 | 不满足 | JSON 无 MAC 字段；`run-fake-r1cs-reshare` 会重构且 debug-only；SPDZ 序列化未实现。 |
| 4. 找到 MAC 验证与电路 witness 绑定方案 | 不满足 | Rust CompatCircuit 路径使用 additive `MpcField`；无 witness MAC check；无 `random_id`/wire 绑定。 |
| 5. 没有依赖 debug-only 或作弊接口 | 不满足 | `mac()`、`ALLOW_CHEATING=true`、`run-fake-*`。 |

因此不能进入 adapter 规格阶段。

## 2. 方案 C1：在 C# 前端生成认证随机 share

### 必要接口

- 认证随机源：`F_PREP.Rand` 或等价 SPDZ preprocessing，输出 `[s_i]` 与 `[γ_i]`，其中 `γ_i = α·s_i`；
- MAC key shares `[α_i]` 全程隐藏，单方不可取全局 α；
- 认证 witness 表示：至少含 `value_share`、`mac_share`、`random_id`、`instance_id`、`attempt_i`；
- C# MPC 运算全程维护 MAC，而不是只在输入处附加一个标签；
- JSON schema v2 能编码认证分享；Rust 端能解码成 `SpdzFieldShare` 或等价类型；
- 证明前或证明内执行 MAC check，并把 `s_i` wire 与承诺约束绑定。

### 数据流

```text
F_PREP.Rand / preprocessing
  -> C# MPC: [s_i], [γ_i] = [α·s_i]
  -> authenticated W_pre,i witness construction
  -> JSON witness shares with MAC material
  -> Rust authenticated witness input
  -> MAC verification
  -> Plonk witness wire s_i
  -> com_i = H(Encode(ictx_i || W_pre,i) || s_i)
```

### 安全假设

- MAC key α 的分享不可被证明方子集重构；
- `[s_i]` 新鲜、一次性、不可重采样；
- C# 每个 MPC 操作都正确维护 MAC；
- 参与方不能把旧 `[s_i]` 的 MAC 挂到替换后的 value share 上；
- Rust 解码与电路 wire 映射受 `instance_id` 绑定。

### 现有代码复用点

- C# `IMpcExecutor.Compute` 的多方执行框架；
- `FieldBeaverTripleShare` / `EdaBitsKaiShare` / `DaBitPrioPlusShare` 的 preprocessing 文件枚举模式；
- `ZkProgramExecutor` 的 R1CS 序列化回调；
- JSON 文件作为参与方间传输载体；
- Rust `SpdzFieldShare` 的加法/乘法/update 结构。

### 必须新增模块

- C# 认证分享类型（替换或并行于 `MpcValue`）；
- C# 认证随机源与一次性台账；
- MAC-aware 的 C# MPC 运算；
- `R1csCircuitWithValues` 认证版本；
- Rust 认证 witness schema 与解码器；
- Rust MAC check 阶段；
- wire ↔ `random_id` ↔ `instance_id` 绑定表。

### 阻断项

- `MpcValue` 无 MAC，C# 运算无 MAC 维护；
- `FieldSecretSharing` 是无认证全阈值加法分享；
- 无 C# `F_PREP.Rand`；
- JSON schema 只定义 `value + is_secret_share`；
- Rust 静态绑定 additive `MpcField`，SPDZ 不在证明路径；
- `SpdzFieldShare` 序列化未实现；
- `mac()` cheat 路径不能作为安全生成。

**判定：C1 理论可构造，但当前 artifact 需要改 C# 执行契约和 Rust 输入契约。**

## 3. 方案 C2：在 Rust 后端生成认证随机 share

### 必要接口

- Rust preprocessing 源产生 `[s_i]`、`[γ_i]`，且不使用 `mac()` cheat；
- 证明器能把 `[s_i]` 注入 `PlonkCircuit<MF>` 的指定 witness wire；
- C# 侧 `W_pre,i` 必须引用同一个认证对象，而不是自己再生成一份 `s_i`；
- 双方共享 `random_id` / `instance_id` / `wire_id` 映射，且该映射在进入证明前固定。

### 数据流

```text
Rust preprocessing: [s_i], [γ_i]
  -> authenticated witness input with stable wire_id/random_id
  -> C# W_pre,i references same binding by id (not by reconstructed value)
  -> Plonk witness wire s_i
  -> com_i constraint
```

### 安全假设

- 生成与证明属于同一认证会话；
- 跨层 ID 绑定不可被恶意参与方重映射；
- 不公开重构 `s_i`；
- C# 与 Rust 对 `W_pre,i` 的序列化/电路 wire 编号一致。

### 现有代码复用点

- `malicious_majority::MpcField<F>` 与 `SpdzFieldShare`；
- `channel::without_cheating` 的模式（但需补齐真实 preprocessing）；
- `mpc_plonk` 的 `PlonkCircuit` witness 结构；
- `atomic_broadcast` 的 MAC 检查通信原语。

### 必须新增模块

- Rust `F_PREP.Rand` / authenticated preprocessing 源；
- Rust 认证 witness 注入接口；
- C# – Rust 共享 witness ID schema；
- C# `W_pre,i` 的外部随机引用机制；
- wire 绑定校验与 MAC check。

### 阻断项

- `--spdz` 与 `PlonkCompatCircuitMultiParty` 不兼容，`client.rs:912-940`；
- `plonk.rs` 静态使用 `honest_but_curious::MpcField`，不接收 SPDZ witness；
- C# `W_pre,i` 当前只能携带本地 field share，没有“引用 Rust 外部 `[s_i]`”的机制；
- Rust SPDZ 当前生成路径依赖 cheat 或 king，不是安全联合随机；
- 序列化接口未实现。

**判定：C2 理论可构造，但当前 artifact 同样需要改证明执行契约，并额外解决跨层 ID 引用。**

## 4. 方案 C3：跨层认证 share adapter

### 必要接口

理想输入：

```text
AuthenticatedWitnessShare {
    party_id,
    instance_id,
    random_id,
    wire_id,
    is_public,
    value_share,      // 加法份额
    mac_share,        // γ share
    mac_key_share?    // 若验证方案需要显式 α share
}
```

理想输出：

```text
Rust authenticated wire value (SpdzFieldShare or equivalent)
  -> MAC verification(instance_id, random_id, wire_id)
  -> Plonk witness assignment
```

### 不允许的行为

- 不允许先 `RecoverFromShares` 公开重构 `s_i` 再重新分享；
- 不允许只传 value share 而丢弃 MAC；
- 不允许调用 `mac()` 抓取全局 MAC 秘密；
- 不允许把 `run-fake-r1cs-reshare` / `run-fake-verify` 当正式通道；
- 不允许用旧 MAC 配新 value share。

### 现有代码复用点

- JSON 文件传输；
- `serde_json` schema；
- `atomic_broadcast` / commit-and-open 通信；
- Plonk circuit wire 编号。

### 必须新增模块

- 认证 witness schema 与 canonical encoding；
- Rust 解码器与安全的 `SpdzFieldShare` 构造入口；
- MAC check 协议；
- wire / random / instance 绑定表；
- 失败即中止的错误传播。

### 阻断项

- 上游 C# 根本没有 MAC 信息，adapter 无物可转发；
- 若 adapter 自行造 MAC，只能依赖全局 α cheat，不安全；
- Rust `SpdzFieldShare` 序列化全部 `unimplemented!()`，字段私有；
- Rust CompatCircuit 证明路径类型不是 SPDZ。

**判定：C3 不是“只缺一个 adapter”。在 C# 契约未升级前，C3 会退化为 C1；在 Rust 路径未升级前，C3 没有安全落点。**

## 5. 最小形式化绑定关系

期望成立的关系：

```text
[s_i], [MAC(s_i)]
       |
       v
authenticated witness input
       |
       v
same circuit wire s_i
       |
       v
com_i = H(Encode(ictx_i || W_pre,i) || s_i)
```

其中 `Encode(ictx_i || W_pre,i)` 与 `s_i` 是两个独立输入，承诺由同一 witness 对象中的 `s_i` wire 参与计算。

### 五项保证及当前状态

| 保证 | 成立所需条件 | 当前架构状态 |
|---|---|---|
| 1. witness 中 `s_i` 与认证 share 对应 | 认证输入携带 `random_id`/`instance_id`/`wire_id`，且由生成阶段写入；电路 witness 只能从该对象取值 | **不成立**：JSON 只有 `value + is_secret_share`，无 ID 绑定 |
| 2. `s_i` 不在转换过程中公开 | 禁止 `reveal`、`open`、`AssumeNonShare`、`unwrap_as_public` 与 debug reshare | **不成立为可证明性质**：正式路径不公开，但 debug reshare 存在；SPDZ 导入依赖 cheat 全局 α |
| 3. 恶意方不能替换 value share 而保留旧 MAC | MAC key 隐藏；每次运算维护 MAC；最终 `∑(γ_t - α_t·x_t)=0` 检查 | **不成立**：C# 无 MAC；Rust 路径无 MAC check |
| 4. 电路使用的 `s_i` 与承诺生成所用 `s_i` 同一值 | 承诺 gadget 与 `W_pre,i` 编码引用同一 circuit wire；wire 映射在证明前固定并纳入实例 | **不成立**：无 wire↔random binding，C# 的 `W_pre,i` 表示与 Rust witness 表示是两条独立表示 |
| 5. MAC 检查失败时整个证明实例中止 | MAC check 在 proof 输出前完成，失败返回 typed abort 并记录 `instance_id`/`attempt_i` | **不成立**：无此阶段；`SpdzFieldShare::reveal` 的断言只在 SPDZ 类型实际使用时出现，且不在当前证明路径 |

因此当前架构无法给出上述五项保证，不能用伪代码掩盖缺失协议。

## 6. 最关键的一个断点

**C# → Rust 的 witness 契约在序列化边界处只定义 `(Field value, bool is_secret_share)`，Rust 又把它硬编码为 additive `MpcField`；MAC share / MAC key share / 认证引用没有任何表示位置或独立通道。**

这是第一断点。后续断点包括 SPDZ cheat 导入、序列化未实现、Rust 类型路径不匹配。但即使修复后续断点，只要第一断点不改，adapter 就没有可保真的认证对象可传。

## 7. 停止标准回答

当前证据支持的答案是：

```text
需要重做 C# 与 Rust 之间的 witness 认证契约。
```

不是“只缺一个 adapter”。需要同时重做：

1. C# `MpcValue` / `R1csCircuitWithValues` 的认证 witness 表示；
2. C# MPC 的 MAC 维护与认证随机源；
3. JSON witness schema；
4. Rust CompatCircuit 证明输入类型与 preprocessing；
5. MAC check 与 `wire_id`/`random_id`/`instance_id` 绑定。

本轮到此停止，不自行启动 adapter 规格阶段。

## 8. 最多三个后续问题

1. 是否接受把 C# witness 契约从 `MpcValue = (Field, bool)` 升级为认证分享结构，并同步修改 R1CS JSON schema？
2. 是否接受把 Rust CompatCircuit 证明路径从 `honest_but_curious::MpcField`（additive）切换到带真实 preprocessing 与非作弊 MAC check 的 SPDZ 路径？
3. 若前两项都不接受，是否将 B2 私有盐集成继续限定为协议层 HOLD，而不再向当前 artifact 增加工程复杂度？
