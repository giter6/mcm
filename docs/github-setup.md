# GitHub 仓库设置

> 模板第一次建仓、加人、配保护时看这份。配完按第 7 节逐项验证。

## 1. 建仓（两种方式）

**A. 用本仓做模板（推荐）**

1. 仓库 Settings → 勾选 **Template repository**（只用一次，建模板仓时）；
2. 新比赛时 GitHub 页面点 **Use this template → Create a new repository**；
3. 命名为 `mcm2026` / `mcm2027` 等，**Private**（比赛期间禁止公开）；
4. 建好后按 README 替换占位符。

**B. 直接把这个目录推上去**

```bash
git remote add origin git@github.com:<org>/mcm2026.git
git push -u origin main
```

加人：Settings → Collaborators → Add people（成员给 **Write**，队长和备份给 **Admin**）。

## 2. 本地第一次配置

```bash
git config user.name "张三"
git config user.email "zhangsan@example.com"
bash tools/install-hooks.sh      # 安装提交信息校验钩子
python tools/mcm.py check        # 环境自检
```

> 提交信息规范：`type(scope): 说明`，type 取 `feat|fix|exp|paper|data|docs|release|chore`。
> 钩子只做软校验，钩子没装也能提交，但 CI 和日志仍会要求规范。

## 3. Settings → General

| 设置项 | 建议值 | 理由 |
| --- | --- | --- |
| Default branch | `main` | 固定 |
| Automatically delete head branches | **关闭** | 保留 adopted 的 hypo 分支，便于回溯 |
| Allow merge commits | 开启 | release → main 需要 merge commit 保留检查点 |
| Allow squash merging | 开启 | part / fix 回合用 squash |
| Allow rebase merging | 关闭 | 统一两种合并方式，减少混乱 |
| Require linear history | **关闭** | 开启会禁止 merge commit，release 就无法保留检查点 |
| Allow auto-merge | 关闭 | 合并必须有人确认 |
| Allow update branch | 开启 | 方便把 main 更新到 PR 分支 |

## 4. Settings → Actions

| 设置项 | 建议值 | 说明 |
| --- | --- | --- |
| Actions permissions | Allow all actions and reusable workflows | 需要官方 checkout/setup-python/latex-action |
| Workflow permissions | **Read and write permissions** | ⚠️ 自动归档要 push `refs/archive/*`，默认只读会 403 |
| Allow GitHub Actions to create and approve pull requests | 不勾 | 本流程不需要 |

## 5. 保护 main（关键）

**Settings → Rules → Rulesets → New branch ruleset**（或旧版 Branches → Add rule）：

- Target branches：`main`；
- ✅ Require a pull request before merging（**1 个 Approve**）；
- ✅ Require status checks to pass：选 `pr-check`；
- ✅ Require conversation resolution；
- ✅ Block force pushes；
- ✅ Restrict deletions；
- ❌ 不要勾 Require linear history（会禁用 merge commit）。

> ⚠️ **私有仓库 + 免费版**：GitHub 对私有仓的 rulesets/分支保护要求 Pro（学生可免费领 Pro）或 Team 计划。若没有：
> 1. 靠纪律：把 `pr-check` 红叉当硬门槛，红叉一律不合并；
> 2. 合并前由队长本地跑 `python tools/mcm.py check` 并人工看 diff；
> 3. 自动归档照常工作（不受影响）；
> 4. 至少两人有 Admin，互相监督。
>
> 比赛仓库是 Private，无需买 Team 也完全可以按上面的软保护跑完比赛。

tag 保护（可选，Rulesets → New tag ruleset）：target `submit-*`，禁止删除/移动。

## 6. 成员与团队

| 角色 | 权限 | 建议 |
| --- | --- | --- |
| 队长 | Admin | 唯一可批准 release 合并、冻结后解冻 |
| 备份管理员 | Admin | 队长不在时顶上（至少 2 个 Admin） |
| 假设负责人/整合人 | Write | 推自己的分支、发 PR |
| 普通成员 | Write | 同上 |

组织级建议建 team：`mcm-captains`（Admin）、`mcm-members`（Write），按 team 加人更快；一赛一仓，赛后归档为只读。

## 7. 配完逐项验证

- [ ] 成员 clone 后能 `bash tools/install-hooks.sh` 并正常提交；
- [ ] 推一个测试分支，Actions 里 **Archive** 成功，`git fetch origin '+refs/archive/*:refs/archive/*'` 能看到归档 ref；
- [ ] 用一个测试 PR 验证 `pr-check` 会跑（故意删一节 PR 模板内容应报错）；
- [ ] `main` 上直接 push 被拒绝（配了保护时）或至少 PR 才能合并；
- [ ] Actions → Build Paper 手动 Run 一次，能下载 `paper-pdf` 产物；
- [ ] `Submit` tag 能创建并推送（`git push origin submit-2026-A-v1`）。

## 8. 归档验证（可回溯的关键）

```bash
# 看远端归档 ref
git ls-remote origin 'refs/archive/*'

# 拉到本地后查看
git fetch origin '+refs/archive/*:refs/archive/*'
python tools/mcm.py restore --list
```

每次 push 都会新增一条归档；force-push、删分支前的历史都在。GitHub 网页不展示自定义 ref，所以用上面的命令验证。

## 9. 常见设置问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| Archive 失败 403 | Actions 权限是只读 | 第 4 节改为 Read and write |
| PR 没有 pr-check 状态 | Actions 被禁用/权限不足 | Settings → Actions 检查；确认 `pr-check.yml` 在分支内 |
| release PR 后 main 出现历史分叉 | 用了 Squash | release → main 必须 **Create a merge commit** |
| 免费版设不了保护 | 私有仓 + Free | 见第 5 节软保护方案，或升级/学生 Pro |
| 成员看不到 Actions | 无权限 | 给 Write 权限 |
| 页面看不到归档 ref | 自定义 ref 不展示 | 用 `git ls-remote origin 'refs/archive/*'` |

## 10. 赛后归档

1. 确认 main 与所有 tag 已推送；
2. 把仓库 Settings → Archive（只读），或给 org 建一个 `archive` 只读副本；
3. 可选：`git clone --mirror` 保存一份完整镜像（含所有分支与归档 ref），存网盘；
4. 把可复用的改进回灌到模板仓（新比赛再 Use this template）。
