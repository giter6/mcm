# 代码目录约定

`code/` 是论文可复现性的唯一入口。**每一张图、每一个数字都要能从这里跑出来。**

## 目录

```
code/
├── README.md            ← 本文件：运行方式 + 对应关系表
├── requirements.txt     ← 依赖（越少越好）
├── q1/                  ← 问题一代码
├── q2/                  ← 问题二代码
├── q3/                  ← 问题三代码
├── sensitivity/         ← 灵敏度分析代码
└── results/             ← 运行输出的指标 JSON（留档用，不手改）
```

## 运行

```bash
pip install -r code/requirements.txt
python code/q1/main.py --seed 42
python code/q2/main.py --seed 42
python code/q3/main.py --seed 42
python code/sensitivity/main.py --seed 42
```

约定：

- 固定随机种子（默认 `42`），论文里出现的数字必须能用同一条命令复现；
- 指标/参数写 `code/results/<问题>_metrics.json`，论文正文直接引用；
- 图用 `matplotlib` 保存为 **PDF**（矢量）到 `figures/q1/` 等目录，文件名形如
  `fig_q1_forecast.pdf`；不要把图存到代码目录；
- **数据不入库**：赛题数据放在仓库外的共享目录（例如 `D:/mcm-data/2026-A/`），
  通过 `--data` 参数传入；仓库里只记录数据来源与校验和（写在 `journal/team.md`）。

## 对应关系表（必须维护）

新增/修改代码后同步更新此表；`python tools/mcm.py check` 会提醒未对应的情况。

| 代码入口 | 输出（图/表/数字） | 论文中的位置 |
| --- | --- | --- |
| `code/q1/main.py` | `figures/q1/图名.pdf`、`code/results/q1_metrics.json` | `paper_content.tex` 问题一（PART p1） |
| `code/q2/main.py` | `figures/q2/图名.pdf`、`code/results/q2_metrics.json` | PART p2 |
| `code/q3/main.py` | `figures/q3/图名.pdf`、`code/results/q3_metrics.json` | PART p3 |
| `code/sensitivity/main.py` | `figures/sensitivity/图名.pdf` | PART sens |

## 纪律

- 只改自己负责的问题目录；跨问题的公共函数先开 `fix/` 分支改，并同步到所有使用处；
- 代码改动后重跑一次并更新 `code/results/`，再同步论文数字；
- 论文截止（冻结）后不再改代码；必须改时走 `fix/` 分支并说明影响。
