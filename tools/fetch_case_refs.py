# -*- coding: utf-8 -*-
"""fetch_case_refs.py — 批量抓取对比文件著录+摘要（CNIPA 公布公告系统），归档为 markdown

用法:
  PYTHONPATH="" .venv_patent/Scripts/python.exe tools/fetch_case_refs.py \
      "cases/<发明名称>/01_source/批注对比文件-著录与摘要.md" CN104581389A CN113807252A ...

说明: 逐个调用 tools/crawl/cnipa_epub_search.py（Playwright 过 WAF，EPUB_WAF_MAX_WAIT_SEC=45），
      按公开号精确匹配后写入目标 md（申请人/申请号/公开日/发明人/IPC/链接/摘要）。
"""
import subprocess, json, os, sys, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根


def fetch(num):
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "tools", "crawl", "cnipa_epub_search.py"), "--type", "all", num],
        capture_output=True, text=True, timeout=90, cwd=BASE,
        env={**os.environ, "EPUB_WAF_MAX_WAIT_SEC": "45"},
    )
    data = None
    for ln in r.stdout.splitlines():
        ln = ln.strip()
        if ln.startswith("EPUB_HITS_JSON:"):
            try:
                data = json.loads(ln[len("EPUB_HITS_JSON:"):])
            except json.JSONDecodeError:
                pass
    if data is None:
        print(f"EMPTY {num}: {(r.stdout or r.stderr).strip()[:100]}", flush=True)
        return None
    hit = next((h for h in data if num in (h.get("pub_number") or "").replace(" ", "")), None)
    if hit:
        print(f"OK {num}: {hit.get('title')}", flush=True)
    else:
        print(f"MISS {num}: 无精确匹配", flush=True)
    return hit


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    out_md = os.path.abspath(sys.argv[1])
    nums = [n.strip() for n in sys.argv[2:] if n.strip()]
    os.makedirs(os.path.dirname(out_md), exist_ok=True)

    rows = [h for h in (fetch(n) for n in nums) if h]

    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# 对比文件著录与摘要（{datetime.date.today().isoformat()} CNIPA 公布公告系统抓取）\n\n")
        f.write("来源：国家知识产权局专利公布公告系统（epub.cnipa.gov.cn，Playwright 过 WAF）\n\n")
        for h in rows:
            f.write(f"## {h.get('pub_number')} — {h.get('title')}\n\n")
            f.write(f"- 申请人：{h.get('applicant')}\n")
            f.write(f"- 申请号：{h.get('application_number')}；申请日：{h.get('filing_date')}；公开日：{h.get('publication_date')}\n")
            f.write(f"- 发明人：{'、'.join(h.get('inventors') or [])}\n")
            f.write(f"- IPC：{'、'.join(h.get('ipc_codes') or [])}\n")
            f.write(f"- 链接：{h.get('link')}\n\n")
            f.write(f"**摘要**：{h.get('abstract')}\n\n---\n\n")
    print("\n归档:", out_md, "共", len(rows), "件", flush=True)


if __name__ == "__main__":
    main()
