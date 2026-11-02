# 分支日志目录

本目录存放**每条分支的独立日志**，文件名 = 分支名把 `/` 换成 `__`，例如：

- `hypo/h01-arima` → `journal/branches/hypo__h01-arima.md`
- `part/h01/p1` → `journal/branches/part__h01__p1.md`

这些文件由 `python tools/mcm.py log "做了什么" --why ...` 自动创建并追加，**不要手改历史条目**。
每条分支分开记日志，是为了让不同分支的日志在合并时永不冲突。

任何推送前的重要动作都应当留一条日志；即使忘了，远程还有自动归档 `refs/archive/...`
兜底（见 MANUAL.md 第 6 节）。
