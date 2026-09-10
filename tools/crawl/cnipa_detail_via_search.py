# -*- coding: utf-8 -*-
"""复用 crawler 的 WAF 会话：搜索专利号 -> 同 session 访问详情页抓全文
用法: python tools/crawl/cnipa_detail_via_search.py CN113807252A CN102469366A CN108769790A
"""
import sys, os, time, json
from pathlib import Path

_CRAWL = Path(__file__).resolve().parent
sys.path.insert(0, str(_CRAWL))
from playwright.sync_api import sync_playwright
from cnipa_epub_crawler import wait_for_epub_home_ready, EPUB_BASE
from browser import launch_chromium

OUTDIR = r"D:\auto_patent\cases\一种基于年龄画像与作息曲线的儿童视频观看时长自适应守护方法及系统\01_source"
WAF = float(os.environ.get("EPUB_WAF_MAX_WAIT_SEC", "120"))

def fetch_detail(page, pub_no):
    url = f"{EPUB_BASE}/patent/{pub_no}"
    try:
        page.goto(url, wait_until="load", timeout=120_000)
    except Exception:
        pass
    deadline = time.time() + 60
    body = ""
    while time.time() < deadline:
        page.wait_for_timeout(2500)
        try:
            body = page.evaluate("document.body ? document.body.innerText : ''")
        except Exception:
            body = ""
        if len(body.strip()) > 300:
            return body
    return body

def main():
    nums = sys.argv[1:]
    if not nums:
        print("usage: python cnipa_detail_via_search.py CNxxxxA ...")
        return
    with sync_playwright() as p:
        browser, _ = launch_chromium(p, headless=True)
        ctx = browser.new_context(locale="zh-CN")
        page = ctx.new_page()
        print("过 WAF...", flush=True)
        wait_for_epub_home_ready(page, max_wait_sec=WAF)
        print("WAF OK", flush=True)
        for num in nums:
            try:
                body = fetch_detail(page, num)
                out = os.path.join(OUTDIR, f"{num}-说明书全文.md")
                with open(out, "w", encoding="utf-8") as f:
                    f.write(f"# {num} — CNIPA 公布公告详情页全文\n\n来源：{EPUB_BASE}/patent/{num}（Playwright 过 WAF）\n\n")
                    f.write(body)
                print(f"OK {num}: {len(body)} chars", flush=True)
            except Exception as e:
                print(f"ERR {num}: {e}", flush=True)
        browser.close()

if __name__ == "__main__":
    main()
