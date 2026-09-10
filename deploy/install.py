#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy/install.py — 把本仓库（auto_patent 专利流水线）部署/迁移到本机 Hermes。

用法（在仓库根目录执行）:
  python deploy/install.py                      # = --check：环境与部署状态体检（只读）
  python deploy/install.py --skills             # 安装/比对 5 个 skill → <HERMES_HOME>/skills
  python deploy/install.py --bots               # 部署 8 个 bot → <HERMES_HOME>/profiles
  python deploy/install.py --venv               # 创建项目 venv（.venv_patent）并装依赖
  python deploy/install.py --all                # venv + skills + bots
  python deploy/install.py --force              # 覆盖已存在文件（默认跳过）
  python deploy/install.py --hermes-home DIR    # 指定 Hermes 配置目录（默认自动探测）

幂等：已存在的文件默认跳过（--force 才覆盖）；bot 目录已存在时只补缺失的骨架文件。
依赖与手工步骤（填 API Key、重启桌面版）见 deploy/README.md。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPLOY = Path(__file__).resolve().parent
SKILLS_SRC = DEPLOY / "skills"
PROFILES_SRC = DEPLOY / "profiles"
SKELETON = PROFILES_SRC / "_skeleton"
VENV = REPO / ".venv_patent"

BOTS = [
    "patent_searcher", "patent_writer", "patent_reviewer", "patent_examiner",
    "patent_auditor", "patent_docx", "patent_report", "patent_reviser",
]


def default_hermes_home() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "hermes"
    return Path.home() / ".hermes"


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def run(cmd, timeout=1800, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                          timeout=timeout, **kw)


def iter_skills():
    for sk in sorted(SKILLS_SRC.glob("*/*")):
        if (sk / "SKILL.md").is_file():
            yield sk.parent.name, sk.name, sk


def venv_python():
    for rel in ("Scripts/python.exe", "bin/python"):
        p = VENV / rel
        if p.exists():
            return p
    return None


def which(*names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def find_browsers():
    found = set()
    if sys.platform == "win32":
        cands = [
            (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "Chrome"),
            (r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "Chrome"),
            (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "Edge"),
            (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "Edge"),
        ]
        for path, name in cands:
            if Path(path).exists():
                found.add(name)
    else:
        for exe, name in (("google-chrome", "Chrome"), ("chromium", "Chromium"), ("msedge", "Edge")):
            if shutil.which(exe):
                found.add(name)
    return sorted(found)


def find_playwright():
    """在若干候选 python 里找 playwright，返回 (python, 版本或'ok')"""
    cands = [Path(sys.executable)]
    for n in ("python", "python3"):
        p = which(n)
        if p:
            cands.append(Path(p))
    vp = venv_python()
    if vp:
        cands.append(vp)
    seen = set()
    for c in cands:
        if str(c).lower() in seen or not c.exists():
            continue
        seen.add(str(c).lower())
        try:
            r = run([str(c), "-c", "import playwright; print('ok')"], timeout=60)
        except Exception:
            continue
        if r.returncode == 0:
            return c, (r.stdout.strip() or "ok")
    return None, None


def cmd_check(home: Path) -> None:
    print(f"仓库根     : {REPO}")
    print(f"HERMES_HOME: {home}  (存在: {home.is_dir()})")
    print(f"当前 Python: {sys.version.split()[0]} — {sys.executable}")
    vp = venv_python()
    print(f"项目 venv  : {VENV}  (存在: {bool(vp)})")
    if vp:
        r = run([str(vp), "-W", "ignore", "-c", "import docx, pymupdf, matplotlib; print('docx/pymupdf/matplotlib OK')"], timeout=120)
        print("  venv 依赖:", (r.stdout or r.stderr).strip()[:80])
        r = run([str(vp), "-c", "import win32com.client; print('pywin32 OK')"], timeout=120)
        print("  Word COM :", (r.stdout or r.stderr).strip()[:80])

    print("\n== 外部工具 ==")
    for label, exe, args, hint in (
        ("pandoc", "pandoc", ["--version"], "公式 LaTeX→OMML 必需"),
        ("node", "node", ["--version"], "mermaid 出图必需"),
        ("npx", "npx", ["--version"], "mermaid-cli 经 npx 调用"),
        ("git", "git", ["--version"], None),
    ):
        p = which(exe)
        out = ""
        if p:
            try:
                r = run([p] + args, timeout=60)
                out = ((r.stdout or r.stderr).strip().splitlines() or [""])[0][:38]
            except Exception as e:
                out = f"(运行失败 {e})"
        tail = f"  {out}" if p else f"  未找到 — {hint}"
        print(f"  {'v' if p else 'x'} {label:8s}{tail}")
    brs = find_browsers()
    print(f"  {'v' if brs else 'x'} 浏览器(Chrome/Edge)   {'/'.join(brs) if brs else '未找到 — mermaid 出图与 CNIPA 爬虫需要'}")
    py, ver = find_playwright()
    if py:
        print(f"  v playwright  {ver}  ({py})")
    else:
        print("  x playwright  未找到 — tools/crawl 需要：任意 python 执行 pip install playwright")
    if sys.platform == "win32":
        word = which("WINWORD.EXE") or next(
            (p for p in (r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                         r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE")
             if Path(p).exists()), None)
        print(f"  {'v' if word else '·'} Word (可选)         {'已安装' if word else '未找到 — docx_render_pdf / 页数统计降级'}")

    print("\n== Skills (deploy/skills → HERMES_HOME/skills) ==")
    for cat, name, src in iter_skills():
        dst = home / "skills" / cat / name / "SKILL.md"
        if dst.is_file():
            same = sha12(dst) == sha12(src / "SKILL.md")
            print(f"  {'=' if same else '!'} {cat}/{name}: {'已安装一致' if same else '已安装但内容不同（--force 更新）'}")
        else:
            print(f"  x {cat}/{name}: 未安装")

    print("\n== Bots (deploy/profiles → HERMES_HOME/profiles) ==")
    for bot in BOTS:
        dst = home / "profiles" / bot
        if not dst.is_dir():
            print(f"  x {bot}: 未部署")
            continue
        soul = dst / "SOUL.md"
        marks = []
        if soul.is_file():
            same = sha12(soul) == sha12(PROFILES_SRC / bot / "SOUL.md")
            marks.append("SOUL.md " + ("一致" if same else "不同"))
        else:
            marks.append("缺 SOUL.md")
        marks.append("profile.yaml " + ("有" if (dst / "profile.yaml").exists() else "缺"))
        marks.append("config.yaml " + ("有" if (dst / "config.yaml").exists() else "缺"))
        print(f"  · {bot}: " + "; ".join(marks))
    print("\n提示：--skills 安装技能；--bots 生成/补齐 bot 骨架；--all 全量部署；详见 deploy/README.md")


def cmd_skills(home: Path, force: bool) -> None:
    print(f"== 安装 skills → {home / 'skills'}")
    n_new = n_skip = 0
    for cat, name, src in iter_skills():
        dst = home / "skills" / cat / name
        if dst.exists() and not force:
            same = (dst / "SKILL.md").is_file() and sha12(dst / "SKILL.md") == sha12(src / "SKILL.md")
            print(f"  = {cat}/{name}: {'已一致，跳过' if same else '已存在且不同，跳过（--force 覆盖）'}")
            n_skip += 1
            continue
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        print(f"  → {cat}/{name}: 已安装")
        n_new += 1
    print(f"  （安装 {n_new} 个，跳过 {n_skip} 个）")


def cmd_bots(home: Path, force: bool) -> None:
    print(f"== 部署 bots → {home / 'profiles'}")
    if not SKELETON.is_dir():
        print("  x 缺少 deploy/profiles/_skeleton/")
        return
    for bot in BOTS:
        src = PROFILES_SRC / bot
        if not (src / "SOUL.md").is_file():
            print(f"  x {bot}: deploy/profiles/{bot}/SOUL.md 缺失，跳过")
            continue
        dst = home / "profiles" / bot
        dst.mkdir(parents=True, exist_ok=True)
        acts = []
        for f in ("profile.yaml", ".no-bundled-skills", ".env"):
            s = SKELETON / f
            if s.exists() and not (dst / f).exists():
                shutil.copy2(s, dst / f)
                acts.append(f"补 {f}")
        if not (dst / "config.yaml").exists():
            shutil.copy2(SKELETON / "config.template.yaml", dst / "config.yaml")
            acts.append("生成 config.yaml（含占位 api_key，需填写）")
        for d in ("skills", "memories", "home"):
            (dst / d).mkdir(exist_ok=True)
        soul_dst = dst / "SOUL.md"
        if not soul_dst.exists() or force:
            shutil.copy2(src / "SOUL.md", soul_dst)
            acts.append("写 SOUL.md")
        elif sha12(soul_dst) != sha12(src / "SOUL.md"):
            acts.append("SOUL.md 已存在但与本仓库不同（--force 覆盖）")
        print(f"  {'→' if acts else '='} {bot}: {'; '.join(acts) if acts else '已就绪'}")


def cmd_venv(force: bool) -> None:
    req = DEPLOY / "requirements-venv.txt"
    vp = venv_python()
    if vp and not force:
        print(f"== venv 已存在：{VENV}（跳过；--force 重装依赖）")
        return
    if not vp:
        print(f"== 创建 venv：{VENV}")
        try:
            r = run([sys.executable, "-m", "venv", str(VENV)], timeout=600)
        except Exception as e:
            print("  创建失败:", e)
            return
        if r.returncode != 0:
            print("  创建失败:", ((r.stderr or r.stdout) or "").strip()[-300:])
            return
        vp = venv_python()
        if not vp:
            print("  创建后未找到 python 可执行文件")
            return
    print(f"== 安装依赖：{req.name}（pip，可能需要几分钟）")
    try:
        r = run([str(vp), "-m", "pip", "install", "-r", str(req)], timeout=1800)
    except Exception as e:
        print("  pip 失败:", e)
        return
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    tail = out.splitlines()[-1][:120] if out else ""
    print(f"  {'OK' if r.returncode == 0 else 'pip 退出码 ' + str(r.returncode)} — {tail}")


def main():
    ap = argparse.ArgumentParser(description="auto_patent 部署/迁移脚本（默认 = --check 体检）")
    ap.add_argument("--check", action="store_true", help="环境与部署状态体检（默认动作）")
    ap.add_argument("--skills", action="store_true", help="安装 skills")
    ap.add_argument("--bots", action="store_true", help="部署 bot profiles")
    ap.add_argument("--venv", action="store_true", help="创建/更新 .venv_patent")
    ap.add_argument("--all", action="store_true", help="venv + skills + bots")
    ap.add_argument("--force", action="store_true", help="覆盖已存在文件")
    ap.add_argument("--hermes-home", default=None, help="Hermes 配置目录（默认自动探测）")
    args = ap.parse_args()

    home = Path(args.hermes_home).expanduser() if args.hermes_home else default_hermes_home()

    if args.all:
        cmd_venv(args.force)
        print()
        cmd_skills(home, args.force)
        print()
        cmd_bots(home, args.force)
        print()
    else:
        did = False
        if args.venv:
            cmd_venv(args.force)
            print()
            did = True
        if args.skills:
            cmd_skills(home, args.force)
            print()
            did = True
        if args.bots:
            cmd_bots(home, args.force)
            print()
            did = True
        if not did:
            cmd_check(home)
            return

    cmd_check(home)
    print("\n下一步：① 填好各 bot config.yaml 的 api_key（或按 hermes-bot-fleet-config 从主配置同步 provider）；"
          "② 重启 Hermes 桌面版并在 Bots 标签页确认；③ `hermes profile list` 验证。")


if __name__ == "__main__":
    main()
