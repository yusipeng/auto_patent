---
name: cn-patent-pdf-download
description: "Use when 下载中国专利 PDF/文本（对比文件）。含来源路由与 drugfuture 流程。"
---

# 中国专利 PDF/文本下载

## 何时用
专利流水线需要对比文件 PDF / 权利要求书文本时。目的通常是创造性对比，**权利要求书文本往往已够用**，PDF 是补充材料。

## 来源路由（本机实测 2026-09，Windows + Clash 7897）

| 来源 | 状态 | 说明 |
|---|---|---|
| **drugfuture 中国专利下载**（www2.drugfuture.com/cnpat/cn_patent.asp） | ✅ 可达 | 公开号/申请号下载官方 PDF；有汉字验证码 |
| Google Patents（patents.google.com） | ⚠️ 网络级反爬 | 本网段返回 "Sorry... automated queries"；换 UA / headless 开关 / stealth 脚本 / 有头无头均无效（是 IP/网段标记，不是特征检测）；XHR /xhr/query 偶发 503 限流（临时，可稍后重试） |
| CNIPA epub.cnipa.gov.cn | ✅ 可过（Playwright 爬虫） | 2026-09-04 实测：curl / requests / 短等待 headless 直连会被瑞数类 WAF 拦（JS 挑战 z5gPWiiwO6ht/*.js + POST 400），但 **Playwright 打开首页后轮询等 `#searchStr` 出现（EPUB_WAF_MAX_WAIT_SEC 默认 180，实测 45-60s 即过）即可过 WAF**。现成工具 `D:\auto_patent\tools\crawl\cnipa_epub_search.py`（按公开号/关键词检索，输出含 abstract/IPC/申请人/link） |
| pss-system.cponline.cnipa.gov.cn | ⚠️ 412 WAF | |
| Espacenet | ⚠️ curl 403；headless 渲染为空 | |
| ipdps.cnipa.gov.cn（知识产权数据资源公共服务系统） | ❌ 对拿专利全文无用 | SPA，需实名注册登录+验证码（/public/login/code）；API 基路径 /public/（myResource/download 等）。**「我的下载」里只有专利提交规范/模板等规范文件，没有专利全文数据**；真正数据走 FTP 分配链接。用户误以为能下载专利内容时会白费一轮 |

**结论**：CN 专利 PDF 优先 drugfuture（需人工验证码）；CN 专利**完整文本**用 Google Patents 的 web_extract（已实测拿到 CN120892603B 完整说明书 30K+ 字符，含权利要求+技术领域/背景技术/发明内容/附图说明/具体实施方式）；CN 专利**著录+摘要批量抓取**（按公开号或关键词）用 `tools/crawl/cnipa_epub_search.py`（Playwright 过 CNIPA WAF，输出 JSON 含 abstract/IPC/申请人/link，实测按公开号精确命中）。**CNIPA 详情页全文抓取脚本（goto /patent/xxx，cnipa_detail_fetch.py）2026-09-04 实测过 WAF 超时不可靠，别依赖；对比文件细节核验走 Google Patents /en 更稳**。drugfuture 下载的 PDF 是**扫描版无文本层**（pymupdf get_text 为 0），要文本就 web_extract 或 OCR，别指望扫描 PDF 提字。

## drugfuture 下载流程（2026-09 实测全通）
1. 打开 `https://www.drugfuture.com/cnpat/cn_patent.asp`
2. 填 `op_num`=公开号（含 CN 前缀、**去末尾类别码字母**：CN120892603 ← CN120892603B）；或 `cnpatentno`=申请号（不加前缀 CN）
3. 点 `btn2`（公开号查询）→ 跳 `verify.aspx?op_num=...` → 汉字验证码（img `#imgVerify`，输入框 `ValidCode`）
4. **验证码人工输入**（汉字+干扰线，ddddocr default/beta 识别率极低、vision_analyze 也不准 → 直接弹有头浏览器让用户输一次，别浪费轮次在 OCR）。验证码错回 search.aspx 显示"验证码输入错误"，页面 URL 不变
5. 验证码通过 → search.aspx 结果页。**关键坑**：直接 GET search.aspx?op_num= 拿的是默认 session 的**别的专利**（曾返回辉瑞抗体专利），必须走表单+验证码才有正确 session
6. 点"发明专利申请说明书PDF下载(极速版)"（`QuickPdf1()`，javascript 链接）→ **新标签页打开** `PatentReady.aspx`（域名轮换 www5/6/8/9/10:88）
7. PatentReady 页出现"下载专利"链接（`javascript:QuickPdf()`）→ **必须再点击它**才开始逐页加载 PDF（10-40s）→ 然后才触发 download 事件
8. 下载事件要注册在 **PatentReady 新标签页**上（`ready_page.on("download", ...)`），不是主页面
9. 申请说明书=`QuickPdf1`，授权说明书=`QuickPdf2`（两者可能返回同一扫描文件，md5 相同）

现成脚本：`D:\auto_patent\tools\dl_drugfuture.py`（Playwright 有头 + 人工验证码 + 自动点下载专利 + 等逐页加载 + 保存，全流程已跑通）。浏览器弹窗后脚本有 `--wait` 秒等用户输验证码，检测到 search.aspx 后自动 QuickPdf1() → 点 QuickPdf() → 等 download。

批量按公开号抓 CN 著录+摘要（补齐批注对比文件）：见 `references/batch-fetch-cn-refs.md`（工具 cnipa_epub_search.py + _fetch_case_refs.py，实测按号精确命中）。

**对比文件细节核验流程**（reviewer 报"描述超出归档摘要"时）：见 `references/prior-art-fulltext-verification.md`（用 `/en` 全文核验具体数值/选项是否真实存在 → 每件一份核实材料归档 01_source → 区分"描述有据但缺出处"与"描述失真"）。

**无对比文件案件的创造性增强**（01_source 空、余工未给号时）：不引用 NPL，将 arXiv 论文创新点提炼整合进方案——见 `references/arxiv-innovation-integration.md`。

## Playwright + 系统 Chrome（Windows，免下载浏览器）
```bash
python -m pip install playwright ddddocr
```
```python
from playwright.sync_api import sync_playwright
browser = p.chromium.launch(
    executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    headless=True, args=["--no-sandbox"])
```
- 无需 `playwright install` 下载浏览器，`executable_path` 指向系统 Chrome 即可
- ddddocr 对数字/字母验证码有效，汉字验证码无效
- 下载触发用 `page.on("download", ...)` 回调提前注册，比 expect_download 可靠（点击后事件可能已错过）；**新标签页的下载要注册在新标签页对象上**（`ready_page.on("download", ...)`）
- 监听新标签页：`ctx.on("page", lambda pg: ...)`，QuickPdf1 会开新标签

## Google Patents 文本提取（web_extract 实测有效）
浏览器/curl 直连 patents.google.com 被网络级反爬（"Sorry... automated queries"，IP 网段标记，换 UA/headless/stealth 均无效）；但 `web_extract(urls=["https://patents.google.com/patent/CN120892603B/zh"])` 的后端（Firecrawl）能拿到完整页面文本——含全部 Description 章节。产出存到 `~/.hermes cache/web/*.md`，可 read_file 读取/归档到 01_source。适合拿 CN 专利完整说明书文本（30K+ 字符）。

**关键坑（2026-09-04 实测）**：CN 专利**优先用 `/en` 英文页**，不用 `/zh` 中文页——`/zh` 常返回乱码（GBK 错位，如 CN113807252A 标题变 `ä¸ç§...`）或偶发 http_error（CN102469366A/CN108769790A 一次失败重试即通）。`/en` 页含完整 Abstract/Description/Claims（claims 是英文机翻，但**权利要求的结构、数值、选项**都在，足够核验对比文件细节）。**核验对比文件具体细节（如某等级时长、某保护模式播什么）用 `/en` 页抓 claims 段即可，不必下扫描 PDF。**

## 用户浏览器登录态（"我已经登录了"场景）
用户说 Chrome 开着调试模式时，先分清两个 Chrome：
- **agent-browser**（`C:\Users\<user>\.agent-browser\browsers\chrome-*`，HeadlessChrome，`--remote-debugging-port=0` 随机端口）：**无用户登录态**，独立临时 profile（`Temp\agent-browser-chrome-*`），空白页。browser_exec 的 local 模式驱动的是它（或复制用户 Edge/Chrome profile，被占用会失败）
- **用户普通 Chrome**（`C:\Program Files\Google\Chrome\Application\chrome.exe`，双击启动）：有登录态，但**默认不开调试端口**，无法直接 CDP 附加；需要用户以 `--remote-debugging-port=9222` 重启才有
- 探测法：扫所有 chrome 监听端口逐一 curl `/json/version`；再对比 CommandLine 里 `user-data-dir` 是 `Temp\agent-browser-*` 还是 `\Google\Chrome\User Data`。登录态在后者，调试端口通常只有前者
- 要带登录态自动化：读普通 Chrome profile 的 cookie/localStorage 注入 Playwright，或让用户重启带调试端口

## 相关
- 专利流水线总纲：patent-workflow skill
- 本机网络：Clash 127.0.0.1:7897；Google 系走代理，国内站直连
