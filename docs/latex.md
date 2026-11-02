# LaTeX 论文管理

> 本库的论文是**产品**：最终 `main`/`release` 只保留 `.tex/.cls/.bib/code/figures/fonts`。
> 本文说明文件职责、分块规则、图/文献/字体怎么管，以及编译与排错。

## 1. 编译

```bash
# 推荐：一条命令（自动跑 bibtex 与多遍）
latexmk -pdf main.tex

# 手动（等价）
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

- 编译器由 `project.toml` 的 `latex_engine` 指定，默认 `pdflatex`；
- 中间产物（`.aux/.log/.out/.bbl/.toc/.pdf`）**不提交**，已在 `.gitignore` 忽略；
- 只用标准 TeX Live/MiKTeX 自带宏包，不引入需要额外安装的宏包（队友和 CI 必须能直接编译）；
- 编译失败时先 `latexmk -C` 清干净再编译，避免旧 aux 干扰。

## 2. 文件职责

| 文件 | 职责 | 谁改 |
| --- | --- | --- |
| `main.tex` | 只做装配：定义文档类、`\input` 各部分、参考文献样式。尽量不动 | 整合人 |
| `abstract.tex` | Summary Sheet 摘要与关键词（`\summary{...}`/`\keywords{...}`） | 整合人，最后写 |
| `paper_content.tex` | 正文全部内容，按 PART 分块 | 各 part 分支分别改自己的块 |
| `appendix.tex` | 附录，按问题注释分块 | 各问题负责人 |
| `ref.bib` | 参考文献（MCM 用 thebibliography 也可，本模板用 BibTeX） | 谁引用谁加 |
| `mcmthesis.cls` | 论文样式/Summary Sheet/页边距/页眉页脚 | 不建议改；确需改走 fix 并全队通知 |
| `code/` | 各问题代码与结果 | 各问题负责人 |
| `figures/` | 各问题图（PDF/EPS/PNG） | 各问题负责人 |
| `fonts/` | 可选字体文件（默认不需要） | 整合人 |

## 3. PART 分块规则（写作管理的核心）

`paper_content.tex` 用固定标记分块，**标记行不能删、不能改**：

```latex
% ===== PART front =====      % 背景、问题重述、模型假设、符号说明
% ===== PART p1 =====         % 问题一
% ===== PART p2 =====         % 问题二
% ===== PART p3 =====         % 问题三
% ===== PART sens =====       % 灵敏度/稳健性分析
% ===== PART eval =====       % 模型评价、推广、结论
```

规则：

1. 一条 part 分支**只改自己块**内的内容；块外的文件头注释不要动；
2. 块的顺序固定（front → p1 → p2 → p3 → sens → eval），不要重排；
3. 题目背景/重述/假设/符号这类"和具体模型关系不大"的内容统一进 `front`；
4. 摘要、标题、关键词、难以归类的零散写作进 `abstract.tex` / `misc` 分支，**不要塞进 p1/p2/p3**；
5. 合并 part 分支时按 S6 用 Squash；不同块天然不冲突，若冲突说明有人越界。

检查：`python tools/mcm.py check` 会验证所有 PART 标记是否存在。

## 4. 图的管理

- 图必须由 `code/` 里的脚本生成（可复现），图名 `fig_<问题>_<内容>.pdf`，如 `figures/q2/fig_q2_forecast.pdf`；
- 正文用 `\mcmfigure{figures/q2/fig_q2_forecast.pdf}{Forecast result}{fig:q2-forecast}`（内部是 figure + includegraphics + caption + label）；
- 每新增/删除图，同步更新 `figures/README.md` 的「图文件 → 生成脚本 → 论文位置」表；
- `check` 会检查论文里引用的图文件是否存在、目录里的图是否未引用；
- 图用矢量 PDF 优先；位图 ≥200dpi；图内文字用英文（避免字体缺失）；
- 单栏图宽 ≤3.5in，跨栏图宽 ≤7in。

## 5. 参考文献管理

- key 命名：`第一作者姓氏+年份+关键词`，如 `hyndman2018forecasting`；
- 只在 `ref.bib` **末尾追加**，不要重排已有条目（减少冲突）；
- 正文用 `\citep{key}`（natbib，numbers 模式）；
- `check` 会提示：`\cite` 的 key 在 `ref.bib` 不存在（必须修）、`ref.bib` 有条目未引用（警告，可接受）；
- 引用格式按当年 MCM 要求（通常作者-年份或数字均可，以官方模板为准）。

## 6. 字体

- 默认 `mathptmx`（Times 风格），**不需要任何字体文件**，`fonts/` 为空；
- 特殊需要时把 `.ttf/.otf` 放 `fonts/`，单文件 <5MB，确认可自由使用；`release` 会保留整个 `fonts/`；
- pdflatex：`\fontfamily{...}`；xelatex：`fontspec` + `\setmainfont{...}[Path=fonts/]`；
- 切换引擎要同时改 `project.toml` 的 `latex_engine`，并在 `journal/team.md` 说明原因。

## 7. 页数与结构（MCM/ICM）

- 正文（Summary Sheet 之后、参考文献之前）**不超过 25 页**（以当年官方规则为准，`project.toml` 的 `page_limit` 可改）；
- 结构建议：Summary Sheet（1 页）→ Introduction → Assumptions → Notation → 各问题模型与结果 → Sensitivity → Model Evaluation → References → Appendix；
- 附录不计入页数，但也不宜无限长；
- 提交前用 `pdfinfo main.pdf` 或 PDF 阅读器确认页数。

## 8. 写作与代码/图/文献的对应关系

一条硬规则：**论文里出现的每个数字、每张图、每篇引用，都必须能指回仓库里的实现**。

| 论文内容 | 对应物 | 检查方式 |
| --- | --- | --- |
| 图 | `figures/qN/*.pdf` + 生成脚本 | `mcm.py check` 校验存在性 |
| 数字/表格 | `code/results/*_metrics.json` 或代码输出 | 重跑代码核对 |
| 引用 | `ref.bib` 条目 | `mcm.py check` 校验 key |
| 代码清单 | `code/qN/` | `code/README.md` 对应表 |

## 9. 常见错误与处理

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `LaTeX Error: File 'xxx.sty' not found` | 宏包未安装/拼写错 | 换 TeX Live 自带宏包；或 `tlmgr install`（本地），并通知全队 |
| 引用显示 `[?]` | 没跑 bibtex 或 key 错 | 跑完整 latexmk；`check` 查 key |
| 图片显示红叉/找不到 | 路径或大小写错 | 用相对仓库根的路径；`check` 列缺失文件 |
| `Overfull \hbox` | 内容超宽 | 调整图宽/断行/公式；不严重可忽略 |
| 改完仍显示旧内容 | aux/toc 陈旧 | `latexmk -C` 后重编 |
| 中文乱码 | 用 pdflatex 写中文 | 中文放注释，正文英文；或切 xelatex（见第 6 节） |
| 编译成功但页数为空/0 | 主体被 `\input` 丢失 | 检查 main.tex 的 `\input` 路径 |
| Summary Sheet 队号/题目错 | 未改占位 | `check --setup` 列占位符；改 main.tex 的 `\team/\contest/\problem/\title` |
| 附录编号错乱 | `\appendix` 位置被移动 | 保持 appendix.tex 结构 |

## 10. 编译与 CI

- 本地：提交前必须 `latexmk -pdf main.tex` 通过；
- CI：`pr-check` 会尝试编译（失败不阻断 PR，但会显示红叉）；`build-paper` 在 push 到 main/release 后编译并上传 `paper-pdf` 产物，用于快速拿 PDF；
- 不建议把 `main.pdf` 提交进仓库（`.gitignore` 已忽略），要分发时从 Actions 下载或用共享网盘。
