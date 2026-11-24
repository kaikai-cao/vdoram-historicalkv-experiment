# ABA-02-C1-R1：Git 推送记录准确性补正

本轮为**纯历史记录修正**：只修正 ABA-02-C1 中 Git 推送记录的一处事实不准确——此前把“远端已同步”写成由 `git fetch` 成功确认，而实际权威证据来自 GitHub API 查询、且 `git fetch` 当时因代理 502 失败。不重新审计 ABA-02，不修改任何研究结论、源码、CSV 或远端 ref。上游研究代码仍固定为 `BDS-SDU/vdoram-artifacts@10c90d35464620a35ddb1e2c29d2e8725acedd52`。

## 1. 发现的事实不准确

ABA-02-C1 三份文档在描述 `fa5344c` 的推送过程时，写成“`git fetch origin` 确认 `HEAD` 与 `origin/main` 一致、工作区干净”。这与实际执行报告不符：真实顺序是远端 ref 先由 API 更新并查询确认、`fetch` 随后因 502 失败、本地 `origin/main` 再据已确认 SHA 同步。

## 2. 三份文档的具体修正

- **`docs/aba-02/validation.md`（第 5 节）**：把“最后 `git fetch origin` 确认……”改为两段准确表述——(a) GitHub API 回退上传对象、SHA 逐级核验一致、远端 ref 仅 fast-forward 更新（force=false）；远端 `refs/heads/main` 的权威证据是 **API 查询**，确认更新至最终 commit；(b) 此后 `git fetch origin` 仍因代理 502 失败、未成功，不能声称“fetch 确认远端更新成功”；本地陈旧 `origin/main` 引用被同步到 API 已确认的远端 SHA，从而 HEAD 与 origin/main 一致、工作区干净。明确写出“远端 ref 的权威确认 ≠ `git fetch` 成功”。

- **`docs/aba-02-c1/fix.md`（问题三）**：保留原有修正事实，把推送过程描述改为 API 更新远端 ref → API 查询确认 → fetch 因 502 失败 → 本地 `origin/main` 引用同步 → 最终 HEAD 与 origin/main 一致；删除“fetch 确认远端更新成功”的错误措辞，并注明 R1 再次收紧该表述。

- **`docs/aba-02-c1/validation.md`（第 3 节第 3 项与第 6 节）**：把“fetch 确认 local=remote”改为“API 查询权威确认远端 SHA → 本地 `origin/main` 引用同步至该 SHA；`git fetch` 因 502 失败未成功”；第 6 节写明最终状态 HEAD=origin/main=`fa5344c...`、工作区 clean，并声明本轮 R1 不执行 push、API 回退、fetch 或任何远端 ref 修改。

## 3. 本轮明确不做的事

不重新执行 Git push、不调用 GitHub API 修改任何 ref、不上传任何 Git 对象、不重新尝试 fetch、不重新下载上游源码、不重新执行 ABA-02 审计、不新增研究假设/实验/公式/成本模型；不改变 ABA-02 的 `GO_WITH_ADDED_INPUT_CONSTRAINTS`，不改变 EXP-DORAM-06 的 `NO_GO_CURRENT_ARCHITECTURE`。本轮不运行代码测试。

## 4. 范围外的遗留事项（未修改，如实记录）

`docs/aba-02-c1/decision.md` 第 9 行仍有一句“→ fetch 确认 local=remote”的同类不准确表述。该文件**不在本轮授权修改的三个既有文档之列**，故按边界未改动。如实记录，供后续决定是否单独修正；本轮不擅自扩大范围。
