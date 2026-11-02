# 操作手册（MANUAL）

> 给第一次用这套库的人。按顺序读前 4 节，然后直接翻到你要做的场景。
> 命令都在仓库根目录执行；Python ≥3.11，无需安装任何第三方包即可运行 `tools/mcm.py`。

---

## 1. 这套库怎么运行（一页看懂）

一句话：**一个假设 = 一条 `hypo/` 分支（完整的一篇论文）**；假设内部**按问题切成 `part/` 小分支**分别写；最后从**一条** `hypo/` 生成 `release/`，裁剪成只含论文产品文件，合入 `main`。

```text
main    ──●───────────────●────────────────●──▶  只保留论文产品文件
          \             /                /
hypo/h01   ●──●──●──●──●                /       一条假设：完整论文+代码+图
           \   \   \  /                 /
part/h01/p1 ●───●   (按问题一独立分支)  /
part/h01/p2     ●───●                  /
release/v1  ──────────────────────────●         从 h01 裁剪出的提交版
```

- **为什么按假设分大分支**：不同假设（模型、参数、数据处理方式）会得出完全不同的论文，开发期间必须并行、可对比、互不污染。
- **为什么假设内还要按问题分小分支**：问题一/二/三/灵敏度分析可以同时由不同人写，合并时各块互不冲突。
- **为什么最后要 `release` 再进 main**：保证最终版本"只有一个假设的成果"，且只含论文文件，不会把管理文件混进提交版。

| 分支 | 从哪来 | 合并回哪里 | 用什么方式 | 允许改什么 |
| --- | --- | --- | --- | --- |
| `main` | — | — | 只通过 PR | 只收 release；最终只有产品文件 |
| `hypo/hNN-<slug>` | `main` | `release/`（不直接进 main） | — | 整条假设的论文/代码/图 |
| `part/hNN/<块>` | 同假设的 `hypo` | 自己的 `hypo` | Squash | 自己那个 PART 块 + 对应 `code/`、`figures/` |
| `fix/<slug>` | 出问题的分支 | 原分支或 main | Squash | 只改修复相关文件，先登记 bug |
| `release/<slug>` | **一条** `hypo` | `main` | **Merge commit** | 只能删管理文件，不能引入新内容 |
| `wip/<成员>/<slug>` | 任意 | 不合并 | — | 什么都行，靠自动归档留档 |

规则里最重要的三条：

1. **不许直接 push `main`**，main 只接受 release PR；
2. **`hypo` 不许直接合入 main**，必须经 `release` 裁剪；
3. **每条分支的改动都要有日志**（`mcm.py log` 一句也行），这是回溯的基础。

## 2. 角色

| 角色 | 谁 | 主要职责 |
| --- | --- | --- |
| 队长 | 1 人 | 选题、最终方案拍板、合并 release PR、冻结后唯一有权批准修改 |
| 整合人 | 1–2 人 | 维护 main、`misc` 写作（摘要/标题）、组织 `release`、提交论文 |
| 假设负责人 | 每条 hypo 1 人 | 维护 `hypo.toml` 卡片、推进假设、把 part 分支合回 |
| 全员 | 所有人 | 在自己分支写代码/论文、记日志、互评 PR |

## 3. 第一次上手（30 分钟）

```bash
# ① 克隆
git clone git@github.com:<org>/mcm2026.git && cd mcm2026

# ② 配置身份（只第一次）
git config user.name "张三"
git config user.email "zhangsan@example.com"

# ③ 安装提交信息钩子
bash tools/install-hooks.sh

# ④ 环境自检 + 编译论文
python tools/mcm.py check
latexmk -pdf main.tex          # 能生成 main.pdf 即正常

# ⑤ 认识目录
#   main.tex / abstract.tex / paper_content.tex / appendix.tex / ref.bib
#   code/  figures/  journal/  docs/

# ⑥ 走一遍最小流程：开一条试验假设 → 开 part 分支 → 记日志 → 删掉
python tools/mcm.py new-hypo --title "试验假设" --slug test --owner @zhangsan
python tools/mcm.py new-part p1
python tools/mcm.py log "跑通示例代码" --metric rmse=3.21
# 确认无误后删除试验分支（远程 + 本地）
git push origin --delete hypo/h01-test
git switch main && git branch -D hypo/h01-test
```

第 ⑦ 步：读第 5 节的 S2，开始你负责的问题；第 ⑧ 步：把本文件收藏。

## 4. 分支与文件规则

### 4.1 命名

| 类型 | 格式 | 例子 |
| --- | --- | --- |
| 假设 | `hypo/hNN-<英文小写slug>` | `hypo/h01-arima-residual` |
| 子任务 | `part/hNN/<块>` | `part/h01/p2`、`part/h01/front`、`part/h01/misc` |
| 修复 | `fix/<英文小写slug>` | `fix/b001-reindex` |
| 发布 | `release/<英文小写slug>` | `release/v1`、`release/final-a` |
| 草稿 | `wip/<成员>/<slug>` | `wip/zhangsan/scratch` |

`<块>` 的标准取值：`front`（背景/重述/假设/符号）、`p1`、`p2`、`p3`、`sens`（灵敏度）、`eval`（评价与结论）、`misc`（摘要/标题/杂项写作）。自定义块也可以（英文小写），但要在 `journal/team.md` 说明用途。

### 4.2 允许的合并方向

| 源 → 目标 | 允许？ | 方式 |
| --- | --- | --- |
| part → 同 hNN 的 hypo | ✅ | Squash |
| fix → 出问题的分支 / main | ✅ | Squash |
| release → main | ✅ | **Merge commit** |
| hypo → main | ❌ | 必须先 release |
| hypo → hypo | ❌ | 假设之间互相对比，不合并 |
| main → 任何分支 | ✅ | 同步最新 |
| wip → 任何分支 | ❌ | 草稿只留档 |

### 4.3 谁能 push

- `main`：谁都不能直接 push，只能 PR（merge 由队长/整合人操作）；
- 其他分支：分支创建者及其协作者可以直接 push（方便比赛节奏），但重要改动仍要走 PR 以便留痕；
- 永远不要对 `main` 做 force-push。

### 4.4 最终版本的文件树（main 与 release）

主分支/release 分支**顶层只允许**：

```text
main.tex  paper_content.tex  abstract.tex  appendix.tex  mcmthesis.cls  ref.bib
code/  figures/  fonts/
.github/        ← 唯一例外，见下
```

- `mcm.py release` 会自动删除管理文件（README、MANUAL、docs、tools、journal、project.toml、hypo.toml、STATUS.md、.gitignore、.gitattributes、data）；
- **`.github/` 为什么保留**：GitHub 要求 workflow 文件必须存在于被 push/PR 的分支上，否则自动归档（每次 push 建 `refs/archive`）和 PR 检查会直接失效。只保留 CI 配置，不含任何论文内容，可接受为唯一例外。若要"绝对纯净"，可以删掉 `.github/`，代价是失去自动归档与 PR 门禁（不推荐）。
- `code/README.md`、`figures/README.md` 保留在目录内（它们是代码/图与论文的对应说明，属于产品的一部分）。

## 5. 场景操作手册

> 每个场景给出「命令 / 等价手动 git 命令」，赛场上直接照抄。

### S1 开一条新假设

```bash
python tools/mcm.py new-hypo --title "ARIMA 残差修正" --slug arima-residual --owner @zhangsan
# 等价手动：
#   git switch main && git pull --rebase
#   git switch -c hypo/h01-arima-residual
#   创建 hypo.toml 卡片 + journal/branches/hypo__h01-arima-residual.md
#   git add -A && git commit -m "chore(h01): 创建假设分支与卡片"
#   git push -u origin hypo/h01-arima-residual
```

要点：自动编号不用自己管；卡片 `hypo.toml` 里填 `problem`（对应的赛题问题编号/描述）和 `primary_metric`（主指标，默认 rmse）。

### S2 在假设里开一个子任务分支

```bash
git switch hypo/h01-arima-residual && git pull --rebase
python tools/mcm.py new-part p1        # 或 front / p2 / p3 / sens / eval / misc / 自定义
```

之后循环：

```bash
# 干活……
git add -A && git commit -m "paper(p1): 补充问题一模型推导"
git push
```

要点：**part 分支只改自己那块**（`paper_content.tex` 里的对应 PART、对应 `code/qN/`、`figures/qN/`、自己负责的 `appendix.tex` 注释块）。写完一个阶段就 `log` 一条。

### S3 写论文的某个 PART 块

1. 从 hypo 开 part 分支（见 S2），`git merge hypo/h01-arima-residual` 拿到最新内容；
2. 只编辑 `paper_content.tex` 中 `% ===== PART p1 =====` 与下一个 `% =====` 之间；
3. 新增图：先由代码生成到 `figures/q1/`，再用 `\mcmfigure{...}{...}{fig:q1-...}` 引用，更新 `figures/README.md` 对应表；
4. 新增引用：在 `ref.bib` **末尾追加**，正文 `\citep{...}`；
5. 本地编译通过后 `git push`，发 PR 回合 hypo（Squash）。

### S4 写代码、出图

```bash
python code/q1/main.py --seed 42 --data /path/to/shared/data   # 数据不在仓库里，用 --data 传入
# 结果写 code/results/q1_metrics.json；图写 figures/q1/*.pdf
```

要点：数据不入库；同一问题固定随机种子便于复现；结果数字记入日志和 `hypo.toml` 的 `[metrics]`；图名与代码文件对应（`fig_q1_xxx.pdf` ← `code/q1/main.py`）。

### S5 日常记录与提交

```bash
python tools/mcm.py log "完成问题二初版" --why "验证假设是否成立" \
    --result "RMSE 3.21，比基线低 22%" --next "明天做灵敏度" --metric rmse=3.21
```

- `log` 会追加到 `journal/branches/<当前分支>.md`，并自动提交；
- 在 `hypo/` 分支上还会同步更新 `hypo.toml` 的指标与状态；
- 提交信息格式：`type(scope): 说明`，type 取 `feat|fix|exp|paper|data|docs|release|chore`，正文写「为什么/验证」。

### S6 把 part 分支合回 hypo

网页：发 PR（part/hNN/<块> → hypo/hNN-*），按模板五节写清楚，CI 绿后 **Squash and merge**。
命令行等价：

```bash
git switch hypo/h01-arima-residual && git pull
git merge --squash part/h01/p1
git commit -m "merge(h01): 回合问题一内容"
git push
```

合并后 part 分支可删除（远程 + 本地）；hypo 分支永不删除。

### S7 修 bug

```bash
# ① 先在 journal/bugs.md 登记 B001（现象/严重度/所在分支）
python tools/mcm.py new-fix --slug b001-reindex --base hypo/h01-arima-residual
# ② 修复、重跑、验证，记日志
python tools/mcm.py log "修复索引错位，RMSE 回到 3.21" --why "原索引导致数据错位" --metric rmse=3.21
# ③ push 并发 PR 回合原分支（Squash）；另一位成员验证后把 bugs.md 状态改为“已验证”
```

### S8 对比假设、定采纳方案

```bash
git fetch origin
python tools/mcm.py status --write     # 生成 STATUS.md：各假设的状态/主指标/最新日志
```

按 `STATUS.md` 的指标 + 论文完整度 + 运行时间综合判断，在 `journal/decisions.md` 记一条决策（DNNN），然后：

```bash
python tools/mcm.py log "本假设定为最终方案" --status adopted
git push
```

要点：**不要手改 STATUS.md**，它由命令生成；决策要有数字依据。

### S9 从假设生成提交版（release）

```bash
git switch hypo/h01-arima-residual && git pull
python tools/mcm.py release v1
```

命令会：跑完整 `check` → 建 `release/v1` → 删管理文件 → 校验顶层树严格等于产品文件（+`.github/`）→ 提交并推送，并打印后续指令。然后：

1. 发 PR：`release/v1` → `main`，选 **Create a merge commit**（不要 squash）；
2. 队长合并后，打 tag：
   ```bash
   git switch main && git pull
   git tag -a submit-2026-A-v1 -m "2026 MCM Problem A 提交版 v1"
   git push origin submit-2026-A-v1
   ```
3. 在 `journal/team.md` 记录提交（时间/账号/结果）。

### S10 冻结期（最后 8–12 小时）

- 冻结后**不再改代码与数据**，只允许改论文文字、图注、引用、排版；
- 冻结后的每一次修改也必须：开 part 分支（或 fix）→ PR → 合并 → 记日志，不许直接改 main；
- 致命错误（结果错误/编译失败）才允许解冻：在 `journal/team.md` 写明原因，队长同意后执行；
- 提交版任何改动都重新走一次 S9，并打新 tag（`v2`），旧 tag 保留。

### S11 回溯与恢复

```bash
# 手动快照（重要节点前做一次）
python tools/mcm.py snapshot --name before-refactor

# 查看 / 恢复自动归档
git fetch origin '+refs/archive/*:refs/archive/*'
python tools/mcm.py restore --list
python tools/mcm.py restore --ref 20261102T031500        # 唯一匹配片段
```

- 每次 push 都会自动归档（含 force-push 之前的版本）；
- `restore` 会新建 `fix/restore-<sha7>` 分支，不会覆盖你当前工作；
- 想回到某个旧版本看内容：`git show <归档sha>:paper_content.tex`。

### S12 全队日常检查

```bash
python tools/mcm.py check          # 提交前自检：文件齐全、引用/图对应、卡片、大文件
python tools/mcm.py check --setup  # 赛前检查占位符是否替换完
python tools/mcm.py status --write # 更新对比看板
latexmk -pdf main.tex              # 论文能编译
git status                         # 工作区干净
```

## 6. 写作分类与合并管理（重点）

写作比代码"碎"，所以规定：**正文按 PART 分块，写作碎活统一进 `misc`，合并顺序固定**。

### 6.1 内容归位表

| 内容 | 放哪 | 由谁写 |
| --- | --- | --- |
| 题目背景、问题重述、模型假设、符号说明 | `paper_content.tex` 的 `front` 块 | front part 分支（整合人/队长） |
| 问题一/二/三的模型、求解、结果 | 各自的 `p1/p2/p3` 块 | 各问题负责人 |
| 灵敏度分析 | `sens` 块 | 指定的成员 |
| 模型评价、推广、结论 | `eval` 块 | 整合人 |
| 摘要、标题、关键词、零散写作 | `abstract.tex`、`misc` 块 | 整合人最后写 |
| 详细推导、补充表格、代码说明 | `appendix.tex` 按问题注释分块 | 各问题负责人 |
| 参考文献 | `ref.bib` | 谁引用谁加 |

### 6.2 合并顺序与冲突处理

推荐顺序：`front → p1 → p2 → p3 → sens → eval → misc`。

- **不同 PART 块永远不冲突**：因为大家改的是文件里不同段落；若 git 仍报冲突，说明有人越界改了别人块，保留对方块，只提交自己的部分；
- **同一块内两人同时写**：先合并一个人，另一个人 `git merge hypo/...` 后手动合入，不要整段覆盖；
- **`ref.bib` 冲突**：两侧条目都保留（按字母序整理），绝不能"用我的版本"覆盖别人的文献；
- **`figures/README.md`、`code/README.md` 对应表冲突**：保留双方新增行。

### 6.3 写作冗余怎么处理

- 写不下去/暂时归类不定的内容 → **`misc`** 或 `front`，最后整合人决定去留，不要为归类纠结；
- 一段文字只属于一个问题 → 进对应块；
- 同一段被多个问题引用 → 放在最先出现的块，其他地方 `\ref`/复述一句；
- 被删掉的整段好文字 → 挪到 `appendix.tex` 或 `misc`，不要直接删（万一要用）；
- **摘要最后统一写**，数字以正文定稿为准。

## 7. 96 小时时间轴（要点）

完整表在 [journal/team.md](journal/team.md)。关键节点：

| 时间 | 要做的事 |
| --- | --- |
| T+0–4 | 选题，开 2–3 条 hypo，分工 |
| T+4–12 | 各 hypo 开 part 分支；数据/背景/假设就位 |
| T+12–30 | 三问并行建模求解，代码出指标，图进 figures |
| T+30–48 | 对比假设（status）、灵敏度、定采纳决策 |
| T+48–60 | 成文（PART 块拼合）、摘要初稿 |
| T+60–76 | 打磨：引用、图表、页数、编译 |
| T+76–88 | 冻结检查：数字/摘要/附录/引用逐项核对 |
| T+88–92 | release → PR → merge → tag → 官网提交 |
| T+92–96 | 归档、复盘、记录 |

## 8. 冻结与提交清单

- [ ] `main` 最新，`python tools/mcm.py check` 通过
- [ ] `latexmk -pdf main.tex` 无 Error，页数符合当年规则
- [ ] Summary Sheet 数字与正文一致，队号/题目正确
- [ ] 所有图都能由 `code/` 复现，`figures/README.md` 已更新
- [ ] 所有 `\cite` 都能在 `ref.bib` 找到，无未引用条目（警告可接受）
- [ ] `release` 生成并合并进 main，打了 `submit-...` tag
- [ ] 官网提交完成，截图存到团队共享位置，`journal/team.md` 记录

## 9. GitHub 设置

见 [docs/github-setup.md](docs/github-setup.md)：建仓、Actions 写权限、main 保护、成员权限、归档验证。免费版私有仓没有分支保护的替代方案也在其中。

## 10. FAQ

**Q：忘了开分支，直接在 hypo 上改了一堆怎么办？**
现在补：`git switch -c part/h01/xxx` → `git commit` → push → 发 PR 回合 hypo。改动不会丢，日志补一条即可。

**Q：在错误的分支 commit 了怎么办？**
`git log` 找到 sha → `git switch 正确分支` → `git cherry-pick <sha>` → 回到错误分支 `git reset --hard HEAD~1`（只对本地未 push 的分支这样做；已 push 的用 revert）。

**Q：part 分支太久没更新，落后 hypo 了？**
`git switch part/... && git merge hypo/h01-arima-residual`，解决冲突后再继续；合并回 hypo 前必须同步一次。

**Q：合并时同一个 PART 块冲突了？**
说明两人改了同一块。解决：保留双方内容并人工融合，别整段选一边；融合后编译一遍。

**Q：论文编译报错/图表错位？**
看 [docs/latex.md](docs/latex.md) 第 9 节常见错误表；先 `latexmk -C` 清理再编译。

**Q：图生成了但论文里是红叉/找不到？**
检查图文件名与 `\includegraphics` 路径大小写一致；跑 `python tools/mcm.py check` 会列出缺失的图。

**Q：论文数字和代码结果对不上？**
以 `code/results/*_metrics.json` 和重跑结果为准，改论文；并在 `journal/bugs.md` 登记，防止再犯。

**Q：误提交了数据/PDF/大文件？**
`git rm --cached <文件>` 并加入 `.gitignore` 后提交；如果已 push 且文件很大，联系队长决定是否用 `git filter-repo` 清理（清理前先 `mcm.py snapshot`，并通知全员重新克隆）。密钥泄露要第一时间更换。

**Q：force-push 把历史搞丢了？**
从自动归档恢复：`git fetch origin '+refs/archive/*:refs/archive/*'` → `mcm.py restore --list` → `mcm.py restore --ref <片段>`。

**Q：免费版私有仓不能设分支保护？**
用软保护：把 `pr-check` 的红叉当硬门槛、合并前队长人工 `check`、保留自动归档；或升级 Pro/Team（学生可免费领 Pro）。

**Q：`check` 报错看不懂？**
错误文字就是原因，例如"缺少产品文件"、"图片不存在"、"卡片缺少字段"、"超大文件"。先按提示修，再把提示贴给队长。占位符警告只在 `--setup` 下出现，赛前替换完即可。

**Q：能不能只在一个分支上直接用网页编辑？**
紧急小改可以（网页编辑会自动提交），但之后要 `git pull` 再继续，且仍要补日志。

**Q：wip 分支到底有什么用？**
放不成熟的草稿，随便推，不合并；靠自动归档保底。不要在 wip 上写"最终版"。

## 11. 命令速查卡

```bash
bash tools/install-hooks.sh                # 安装提交钩子（一次）
python tools/mcm.py check                  # 提交前自检
python tools/mcm.py check --setup          # 赛前占位符检查
python tools/mcm.py new-hypo --title "..." --slug xxx --owner @zhangsan
python tools/mcm.py new-part p1            # 在 hypo 分支上执行
python tools/mcm.py new-fix --slug b001-xxx --base <分支>
python tools/mcm.py log "做了什么" --why "..." --result "..." --metric rmse=3.21
python tools/mcm.py status --write         # 更新 STATUS.md 对比看板
python tools/mcm.py release v1             # 在 hypo 分支上生成提交版
python tools/mcm.py snapshot --name xxx    # 手动快照
python tools/mcm.py restore --list         # 查看归档
python tools/mcm.py restore --ref <片段>   # 恢复到新分支
python tools/mcm.py pr-check --head <分支> --base <分支> --body-file pr.md
latexmk -pdf main.tex                      # 编译论文
git log --oneline --graph --all            # 看全局历史
```

## 12. 新人自测清单

做完以下 8 项，说明你已经会用了：

- [ ] 装好钩子，提交一条信息，故意写成 `随便写` 会被拦下；
- [ ] `new-hypo` 建一条假设，能说出它的卡片路径和日志路径；
- [ ] 在假设下开 `part/hNN/p1`，只改问题一块并编译通过；
- [ ] `log` 一条带指标和"为什么"的记录，能在 `journal/branches/` 找到；
- [ ] 发一个 part→hypo 的 PR，五节写全，CI 绿；
- [ ] `status --write` 后能在 `STATUS.md` 看到自己假设的指标；
- [ ] 用 `mcm.py release` 生成一次提交版，确认顶层只剩产品文件；
- [ ] 用 `snapshot` + `restore` 找回一个旧版本。
