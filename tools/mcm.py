#!/usr/bin/env python3
"""mcm.py — 美赛（MCM/ICM）团队仓库管理助手。

零第三方依赖，要求 Python 3.11+（使用标准库 tomllib）与 Git 2.23+。

常用命令（在仓库根目录运行）：
    python tools/mcm.py new-hypo --title "SARIMA + 残差修正" --slug arima-residual --owner @zhangsan
    python tools/mcm.py new-part p1
    python tools/mcm.py log "完成问题一模型" --why "..." --result "RMSE=1.23"
    python tools/mcm.py status --write
    python tools/mcm.py check
    python tools/mcm.py snapshot
    python tools/mcm.py restore --list
    python tools/mcm.py release v1

完整说明见 MANUAL.md 与 docs/latex.md。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _force_utf8() -> None:
    """Windows 终端下统一用 UTF-8 输出，避免中文乱码。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


_force_utf8()

# ---------------------------------------------------------------------------
# 分支与文件约定
# ---------------------------------------------------------------------------
HYPO_RE = re.compile(r"^hypo/h(\d{2})-[a-z0-9][a-z0-9-]*$")
PART_RE = re.compile(r"^part/h(\d{2})/([a-z0-9][a-z0-9-]*)$")
FIX_RE = re.compile(r"^fix/[a-z0-9][a-z0-9-]*$")
RELEASE_RE = re.compile(r"^release/[a-z0-9][a-z0-9-]*$")
WIP_RE = re.compile(r"^wip/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")

PART_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STANDARD_PARTS = ("front", "p1", "p2", "p3", "sens", "eval", "misc")

#: 最终提交版（release/main）允许出现的顶层条目；.github 是唯一例外
PRODUCT_FILES = (
    "main.tex",
    "paper_content.tex",
    "abstract.tex",
    "appendix.tex",
    "mcmthesis.cls",
    "ref.bib",
)
PRODUCT_DIRS = ("code", "figures", "fonts")
GITHUB_DIR = ".github"

#: release 分支要删除的管理文件
MANAGEMENT_PATHS = (
    "README.md",
    "MANUAL.md",
    "docs",
    "tools",
    "journal",
    "project.toml",
    "hypo.toml",
    "STATUS.md",
    ".gitignore",
    ".gitattributes",
    "data",
)

STATUSES = ("idea", "active", "candidate", "adopted", "failed")
CARD_KEYS = ("id", "title", "owner", "status", "branch", "primary_metric")
REQUIRED_PARTS = ("front", "p1", "p2", "p3", "sens")
PR_SECTIONS = ("改动内容", "为什么改", "验证证据", "影响与回退", "检查清单")
PR_SECTION_MIN = 8
SIZE_WARN = 5 * 1024 * 1024
SIZE_FAIL = 15 * 1024 * 1024

# ---------------------------------------------------------------------------
# 终端输出与 Git 基础
# ---------------------------------------------------------------------------
_TTY = sys.stdout.isatty()


def _color(code: str) -> str:
    return f"\033[{code}m" if _TTY else ""


GREEN, RED, YELLOW, CYAN, RESET = _color("32"), _color("31"), _color("33"), _color("36"), _color("0")


class GitError(RuntimeError):
    """可直接展示给用户的错误。"""


def run(argv: list[str], check: bool = True) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            argv,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - 环境问题
        raise GitError(f"找不到命令 {argv[0]}，请先安装 Git / Python") from exc
    if check and proc.returncode != 0:
        raise GitError(f"命令失败：{' '.join(argv)}\n{proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def git(*argv: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git", *argv], check=check)


def info(msg: str) -> None:
    print(f"{CYAN}[mcm]{RESET} {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"{RED}[FAIL]{RESET} {msg}")


def require_repo() -> None:
    if not (ROOT / ".git").exists():
        raise GitError(f"{ROOT} 不是 Git 仓库根目录（先在仓库根目录运行 git init）")


def require_clean() -> None:
    out = git("status", "--porcelain", check=False).stdout.strip()
    if out:
        raise GitError(
            "工作区有未提交的改动，请先提交或暂存（git stash）后再执行本命令：\n" + out
        )


def branch_exists(name: str) -> bool:
    return git("show-ref", "--verify", "--quiet", f"refs/heads/{name}", check=False).returncode == 0


def remote_exists() -> bool:
    return git("remote", "get-url", "origin", check=False).returncode == 0


def current_branch() -> str:
    proc = git("rev-parse", "--abbrev-ref", "HEAD", check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "HEAD"


def resolve_ref(name: str) -> str | None:
    """把分支名解析成 commit sha；本地和 origin 都找不到时返回 None。"""
    for cand in (name, f"origin/{name}"):
        proc = git("rev-parse", "--verify", "-q", f"{cand}^{{commit}}", check=False)
        if proc.returncode == 0:
            return proc.stdout.strip()
    return None


def ref_time(ref: str) -> int:
    proc = git("log", "-1", "--format=%ct", ref, check=False)
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return 0


def list_branches() -> list[str]:
    out = git(
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads/",
        "refs/remotes/origin/",
        check=False,
    ).stdout.splitlines()
    names: list[str] = []
    for ref in out:
        if ref.startswith("refs/heads/"):
            names.append(ref[len("refs/heads/"):])
        elif ref.startswith("refs/remotes/origin/"):
            short = ref[len("refs/remotes/origin/"):]
            if short != "HEAD":
                names.append(short)
    return names


def safe_name(branch: str) -> str:
    """分支名 → 可安全用作文件名的字符串。"""
    return re.sub(r"[^A-Za-z0-9._-]+", "__", branch)


def journal_path(branch: str) -> str:
    return f"journal/branches/{safe_name(branch)}.md"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return dt.date.today().isoformat()


def commit_author() -> str:
    name = git("config", "user.name", check=False).stdout.strip()
    return name or "unknown"


def resolve_json_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 仓库文件读取
# ---------------------------------------------------------------------------
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(read_text(path))
    except tomllib.TOMLDecodeError as exc:
        raise GitError(f"{path.relative_to(ROOT)} 不是合法 TOML：{exc}") from exc


def load_project() -> dict:
    path = ROOT / "project.toml"
    if not path.is_file():
        return {}
    return load_toml(path).get("project", {})


def git_show(ref: str, path: str) -> str | None:
    proc = git("show", f"{ref}:{path}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def card_from_toml(text: str, where: str) -> dict:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise GitError(f"{where} 不是合法 TOML：{exc}") from exc
    return data


# ---------------------------------------------------------------------------
# 日志（可回溯性的核心）
# ---------------------------------------------------------------------------
def append_branch_log(
    branch: str,
    did: str,
    why: str = "",
    result: str = "",
    nxt: str = "",
) -> str:
    """向该分支的独立日志追加一条记录，返回文件相对路径。"""
    rel = journal_path(branch)
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# 分支日志：{branch}\n\n"
        "> 本文件只追加、不改写历史；由 `python tools/mcm.py log` 自动写入。\n"
        "> 任何推送前的重要动作都应在这里留一条记录。\n\n"
    )
    parts = [f"## {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · {commit_author()} · {branch}\n"]
    parts.append(f"- **做了什么**：{did}\n")
    if why:
        parts.append(f"- **为什么**：{why}\n")
    if result:
        parts.append(f"- **结果**：{result}\n")
    if nxt:
        parts.append(f"- **下一步**：{nxt}\n")
    parts.append("\n")
    entry = "".join(parts)
    text = read_text(path) if path.is_file() else header
    path.write_text(text + entry, encoding="utf-8")
    return rel


def render_card(hid: str, title: str, owner: str, branch: str, metric: str, problem: str) -> str:
    return (
        "# 假设卡片：一条假设 = 一个长驻分支 = 一份完整论文 + 代码 + 图。\n"
        "# status: idea | active | candidate | adopted | failed\n\n"
        "[hypo]\n"
        f"id = {resolve_json_str(hid)}\n"
        f"title = {resolve_json_str(title)}\n"
        f"owner = {resolve_json_str(owner)}\n"
        'status = "idea"\n'
        f"branch = {resolve_json_str(branch)}\n"
        f"created = {resolve_json_str(today())}\n"
        + (f"problem = {resolve_json_str(problem)}\n" if problem else "")
        + f"primary_metric = {resolve_json_str(metric)}\n\n"
        "[metrics]\n"
        "# 主指标与辅助指标写在这里，`status --write` 会汇总到 STATUS.md\n"
        "# rmse = 1.23\n\n"
        "[links]\n"
        "# issue = \"#12\"\n"
        "# decision = \"journal/decisions.md D003\"\n"
    )


def update_card(metrics: dict[str, object] | None = None, status: str | None = None) -> bool:
    """更新当前 hypo 分支上的 hypo.toml，返回是否有改动。"""
    path = ROOT / "hypo.toml"
    if not path.is_file():
        return False
    data = load_toml(path)
    hypo = data.get("hypo", {})
    changed = False
    if status:
        if status not in STATUSES:
            raise GitError(f"status 必须是 {'/'.join(STATUSES)} 之一")
        if hypo.get("status") != status:
            hypo["status"] = status
            changed = True
    if metrics:
        table = data.setdefault("metrics", {})
        for key, value in metrics.items():
            try:
                table[key] = float(value)
            except (TypeError, ValueError):
                table[key] = str(value)
            changed = True

    data["hypo"] = hypo
    lines = ["# 假设卡片：一条假设 = 一个长驻分支 = 一份完整论文 + 代码 + 图。",
             "# status: idea | active | candidate | adopted | failed", "", "[hypo]"]
    order = ("id", "title", "owner", "status", "branch", "created", "problem", "primary_metric")
    for key in order:
        if key in hypo:
            value = hypo[key]
            if isinstance(value, str):
                lines.append(f"{key} = {resolve_json_str(value)}")
            else:
                lines.append(f"{key} = {value}")
    lines += ["", "[metrics]"]
    for key, value in data.get("metrics", {}).items():
        lines.append(f"{key} = {value}")
    links = data.get("links", {})
    if links:
        lines += ["", "[links]"]
        for key, value in links.items():
            lines.append(f"{key} = {resolve_json_str(str(value))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.failures: list[str] = []

    def check(self, cond: bool, msg: str) -> None:
        if cond:
            ok(msg)
        else:
            self.fail(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        warn(msg)

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        fail(msg)

    def summary(self) -> int:
        print()
        if self.failures:
            fail(f"共 {len(self.failures)} 项未通过，{len(self.warnings)} 项警告")
            return 1
        if self.warnings:
            warn(f"检查通过，但有 {len(self.warnings)} 项警告")
        else:
            ok("全部检查通过")
        return 0


# ---------------------------------------------------------------------------
# new-hypo / new-part / new-fix
# ---------------------------------------------------------------------------
def next_hypo_id() -> str:
    ids = [int(m.group(1)) for name in list_branches() if (m := HYPO_RE.match(name))]
    return f"h{max(ids) + 1 if ids else 1:02d}"


def require_slug(text: str, what: str) -> None:
    if not PART_SLUG_RE.fullmatch(text):
        raise GitError(f"{what} 只能用小写字母、数字、连字符，例如 arima-residual")


def push_new_branch(branch: str, no_push: bool) -> None:
    if remote_exists() and not no_push:
        git("push", "-u", "origin", branch)
        info(f"已推送到 origin/{branch}")


def cmd_new_hypo(args: argparse.Namespace) -> int:
    require_repo()
    require_clean()
    require_slug(args.slug, "--slug")
    owner = args.owner
    if not owner.startswith("@"):
        raise GitError("--owner 必须是 GitHub 账号，以 @ 开头，例如 @zhangsan")
    hid = f"h{args.id:02d}" if args.id else next_hypo_id()
    if not re.fullmatch(r"h\d{2}", hid):
        raise GitError("--id 必须是 1-99 的编号")
    branch = f"hypo/{hid}-{args.slug}"
    if branch_exists(branch) or any(name == branch for name in list_branches()):
        raise GitError(f"分支已存在：{branch}")
    base = args.base
    if not resolve_ref(base):
        raise GitError(f"基准分支不存在：{base}（先在 main 上 git pull）")

    git("switch", "-c", branch, base)
    (ROOT / "hypo.toml").write_text(
        render_card(hid, args.title, owner, branch, args.metric, args.problem),
        encoding="utf-8",
    )
    log_rel = append_branch_log(
        branch,
        f"创建假设 {hid}「{args.title}」",
        why="提出一条可独立建模求解的假设，作为与其他假设对比的候选方案",
        result=f"分支 {branch} 建立，卡片 hypo.toml 初始化",
    )
    git("add", "hypo.toml", log_rel)
    git("commit", "-m", f"chore({hid}): 创建假设分支与卡片")
    info(f"假设分支已建立：{branch}（id={hid}）")
    info("下一步：在 MANUAL.md「场景 2」里开始建模；用 new-part 拆分写作，用 log 记录进展")
    push_new_branch(branch, args.no_push)
    return 0


def cmd_new_part(args: argparse.Namespace) -> int:
    require_repo()
    require_clean()
    branch = current_branch()
    match = HYPO_RE.match(branch)
    if not match:
        raise GitError("请先切换到假设分支（hypo/hNN-slug），再创建 part 分支")
    hid = f"h{match.group(1)}"
    slug = args.slug
    require_slug(slug, "--slug")
    new_branch = f"part/{hid}/{slug}"
    if branch_exists(new_branch):
        raise GitError(f"分支已存在：{new_branch}")
    title = args.title or slug
    git("switch", "-c", new_branch)
    log_rel = append_branch_log(
        new_branch,
        f"开始 part 分支：{title}",
        why="把写作/代码按问题拆分，减少并行修改同一文件的冲突",
        result=f"从 {branch} 创建，只改自己负责的 PART 块或目录",
    )
    git("add", log_rel)
    git("commit", "-m", f"chore({hid}/{slug}): 开始 part 分支")
    info(f"已创建 {new_branch}")
    info(f"完成后向 {branch} 提 PR（Squash 合并）；只改自己负责的 PART 块/目录")
    push_new_branch(new_branch, args.no_push)
    return 0


def cmd_new_fix(args: argparse.Namespace) -> int:
    require_repo()
    require_clean()
    slug = args.slug
    require_slug(slug, "--slug")
    base = args.base or current_branch()
    if not resolve_ref(base):
        raise GitError(f"起始分支不存在：{base}")
    branch = f"fix/{slug}"
    if branch_exists(branch):
        raise GitError(f"分支已存在：{branch}")
    git("switch", "-c", branch, base)
    log_rel = append_branch_log(
        branch,
        f"开始修复：{args.why or slug}",
        why=args.why or "修复缺陷",
        result=f"从 {base} 创建 fix 分支",
    )
    git("add", log_rel)
    git("commit", "-m", f"chore(fix): 开始修复 {slug}")
    info(f"已创建 {branch}（起点 {base}）")
    info(f"修复后向 {base} 提 PR（Squash）；同时把问题登记到 journal/bugs.md")
    push_new_branch(branch, args.no_push)
    return 0


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------
def _parse_metrics(items: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in items or []:
        if "=" not in item:
            raise GitError(f"--metric 需要 NAME=VALUE 形式，收到：{item}")
        name, value = item.split("=", 1)
        name = name.strip()
        if not name:
            raise GitError(f"--metric 名称不能为空：{item}")
        value = value.strip()
        try:
            result[name] = float(value)
        except ValueError:
            result[name] = value
    return result


def branch_scope(branch: str) -> str:
    for regex in (HYPO_RE, PART_RE):
        match = regex.match(branch)
        if match:
            return match.group(1) if regex is HYPO_RE else f"h{match.group(1)}/{match.group(2)}"
    if FIX_RE.match(branch):
        return "fix"
    if RELEASE_RE.match(branch):
        return "release"
    return "repo"


def cmd_log(args: argparse.Namespace) -> int:
    require_repo()
    branch = current_branch()
    if branch == "HEAD":
        raise GitError("当前处于 detached HEAD，请先切回分支")
    if not args.message.strip():
        raise GitError("请提供做了什么（第一个参数），例如：\"完成问题一模型\"")
    metrics = _parse_metrics(args.metric)
    if args.status and not HYPO_RE.match(branch):
        raise GitError("--status 只能在假设分支（hypo/...）上使用")
    if metrics and not HYPO_RE.match(branch):
        info("提示：--metric 只写入 hypo 分支的 hypo.toml；当前分支只记录日志")

    log_rel = append_branch_log(
        branch,
        args.message.strip(),
        why=args.why,
        result=args.result or (", ".join(f"{k}={v}" for k, v in metrics.items()) if metrics else ""),
        nxt=args.next,
    )
    staged = [log_rel]
    if metrics or args.status:
        if update_card(metrics or None, args.status):
            staged.append("hypo.toml")
    if args.no_commit:
        info(f"日志已写入 {log_rel}（--no-commit，未提交）")
        return 0
    git("add", *staged)
    subject = args.message.strip()
    if len(subject) > 60:
        subject = subject[:57] + "..."
    body_lines = []
    if args.why:
        body_lines.append(f"为什么：{args.why}")
    if args.result:
        body_lines.append(f"验证：{args.result}")
    commit_args = ["commit", "-m", f"exp({branch_scope(branch)}): {subject}"]
    if body_lines:
        commit_args += ["-m", "\n".join(body_lines)]
    git(*commit_args)
    ok(f"已记录并提交：{log_rel}")
    if remote_exists():
        info("别忘了 git push")
    return 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def collect_hypo_cards() -> list[dict]:
    """收集所有 hypo 分支的卡片：本地/远端同名时取提交较新的。"""
    refs: dict[str, tuple[str, int, str]] = {}
    out = git(
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads/hypo/",
        "refs/remotes/origin/hypo/",
        check=False,
    ).stdout.splitlines()
    for ref in out:
        if ref.startswith("refs/heads/"):
            name, read_ref = ref[len("refs/heads/"):], ref[len("refs/heads/"):]
        elif ref.startswith("refs/remotes/origin/"):
            name = ref[len("refs/remotes/origin/"):]
            read_ref = f"origin/{name}"
        else:
            continue
        match = HYPO_RE.match(name)
        if not match:
            continue
        hid = match.group(1)
        stamp = ref_time(read_ref)
        prev = refs.get(hid)
        if prev is None or stamp > prev[1]:
            refs[hid] = (read_ref, stamp, name)

    cards: list[dict] = []
    for hid in sorted(refs):
        read_ref, _stamp, branch = refs[hid]
        text = git_show(read_ref, "hypo.toml")
        card: dict = {"hid": hid, "branch": branch, "missing": True}
        if text:
            try:
                data = card_from_toml(text, f"{branch}:hypo.toml")
                hypo = data.get("hypo", {})
                card.update(
                    {
                        "missing": False,
                        "title": hypo.get("title", ""),
                        "owner": hypo.get("owner", ""),
                        "status": hypo.get("status", ""),
                        "primary_metric": hypo.get("primary_metric", ""),
                        "metrics": data.get("metrics", {}),
                    }
                )
            except GitError:
                card["missing"] = True
        log_text = git_show(read_ref, journal_path(branch))
        latest = "-"
        if log_text:
            headers = [line for line in log_text.splitlines() if line.startswith("## ")]
            if headers:
                latest = headers[-1][3:].strip()
        card["latest"] = latest
        cards.append(card)
    return cards


def render_status(cards: list[dict]) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    counts = {status: 0 for status in STATUSES}
    for card in cards:
        status = card.get("status", "")
        if status in counts:
            counts[status] += 1
    lines = [
        "<!-- 本文件由 `python tools/mcm.py status --write` 自动生成，请勿手改。 -->",
        "",
        "# 假设对比看板",
        "",
        f"生成时间（UTC）：{now_utc()}",
        f"共 {len(cards)} 条假设｜" + " · ".join(f"{k} {v}" for k, v in counts.items()),
        "",
        "| 假设 | 标题 | 负责人 | 状态 | 主指标 | 指标 | 最新日志 | 分支 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not cards:
        lines.append("| — | 还没有假设分支（用 `mcm.py new-hypo` 创建） | | | | | | |")
    for card in cards:
        if card.get("missing"):
            lines.append(
                f"| {card['hid']} | ⚠️ 缺少 hypo.toml | | | | | | {card['branch']} |"
            )
            continue
        metrics = card.get("metrics", {})
        shown = ", ".join(f"{k}={v}" for k, v in metrics.items()) or "-"
        primary = card.get("primary_metric", "") or "-"
        lines.append(
            f"| {cell(card['hid'])} | {cell(card['title'])} | {cell(card['owner'])} | "
            f"{cell(card['status'])} | {cell(primary)} | {cell(shown)} | "
            f"{cell(card['latest'])} | {cell(card['branch'])} |"
        )
    lines += [
        "",
        "## 说明",
        "",
        "- 本表只统计 `hypo/*` 假设分支；part/fix/wip 分支不进入看板。",
        "- 指标由各假设分支的 `hypo.toml` 维护，更新方法：",
        "  1. 切到假设分支；2. `python tools/mcm.py log \"...\" --metric rmse=1.23`；3. `git push`。",
        "- 更新本文件：`git pull` 后运行 `python tools/mcm.py status --write`，提交并推送。",
        "- 选定最终假设后，把该分支 `hypo.toml` 的 status 改为 `adopted`，再运行 `mcm.py release`。",
        "",
    ]
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    require_repo()
    if remote_exists() and not args.no_fetch:
        fetched = git("fetch", "origin", "--prune", check=False)
        if fetched.returncode != 0:
            warn("git fetch 失败，使用本地已有信息生成看板")
    cards = collect_hypo_cards()
    text = render_status(cards)
    if args.write:
        path = ROOT / "STATUS.md"
        path.write_text(text, encoding="utf-8")
        ok(f"已写入 STATUS.md（{len(cards)} 条假设）")
        info("提交并推送：git add STATUS.md && git commit -m \"docs(status): 更新假设看板\" && git push")
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------
def check_product_files(report: Report) -> None:
    for name in PRODUCT_FILES:
        report.check((ROOT / name).is_file(), f"产品文件存在：{name}")
    for name in ("code", "figures"):
        report.check((ROOT / name).is_dir(), f"产品目录存在：{name}/")
    report.check((ROOT / "code" / "README.md").is_file(), "code/README.md 存在（代码→论文对应表）")
    report.check((ROOT / "figures" / "README.md").is_file(), "figures/README.md 存在（图→论文对应表）")
    if (ROOT / "main.tex").is_file():
        main = read_text(ROOT / "main.tex")
        for part in ("abstract", "paper_content", "appendix"):
            report.check(f"\\input{{{part}}}" in main, f"main.tex 引入 {part}.tex")
        # 社区标准 mcmthesis v6 的结构与美赛合规项
        report.check("\\documentclass{mcmthesis}" in main, "main.tex 使用社区标准 mcmthesis 文档类")
        report.check("\\mcmsetup" in main, "main.tex 用 \\mcmsetup 配置队号/题号（Summary Sheet）")
        report.check("\\begin{abstract}" in main and "\\maketitle" in main,
                     "main.tex 用 abstract 环境 + \\maketitle 生成三栏 Summary Sheet")
        report.check("\\bibliography{ref}" in main, "main.tex 引用 ref.bib 生成参考文献")
        author = re.search(r"\\author\{([^}]*)\}", main)
        report.check(not (author and author.group(1).strip()),
                     "main.tex 的 \\author 为空（美赛禁止出现队员/学校姓名）")
    cls = ROOT / "mcmthesis.cls"
    if cls.is_file():
        cls_text = read_text(cls)
        report.check("ProvidesClass{mcmthesis}" in cls_text or "mcmthesis" in cls_text,
                     "mcmthesis.cls 为社区标准类文件")
        report.check("v6.3.3" in cls_text or "The Thesis Template Designed For MCM/ICM" in cls_text,
                     "mcmthesis.cls 版本为 v6.3.3（CTAN 社区标准）")
    appendix = ROOT / "appendix.tex"
    if appendix.is_file():
        app = read_text(appendix)
        report.check("\\AImatter" in app, "appendix.tex 用 \\AImatter 标记 25 页界（AI 报告不计页数）")
        report.check("ReportAiUse" in app, "appendix.tex 含 Report on Use of AI 声明节")


def check_parts(report: Report) -> None:
    path = ROOT / "paper_content.tex"
    if not path.is_file():
        return
    text = read_text(path)
    found = re.findall(r"^%\s*=+\s*PART\s+([A-Za-z0-9_]+)\s*=+", text, flags=re.MULTILINE)
    for part in REQUIRED_PARTS:
        report.check(part in found, f"paper_content.tex 含 PART {part} 标记")
    if "eval" not in found:
        report.warn("paper_content.tex 缺少 PART eval（模型评价与结论）标记")
    if found:
        ok(f"PART 标记：{' → '.join(found)}")


def tex_files() -> list[Path]:
    return sorted(p for p in ROOT.glob("*.tex") if p.is_file())


def strip_tex_comments(text: str) -> str:
    """去掉 LaTeX 注释（保留转义百分号 \\%），避免把示例命令当成真实引用。"""
    lines = []
    for line in text.splitlines():
        out: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            out.append(ch)
            i += 1
        lines.append("".join(out))
    return "\n".join(lines)


def check_figures(report: Report) -> None:
    referenced: set[str] = set()
    for tex in tex_files():
        text = strip_tex_comments(read_text(tex))
        for match in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            raw = match.group(1).strip()
            if raw.startswith("#"):  # 宏定义中的参数占位
                continue
            candidate = ROOT / raw
            if not candidate.suffix:
                for suffix in (".pdf", ".png", ".jpg", ".jpeg"):
                    if (ROOT / f"{raw}{suffix}").is_file():
                        candidate = ROOT / f"{raw}{suffix}"
                        break
            rel = candidate.relative_to(ROOT).as_posix()
            report.check(candidate.is_file(), f"图文件存在：{rel}")
            referenced.add(rel)
        # main.tex 定义的 \mcmfigure{路径}{caption}{label}（可带可选位置参数）
        for match in re.finditer(r"\\mcmfigure(?:\[[^\]]*\])?\{([^}]+)\}", text):
            raw = match.group(1).strip()
            candidate = ROOT / raw
            rel = candidate.relative_to(ROOT).as_posix()
            report.check(candidate.is_file(), f"图文件存在（\\mcmfigure）：{rel}")
            referenced.add(rel)

    fig_root = ROOT / "figures"
    if not fig_root.is_dir():
        return
    for path in sorted(fig_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in (".pdf", ".png", ".jpg", ".jpeg"):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel not in referenced:
            report.warn(f"图未被论文引用：{rel}")
    if referenced:
        ok(f"论文引用 {len(referenced)} 张图，均存在")
    else:
        report.warn("论文还没有引用任何图（\\includegraphics），写正文时记得加")


def bib_keys() -> dict[str, str]:
    path = ROOT / "ref.bib"
    if not path.is_file():
        return {}
    keys: dict[str, str] = {}
    current: list[str] = []
    for line in read_text(path).splitlines():
        if line.startswith("@"):
            current = [line]
        elif current:
            current.append(line)
            if line.strip() in ("}", "},"):
                text = "\n".join(current)
                match = re.search(r"@\w+\s*\{\s*([^,\s]+)\s*,", text)
                if match:
                    keys[match.group(1)] = text
                current = []
    return keys


def check_citations(report: Report) -> None:
    entries = bib_keys()
    cited: set[str] = set()
    for tex in tex_files():
        text = read_text(tex)
        for match in re.finditer(r"\\cite[a-zA-Z]*\{([^}]*)\}", text):
            for key in match.group(1).split(","):
                key = key.strip()
                if key:
                    cited.add(key)
    for key in sorted(cited):
        report.check(key in entries, f"参考文献存在：{key}")
    for key in sorted(set(entries) - cited):
        report.warn(f"参考文献未被引用：{key}")
    ok(f"论文引用 {len(cited)} 个文献，ref.bib 共 {len(entries)} 条")


LATEX_ARTIFACTS = {
    ".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out",
    ".synctex.gz", ".toc", ".lof", ".lot", ".nav", ".snm", ".vrb",
}


def check_hygiene(report: Report) -> None:
    """只检查已经被 Git 跟踪的文件；被 .gitignore 忽略的本地数据不算问题。"""
    proc = git("ls-files", check=False)
    tracked = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not tracked:
        report.warn("仓库还没有任何提交，跳过入库文件检查")
        return
    for rel in tracked:
        path = ROOT / rel
        if path.suffix in (".pyc", ".zip", ".7z"):
            report.fail(f"不应入库的文件：{rel}")
            continue
        if path.name == ".env" or rel.startswith(("data/", "code/data/", "secrets/")):
            report.fail(f"不应入库的文件：{rel}")
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > SIZE_FAIL:
            report.fail(f"文件过大（>{SIZE_FAIL // 1024 // 1024}MB）：{rel}")
        elif size > SIZE_WARN:
            report.warn(f"文件较大（>{SIZE_WARN // 1024 // 1024}MB）：{rel}（数据/大文件不入库）")
    report.check((ROOT / ".gitignore").is_file(), ".gitignore 存在，防止误提交数据与大文件")


def check_management_files(report: Report) -> None:
    if not (ROOT / "tools").is_dir():
        return
    for rel in ("journal/team.md", "journal/decisions.md", "journal/bugs.md", "MANUAL.md"):
        report.check((ROOT / rel).is_file(), f"管理文件存在：{rel}")
    branch = current_branch()
    if branch not in ("main", "HEAD") and not (ROOT / journal_path(branch)).is_file():
        report.warn(f"当前分支还没有日志：{journal_path(branch)}（用 mcm.py log 记一条）")


def check_branch(report: Report) -> None:
    branch = current_branch()
    if branch == "HEAD":
        report.warn("当前处于 detached HEAD")
        return
    if branch == "main":
        ok("当前分支：main（提交版）")
        return
    known = (HYPO_RE, PART_RE, FIX_RE, RELEASE_RE, WIP_RE)
    if any(regex.match(branch) for regex in known):
        ok(f"当前分支名符合规范：{branch}")
    else:
        report.warn(f"当前分支名不在规范内（自由分支请加 wip/）：{branch}")


def check_hypo_card(report: Report) -> None:
    branch = current_branch()
    if not HYPO_RE.match(branch):
        return
    path = ROOT / "hypo.toml"
    if not path.is_file():
        report.fail("假设分支缺少 hypo.toml 卡片")
        return
    data = load_toml(path)
    hypo = data.get("hypo", {})
    for key in CARD_KEYS:
        report.check(bool(str(hypo.get(key, "")).strip()), f"hypo.toml 含 {key}")
    if hypo.get("status") not in STATUSES:
        report.fail(f"hypo.toml 的 status 必须是 {'/'.join(STATUSES)}")
    if hypo.get("branch") != branch:
        report.fail(f"hypo.toml 的 branch 与实际分支不一致（{hypo.get('branch')} != {branch}）")
    if not isinstance(data.get("metrics", {}), dict):
        report.fail("hypo.toml 的 [metrics] 必须是表格")


def release_tree_entries(ref: str) -> list[str]:
    proc = git("ls-tree", "--name-only", ref, check=False)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def allowed_root_entries() -> set[str]:
    return set(PRODUCT_FILES) | set(PRODUCT_DIRS) | {GITHUB_DIR}


def check_release_tree(report: Report, ref: str) -> None:
    entries = release_tree_entries(ref)
    if not entries:
        report.fail(f"无法读取 {ref} 的顶层文件树")
        return
    allowed = allowed_root_entries()
    extra = [name for name in entries if name not in allowed]
    missing = [name for name in PRODUCT_FILES if name not in entries]
    for name in extra:
        report.fail(f"提交版不应包含：{name}")
    for name in missing:
        report.fail(f"提交版缺少产品文件：{name}")
    if not extra and not missing:
        ok(f"提交版文件树符合要求（{len(entries)} 个顶层条目，含 .github 例外）")


def check_placeholders(report: Report) -> None:
    if not (ROOT / "project.toml").is_file():
        report.warn("当前分支没有 project.toml（提交版分支属正常）")
        return
    project = load_project()
    checks = [
        ("team_control_number", project.get("team_control_number")),
        ("captain", project.get("captain")),
        ("repo", project.get("repo")),
        ("problem", project.get("problem")),
    ]
    for key, value in checks:
        text = str(value or "")
        if not text or text in ("0000000", "unknown") or text.startswith("@your") or text.startswith("your-org"):
            report.warn(f"project.toml 的 {key} 还是占位符：{text!r}")
    main = ROOT / "main.tex"
    if main.is_file():
        main_text = read_text(main)
        if "Your Paper Title" in main_text:
            report.warn("main.tex 标题还是占位符 Your Paper Title")
        if re.search(r"tcn\s*=\s*0{7}", main_text):
            report.warn("main.tex 的 \\mcmsetup tcn 还是占位队号 0000000")
        if re.search(r"problem\s*=\s*[A-F]\b", main_text) and str(project.get("problem")) in ("", "unknown"):
            report.warn("project.toml 的 problem 还是 unknown（选题后填 A-F）")
    abstract = ROOT / "abstract.tex"
    if abstract.is_file() and "Write one to two paragraphs here" in read_text(abstract):
        report.warn("abstract.tex 摘要还是占位文本（最后一步必须重写）")
    appendix = ROOT / "appendix.tex"
    if appendix.is_file() and "Describe here every AI tool you used" in read_text(appendix):
        report.warn("appendix.tex 的 Report on Use of AI 还是占位文本（无 AI 使用也需写一句声明）")
    figures_readme = ROOT / "figures" / "README.md"
    if figures_readme.is_file() and "fig_q1_xxx.pdf" in read_text(figures_readme):
        report.warn("figures/README.md 对应关系表还是示例行，请替换为真实图")


def check_hooks(report: Report) -> None:
    hook = ROOT / ".git" / "hooks" / "commit-msg"
    if hook.is_file():
        ok("已安装 commit-msg 钩子（提交信息校验）")
    else:
        report.warn("未安装 commit-msg 钩子：运行 bash tools/install-hooks.sh")


def run_all_checks(setup: bool = False, submission: bool = False) -> int:
    report = Report()
    check_product_files(report)
    check_parts(report)
    check_figures(report)
    check_citations(report)
    check_hygiene(report)
    check_branch(report)
    check_hypo_card(report)
    check_management_files(report)
    check_hooks(report)
    branch = current_branch()
    if RELEASE_RE.match(branch) or submission:
        check_release_tree(report, "HEAD")
    if setup:
        check_placeholders(report)
    return report.summary()


def cmd_check(args: argparse.Namespace) -> int:
    require_repo()
    return run_all_checks(setup=args.setup, submission=args.submission)


# ---------------------------------------------------------------------------
# pr-check
# ---------------------------------------------------------------------------
def validate_pr_head(report: Report, head: str, base: str) -> None:
    if head == "main":
        report.fail("main 不能作为 PR 的源分支")
        return
    if HYPO_RE.match(head):
        report.fail("假设分支不能直接合入 main：请先 mcm.py release 生成 release 分支")
        return
    match = PART_RE.match(head)
    if match:
        hid = f"h{match.group(1)}"
        if not re.fullmatch(rf"hypo/{hid}-[a-z0-9][a-z0-9-]*", base):
            report.fail(f"part 分支必须合回同一个假设分支 hypo/{hid}-*，当前目标：{base}")
        else:
            ok(f"PR 目标合法：{head} → {base}（Squash 合并）")
        return
    if FIX_RE.match(head):
        if base == "wip" or WIP_RE.match(base):
            report.fail("fix 不能合入 wip 分支")
        elif base not in ("main",) and not (HYPO_RE.match(base) or PART_RE.match(base) or RELEASE_RE.match(base)):
            report.fail(f"fix 分支的目标分支不合法：{base}")
        else:
            ok(f"PR 目标合法：{head} → {base}（Squash 合并）")
        return
    if RELEASE_RE.match(head):
        if base != "main":
            report.fail(f"release 分支只能合入 main，当前目标：{base}")
        else:
            ok(f"PR 目标合法：{head} → main（Merge commit 合并）")
        return
    if WIP_RE.match(head):
        report.fail("wip 分支是自由草稿，不发起 PR，也不合并")
        return
    report.fail(f"未知分支类型，不能发起 PR：{head}")


def section_text(body: str, name: str) -> str:
    pattern = re.compile(rf"^##\s*{re.escape(name)}\s*$", re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    rest = body[match.end():]
    nxt = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    section = rest[: nxt.start()] if nxt else rest
    return section.strip()


def validate_pr_body(report: Report, body: str, title: str = "") -> None:
    clean = re.sub(r"<!--.*?-->", "", body or "", flags=re.DOTALL)
    if "TODO" in clean:
        report.fail("PR 描述里还有 TODO，请填写完整")
    for name in PR_SECTIONS:
        text = section_text(clean, name)
        if name == "检查清单":
            has_box = bool(re.search(r"^\s*-\s*\[[ xX]\]", text, flags=re.MULTILINE))
            report.check(has_box, "PR 模板含检查清单 checkbox")
            continue
        stripped = re.sub(r"^\s*-\s*\[[ xX]\]\s*", "", text, flags=re.MULTILINE).strip()
        report.check(len(stripped) >= PR_SECTION_MIN, f"PR 描述已填写「{name}」")
    if title and not (title.startswith("[") or title.startswith("Merge")):
        report.warn("PR 标题建议以 [类型] 开头，例如 [paper] 问题二模型")


def changed_files(base_ref: str, head_ref: str) -> list[str]:
    proc = git("diff", "--name-only", f"{base_ref}...{head_ref}", check=False)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def check_forbidden_files(report: Report, files: list[str]) -> None:
    for rel in files:
        path = Path(rel)
        if path.name in (".env",) or path.suffix in (".pyc", ".zip", ".7z"):
            report.fail(f"PR 中含不应入库的文件：{rel}")
        if rel.startswith(("data/", "code/data/", "__pycache__/", ".venv/", "venv/")):
            report.fail(f"PR 中含不应入库的文件：{rel}")
        if (ROOT / rel).is_file() and (ROOT / rel).stat().st_size > SIZE_FAIL:
            report.fail(f"PR 中含过大的文件：{rel}")


def check_commit_subjects(report: Report, base_ref: str, head_ref: str) -> None:
    proc = git("log", "--format=%s", f"{base_ref}..{head_ref}", check=False)
    pattern = re.compile(r"^(feat|fix|exp|paper|data|docs|release|chore|merge)(\([a-z0-9][a-z0-9._/-]*\))?!?: \S")
    bad = [line for line in proc.stdout.splitlines() if line.strip() and not pattern.match(line)]
    for line in bad:
        report.warn(f"提交信息不符合规范（建议 type(scope): 说明）：{line}")


def run_pr_checks(head: str, base: str, body: str, title: str) -> int:
    report = Report()
    validate_pr_head(report, head, base)
    validate_pr_body(report, body, title)
    base_ref = resolve_ref(base)
    head_ref = resolve_ref(head)
    if not base_ref or not head_ref:
        report.fail(f"无法解析分支：base={base!r} head={head!r}（本地请先 git fetch origin）")
        return report.summary()
    files = changed_files(base_ref, head_ref)
    ok(f"改动文件 {len(files)} 个")
    check_forbidden_files(report, files)
    if RELEASE_RE.match(head):
        check_release_tree(report, head_ref)
        changed_management = [
            rel for rel in files
            if rel.split("/")[0] in ("docs", "tools", "journal", "README.md", "MANUAL.md", "project.toml")
        ]
        if changed_management:
            report.warn(f"release PR 改动了管理文件（应已被裁剪）：{changed_management[:5]}")
    check_commit_subjects(report, base_ref, head_ref)
    return report.summary()


def cmd_pr_check(args: argparse.Namespace) -> int:
    head = args.head or os.environ.get("HEAD_REF", "")
    base = args.base or os.environ.get("BASE_REF", "")
    title = args.title or os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "") if args.body is None else args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    head = head or current_branch()
    base = base or "main"
    info(f"PR 检查：{head} → {base}")
    return run_pr_checks(head, base, body, title)


# ---------------------------------------------------------------------------
# release
# ---------------------------------------------------------------------------
def prune_management_files() -> None:
    for name in MANAGEMENT_PATHS:
        path = ROOT / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def validate_release_worktree() -> tuple[list[str], list[str]]:
    allowed = allowed_root_entries()
    entries = {p.name for p in ROOT.iterdir() if p.name != ".git"}
    extra = sorted(entries - allowed)
    missing = sorted(
        [name for name in PRODUCT_FILES if name not in entries]
        + [name for name in ("code", "figures") if name not in entries]
    )
    return extra, missing


def cmd_release(args: argparse.Namespace) -> int:
    require_repo()
    require_clean()
    branch = current_branch()
    match = HYPO_RE.match(branch)
    if not match:
        raise GitError("请在假设分支（hypo/hNN-slug）上运行 release")
    hid = match.group(1)
    slug = args.slug
    require_slug(slug, "release 名称")
    card_path = ROOT / "hypo.toml"
    if not card_path.is_file():
        raise GitError("当前假设分支缺少 hypo.toml")
    card = load_toml(card_path)
    hypo = card.get("hypo", {})
    if hypo.get("status") != "adopted" and not args.force:
        raise GitError("当前假设的 status 还不是 adopted：确认选它作为最终方案后，用 log --status adopted 更新，或加 --force")
    for name in PRODUCT_FILES:
        if not (ROOT / name).is_file():
            raise GitError(f"缺少产品文件：{name}，不能生成提交版")

    info("先运行完整自检 ...")
    if run_all_checks() != 0 and not args.force:
        raise GitError("自检未通过，先修复后再 release（或加 --force）")

    branch_out = f"release/{slug}"
    if branch_exists(branch_out):
        raise GitError(f"分支已存在：{branch_out}")
    project = load_project()
    git("switch", "-c", branch_out)

    try:
        prune_management_files()
        extra, missing = validate_release_worktree()
        if extra or missing:
            raise GitError(f"提交版文件树不符合要求：多余 {extra}，缺少 {missing}")
        git("add", "-A")
        tree = git("write-tree").stdout.strip()
        entries = git("ls-tree", "--name-only", tree).stdout.split()
        allowed = allowed_root_entries()
        unexpected = sorted(set(entries) - allowed)
        missing_files = sorted(set(PRODUCT_FILES) - set(entries))
        if unexpected or missing_files:
            raise GitError(f"提交版文件树不符合要求：多余 {unexpected}，缺少 {missing_files}")
        git(
            "commit",
            "--no-verify",
            "-m",
            f"release({slug}): 生成提交版论文树",
            "-m",
            (
                f"由假设分支 {branch} 生成；仅保留产品文件与 .github（CI 必需）。\n"
                f"假设：{hypo.get('title', '')}（{hid}）"
            ),
        )
    except GitError:
        git("switch", "-f", branch)
        git("branch", "-D", branch_out, check=False)
        raise

    info(f"提交版分支已生成：{branch_out}")
    print()
    print("接下来：")
    print(f"  1. git push -u origin {branch_out}")
    print("  2. 在 GitHub 开 PR：head = release/%s → base = main，标题写 [release] %s" % (slug, slug))
    print("     （release → main 必须使用 Merge commit，保留假设分支的完整历史）")
    year = project.get("year", "")
    problem = project.get("problem", "")
    tag = f"submit-{year}-{problem}-{slug}"
    print(f"  3. 合并后在 main 上打提交标签：")
    print(f"     git tag -a {tag} -m \"MCM/ICM {year} Problem {problem} 提交版 {slug}\"")
    print(f"     git push origin {tag}")
    print("  4. 提交完成后在假设分支上运行归档（main 裁剪后没有 tools）：")
    print(f"     python tools/mcm.py snapshot --branch main --name submitted-{tag}")
    if remote_exists() and not args.no_push:
        git("push", "-u", "origin", branch_out)
        info(f"已推送 {branch_out}")
    return 0


# ---------------------------------------------------------------------------
# snapshot / restore
# ---------------------------------------------------------------------------
def archive_refs() -> list[str]:
    out = git("for-each-ref", "--format=%(refname)\t%(committerdate:iso8601-strict)\t%(subject)",
              "refs/archive/", check=False).stdout
    refs = []
    for line in out.splitlines():
        if "\t" in line:
            refs.append(line)
    return sorted(refs)


def cmd_snapshot(args: argparse.Namespace) -> int:
    require_repo()
    branch = args.branch or current_branch()
    if branch == "HEAD":
        raise GitError("detached HEAD 请用 --branch 指定分支名")
    target = args.branch or "HEAD"
    try:
        sha = git("rev-parse", "--short=7", target).stdout.strip()
    except GitError:
        raise GitError(f"找不到要快照的分支/提交：{target}")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"-{safe_name(args.name)}" if args.name else ""
    ref = f"refs/archive/{safe_name(branch)}/{stamp}{name}-{sha}"
    git("update-ref", ref, target)
    info(f"本地快照：{ref}（{branch} @ {sha}）")
    if remote_exists() and not args.no_push:
        git("push", "origin", ref)
        info("已推送到远端（GitHub 上作为不可变归档保留）")
    else:
        warn("未推送到远端；远端归档由 GitHub Actions 的 archive.yml 自动完成")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    require_repo()
    if remote_exists():
        git("fetch", "origin", "+refs/archive/*:refs/archive/*", check=False)
    refs = archive_refs()
    if args.list or not args.ref:
        if not refs:
            info("还没有任何归档快照（分支 push 后由 archive.yml 自动生成，或本地 mcm.py snapshot）")
            return 0
        print("可用归档快照（ref 时间 提交主题）：")
        for line in refs:
            ref, when, subject = line.split("\t", 2)
            print(f"  {ref}\n    {when}  {subject[:60]}")
        info("恢复：python tools/mcm.py restore --ref <ref 的一部分>")
        return 0

    matches = [line for line in refs if args.ref in line]
    if not matches:
        raise GitError(f"没有匹配 `{args.ref}` 的归档，用 --list 查看全部")
    if len(matches) > 1:
        raise GitError(f"`{args.ref}` 匹配到 {len(matches)} 个归档，请给更精确的片段：\n" +
                       "\n".join(line.split("\t")[0] for line in matches[:10]))
    ref = matches[0].split("\t")[0]
    sha = git("rev-parse", "--short=7", ref).stdout.strip()
    branch = args.branch or f"fix/restore-{sha}"
    if branch_exists(branch):
        raise GitError(f"分支已存在：{branch}")
    git("switch", "-c", branch, ref)
    info(f"已从 {ref} 恢复出分支 {branch}（提交 {sha}）")
    info("确认内容后：修好开 PR，或把需要的文件复制回当前工作分支")
    return 0


# ---------------------------------------------------------------------------
# check-commit（本地钩子）
# ---------------------------------------------------------------------------
COMMIT_TYPES = "feat|fix|exp|paper|data|docs|release|chore|merge"
COMMIT_RE = re.compile(rf"^({COMMIT_TYPES})(\([a-z0-9][a-z0-9._/-]*\))?!?: \S")


def cmd_check_commit(args: argparse.Namespace) -> int:
    path = Path(args.message_file)
    if not path.is_file():
        raise GitError(f"找不到提交信息文件：{path}")
    lines = [line.rstrip() for line in read_text(path).splitlines()]
    subject = lines[0] if lines else ""
    if re.match(r"^(Merge|Revert|fixup!|squash!|amend!)", subject):
        return 0
    if not COMMIT_RE.match(subject):
        fail("提交信息格式不符合规范")
        print("  正确格式：type(scope): 说明")
        print(f"  允许的 type：{COMMIT_TYPES.replace('|', ' / ')}")
        print("  例：paper(p2): 补充问题二模型推导")
        print("  例：exp(h01): 尝试对数变换，RMSE 降到 1.18")
        return 1
    body = "\n".join(lines[1:])
    if re.match(r"^(feat|fix|exp|paper|fix)", subject.split("(")[0].split(":")[0]):
        if "为什么" not in body and "验证" not in body and not subject.startswith("chore"):
            print(f"{YELLOW}[提示]{RESET} 建议在提交正文里写「为什么」和「验证」")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcm.py",
        description="美赛（MCM/ICM）仓库管理助手：分支、日志、看板、检查、发布、归档",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new-hypo", help="创建一条假设分支（hypo/hNN-slug）")
    p.add_argument("--title", required=True, help="假设标题")
    p.add_argument("--slug", required=True, help="英文短名，例如 arima-residual")
    p.add_argument("--owner", required=True, help="负责人 GitHub 账号，例如 @zhangsan")
    p.add_argument("--id", type=int, default=None, help="手动指定编号（默认自动递增）")
    p.add_argument("--metric", default="rmse", help="主指标名（默认 rmse）")
    p.add_argument("--problem", default="", help="对应问题，例如 q1")
    p.add_argument("--base", default="main", help="从哪个分支创建（默认 main）")
    p.add_argument("--no-push", action="store_true", help="不自动 push")
    p.set_defaults(func=cmd_new_hypo)

    p = sub.add_parser("new-part", help="在假设分支内创建写作/代码子分支 part/hNN/slug")
    p.add_argument("slug", help="子任务名：front/p1/p2/p3/sens/eval/misc 或自定义")
    p.add_argument("--title", default="", help="子任务说明")
    p.add_argument("--no-push", action="store_true", help="不自动 push")
    p.set_defaults(func=cmd_new_part)

    p = sub.add_parser("new-fix", help="创建修复分支 fix/slug")
    p.add_argument("--slug", required=True, help="修复短名，例如 q1-reindex")
    p.add_argument("--base", default="", help="从哪个分支修（默认当前分支）")
    p.add_argument("--why", default="", help="修复的问题描述")
    p.add_argument("--no-push", action="store_true", help="不自动 push")
    p.set_defaults(func=cmd_new_fix)

    p = sub.add_parser("log", help="记录一条实验/修改日志（可回溯性的核心）")
    p.add_argument("message", help="做了什么")
    p.add_argument("--why", default="", help="为什么这么做")
    p.add_argument("--result", default="", help="结果/证据（数字）")
    p.add_argument("--next", default="", help="下一步")
    p.add_argument("--metric", action="append", default=[], help="写入卡片的指标 NAME=VALUE，可重复")
    p.add_argument("--status", default="", help="更新假设状态：idea/active/candidate/adopted/failed")
    p.add_argument("--no-commit", action="store_true", help="只写文件不提交")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("status", help="生成/查看假设对比看板")
    p.add_argument("--write", action="store_true", help="写入 STATUS.md")
    p.add_argument("--no-fetch", action="store_true", help="不执行 git fetch")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("check", help="自检：产品文件、论文一致性、仓库卫生、分支规范")
    p.add_argument("--setup", action="store_true", help="额外检查模板占位符是否已替换")
    p.add_argument("--submission", action="store_true", help="按提交版标准检查当前文件树")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("pr-check", help="检查一个 PR 是否合规（CI 与本地共用）")
    p.add_argument("--head", default="", help="源分支（默认读 env HEAD_REF 或当前分支）")
    p.add_argument("--base", default="", help="目标分支（默认读 env BASE_REF 或 main）")
    p.add_argument("--title", default="", help="PR 标题（默认读 env PR_TITLE）")
    p.add_argument("--body", default=None, help="PR 描述正文")
    p.add_argument("--body-file", default="", help="从文件读取 PR 描述")
    p.set_defaults(func=cmd_pr_check)

    p = sub.add_parser("release", help="从当前假设分支生成裁剪后的提交版 release/slug")
    p.add_argument("slug", help="版本名，例如 v1")
    p.add_argument("--force", action="store_true", help="跳过 status=adopted 与自检未通过的拦截")
    p.add_argument("--no-push", action="store_true", help="不自动 push")
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("snapshot", help="给指定提交打不可变归档快照 refs/archive/...")
    p.add_argument("--name", default="", help="快照名（可选）")
    p.add_argument("--branch", default="", help="要快照的分支（默认当前分支；裁剪后的 main 可在其他分支上用它）")
    p.add_argument("--no-push", action="store_true", help="不推送远端")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("restore", help="列出/恢复归档快照")
    p.add_argument("--list", action="store_true", help="列出所有归档")
    p.add_argument("--ref", default="", help="归档 ref 的一部分（唯一匹配即可）")
    p.add_argument("--branch", default="", help="恢复出的新分支名（默认 fix/restore-<sha>）")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("check-commit", help="校验提交信息（供 commit-msg 钩子调用）")
    p.add_argument("message_file", help="提交信息文件路径")
    p.set_defaults(func=cmd_check_commit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except GitError as exc:
        fail(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
