# 字体目录

**默认不需要放任何字体文件**：模板用 `pdflatex` + Times（`mathptmx`），
TeX Live 自带，编译产物在任何机器上一致。

只有以下情况才把字体文件放这里：

1. 学校/赛题要求特定字体（例如某些中文字体、特定英文字体）；
2. 需要 `xelatex`/`lualatex` + `fontspec` 使用系统外字体。

## 放置规则

- 只放 `.ttf` / `.otf`，单文件建议 < 5MB，不要放整个字体包；
- 确认字体许可证允许随论文分发；商用字体不要提交（可用开源替代，如
  `TeX Gyre Termes` = Times 克隆、`Noto Serif` 系列）；
- 文件名用英文，例如 `fonts/MyFont-Regular.ttf`；
- `release/` 版本会保留整个 `fonts/` 目录（属于最终论文文件清单的第 5 项）。

## 用法

pdflatex 下（推荐，兼容模板）：

```latex
\newcommand{\myfont}{\fontfamily{...}\selectfont}
```

xelatex/lualatex 下需在 `main.tex` 导言区加：

```latex
\usepackage{fontspec}
\setmainfont{MyFont-Regular.ttf}[Path=fonts/]
```

注意：切换 `xelatex` 会改变 `mcmthesis.cls` 的字体设置，需同步修改
`project.toml` 的 `latex_engine` 并在 `docs/latex.md` 记录；编译命令改为：

```bash
latexmk -xelatex main.tex
```
