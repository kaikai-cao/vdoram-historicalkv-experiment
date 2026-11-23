# B. Rust 协作证明输入路径审计

证据均来自 `BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52` 的固定源码 blob。行号为该 blob 行号。

## B.1 入口与类型绑定

### 1. CLI 入口

`collaborative-zksnark-mod/mpc-snarks/src/client.rs:201-209`：

```rust
Computation::PlonkCompatCircuitMultiParty => {
    plonk::mpc_prove_and_verify_compat_circuit(compat_circuit_r1cs_json_path);
}
```

`client.rs:941-945` 在 CompatCircuit 域下取第一个 `args` 作为 JSON 路径，然后调用上述函数。

`--spdz` 分支在 `client.rs:912-940`，只把命令行 `u64` 转成 `malicious_majority::MpcField::<Fr>::from_add_shared(...)` 并用于 Field/Group 计算。若 computation 是 `PlonkCompatCircuitMultiParty`，其 domain 是 `BlsPairingCompatCircuitMultiParty`（`:144-146`），进入 `opt.spdz` 分支后会落到 `d => panic!("Bad domain: ...")`（`:939`）。

**结论：当前 CLI 不能用 `--spdz` 跑 CompatCircuit JSON 证明路径。**

### 2. JSON 读取与 witness 转换

`collaborative-zksnark-mod/mpc-snarks/src/plonk.rs:97-110`：

```rust
struct WireValue {
    value: String,
    is_secret_share: bool,
}
struct CompatCircuitR1csJson {
    wire_values: Vec<WireValue>,
    wire_count: u32,
    public_wire_count: u32,
    product_constraints: Vec<String>,
    sum_constraints: Vec<String>,
}
```

`plonk.rs:261-267` 用 `serde_json::from_str` 读取。JSON schema 没有 MAC 字段。

`plonk.rs:203-218` 是关键转换：

```rust
let values: Vec<MF> = self.wire_values.iter().map(|wire_value| {
    if wire_value.is_secret_share {
        MF::from_add_shared(wire_value.value.parse().unwrap())
    } else {
        MF::from_public(wire_value.value.parse().unwrap())
    }
}).collect();
```

其中 `MF = MpcField<F>`（`plonk.rs:19`），而 `plonk.rs:5` 导入的是 `mpc_algebra::honest_but_curious::*`。

`collaborative-zksnark-mod/mpc-algebra/src/lib.rs:14-20`：

```rust
pub mod honest_but_curious {
    pub type MpcField<F> = field::MpcField<F, AdditiveFieldShare<F>>;
    ...
}
```

因此 Rust 端把 C# 的 secret wire **直接理解为 additive share**，然后进入 `MpcPlonk::prove`（`plonk.rs:293-315`）。

### 3. Additive share 无 MAC

`collaborative-zksnark-mod/mpc-algebra/src/share/add.rs:34-37`：

```rust
pub struct AdditiveFieldShare<T> {
    pub val: T,
}
```

`add.rs:82-98` 的 `reveal()` 是广播求和，`from_add_shared(f)` 直接 `Self { val: f }`。没有 MAC 或 MAC 检查。

## B.2 `SpdzFieldShare` 的真实状态

### 1. 类型存在

`collaborative-zksnark-mod/mpc-algebra/src/share/spdz.rs:49-53`：

```rust
pub struct SpdzFieldShare<T> {
    sh: AdditiveFieldShare<T>,
    mac: AdditiveFieldShare<T>,
}
```

`mpc-algebra/src/lib.rs:31-45` 定义 `malicious_majority::MpcField<F> = field::MpcField<F, SpdzFieldShare<F>>`，也有 `SpdzPairingShare<E>`。

区分三层事实：

| 层次 | 当前状态 |
|---|---|
| 代码中存在类型 | 是：`SpdzFieldShare`、`SpdzPairingShare`、`malicious_majority::MpcField` 均存在。 |
| 类型有可调用生成/运算路径 | 部分有：`from_add_shared`、`from_public`、`UniformRand::rand`、`king_share` 以及 `Reveal`/`FieldShare` 运算存在，但认证生成依赖 `mac()` cheat 路径。 |
| 类型实际进入当前 VDORAM / CompatCircuit 证明路径 | 否：`plonk.rs` 静态使用 `honest_but_curious::MpcField`，即 additive share。 |

### 2. MAC 来自哪里

`spdz.rs:39-47`：

```rust
/// A huge cheat. Useful for importing shares.
pub fn mac<F: Field>() -> F {
    if can_cheat() {
        F::one()
    } else {
        panic!("Attempted to grab the MAC secret while cheating was not allowed")
    }
}
```

`spdz.rs:119-143`：

- `reveal()`：广播 `sh.val` 得到 `x`，计算 `dx_t = mac_share::<F>() * x - mac.val`，`atomic_broadcast` 后断言和为 0；
- `from_public(f)`：`mac = f * mac_share::<F>()`，其中 `mac_share` 是 king 持 1、其他持 0 的 additive share；
- `from_add_shared(f)`：`mac = f * mac::<F>()`，即抓取全局 MAC 秘密。

`collaborative-zksnark-mod/mpc-algebra/src/channel.rs:86, 128-144`：

```rust
const ALLOW_CHEATING: Cell<bool> = Cell::new(true);
pub fn can_cheat() -> bool { ALLOW_CHEATING.get() }
pub fn without_cheating<O, F: FnOnce() -> O>(f: F) -> O { ... }
```

所以：

- `mac()` 是明确的 cheat/import 捷径；
- `ALLOW_CHEATING` 默认 `true`；
- `proof.rs` 的部分 benchmark 用 `channel::without_cheating` 包住证明（`proof.rs:131-138, 197-204, 287-297`），但 `plonk.rs:293-315` 的 CompatCircuit JSON 证明**没有**这样的包装；
- 即便包装，当前 CompatCircuit 路径也不使用 SPDZ 类型。

`UniformRand::rand` 对 `SpdzFieldShare` 调用 `Self::from_add_shared(T::rand(rng))`（`spdz.rs:110-113`），因此也经过 `mac()` cheat 路径。`king_share`/`king_share_batch`（`:144-162`）由 king 生成加法份额后同样调用 `from_add_shared`。

**未发现** SPDZ `F_PREP.Rand` 式联合随机源：没有参与方共同生成隐藏 MAC key、输出 `[r]` 与 `[α·r]` 并附一次性 ID 的真实预处理协议。

### 3. 序列化接口不可用

`spdz.rs:67-109` 对 `SpdzFieldShare` 的 `ToBytes`、`FromBytes`、`CanonicalSerialize`、`CanonicalSerializeWithFlags`、`CanonicalDeserialize`、`CanonicalDeserializeWithFlags` 全部是 `unimplemented!()`。`SpdzGroupShare` 同样在 `spdz.rs:328-370` 全部 `unimplemented!()`。

因此即使想新增 JSON 字段传输 `sh + mac`，也没有现成的 canonical 序列化接口；且 `sh`、`mac` 字段为私有（`spdz.rs:50-53`），外部 adapter 不能从任意份额构造 `SpdzFieldShare`，只能走 `from_add_shared` cheat 或 `from_public`。

## B.3 Beaver / preprocessing 数据

 CompatCircuit JSON 证明路径没有加载 preprocessing 文件的接口。`client.rs` 的 CompatCircuit 分支只接收 JSON path（`client.rs:941-945`）。

Rust `MpcField` 的乘法与求逆调用 `DummyFieldTripleSource`（`mpc-algebra/src/wire/field.rs:34-77, 107-134, 154-180`），该 source 返回固定的 `(1,1,1)` 加法三元组，而不是真实 Beaver triple 文件。该实现可用于特定 benchmark 结构，但不能作为“协作证明已具备安全预处理/认证随机通道”的证据。

C# 前端确实有 `fieldBeaverFile`、`boolBeaverFile`、`edaBits`、`daBitPrioPlus` 等预处理入口（`CollaborativeZkVm/Program.cs:136-180`），但这些数据服务 C# MPC 执行；Rust CompatCircuit 证明客户端没有对应输入，也没有把 C# Beaver 状态转成 SPDZ preprocessing 的路径。

## B.4 公开输入、私有输入与 witness share 边界

- JSON `wire_values` 覆盖所有 wire；`is_secret_share` 是逐 wire 标志。
- 对 `i < public_wire_count` 的 wire，`plonk.rs:148-152` 要求 `is_secret_share == false`，否则 panic；这些值解析为明文 `F` 并放入 `public` map。
- 对 secret wire，`plonk.rs:213` 把本地 field 字符串直接变成 `MF::from_add_shared(...)`，即加法 share。
- `PlonkCircuit` 的 `values` 是 `Vec<MF>`（`plonk.rs:220-230`），因此 witness share 与公开 wire 共用同一个 values 向量，靠 `is_secret_share`/wire 范围区分。
- 证明结束时 `mpc_pf.reveal()` 公开 proof（`plonk.rs:311-314`），没有针对 witness 的 MAC 检查阶段。

## B.5 八个必答问题

| 问题 | 回答 |
|---|---|
| Rust 端是否直接消费 C# 输出的 additive shares？ | 是。`plonk.rs:203-218` 将 `value + is_secret_share=true` 映射为 `MF::from_add_shared(...)`，而 `MF` 是 additive `MpcField`。 |
| 如果使用 `SpdzFieldShare`，MAC 部分从何处生成？ | 当前代码只有 `mac_share()`（公开常量分享）和 `mac()` cheat。外部导入走 `from_add_shared(f)`，其 MAC 为 `f * mac()`，依赖 `can_cheat()` 默认开启。没有真实联合 MAC key/随机源。 |
| 是否存在把已有 additive shares 安全转换成 authenticated shares 的真实协议？ | 未发现。`from_add_shared` 不是安全转换；它抓取全局 MAC 秘密。`run-fake-r1cs-reshare` 会公开重构，且是 debug-only。 |
| 是否需要公开重构秘密？ | C# additive → Rust additive 不需要；但当前 artifact 中 additive → SPDZ 的可用导入路径依赖 cheat 全局 α，不是公开重构也不是安全转换。debug reshare 路径确会公开重构，但禁止依赖。 |
| 是否存在仅在调试或 `can_cheat()` 模式下可用的导入捷径？ | 是。`mac()` 明确标注 “huge cheat. Useful for importing shares”；`ALLOW_CHEATING` 默认 true；`without_cheating` 未用于 CompatCircuit JSON 证明；C# 还有 `run-fake-*`。 |
| `SpdzFieldShare` 的序列化接口是否真实可用？ | 否。所有 `ToBytes`/`FromBytes`/Canonical 系列均 `unimplemented!()`。 |
| Rust 证明阶段是否消费外部 Beaver/preprocessing？ | CompatCircuit JSON 客户端没有该输入；`MpcField` 使用 `DummyFieldTripleSource` 常量三元组。 |
| 三类事实是否区分？ | 是：类型存在 ≠ 生成路径安全可用 ≠ 进入当前 VDORAM 证明路径。第三项明确为否。 |

## B.6 Rust 侧结论

Rust 侧存在 SPDZ 类型和 benchmark，但当前 VDORAM/CompatCircuit JSON 证明路径是 additive-only。MAC 信息既不在输入 schema 中，也不在 witness 类型的静态选择中；SPDZ 的外部导入还依赖 cheat 全局 MAC。因此“Rust 后端有 SPDZ share 类型”不能推导为“VDORAM 已能把认证随机数送入 SNARK witness”。
