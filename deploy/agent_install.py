#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy/agent_install.py — 把本仓库的 5 个 skill 安装到各类 AI Agent 的技能目录。

覆盖：Claude Code / OpenAI Codex / 腾讯 WorkBuddy / 腾讯 CodeBuddy Code / 通用 AGENTS.md 规范。

用法（在仓库根目录执行，默认 = --list 探测）:
  python deploy/agent_install.py --list          # 探测本机已装 Agent 与技能目录现状
  python deploy/agent_install.py --all           # 安装到全部已探测到的 Agent（用户级）
  python deploy/agent_install.py --claude-code   # → ~/.claude/skills/<skill>/
  python deploy/agent_install.py --codex         # → ~/.agents/skills/<skill>/
  python deploy/agent_install.py --workbuddy     # → ~/.workbuddy/skills/<skill>/
  python deploy/agent_install.py --codebuddy     # → ~/.codebuddy/skills/<skill>/
  python deploy/agent_install.py --project       # → <仓库>/.claude/skills/ 与 <仓库>/.agents/skills/
  python deploy/agent_install.py --remove        # 从所选目标移除本仓库的 skill
  python deploy/agent_install.py --force         # 覆盖已存在文件
  python deploy/agent_install.py --home DIR      # 覆盖用户主目录（测试用）

说明：安装 = 把 deploy/skills/<category>/<name>/ 整个目录复制为目标目录下的 <name>/。
均幂等：已存在默认跳过。各 Agent 路径依据其官方文档（2026-09），详见 deploy/AGENT-INSTALL.md。
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPLOY = Path(__file__).resolve().parent
SKILLS_SRC = DEPLOY / "skills"


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def skills():
    for sk in sorted(SKILLS_SRC.glob("*/*")):
        if (sk / "SKILL.md").is_file():
            yield sk.name, sk, sk.parent.name


def agent_targets(home: Path):
    """agent key -> (显示名, 用户级技能目录, 探测标志路径)"""
    return {
        "claude-code": ("Claude Code", home / ".claude" / "skills", home / ".claude"),
        "codex": ("OpenAI Codex", home / ".agents" / "skills", home / ".codex"),
        "workbuddy": ("WorkBuddy(腾讯)", home / ".workbuddy" / "skills", home / ".workbuddy"),
        "codebuddy": ("CodeBuddy Code(腾讯)", home / ".codebuddy" / "skills", home / ".codebuddy"),
    }


def detected(key: str, flag: Path, skills_dir: Path) -> bool:
    if flag.exists() or skills_dir.exists():
        return True
    exe = {"claude-code": "claude", "codex": "codex", "codebuddy": "codebuddy", "workbuddy": None}.get(key)
    return bool(exe and shutil.which(exe))


def count_installed(skills_dir: Path) -> int:
    return sum(1 for name, _, _ in skills() if (skills_dir / name / "SKILL.md").is_file())


def cmd_list(home: Path) -> None:
    total = len(list(skills()))
    print("== Agent 探测（用户级技能目录） ==")
    for key, (label, sdir, flag) in agent_targets(home).items():
        ok = detected(key, flag, sdir)
        n = count_installed(sdir) if sdir.exists() else 0
        print(f"  {'v' if ok else 'x'} {label:22s} {sdir}   [已装 {n}/{total}]")
    print("\n== 项目级 / 通用规范 ==")
    print("  · 仓库根 AGENTS.md 已提供：Codex / Cursor / OpenCode / Amp 等支持该规范的 Agent 打开本仓库即读取")
    print(f"  · 仓库内技能目录（可选，随仓库分发）：--project → {REPO / '.claude' / 'skills'} 与 {REPO / '.agents' / 'skills'}")
    print("\n提示：--all 安装到全部探测到的 Agent；各路径依据与手动安装方式见 deploy/AGENT-INSTALL.md")


def install_into(sdir: Path, force: bool, remove: bool) -> tuple:
    n_new = n_skip = n_del = n_keep = 0
    for name, src, _cat in skills():
        dst = sdir / name
        if remove:
            if not dst.exists():
                continue
            if (dst / "SKILL.md").is_file() and not force and sha12(dst / "SKILL.md") != sha12(src / "SKILL.md"):
                print(f"    ! {name}: 内容与仓库不同，保留（--force 强制删除）")
                n_keep += 1
            else:
                shutil.rmtree(dst)
                print(f"    - {name}: 已移除")
                n_del += 1
            continue
        if dst.exists() and not force:
            same = (dst / "SKILL.md").is_file() and sha12(dst / "SKILL.md") == sha12(src / "SKILL.md")
            print(f"    = {name}: {'已一致，跳过' if same else '已存在且不同，跳过（--force 覆盖）'}")
            n_skip += 1
            continue
        sdir.mkdir(parents=True, exist_ok=True)
        existed = dst.exists()
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        print(f"    → {name}: {'覆盖安装' if existed else '已安装'}")
        n_new += 1
    return n_new, n_skip, n_del, n_keep


def main() -> None:
    ap = argparse.ArgumentParser(description="把本仓库 skill 安装到各类 AI Agent 技能目录（默认 = --list）")
    ap.add_argument("--list", action="store_true", help="探测本机 Agent 与技能目录现状")
    ap.add_argument("--all", action="store_true", help="安装到全部已探测到的 Agent")
    ap.add_argument("--claude-code", dest="claude_code", action="store_true", help="→ ~/.claude/skills/")
    ap.add_argument("--codex", action="store_true", help="→ ~/.agents/skills/")
    ap.add_argument("--workbuddy", action="store_true", help="→ ~/.workbuddy/skills/")
    ap.add_argument("--codebuddy", action="store_true", help="→ ~/.codebuddy/skills/")
    ap.add_argument("--project", action="store_true", help="→ 仓库内 .claude/skills 与 .agents/skills")
    ap.add_argument("--remove", action="store_true", help="移除模式（仅对所选目标）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在文件 / 强制移除")
    ap.add_argument("--home", default=None, help="覆盖用户主目录（默认自动）")
    args = ap.parse_args()

    home = Path(args.home).expanduser() if args.home else Path.home()
    tgt = agent_targets(home)

    picked = []
    if args.all:
        picked = [k for k, (_l, sdir, flag) in tgt.items() if detected(k, flag, sdir)]
    else:
        for key, chosen in (("claude-code", args.claude_code), ("codex", args.codex),
                            ("workbuddy", args.workbuddy), ("codebuddy", args.codebuddy)):
            if chosen:
                picked.append(key)

    did = False
    for key in picked:
        label, sdir, _flag = tgt[key]
        print(f"== {label} → {sdir}")
        n_new, n_skip, n_del, n_keep = install_into(sdir, args.force, args.remove)
        if args.remove:
            print(f"    （移除 {n_del} 个，保留 {n_keep} 个）")
        else:
            print(f"    （安装 {n_new} 个，跳过 {n_skip} 个）")
        did = True
        print()

    if args.project:
        print("== 项目级（仓库内，可随仓库提交分发） ==")
        for sub in (".claude", ".agents"):
            d = REPO / sub / "skills"
            print(f"  → {d}")
            n_new, n_skip, n_del, n_keep = install_into(d, args.force, args.remove)
            print(f"    （安装 {n_new} 个，跳过 {n_skip} 个）" if not args.remove else f"    （移除 {n_del} 个）")
        did = True
        print()

    if not did:
        cmd_list(home)
        return

    cmd_list(home)
    print("\n生效说明：重启对应 Agent / 开新会话后生效。"
          "Claude Code：`/skills` 查看、`/patent-workflow` 调用；"
          "Codex：`/skills` 或 `$patent-workflow` 提及；"
          "WorkBuddy：在「技能」面板查看已安装列表。")


if __name__ == "__main__":
    main()
