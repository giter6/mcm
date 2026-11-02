<!-- 本文件由 `python tools/mcm.py status --write` 自动生成，请勿手改。 -->

# 假设对比看板

生成时间（UTC）：2026-11-02T14:36:26Z
共 0 条假设｜idea 0 · active 0 · candidate 0 · adopted 0 · failed 0

| 假设 | 标题 | 负责人 | 状态 | 主指标 | 指标 | 最新日志 | 分支 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | 还没有假设分支（用 `mcm.py new-hypo` 创建） | | | | | | |

## 说明

- 本表只统计 `hypo/*` 假设分支；part/fix/wip 分支不进入看板。
- 指标由各假设分支的 `hypo.toml` 维护，更新方法：
  1. 切到假设分支；2. `python tools/mcm.py log "..." --metric rmse=1.23`；3. `git push`。
- 更新本文件：`git pull` 后运行 `python tools/mcm.py status --write`，提交并推送。
- 选定最终假设后，把该分支 `hypo.toml` 的 status 改为 `adopted`，再运行 `mcm.py release`。
