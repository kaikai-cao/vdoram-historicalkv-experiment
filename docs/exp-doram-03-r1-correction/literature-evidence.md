# literature-evidence.md — 定点文献与源码证据

> 2026-11-23 · 起点 `b1bfe29` · 只做必要定点核查，不重新开展大规模综述。
> 标记：**VERIFIED** 一手论文/固定源码直接支持 · **INFERRED** 有依据推导 · **UNKNOWN** 现有证据不能确定。
> 每条记录写明：证据位置 → 直接支持 → 不能支持。

---

## F1. VDORAM 固定 artifact（commit `10c90d3`）

| 证据 | 位置 | 直接支持 | 不能支持 |
| --- | --- | --- | --- |
| `MimcEncryptGadget.cs` | 本地快照 `../exp-doram-02/source-evidence/`，blob `8dd4c8aa…`，L16-20 | 默认 65 个轮常量、`SBox=7`；轮数=`RoundConstants.Count`（VERIFIED） | MiMC 抗碰撞安全裕度；128-bit 参数充分性 |
| `MimcHashGadget.cs` | 同上，blob `bf11f4af…`，L24-32 | hash = key=0 链式 encrypt，k preimage → k encrypt（VERIFIED） | Poseidon/P128Pow5T3 参数；替换后端成本 |
| `SelectComposeGadget.cs` | 同上，blob `dc19cb7a…`，L25-40 | k 选 1、每字段一次 `FieldMul`（VERIFIED） | 一次秘密比较可当作一次乘法 |
| `BitDecompositionGadget.cs` | 同上，blob `1b63c4de…`，L19-25 | bit 分解输出 `ArithConfig.BitSize` 位（VERIFIED） | 具体后端每个 bit 约束的展开倍率 |
| `FieldEqualsGadget.cs` | 同上，blob `fbd6c007…`，L19-29 | artifact 相等由减法 + FieldNorm + BoolNot 构成（VERIFIED） | 本文使用的 ℓ-bit `EQ(ℓ)=2ℓ−1` 与 artifact gadget 等价 |
| `ZkProgramExecutor.cs` | 固定源码 L230/L297/L302/L375-376 | 地址用 reg0；`in_mem_val` 绑定；registers 跨 session 传递（VERIFIED） | ORAM 状态线存在；ORAM witness 已绑定 |
| `Program.cs` 回调 | `CollaborativeZkVm/Program.cs` L106-111/L211-214 | 单方落盘+`SelfVerify()`、多方只落盘（VERIFIED） | 自动进入协作证明；verifier 强制串联 |
| `R1csCircuitWithValues.cs` | L22-38 | `SelfVerify()` 只验单电路（VERIFIED） | 跨电路根链、步数、锚点检查 |
| `groth16/src/verifier.rs` | L27-61 | arkworks 标准单 proof `verify_proof`（VERIFIED） | ORAM 状态转换或历史链检查 |
| prove scripts | `collaborative-zksnark-mod.md` L42-78、`prove-r1cs-multiparty-inner.py` | 外部 Rust client 逐电路手动证明（VERIFIED） | 同执行 witness 到 co-SNARK 的认证交接 |

---

## F2. 论文证据

### F2.1 Path ORAM（Stefanov et al., CCS 2013）

- 来源：`https://eprint.iacr.org/2013/280`；参数页面 `https://docs.rs/oram/0.1.0/oram/path_oram/struct.PathOram.html`（VERIFIED 页面文本）。
- 直接支持：tree/pos/stash 结构、bucket Z=4/5、递归 pos map、`SO=89 suffices for 2^-80`（页面称来自原论文 Figure 3 的实验/保守估计）。
- 不能支持：任务给定解析界 `14·0.6002^R` 下 R=89；公开 Merkle 承诺；ORAM state SNARK。

### F2.2 Keller & Scholl, *Efficient, Oblivious Data Structures for MPC*, ASIACRYPT 2014 / ePrint 2014/137

- 来源：`https://eprint.iacr.org/2014/137`，Abstract（VERIFIED）。
- 原文要点：oblivious data structures 仅 polylog overhead；用 SPDZ，“active security against an adversary corrupting all but one players”；2 方 100 万元素 oblivious array access <250ms。
- 直接支持：任意方、dishonest-majority、active-secure 秘密索引 ORAM 的**存在性**。
- 不能支持：公开可验证性、SNARK witness 接口、跨步状态承诺、非禁用 Poseidon 参数。

### F2.3 SPDZ 原始论文与 MAC 检查

- Damgård, Pastro, Smart, Zakarias, *Multiparty Computation from Somewhat Homomorphic Encryption*, CRYPTO 2012, LNCS 7417, pp.643–662（VERIFIED 书目信息：Bristol Research Portal / Springer）。
- 2025/789：Kyster, Nielsen, Oechsner, Scholl, *Rushing at SPDZ: On the Practical Security of Malicious MPC Implementations*, IEEE S&P 2025；摘要原文指出 SPDZ “provides security against malicious adversaries when all-but-one … may be corrupted”，并发现 MAC check 的 key leakage 可在并发/多线程环境破坏输出完整性（VERIFIED 摘要）。
- 直接支持：SPDZ 的认证份额/MAC 检查是协议核心；实现层 MAC key 一致性是真实风险。
- 不能支持：本 artifact 的 proof witness 每个输入份额都带 MAC 且被检查；外部 co-SNARK 接口已安全。

### F2.4 VDORAM 论文（Qi et al., NDSS 2026 / ePrint 2025/039）

- 来源：`https://eprint.iacr.org/2025/039` 摘要；本地摘录 `../exp-doram-02/paper/EXCERPTS.md` p4-5、p9（VERIFIED）。
- 摘要原文：“existing DORAMs lack public verifiability”；CompatCircuit 把 collaborative zkSNARK 与 MPC 统一为 compatible circuit paradigm。
- p4-5：MPC 计算中间值为 shares，co-SNARK 用这些 shares 作 witness；`(m,t)` co-SNARK 有 knowledge soundness、t-zero-knowledge、succinct verification；Prove 在 MPC 中执行。
- p9：因高效 DORAM 参与方受限与双结构开销，VDORAM 改用单个线性扫描 oblivious array。
- 直接支持：MPC 份额作为 witness 的协议范式；任意方公开验证目标；当前基线为线性扫描。
- 不能支持：ORAM 状态转换已被公开证明；当前 artifact 已实现跨电路 verifier-chain；具体 ORAM witness 的 MAC 覆盖。

### F2.5 OMap（Feng et al., ePrint 2024/1650）

- 来源：`https://eprint.iacr.org/2024/1650` 摘要（VERIFIED）。
- 直接支持：OMap 基于 tree-based ORAM/ODS，客户端—服务器，交互/通信 polylog。
- 不能支持：多方协作证明或公共 verifier 接口。

---

## F3. 数学依据（非文献 VERIFIED）

| 命题 | 本轮处理 |
| --- | --- |
| 随机线性/幂累加器多重集相等 soundness | **CONSTRUCTED 数学推导**：若挑战在 witness 固定后均匀随机，差多项式次数 d，误差 ≤d/\|F\|；两个独立挑战约平方。固定集合中未找到直接对应的 ORAM-stash 文献，故不标 VERIFIED |
| `ρ=H(x_i)` 在 witness 前已知 | **CONSTRUCTED 反例论证**：soundness 论证失效；具体能否构造编码内根不依赖 |
| Merkle root 的 binding/hiding 区分 | **INFERRED**：抗碰撞哈希给 binding，不给 hiding；低熵输入可字典猜测。未引用专门论文作为本轮 VERIFIED 依据 |
| nonce 刷新削弱可关联性 | **CONDITIONAL_CONSTRUCTION**：依赖 λ-bit 秘密 nonce、随机带绑定与防重放；不是零知识证明 |

---

## F4. 定点核查结论

1. **commit-then-challenge 的可靠依据**：本轮只给出数学推导与顺序规则，固定文献集合没有可直接引用的 ORAM-stash 实例 → UNKNOWN（文献实例）/ CONSTRUCTED（推导）。
2. **MPC coin-toss 防偏置**：SPDZ 文献证明 active security 大框架，但本轮未取得“任意 m、dishonest majority、可证明无偏置且无选择性 abort 的 coin-toss 实例”一手细节 → UNKNOWN。
3. **协作 SNARK 后端 witness 接口**：VDORAM 论文给定义，固定 artifact 给落盘与外部逐电路证明；两者之间缺少“同执行认证交接”证据 → BLOCKED。
4. **Merkle hiding 安全定义**：标准 commitment hiding/binding 概念可用，但本轮未把 C3 写成已证明安全实现 → CONDITIONAL_CONSTRUCTION。
