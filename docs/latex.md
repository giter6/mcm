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
| `main.tex` | 只做装配：文档类、`\mcmsetup`（队号/题号）、`\input` 各部分、参考文献样式。尽量不动 | 整合人 |
| `abstract.tex` | Summary Sheet 的摘要正文 + `keywords` 环境（最后写） | 整合人，最后写 |
| `paper_content.tex` | 正文全部内容，按 PART 分块 | 各 part 分支分别改自己的块 |
| `appendix.tex` | 附录（`appendices` 环境）+ 25 页之后的 `Report on Use of AI` | 各问题负责人 / 整合人 |
| `ref.bib` | 参考文献（BibTeX；正文用 `\citep` 数字引用） | 谁引用谁加 |
| `mcmthesis.cls` | 社区标准类 v6.3.3：三栏 Summary Sheet、`Team # / Page X of N` 页眉、AI 报告环境、12pt | **不要改**；升级走 fix 并全队通知 |
| `code/` | 各问题代码与结果 | 各问题负责人 |
| `figures/` | 各问题图（PDF/EPS/PNG） | 各问题负责人 |
| `fonts/` | 可选字体文件（默认不需要） | 整合人 |

### 2.1 论文类：mcmthesis v6.3.3（社区标准）

- 来源：[CTAN mcmthesis](https://ctan.org/pkg/mcmthesis)，上游 <https://github.com/latexstudio-org/mcmthesis>，协议 LPPL 1.3c；
- 仓库内置一份 `mcmthesis.cls`，**保证每台机器和 CI 编译出同一版式**，不要改它；
- 队在 `main.tex` 顶部用 `\mcmsetup{tcn=队号, problem=A, ...}` 填队号/题号，类自动生成：
  - 第 1 页三栏 Summary Sheet（Problem Chosen / MCM/ICM Summary Sheet / Team Control Number）；
  - 之后每页页眉 `Team # <队号> ... Page <当前页> of <总页数>`（官方硬性要求）；
  - `\AImatter` + `ReportAiUse` 环境，用于 25 页之后的 AI 使用声明；
- `\author{}` 必须为空：官方禁止出现队员、学校、导师姓名；
- 升级类文件：用 TeX Live 里新版覆盖后必须全队通知并重新编译，不能只改个人电脑的系统版本。

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
- 正文用 `\citep{key}`（`main.tex` 已加载 natbib 的 numbers 模式）；
- **不要换成 plainnat / 作者-年份样式**：mcmthesis 类把 `\citation` 交给 natbib，作者-年份模式会报
  `Bibliography not compatible with author-year citations`；保持 `\bibliographystyle{plain}`；
- AI 工具的引用用 `\AIcite{AI1}`，条目写在 `appendix.tex` 的 `ReportAiUse` 里，**不进 `ref.bib`**；
- `check` 会提示：`\cite` 的 key 在 `ref.bib` 不存在（必须修）、`ref.bib` 有条目未引用（警告，可接受）；
- 引用格式按当年 MCM 要求（本模板用数字引用 [1]，官方未限定风格，以当年模板为准）。

## 6. 字体

- 类固定 **12pt letterpaper**；`main.tex` 预加载 `txfonts`（Times 风格，与上游 demo 一致），**不需要任何字体文件**，`fonts/` 为空；
- 官方只要求「可读字体 ≥12pt」，因此去掉 `txfonts` 也能提交；但全队必须统一，改 `main.tex` 要通知全队；
- 特殊需要时把 `.ttf/.otf` 放 `fonts/`，单文件 <5MB，确认可自由使用；`release` 会保留整个 `fonts/`；
- pdflatex：`\fontfamily{...}`；xelatex：`fontspec` + `\setmainfont{...}[Path=fonts/]`；
- 切换引擎要同时改 `project.toml` 的 `latex_engine`，重新验证编译，并在 `journal/team.md` 说明原因。

## 7. 页数与结构（MCM/ICM 2027 规则）

- **25 页上限包含**：Summary Sheet、目录、正文、参考文献、附录——即从第 1 页到附录结束的全部页数
  （以当年官方规则为准，`project.toml` 的 `page_limit` 可改）；
- **`Report on Use of AI` 放在 25 页之后**：`\AImatter` 会记录总页数（LastPage）并切换页眉，该节不计页数、无上限；
- 结构建议顺序：Summary Sheet（1 页）→ Contents（可选，算页数）→ Introduction → Assumptions → Notation →
  各问题模型与结果 → Sensitivity → Model Evaluation → References → Appendix → Report on Use of AI；
- 每页页眉由类自动生成 `Team # 队号 / Page X of N`；字体 12pt；**不得出现姓名/学校**；
- 提交前用 `pdfinfo main.pdf` 确认总页数（AI 报告页除外），并抽查第 1 页 Summary Sheet 的队号/题号。

### 7.1 AI 使用声明（2027 新增）

- 官方要求：使用了 AI 工具就必须在正文引用，并在 25 页之后附 `Report on Use of AI` 逐条说明
  （工具名/版本、查询内容、输出用途）；未使用也要写一句声明；
- 写法：`appendix.tex` 中 `\AImatter` 之后的 `ReportAiUse` 环境里用 `\bibitem{AI1} ...`；正文用 `\AIcite{AI1}`；
  完全没用 AI 时把环境参数改成 `0` 或保留一句 "No AI tools were used"；
- **不要写进 `ref.bib`**（AI 报告是独立小节）；`check` 会提示占位文本未替换。

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
| Summary Sheet 队号/题目错 | 未改占位 | `check --setup` 列占位符；改 main.tex 的 `\mcmsetup`（`tcn`/`problem`）与 `\title` |
| 页眉显示 `Page X of ??` | `\AImatter` 被删或位置错误 | 保持 appendix.tex 中 `\AImatter` 在附录之后、AI 报告之前 |
| `Bibliography not compatible with author-year citations` | 用了 plainnat/作者-年份 | 保持 natbib numbers 模式 + `\bibliographystyle{plain}` |
| `ReportAiUse` 报空列表/警告 | 没有 `\bibitem` 条目 | 无 AI 使用把环境参数改 `0`，或写一句声明 |
| 附录编号错乱 | `appendices` 环境/结构被移动 | 保持 appendix.tex 的 `begin{appendices}` 结构 |

## 10. 编译与 CI

- 本地：提交前必须 `latexmk -pdf main.tex` 通过；
- CI：`pr-check` 会尝试编译（失败不阻断 PR，但会显示红叉）；`build-paper` 在 push 到 main/release 后编译并上传 `paper-pdf` 产物，用于快速拿 PDF；
- 不建议把 `main.pdf` 提交进仓库（`.gitignore` 已忽略），要分发时从 Actions 下载或用共享网盘。
