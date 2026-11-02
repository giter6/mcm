# 图目录对应表

`figures/` 与论文严格对应：**论文里出现的每张图都在这里，且每张图都能由 `code/` 中的脚本生成。**

## 命名与质量

- 文件名：`fig_<问题>_<内容>.pdf`，例如 `fig_q1_forecast.pdf`、`fig_sensitivity_parameter.pdf`；
- 一律保存为 **PDF（矢量）**；位图（热力图、照片类）用 PNG 且 ≥ 200 dpi；
- 图中文字用英文、字号不小于 8pt，坐标轴必须有单位；字体嵌入（matplotlib 默认即可）；
- 宽度：单栏 3.5 in，跨栏 7 in；不要用截图。

## 对应关系表（必须维护）

| 图文件 | 生成脚本 | 论文位置（PART / 小节） | 是否已核对 |
| --- | --- | --- | --- |
| `figures/q1/fig_q1_xxx.pdf` | `code/q1/main.py` | PART p1 · 4.2 结果 | 否 |
| `figures/q2/fig_q2_xxx.pdf` | `code/q2/main.py` | PART p2 · 5.2 结果 | 否 |
| `figures/q3/fig_q3_xxx.pdf` | `code/q3/main.py` | PART p3 · 6.2 结果 | 否 |
| `figures/sensitivity/fig_sens_xxx.pdf` | `code/sensitivity/main.py` | PART sens · 7 灵敏度 | 否 |

把示例行替换成真实图，新增图时同步加行。`python tools/mcm.py check` 会校验：
论文 `\includegraphics` 引用的文件是否存在、`figures/` 中的图是否都被论文引用。

## 纪律

- 同一问题只改自己的目录（`figures/q1/` 等），不碰其他问题的图；
- 论文正文引图用 `\ref{fig:...}`，图内标注与正文数字一致；
- 冻结后不再改图；必须改时走 `fix/` 分支并重新编译核对。
