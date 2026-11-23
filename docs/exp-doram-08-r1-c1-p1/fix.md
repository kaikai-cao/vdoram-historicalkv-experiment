# EXP-DORAM-08-R1-C1-P1：E0 LowBit 参数化修正

## 1. 原硬编码位置与错误原因

`src/exp_doram_08_r1/costs.py` 的 `e0_total_closed()` 原写为：

```python
K = p.c_eq + p.c_sel + 3  # 393 with defaults
b = p.lowbit_and           # 2
return K * T * (T - 1) // 2 - b * (T - 1) + T * p.append_mults
```

错误原因：E0 每步 Fetch 的真实成本（同文件 `fetch_e0`）为

```
fetch_e0(s) = s*(c_eq + c_sel) + lowbit(s)
lowbit(s)   = s*lowbit_not + (s-1)*lowbit_and    (s > 0)
            = s*(lowbit_not + lowbit_and) - lowbit_and
```

对 `s = 1..T-1` 求和得

```
C_E0(T) = K*T*(T-1)/2 - b*(T-1) + T*append_mults
其中 K = c_eq + c_sel + lowbit_not + lowbit_and，b = lowbit_and
```

因此 LowBit 的线性系数应为 `lowbit_not + lowbit_and`，不能写成常量 `3`。常量 `3` 只是默认值 `lowbit_not=1, lowbit_and=2` 下的巧合。

同一文件的 `cross_threshold_n()` 在 R1-C1 时已参数化（第 219 行 `K = p.c_eq + p.c_sel + p.lowbit_not + p.lowbit_and`），本补丁前两处 `K` 不一致：默认参数下无感知，非默认参数下 `e0_total_closed` 与 `cross_threshold_n` 会给出不同模型。

## 2. 修正后的表达式

`e0_total_closed()` 仅替换 `K` 一行：

```python
# P1: LowBit linear coefficient is parameterised (was hardcoded +3).
# With defaults lowbit_not+lowbit_and = 1+2 = 3, so K is still 393.
K = p.c_eq + p.c_sel + p.lowbit_not + p.lowbit_and
b = p.lowbit_and
return K * T * (T - 1) // 2 - b * (T - 1) + T * p.append_mults
```

检查范围：`cross_threshold_n()` 已是同一套参数化 `K`，无需改动；`fetch_e0/fetch_a/fetch_b`、`e1a/e1b_total_closed` 均通过 `CostParams.lowbit()` 参数化；未重构其他函数、未改 `CostParams` 定义、未改增删任何成本项。

## 3. 默认参数为何不变

默认 `lowbit_not=1, lowbit_and=2`，故 `lowbit_not + lowbit_and = 3`，新 `K = 389 + 1 + 1 + 2 = 393`，与旧硬编码完全相同；`b = lowbit_and = 2` 未变。因此所有已发布的默认 E0 数值、交叉阈值（E1-A `n<T/2`、E1-B `n<(393T−4)/780`）与 CSV 全部保持不变。

反向验证（内存模拟旧硬编码，不改文件）确认：对 `T = 0..129`，旧式与修正后 `e0_total_closed` 在默认参数下逐点相等。

## 4. 非默认参数测试覆盖

`tests/test_exp_doram_08_r1.py` 新增 `TestLowBitParameterizationP1`，使用

```python
P_ND = CostParams(lowbit_not=4, lowbit_and=5)   # K=399, b=5（默认 K=393, b=2）
```

覆盖内容：

1. 断言非默认参数之和确与默认值不同（防止用例退化）。
2. `T ∈ {0,1,2,5,17}`：`e0_total_closed(T,p) == e0_total_by_sum(T,p)`。
3. 同组 `T`：闭式等于 `sum(p.fetch_e0(s) + p.append_mults for s in range(T))`——对照实际逐步成本函数，而非复制闭式自证。
4. `T ∈ {17,65,67,128}`、E1-A/E1-B 两变体、全整数 `n ∈ [1,T+1]`：`cross_threshold_n()` 预测的胜负与真实 `e1X_total_closed(T,n,·) < e0_total_closed(T,·)` 的符号逐点一致。
5. 非默认参数下 E1-A 只读阈值仍严格为 `T/2`（K 在双方抵消）——验证交叉函数与 E0 闭式共享同一 K。
6. 默认参数测试保留：原有 34 项全部保留，另加默认 K/b 与默认闭式常数的显式断言。

反向验证（内存模拟旧硬编码）证明新测试确有捕获能力：

- 逐步/闭式失配：`T=2`（388 vs 394）、`T=5`（3910 vs 3970）、`T=17`（53368 vs 54184）。
- 交叉/成本符号失配 4 处：`(T=65,B,n=33)`、`(T=67,A,n=33)`、`(T=67,B,n=34)`、`(T=128,B,n=65)`。

修正后上述失配全部消失。
