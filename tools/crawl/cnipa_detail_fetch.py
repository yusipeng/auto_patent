# -*- coding: utf-8 -*-
"""CNIPA 详情页全文抓取（自包含：过 WAF 后同浏览器访问详情）
用法: python tools/crawl/cnipa_detail_fetch.py CN113807252A CN102469366A CN108769790A
"""
import sys, os, time
from pathlib import Path

_CRAWL = Path(__file__).resolve().parent
sys.path.insert(0, str(_CRAWL))
from playwright.sync_api import sync_playwright
from cnipa_epub_crawler import wait_for_epub_home_ready, EPUB_BASE

OUTDIR = r"D:\auto_patent\cases\一种基于年龄画像与作息曲线的儿童视频观看时长自适应守护方法及系统\01_source"

def fetch_detail(page, pub_no):
    url = f"{EPUB_BASE}/patent/{pub_no}"
    try:
        page.goto(url, wait_until="load", timeout=120_000)
    except Exception as e:
        print(f"  goto warn: {e}")
    deadline = time.time() + 90
    body = ""
    while time.time() < deadline:
        page.wait_for_timeout(3000)
        try:
            body = page.evaluate("document.body ? document.body.innerText : ''")
        except Exception:
            body = ""
        if len(body.strip()) > 400:
            return body
    return body

def main():
    nums = sys.argv[1:]
    if not nums:
        print("usage: python cnipa_detail_fetch.py CNxxxxA ...")
        return
    os.environ.setdefault("EPUB_WAF_MAX_WAIT_SEC", "180")
    with sync_playwright() as p:
        # 复用 crawl 的 launch（browser.py 提供，channel=chrome）
        from browser import launch_chromium
        browser, _ = launch_chromium(p, headless=True)
        ctx = browser.new_context(locale="zh-CN")
        page = ctx.new_page()
        print("过 WAF（最多 180s）...", flush=True)
        wait_for_epub_home_ready(page)
        print("WAF 通过", flush=True)
        for num in nums:
            try:
                body = fetch_detail(page, num)
                out = os.path.join(OUTDIR, f"{num}-说明书全文.md")
                with open(out, "w", encoding="utf-8") as f:
                    f.write(f"# {num} — CNIPA 公布公告详情页全文\n\n来源：{EPUB_BASE}/patent/{num}（Playwright 过 WAF，2026-09-04）\n\n")
                    f.write(body)
                print(f"OK {num}: {len(body)} chars", flush=True)
            except Exception as e:
                print(f"ERR {num}: {e}", flush=True)
        browser.close()

if __name__ == "__main__":
    main()
