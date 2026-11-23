# EXP-DORAM-08 — SelectCompose 计数语义修正

## 1. 旧计数器为什么不够

EXP-DORAM-07-R1 的 `selection_operations` 定义为：**本次 Fetch 是否产生了一个被选中的逻辑结果**。
- E0：`_fetch_scan` 中 `matched == True` 时 +1；
- E1：`0 ≤ address < n` 时 +1。

它记录的是**逻辑结果**，不是选择计算次数。上游 `SelectComposeGadget.ApplyGadget`（blob `dc19cb7a…`）对 `i = 0..SelectionCount−1` **无条件**循环：每行执行一次 `FieldMul(condition_i, value_i)`，再线性累加；源码中没有对 `condition_i == 0` 的分支、提前退出或常量折叠。因此“未命中”时选择乘法**仍然全部发生**。用旧字段推导 MPC 成本会系统性低估。

## 2. 新计数器（仅本轮新目录使用，旧字段保留不改）

| 字段 | 严格含义 | 取值 |
| --- | --- | --- |
| `logical_selection_results` | 本次 Fetch 是否存在被选中的逻辑输出；等价于旧 `selection_operations` 的含义，但重新命名以明确其非成本属性 | 0 或 1 |
| `select_compose_rows` | 本次 Fetch 进入 `SelectComposeGadget` 的行/槽数 | E0：`t`（可见历史行数）；E1：`n` |
| `select_compose_field_mul` | 本次 Fetch 在 select 阶段实际产生的 `FieldMul` 次数 | `select_compose_rows × 1`（`ColumnNamesToBeFetched = ["mem_val"]`，只有 1 列） |
| `e1_read_select_rows` | E1 读路径的 select 行数 | `n` / Fetch |
| `e1_write_select_rows` | E1 写路径的条件更新 select 行数 | STORE 时 `n`，否则 0 |

关系：
```
select_compose_field_mul = select_compose_rows × len(ColumnNamesToBeFetched) = select_compose_rows
```
这与 `c_sel = 1` / 行一致；**不是** `logical_selection_results`。无匹配时 `logical_selection_results = 0` 但 `select_compose_field_mul = rows > 0`。

## 3. 三个验证例

### 例 1：地址命中最新历史行
历史（旧→新）：`(addr=0,v=10), (addr=1,v=20), (addr=0,v=99)`；查询 `addr=0`。
- E0 扫描 3 行；最新匹配为第 3 行 → `logical_selection_results = 1`。
- 选择阶段仍对 3 行全部执行 `sel_i × val_i` → `select_compose_rows = 3`，`select_compose_field_mul = 3`。
- 旧 `selection_operations = 1`，与新“逻辑”字段一致，但无法表达 3 次乘法。

### 例 2：地址完全未命中（空匹配集）
历史：`(addr=0,v=10), (addr=1,v=20), (addr=2,v=30)`；查询 `addr=99`。
- E0 扫描 3 行；无匹配 → `logical_selection_results = 0`，返回默认值 0。
- `LowBit` 全 0 选择位；`SelectCompose` 仍对 3 行执行 `0 × val_i` → `select_compose_rows = 3`，`select_compose_field_mul = 3`。
- **旧计数器记 0，真实选择乘法为 3**：这是最直接的语义差异。未命中**不省**选择计算。

### 例 3：存在历史行但全部为不同地址
历史：`(addr=5), (addr=6), (addr=7), (addr=8)`；查询 `addr=0`。
- 与例 2 同为无匹配，但历史上非空且全为异址 → `logical_selection_results = 0`；
- `select_compose_rows = 4`，`select_compose_field_mul = 4`；旧字段仍记 0。
- 说明旧字段无法区分“空历史”“非空但异址”“有匹配”三种成本相同的扫描场景。

### E1 读写分离补充例
`n = 4`，一步 LOAD(addr=2)：`e1_read_select_rows = 4`，`e1_write_select_rows = 0`，`select_compose_field_mul = 4`。
同一步改为 STORE(addr=2, v=7)：read 4 + write 4 → `e1_read_select_rows = 4`，`e1_write_select_rows = 4`，选择/更新阶段共 8 次 FieldMul。E1 必须分别统计读、写，不能只算“一次比较 + 一次选择”。

## 4. 与其他成本的关系

`select_compose_field_mul` 只是 Fetch 电路总秘密乘法 `393k−2` 中的 `k` 那一项；`389k` 来自每行 `FieldEquals`，`(3k−2)` 来自 `LowBit`。因此即使把选择计数修正正确，也**不能**说“一次选择 = 一次比较 = 一次乘法成本”：本项目当前执行器里它们都走 Beaver，但外部实现可能不同；本轮只按当前执行器建模。
