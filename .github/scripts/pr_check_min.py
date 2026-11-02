#!/usr/bin/env python3
"""轻量 PR 检查：main / release 分支裁剪掉 tools/ 之后由 CI 使用。

与 tools/mcm.py pr-check 保持相同的「分支规则 + PR 描述 + release 文件树」
检查口径，但不检查卡片与提交信息（那些需要管理文件）。
环境变量：HEAD_REF / BASE_REF / PR_TITLE / PR_BODY
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HYPO = re.compile(r"^hypo/h(\d{2})-[a-z0-9][a-z0-9-]*$")
PART = re.compile(r"^part/h(\d{2})/[a-z0-9][a-z0-9-]*$")
FIX = re.compile(r"^fix/[a-z0-9][a-z0-9-]*$")
RELEASE = re.compile(r"^release/[a-z0-9][a-z0-9-]*$")
WIP = re.compile(r"^wip/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")

PRODUCT_FILES = (
    "main.tex", "paper_content.tex", "abstract.tex",
    "appendix.tex", "mcmthesis.cls", "ref.bib",
)
PRODUCT_DIRS = ("code", "figures", "fonts")
GITHUB_DIR = ".github"
ALLOWED = set(PRODUCT_FILES) | set(PRODUCT_DIRS) | {GITHUB_DIR}

SECTIONS = ("改动内容", "为什么改", "验证证据", "影响与回退", "检查清单")
MIN_CHARS = 8

warnings: list[str] = []
failures: list[str] = []


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"::error::{msg}")


def check(cond: bool, msg: str) -> None:
    if cond:
        ok(msg)
    else:
        fail(msg)


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], text=True, encoding="utf-8",
                          errors="replace", capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def check_branch(head: str, base: str) -> None:
    if head == "main":
        fail("main 不能作为 PR 的源分支")
    elif HYPO.match(head):
        fail("假设分支不能直接合入 main：请先 mcm.py release 生成 release 分支")
    elif PART.match(head):
        hid = f"h{PART.match(head).group(1)}"
        check(bool(re.fullmatch(rf"hypo/{hid}-[a-z0-9][a-z0-9-]*", base)),
              f"part 分支必须合回同一个假设分支 hypo/{hid}-*，当前目标：{base}")
    elif FIX.match(head):
        allowed = base == "main" or HYPO.match(base) or PART.match(base) or RELEASE.match(base)
        check(bool(allowed), f"fix 分支的目标分支不合法：{base}")
    elif RELEASE.match(head):
        check(base == "main", f"release 分支只能合入 main，当前目标：{base}")
    elif WIP.match(head):
        fail("wip 分支是自由草稿，不发起 PR，也不合并")
    else:
        fail(f"未知分支类型，不能发起 PR：{head}")


def section_text(body: str, name: str) -> str:
    match = re.search(rf"^##\s*{re.escape(name)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end():]
    nxt = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return (rest[: nxt.start()] if nxt else rest).strip()


def check_body(body: str, title: str) -> None:
    clean = re.sub(r"<!--.*?-->", "", body or "", flags=re.DOTALL)
    if "TODO" in clean:
        fail("PR 描述里还有 TODO，请填写完整")
    for name in SECTIONS:
        text = section_text(clean, name)
        if name == "检查清单":
            check(bool(re.search(r"^\s*-\s*\[[ xX]\]", text, flags=re.MULTILINE)),
                  "PR 模板含检查清单 checkbox")
        else:
            stripped = re.sub(r"^\s*-\s*\[[ xX]\]\s*", "", text, flags=re.MULTILINE).strip()
            check(len(stripped) >= MIN_CHARS, f"PR 描述已填写「{name}」")
    if title and not (title.startswith("[") or title.startswith("Merge")):
        warn("PR 标题建议以 [类型] 开头，例如 [paper] 问题二模型")


def check_release_tree() -> None:
    entries = [line.strip() for line in git("ls-tree", "--name-only", "HEAD").splitlines() if line.strip()]
    extra = [name for name in entries if name not in ALLOWED]
    missing = [name for name in PRODUCT_FILES if name not in entries]
    for name in extra:
        fail(f"提交版不应包含：{name}")
    for name in missing:
        fail(f"提交版缺少产品文件：{name}")
    if not extra and not missing:
        ok(f"提交版文件树符合要求（{len(entries)} 个顶层条目，含 .github 例外）")


def check_files(base: str) -> None:
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base}...HEAD"],
            text=True, encoding="utf-8", errors="replace", capture_output=True,
        )
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:  # pragma: no cover
        files = []
    for rel in files:
        path = rel.rsplit("/", 1)[-1]
        if path in (".env",) or rel.endswith((".pyc", ".zip", ".7z")):
            fail(f"PR 中含不应入库的文件：{rel}")
        if rel.startswith(("data/", "code/data/", "secrets/")):
            fail(f"PR 中含不应入库的文件：{rel}")


def main() -> int:
    head = os.environ.get("HEAD_REF", "")
    base = os.environ.get("BASE_REF", "")
    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "")
    print(f"PR 检查：{head} → {base}")
    check_branch(head, base)
    check_body(body, title)
    check_files(base)
    if RELEASE.match(head):
        check_release_tree()
    print()
    if failures:
        print(f"[FAIL] 共 {len(failures)} 项未通过，{len(warnings)} 项警告")
        return 1
    print(f"[OK] 检查通过（{len(warnings)} 项警告）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
