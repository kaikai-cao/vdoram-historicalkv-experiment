# ABA-02-C1-R1 验证记录

## 1. 基线

- 分支：`main`；起始 HEAD = `fa5344cab47fd4eeb568d0bca2f0db2caebca58c` = `origin/main`；工作区干净；`git diff --check` 无输出。
- ABA-02 七份文档、ABA-02-C1 三份文档（`fix.md`/`validation.md`/`decision.md`）均存在；`docs/aba-02-c1-r1/` 起始时不存在。
- 上游研究代码固定：`BDS-SDU/vdoram-artifacts@10c90d35464620a35ddb1e2c29d2e8725acedd52`（本轮不重新下载、不重新审计）。

## 2. 六份授权文件

修改的既有文档（3 份）：

| 文件 | 修正 |
| --- | --- |
| `docs/aba-02/validation.md` | 第 5 节推送记录：API 查询为权威确认；fetch 因 502 失败；本地 `origin/main` 引用同步；明确区分“远端 ref 权威确认 ≠ fetch 成功” |
| `docs/aba-02-c1/fix.md` | 问题三修正方式：API 更新→API 查询确认→fetch 失败→本地引用同步→最终一致 |
| `docs/aba-02-c1/validation.md` | 第 3 节第 3 项、第 6 节：删除“fetch 确认 local=remote”，改为 API 确认 + 本地引用同步，声明 R1 不做远端操作 |

新增文档（3 份）：`docs/aba-02-c1-r1/fix.md`、`docs/aba-02-c1-r1/validation.md`（本文件）、`docs/aba-02-c1-r1/decision.md`。

## 3. 网络操作自查

本轮**没有**执行：Git push、任何 GitHub API 写操作（更新 ref / 上传对象）、fetch、上游源码下载。远端 `refs/heads/main` 未被本轮改动；最终 SHA `fa5344c...` 未被改写。远端同步状态沿用历史记录（API 查询确认为准），本轮只是修正文档表述。

## 4. 验收命令与结果

```text
git diff --name-only   -> 上述三份既有文档
git status --short     -> 三份 M + 新增 docs/aba-02-c1-r1/
git diff --check       -> 无输出（clean）
```

范围核验：除上述三改三增外，源码、测试、CSV、数据文件、`docs/aba-02/{decision,address_domain_audit,interface_design,source_inventory}.md`、EXP-DORAM、ABA-01、ABA-01-C1 均无改动。

未运行代码测试：本轮仅文档修正，无代码改动（按任务要求不运行）。

## 5. 内容核验（逐项）

1. 三份修正文档均不再声称 `git fetch` 成功。
2. 明确记录 GitHub API 查询确认远端 ref。
3. 明确记录 `git fetch` 因代理 502 失败。
4. 明确记录本地 `origin/main` 引用同步至 API 已确认 SHA。
5. 未把本地引用同步写成远端 ref 更新。
6. 最终 SHA `fa5344c...` 未被改写。
7. ABA-02 决策 `GO_WITH_ADDED_INPUT_CONSTRAINTS`、EXP-DORAM-06 `NO_GO_CURRENT_ARCHITECTURE` 均未变化。
8. 遗留事项：`docs/aba-02-c1/decision.md` 第 9 行同类表述因不在授权范围未改，已在 R1 `fix.md` 记录。

## 6. 最终 commit 与同步状态

- 提交信息：`docs(aba-02-c1): correct remote sync record`（六份授权文件）。
- 最终 commit 即本文件所属提交，以 `git rev-parse HEAD` 为准。
- **推送说明**：本轮按任务要求只做常规 `git push origin main`，不使用 API 回退、不修改远端 ref。若常规 push 因代理故障失败，则如实报告阻断情况，本地提交保留、远端未同步，不声称远端同步完成；只有常规 push 正常成功时才报告 HEAD = origin/main。
