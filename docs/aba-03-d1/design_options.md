# ABA-03-D1 / Phase C：三类 P2 地址绑定方案的同维度比较

> 基线：`BDS-SDU/vdoram-artifacts @ 10c90d35…`；起点 `f3933474…`。只读设计评估，不实现电路、不改 HOLD。
>
> 目标关系（见 `p2_binding_semantics.md` §3）：B1 真实访问 `fetch_addr=reg0=trace_addr` + 范围；B2 dummy `trace_addr=p−1` 且不要求三者相等；B3 step0 排除；B4 轨迹完整性。
>
> 标签：`VERIFIED` = 固定源码/明确定义直接支持；`CONSTRUCTED` = 本轮候选构造；`INFERRED` = 由事实推导；`UNKNOWN` = 缺必要证据；`BLOCKED` = 现有接口无法支撑结论。

---

## 0. 比较前的两个硬约束

1. **地址必须在真实访问时三值相等，dummy 时不得相等**（Phase A 已固定）。任何方案都要表达 `is_mem_op` 门控，不能全局强加相等。
2. **当前地址是私有 witness/私有输出，不在 proof statement**（`MemoryTraceFetch...cs:42`、`ZkVmExecutor...cs:996/1006`；ABA-03-C2 §3）。三类方案的差别本质在「把什么公开、公开多少、由谁核对」。

---

## 1. 方案 C1：直接公开地址

### 构造

VM 电路与 Fetch 电路各自把必要字段作为 public input 输出：

```
public_per_step_i = (step_i, pc_i, opcode_i, is_mem_op_i, addr_i)
真实步：addr_i = reg0_i（公开）        # 供 verifier 跨两份 proof 比较
dummy 步：addr_i = p−1（公开），不暴露 reg0
step 0：无 Fetch proof；不输出 fetch_addr
```

verifier 从两份 proof 的 public inputs 取 `(step, is_mem_op, addr)`，按 step 比较：真实步要求 `fetch_addr = trace_addr` 且 `0≤addr<n`，dummy 步要求双方都标 `is_mem_op=0` 且 trace 地址为 `p−1`。

### 同维度评估

| 维度 | 评估 | 标签 |
| --- | --- | --- |
| 能否复用现有 public-input 通道 | 通道本身存在（opcode 四列已公开，`InstructionFetch...cs:126-156`；`plonk.rs:143-161`），但**当前没有逐步 `(step,pc,opcode,is_mem_op,addr)` 公开字段**，需新增公开输出 | `VERIFIED`（通道在）+ `INFERRED`（需新增字段） |
| verifier 如何比较两份 proof 的公开地址 | 比较逐 step 的公开地址值；须先有稳定 step 索引与事件计数，否则无法对齐 | `CONSTRUCTED` |
| 如何绑定 step/PC/opcode/事件类型 | 需把 step（当前由宿主公开注入 `:393-395`）、PC（当前私有，`:134-136`）、opcode（选中行私有，`:231-241`）提升为受约束公开输入；PC↔opcode 选择骨架存在（`:158-213`） | `VERIFIED`（骨架在）+ `CONSTRUCTED`（提升为公开） |
| 地址是否泄漏 | **泄漏真实内存访问地址**（每步 `reg0` 明文进入 public inputs）。对 VDORAM 是实质性隐私退化 | `INFERRED` |
| dummy 步与 step0 表示 | dummy 步公开 `is_mem_op=0`、`addr=p−1`，不公开 reg0（否则泄漏非内存寄存器）；step0 无 Fetch proof | `CONSTRUCTED` |
| 多步/证明数量/公开规模影响 | 每步每份 proof 新增约 5 个公开字段，公开规模随 `T` 线性增长；proof 数量维持每步一份 Fetch + 一份 VM（现状，`:205-228`） | `INFERRED` |
| B4 轨迹完整性 | 仅公开字段不足以证明无遗漏/无重排，仍需 step 单调、事件计数与 halt 边界约束 | `INFERRED` |

**小结**：实现路径最直接、可复用公开通道，但以**真实地址明文公开**为代价。若地址机密性是目标，C1 单独不可接受。

---

## 2. 方案 C2：跨电路共享隐藏承诺

### 构造

对每步定义承诺（示例形式，非唯一）：

```
com_i = Commit(step_i, pc_i, opcode_i, is_mem_op_i, addr_i ; r_i)
```

VM 电路与 Fetch 电路各自以自身 witness 计算同一个 `com_i` 并公开输出；verifier 只比较两份 proof 的 `com_i` 是否相等，地址本身隐藏。真实步承诺覆盖 `reg0`；dummy 步承诺覆盖 `p−1` 且 `is_mem_op=0`。

### 同维度评估

| 维度 | 评估 | 标签 |
| --- | --- | --- |
| 两个电路是否都能约束同一个 `com_i` | 需在同一域内由各自 witness 重算承诺并公开输出；上游无此共享承诺（跨电路仅宿主哈希 `throw`，`ZkProgramExecutor.cs:302-332,551-583`） | `CONSTRUCTED` + `INFERRED`（需新增） |
| binding / hiding 性质 | 候选：MiMC（电路内已有 `MimcHashGadget`，`ZkVmExecutor...cs:1013`）或 Pedersen 类。MiMC 抗碰撞可作 binding，但是否构成 hiding 取决于输入熵与域大小，需形式化；Pedersen hiding 依赖离散对数假设且需额外群运算 | `UNKNOWN`（hiding 强度需证明） |
| 随机数 `r_i` 的产生/分发/绑定/防重采样 | 若 `r_i` 由 prover 自由选，可重采样制造不同承诺；需由 verifier 固定、MPC 认证随机、或从公开 seed 派生并约束。上游每次执行用随机 `enc_key`（`ZkProgramExecutor.cs:61`），但这不是承诺随机性，不能复用 | `INFERRED` + `UNKNOWN`（具体机制未定） |
| 是否需要 MPC 认证随机性 | 若要防 prover 重采样且 verifier 不见 `r_i`，可能需要 MPC 生成/认证随机；当前 additive-share 无 MAC（见 `../exp-doram-06/rust-authenticated-share-path.md` B.1/B.4），是否足够 `UNKNOWN` | `UNKNOWN` |
| 哈希/MiMC 与 Pedersen 的代价与安全假设差异 | 符号级：MiMC 走域内哈希、无群运算；Pedersen 需群标量乘且域/群匹配问题更复杂。具体门数未测 | `INFERRED`（定性）；数值 `UNKNOWN` |
| BLS12-377 Fr 域兼容性 | MiMC gadget 已在 Fr 电路使用（`:1013`）→ 若承诺用同类 MiMC，域兼容 `VERIFIED`；Pedersen 需额外群，`UNKNOWN` | `VERIFIED`（MiMC）/ `UNKNOWN`（Pedersen） |
| 公开承诺是否防跨步/跨程序/跨执行重放 | 若 `com_i` 含 `step_i` 与程序身份/实例 nonce，可防重放；否则同一承诺可在不同 step/程序复用。是否纳入这些字段取决于承诺内容设计与 verifier 锚定 | `CONSTRUCTED` + `INFERRED` |
| dummy 与真实访问的承诺语义 | 用 `is_mem_op` 作为承诺字段并分别规定真实步覆盖 `reg0`、dummy 步覆盖 `p−1`；verifier 按公开 `is_mem_op` 解释。但 `is_mem_op` 若只在承诺内隐藏，verifier 需它公开才能分类 | `CONSTRUCTED` |
| 与现有逐行哈希/`enc_key` 的关系 | **不得**把 `out_hash_mem_trace`（含 step 与随机 `enc_key`，`:1009-1017`）当隐藏承诺：其 preimage 含 step/随机量且只做内部一致性 + 宿主多重集比对（`ZkProgramExecutor.cs:551-583`），不是稳定 program/地址承诺 | `VERIFIED`（区分依据） |

**小结**：在隐藏地址的前提下可闭合 B1/B2 的跨电路相等，但 hiding 强度、`r_i` 生命周期、MPC 随机性、防重放字段均未定，属需新增的承诺接口。当前仓库无可复用实现 → 关键安全性质标 `UNKNOWN`。

---

## 3. 方案 C3：证明组合 / 递归绑定

### 构造与一个必须澄清的边界

把 VM proof 与 Fetch proof 纳入一个共同 statement，由组合电路验证：

```
statement_common = (program_hash, n, step_range, event_count, commitment_to_trace)
```

**递归验证能做什么、不能做什么（勘误 C1）**：

- **已验证事实**：普通递归/组合验证可以验证「子 proof 对其**公开输入**成立」。这是递归证明的标准语义。
- **不能直接推出**：递归电路**不能**读取两个子 proof 的**私有 witness** 并直接比较其中的私有地址。地址在两份子电路中都是私有 witness / 私有输出（`MemoryTraceFetch...cs:42`、`ZkVmExecutor...cs:996/1006`），子 proof 只证明这些私有值满足各自电路约束；递归验证看到的是子 proof 及其公开输入，而非私有 witness。因此「递归电路在内部比较两份 witness 的私有地址」这一说法**不成立**，不能作为已建立的关系。

据此，地址同一性要进入可验证 statement，只有以下两条候选路径（均为设计候选，**不是已实现接口**）：

- **候选路径一：共同承诺。** 两份子 proof 各自在**自己的电路内**约束「本电路的私有地址」与**同一个公开承诺**的关系；顶层组合/递归电路只比较这两份**公开承诺**是否相等。地址始终不进入公开 statement。此时递归电路验证的是「两份公开承诺相等」这一公开关系，而非读取私有 witness。
- **候选路径二：合并电路。** 把需要比较的地址关系（真实步 `fetch_addr = reg0 = trace_addr`）放进**同一个电路**，使比较在单一约束系统内完成，根本不需要跨 proof 读取私有 witness。代价是失去「两份独立子 proof」的结构。

### 共同承诺路径尚未解决的问题（均非递归本身自动解决）

1. 承诺的 **binding 与 hiding** 性质（见 `leakage_and_security.md` D1）；
2. 承诺**随机数**的生成、分发与生命周期（含是否需要 MPC 认证随机，见 D6）；
3. **程序身份、step、执行实例 nonce** 的绑定（防跨步/跨程序/跨实例重放，见 D5）；
4. **dummy Fetch 与真实访问的类型区分**（`is_mem_op` 门控，见 D7）；
5. **B4 事件计数、顺序和 halt 边界完整性**（见 D8）；
6. 递归/组合 proof 的**实际接口及成本**（见下表与 `cost_model.md`）。

递归/组合证明本身**不自动解决**上述任何一项；它只提供「验证子 proof 对公开输入成立」的能力。

### 同维度评估

| 维度 | 评估 | 标签 |
| --- | --- | --- |
| 两份 proof 的共同 statement | 需定义同时约束两份子电路公开输入的顶层 statement；当前每步各自 setup/prove/verify（`plonk.rs:293-315`），无统一 statement | `CONSTRUCTED` + `INFERRED` |
| 地址同一性如何进入可验证 statement | 递归**不能**直接比较两份子 proof 的私有 witness；两条候选路径：① 各子电路把私有地址绑定到同一**公开承诺**、顶层比较承诺；② 把地址关系放进**同一电路**。二者均未实现 | `CONSTRUCTED`（候选）+ `VERIFIED`（递归不能读私有 witness） |
| verifier 能否检查完整组合关系 | 理论上可（单一顶层 proof），但需 verifier 持有组合 VK 与顶层公开输入；当前无独立 verifier（ABA-03-C2 §A8） | `UNKNOWN`（接口不存在） |
| 递归/组合是否需非原生域运算 | PLONK 递归通常涉及跨域模拟（BLS12-377 Fr 与内层域不同）；固定 commit 是否有 pairing/非原生域 gadget 未核验 | `UNKNOWN` |
| 是否需改造当前 PLONK/MPC prove 数据通路 | 是：当前 `mpc_prove_and_verify_compat_circuit`（`plonk.rs:293-315`）是单电路 setup→prove→verify，无递归/组合分支；`Computation` 枚举无递归项（`client.rs:36-65`） | `VERIFIED`（现有路径无）+ `INFERRED`（需改） |
| 与 C2 相比是否减少公开数据/重复约束 | 可能把跨电路比较移入证明内，减少 verifier 侧公开值；但引入递归电路自身成本，净收益未测 | `UNKNOWN` |
| 当前仓库是否有可复用递归/proof-composition 接口 | 在固定 commit 内未发现递归/组合接口（依据 `client.rs:36-65` 枚举、`plonk.rs` 函数集合、`tree.json` 路径检索）；不能因库名或理论可行写成已支持 | `VERIFIED`（未发现）+ `UNKNOWN`（论文层） |

**小结（勘误 C1）**：C3 **构造尚不完整，关键接口与成本 `UNKNOWN`**。递归验证子 proof 不等于读取私有 witness，因此当前描述**尚未建立私有地址同一性**；必须先选定共同承诺或合并电路路径，并解决上文六项未决问题（binding/hiding、随机性、防重放、dummy 分类、B4 完整性、递归接口成本），才谈得上可实现。当前无证据支持可复用，不能据此推荐。

---

## 4. 三方案同维度对照表

| 维度（相同粒度） | C1 直接公开 | C2 共享隐藏承诺 | C3 证明组合/递归 |
| --- | --- | --- | --- |
| 复用现有 public-input 通道 | 是（通道在，字段需增） | 部分（公开承诺需新增输出） | 否（需新 statement） |
| 地址机密性 | 无（真实地址明文公开） | 有（承诺隐藏，hiding 待证） | 有（若地址不入公开 statement） |
| `is_mem_op` 分类 | 公开字段直接分类 | 需公开 `is_mem_op` 或分类承诺 | 未定（递归不读私有 witness，分类须进公开承诺或合并电路） |
| step0 / dummy 处理 | 需显式排除/标注 | 承诺字段区分 | 未定（随所选路径） |
| B4 轨迹完整性 | 不自动闭合 | 不自动闭合 | 未证（须显式约束，递归本身不提供） |
| 对现有 VDORAM 侵入 | 低-中 | 中（新增承诺电路） | 高（新增递归/组合 + prove 改造） |
| 关键未决 | 隐私退化不可接受 | hiding/随机性/防重放待证 | 构造尚不完整；共同承诺六项未决 + 递归接口/非原生域/成本全 UNKNOWN |
| 证据等级 | 构造可行 `INFERRED` | 构造可行、安全性质 `UNKNOWN` | 构造尚不完整，关键接口与成本 `UNKNOWN`（递归读私有 witness 不成立 = `VERIFIED`） |

---

## 5. 本轮不选择最终协议

按任务要求，本文只做同维度比较，**不预设任何一种一定可行、不选择最终协议**。可初步排除的是 C1 的「真实地址明文公开」变体（隐私退化，`INFERRED`）；C2/C3 的关键安全与成本项多为 `UNKNOWN`，需在最小原型中核验，但本轮不启动原型。P1-A（固定完整 opcode table 比较，`../aba-03-c2/verifier_interface_audit.md`）作为独立前置条件可复用，与本文 P2 方案选择无关。
