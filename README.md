# MCM/ICM 美赛协作库（模板）

一个给 **3 人小队、96 小时美赛**用的 Git 协作模板。目标只有三件事：

1. **按假设分大分支**：不同建模假设各开一条 `hypo/`，互不干扰，最后选一条最好的；
2. **论文用 LaTeX 组织**：每条假设分支都能独立编译出一篇论文，代码、图、参考文献与正文严格对应；
3. **一切可回溯**：每次改动都有日志，每一次 push 都自动归档，改错了随时找回。

> 最终提交版（`main` / `release` 分支）只保留论文产品文件：
> `main.tex`、`paper_content.tex`、`abstract.tex`、`appendix.tex`、`mcmthesis.cls`、`ref.bib`、
> `code/`、`figures/`、`fonts/`。
> 唯一例外是 `.github/`：GitHub 要求 workflow 文件必须存在于分支里，否则自动归档和 PR 检查会失效，详见 [MANUAL.md](MANUAL.md) 第 4 节。

## 目录结构

```text
mcm-template/
├── main.tex                # 总入口，只负责 \input 各部分
├── abstract.tex            # Summary Sheet 的摘要与关键词（最后写）
├── paper_content.tex       # 正文，按 PART 分成 front/p1/p2/p3/sens/eval
├── appendix.tex            # 附录
├── ref.bib                 # 全部参考文献
├── mcmthesis.cls           # 论文模板类
├── code/                   # q1/ q2/ q3/ sensitivity/ 与 results/
├── figures/                # q1/ q2/ q3/ sensitivity/，与 code 一一对应
├── fonts/                  # 需要特殊字体时才放
├── journal/                # 团队日志、决策、bug、每条分支的日志
├── docs/                   # LaTeX 使用说明、GitHub 配置说明
├── project.toml            # 赛题/队号/队长等占位配置
├── hypo.toml               # 只在 hypo/ 分支上出现的假设卡片
├── README.md / MANUAL.md   # 本文件 / 操作手册
└── .github/                # PR 模板、CI（归档 / PR 检查 / 编译论文）
```

## 六类分支

| 分支 | 干什么 | 合并方式 |
| --- | --- | --- |
| `main` | 最终提交线，只收 PR，只保留产品文件 | — |
| `hypo/hNN-<slug>` | 一条建模假设一支，完整论文+代码+图，可独立编译 | 通过 `release/` 间接进入 main |
| `part/hNN/<块>` | 假设内的子任务：`front` `p1` `p2` `p3` `sens` `eval` `misc` | Squash 回合所属 hypo |
| `fix/<slug>` | 修 bug（先登记 `journal/bugs.md`） | Squash 回合出问题的分支 |
| `release/<slug>` | 从**单条**假设生成提交版，裁剪为产品文件 | Merge commit 进 main，然后打 tag |
| `wip/<成员>/<slug>` | 自由草稿，永不合并，靠自动归档留档 | 不合并 |

## 五分钟上手

```bash
# 0. 克隆后先装钩子（每个成员一次）
bash tools/install-hooks.sh

# 1. 开一条假设分支（自动编号、建卡片、写日志、推送）
python tools/mcm.py new-hypo --title "ARIMA 残差修正" --slug arima-residual --owner @zhangsan

# 2. 在这条假设里开一个子任务分支（例如写问题一）
python tools/mcm.py new-part p1

# 3. 干活……提交时按规范写提交信息
git add -A && git commit -m "paper(p1): 完成问题一模型推导"

# 4. 随时记录"我做了什么"，并同步指标到假设卡片
python tools/mcm.py log "完成问题一初版模型" --why "验证 ARIMA 基线" \
    --result "RMSE=3.21" --next "明天做残差修正" --metric rmse=3.21

# 5. 推送，看各假设对比
git push -u origin "$(git branch --show-current)"
python tools/mcm.py status --write
```

**不知道现在该做什么，就打开 [MANUAL.md](MANUAL.md)**：里面有 12 个场景的逐步操作、写作分块规则和 FAQ。

## 可回溯设计（四层）

1. **分支日志**：`journal/branches/` 下每条分支一个文件，`mcm.py log` 只追加、不冲突；
2. **自动归档**：`.github/workflows/archive.yml` 每次 push 生成不可变 `refs/archive/<分支>/<时间戳>-<sha>`，force-push/删分支也能恢复（`mcm.py restore --list`）；
3. **文档留档**：`journal/team.md`（团队事件）、`journal/decisions.md`（DNNN 决策）、`journal/bugs.md`（BNNN 缺陷）；
4. **提交规范**：`type(scope): 说明`，正文写「为什么/验证」，本地钩子校验；release 后打 `submit-...` tag。

## 把模板变成你的比赛仓库

1. GitHub 上点 **Use this template** 建私有仓库（或直接 push 本仓库）；
2. 替换占位符：`project.toml`、`main.tex` 的 `\team`/`\contest`/`\problem`/`\title`；用
   `python tools/mcm.py check --setup` 列出所有待替换项；
3. 按 [docs/github-setup.md](docs/github-setup.md) 打开 Actions 写权限、给 `main` 配保护规则。

## 文档地图

| 文档 | 内容 |
| --- | --- |
| [MANUAL.md](MANUAL.md) | 角色、分支规则、12 个场景操作、写作分类与合并、冻结提交、FAQ、命令速查 |
| [docs/latex.md](docs/latex.md) | 编译方式、文件职责、PART 块与图表引用规范、页数控制、常见错误 |
| [docs/github-setup.md](docs/github-setup.md) | 建仓、权限、main 保护、Actions 设置、归档验证 |
| [figures/README.md](figures/README.md) | 图 → 生成脚本 → 论文位置 对照表 |
| [code/README.md](code/README.md) | 代码运行方式与对应关系表 |
| [journal/team.md](journal/team.md) | 96 小时时间轴与团队日志 |
