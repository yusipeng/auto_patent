# -*- coding: utf-8 -*-
"""dl_drugfuture.py — drugfuture 对比文件 PDF 下载（人工过验证码 → QuickPdf1 → PatentReady.aspx 捕获下载）
关键点：QuickPdf1() 会打开新标签页（PatentReady.aspx），要操作那个页面。
PDF 逐页加载约 15-25s，加载完生成下载链接（可能直接触发下载，或出现 <a href> 链接）。
用法: PYTHONPATH="" .venv_patent/Scripts/python.exe tools/dl_drugfuture.py CN120892603 --outdir "cases/<案>/01_source"
"""
import sys, os, time, argparse
from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patent_no", help="公开号，如 CN120892603")
    ap.add_argument("--outdir", default=os.getcwd(), help="PDF 输出目录，默认当前目录（建议传案件的 01_source）")
    ap.add_argument("--wait", type=int, default=240, help="人工输验证码等待秒数")
    ap.add_argument("--ready-wait", type=int, default=60, help="等待 PatentReady 加载秒数")
    args = ap.parse_args()
    no = args.patent_no
    out_pdf = os.path.join(args.outdir, f"{no}-说明书.pdf")
    out_pdf2 = os.path.join(args.outdir, f"{no}-授权说明书.pdf")

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=False, args=["--no-sandbox"])
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()
        downloads = []
        page.on("download", lambda d: downloads.append(d))

        # 步骤1：走表单 + 验证码（正确专利 session）
        page.goto("https://www.drugfuture.com/cnpat/cn_patent.asp", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.fill("input[name=op_num]", no)
        page.click("input[name=btn2]")
        page.wait_for_timeout(3000)
        print(f"[*] 请在浏览器输入验证码并提交（等待 {args.wait}s）...", flush=True)
        deadline = time.time() + args.wait
        entered = False
        while time.time() < deadline:
            page.wait_for_timeout(1000)
            if "search.aspx" in page.url:
                entered = True
                break
        if not entered:
            print("[!] 未进入结果页", flush=True)
            browser.close()
            return
        print("[*] 已进入结果页，确认专利...", flush=True)
        body = page.evaluate("document.body.innerText")
        # 验证是否命中目标公开号（页面存在空格/大小写差异，宽松匹配）
        if no.replace(" ", "").upper() in body.replace(" ", "").upper():
            print(f"[+] 已确认目标专利 {no}", flush=True)
        else:
            print(f"[!] 警告：结果页未见 {no}，请人工确认：", flush=True)
            print("   ", body[:200].replace("\n", " "), flush=True)

        # 步骤2：点 PDF下载（极速版）——注意会打开新标签
        print("[*] 调用 QuickPdf1() 下载申请说明书 PDF...", flush=True)
        new_pages = []
        ctx.on("page", lambda pg: new_pages.append(pg))
        page.evaluate("QuickPdf1()")

        # 步骤3：盯新标签页，等 PDF 逐页加载完成
        ready_page = None
        for _ in range(10):
            page.wait_for_timeout(1000)
            for pg in new_pages:
                if "PatentReady" in pg.url and pg != page:
                    ready_page = pg
                    break
            if ready_page:
                break
        if ready_page is None:
            # 可能是同页导航
            for pg in ctx.pages:
                if "PatentReady" in pg.url:
                    ready_page = pg
        if ready_page is None:
            print("[!] 未找到 PatentReady 页面", flush=True)
            print("    pages:", [pg.url for pg in ctx.pages], flush=True)
        else:
            print(f"[*] PatentReady 页面: {ready_page.url}", flush=True)
            ready_page.on("download", lambda d: downloads.append(d))
            ready_page.wait_for_timeout(3000)
            # 等下载或下载链接出现
            print(f"[*] 等待 PDF 逐页加载（最多 {args.ready_wait}s）...", flush=True)
            ddl = time.time() + args.ready_wait
            got_link = None
            while time.time() < ddl:
                ready_page.wait_for_timeout(1000)
                if downloads:
                    print("[+] download event 触发!", flush=True)
                    break
                # 检查页面里是否出现下载链接
                try:
                    links = ready_page.eval_on_selector_all("a", "els => els.map(e=>(e.innerText||'').trim()+'|'+(e.href||'')).filter(x=>x.split('|')[1] && (/pdf|down|zip|rar/i.test(x.split('|')[1]) || /下载|pdf/i.test(x.split('|')[0])))")
                    if links:
                        got_link = links
                        print("[+] 发现下载链接:", flush=True)
                        for l in links[:5]:
                            print("    ", l[:200], flush=True)
                        break
                except Exception:
                    pass
            if downloads:
                dl = downloads[0]
                dl.save_as(out_pdf)
                print(f"[OK] 申请说明书 PDF 已保存: {out_pdf}", flush=True)
            elif got_link:
                # 关键：点击"下载专利"链接（javascript:QuickPdf()），触发真正的 PDF 加载
                print("[*] 点击[下载专利]链接，等待 PDF 加载...", flush=True)
                try:
                    ready_page.evaluate("QuickPdf()")
                except Exception as e:
                    print(f"[!] QuickPdf() 调用失败: {e}", flush=True)
                # 等待下载事件（逐页加载约 15-40s）
                qdl = time.time() + 90
                while time.time() < qdl:
                    ready_page.wait_for_timeout(1000)
                    if downloads:
                        break
                if downloads:
                    dl = downloads[0]
                    dl.save_as(out_pdf)
                    print(f"[OK] 申请说明书 PDF 已保存(点击下载专利后): {out_pdf}", flush=True)
                else:
                    # 再找一次真实链接
                    links2 = ready_page.eval_on_selector_all("a", "els => els.map(e=>(e.innerText||'').trim()+'|'+(e.href||'')).filter(x=>x.split('|')[1] && !x.split('|')[1].startsWith('javascript:'))")
                    real = [l for l in links2 if 'pdf' in l.split('|')[1].lower() or 'pdf' in l.split('|')[0].lower()]
                    if real:
                        href = real[0].split("|")[1]
                        resp = ready_page.request.get(href)
                        with open(out_pdf, "wb") as f:
                            f.write(resp.body())
                        print(f"[OK] 申请说明书 PDF 已保存(真实链接): {out_pdf} ({len(resp.body())} bytes)", flush=True)
                    else:
                        print("[!] 点击下载专利后仍未捕获。浏览器保持 20s 查看...", flush=True)
                        ready_page.wait_for_timeout(20000)

        # 步骤4：同样下载授权说明书（QuickPdf2）
        print("[*] 调用 QuickPdf2() 下载授权说明书 PDF...", flush=True)
        try:
            page.evaluate("QuickPdf2()")
        except Exception as e:
            print("quickpdf2 err:", e)
        time.sleep(20)
        if downloads:
            dl = downloads[-1]
            dl.save_as(out_pdf2)
            print(f"[OK] 授权说明书 PDF 已保存: {out_pdf2}", flush=True)
        else:
            print("[*] 授权说明书未捕获下载（不阻塞）", flush=True)

        page.wait_for_timeout(5000)
        browser.close()

if __name__ == "__main__":
    main()
