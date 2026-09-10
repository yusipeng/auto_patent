#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy/privacy_check.py — 仓库脱敏体检（公司名 / 姓名 / 联系方式 / 内部代号 等）

本仓库为**公开仓库**：提交前用它自查，避免公司信息与个人信息入库。

内置通用规则（始终启用）：
  - 邮箱地址（白名单 example.com / users.noreply.github.com）
  - 中国大陆手机号（1[3-9] 开头 11 位）
  - Windows 用户目录路径（C:\\Users\\<某用户名>；`<user>`、`%USERNAME%`、`<你>` 视为占位符放行）

额外词表（本地维护、不入库）：`deploy/privacy_extra.txt` —— 每行一个词，# 为注释。
  例：公司名称、姓名、内部邮箱域名、项目代号……

用法（仓库根目录）:
  python deploy/privacy_check.py             # 扫描 git 跟踪的文件（推荐）
  python deploy/privacy_check.py --all       # 扫描工作区全部文件（跳过 .git/.venv/cases 等）
  python deploy/privacy_check.py --staged    # 只扫暂存区（可挂到 pre-commit）
退出码: 0=干净; 1=有命中
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRA = Path(__file__).resolve().parent / "privacy_extra.txt"

SKIP_DIRS = {".git", ".venv_patent", ".tmp_render", "cases", "__pycache__", "node_modules"}
OFFICE_EXT = {".docx", ".xlsx", ".pptx", ".docm", ".xlsm"}

GENERIC_PATTERNS = [
    ("邮箱", re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.com|users\.noreply\.github\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("用户目录路径", re.compile(r"[A-Za-z]:[\\/]Users[\\/](?!<user>|%USERNAME%|<你>)[^\\/\s\"'`)]+")),
]


def load_extra() -> list:
    if not EXTRA.exists():
        return []
    words = []
    for line in EXTRA.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line)
    return words


def iter_files(mode: str):
    if mode == "all":
        for p in REPO.rglob("*"):
            if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
                yield p, None
        return
    args = ["git", "ls-files", "-z"] if mode == "tracked" else \
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"]
    r = subprocess.run(args, cwd=str(REPO), capture_output=True)
    for rel in r.stdout.decode("utf-8", errors="replace").split("\0"):
        rel = rel.strip()
        if rel:
            p = REPO / rel
            if p.is_file():
                yield p, rel


def scan_text(text: str, tokens: list) -> list:
    hits = []
    for label, rx in GENERIC_PATTERNS:
        for m in rx.finditer(text):
            hits.append((label, m.group(0)))
    for tok in tokens:
        if tok in text:
            hits.append(("词表", tok))
    return hits


def scan_file(p: Path, tokens: list) -> list:
    if p.suffix.lower() in OFFICE_EXT:
        hits = []
        try:
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.endswith(".xml"):
                        try:
                            for label, v in scan_text(z.read(n).decode("utf-8", "ignore"), tokens):
                                hits.append((f"{label}@{n}", v))
                        except Exception:
                            pass
        except Exception:
            pass
        return hits
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    if "\x00" in text[:1000]:
        return []
    return scan_text(text, tokens)


def main() -> int:
    ap = argparse.ArgumentParser(description="仓库脱敏体检（公开仓库提交前自查）")
    ap.add_argument("--all", action="store_true", help="扫描工作区全部文件")
    ap.add_argument("--staged", action="store_true", help="只扫暂存区")
    args = ap.parse_args()
    mode = "all" if args.all else ("staged" if args.staged else "tracked")

    tokens = load_extra()
    if not tokens:
        print(f"[提示] 未找到额外词表 {EXTRA}")
        print("       可创建它补充公司名/姓名/代号等（每行一个词，不进仓库）。\n")

    n_files = n_hits = 0
    for p, rel in iter_files(mode):
        rel = rel or p.relative_to(REPO).as_posix()
        n_files += 1
        hits = scan_file(p, tokens)
        if hits:
            n_hits += 1
            print(f"[命中] {rel}")
            for label, v in hits[:8]:
                print(f"    {label}: {v[:90]}")
            if len(hits) > 8:
                print(f"    … 其余 {len(hits) - 8} 处")
    print(f"\n扫描 {n_files} 个文件（模式: {mode}），命中 {n_hits} 个。")
    if n_hits:
        print("处理建议：改为占位符、移出仓库并加入 .gitignore；如已提交，还需检查/清理 git 历史。")
        return 1
    print("通过：未发现公司名/姓名/联系方式等敏感内容。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
