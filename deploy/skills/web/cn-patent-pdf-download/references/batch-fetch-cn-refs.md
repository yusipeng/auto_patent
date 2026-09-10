# 按公开号批量抓取 CN 对比文件著录+摘要（2026-09-04 实测）

适用：余工批注列出多件对比文件（CN…A/B），需补齐 01_source 缺失项时。

## 工具
`D:\auto_patent\tools\crawl\cnipa_epub_search.py`（Playwright 过 CNIPA WAF）

## 单件查询
```bash
EPUB_WAF_MAX_WAIT_SEC=60 timeout 120 python tools/crawl/cnipa_epub_search.py --type all CN104581389A
```
- stdout 唯一一行 `EPUB_HITS_JSON:` + JSON 数组；每项含 pub_number/title/applicant/application_number/filing_date/publication_date/inventors/ipc_codes/link/abstract
- **按公开号精确匹配**：循环结果里用 `num in h['pub_number'].replace(' ','')` 过滤，避免误收相似号

## 批量 + 归档脚本
`D:\auto_patent\tools\_fetch_case_refs.py`（可复用）：输入公开号列表，逐件抓取并追加到 `01_source/批注对比文件-著录与摘要.md`。

## 坑
- **每件一个独立进程**，一次一浏览器，约 30-90s；WAF 限流时单件可能超时（timeout 90），**单独重跑该件**即可（EPUB_WAF_MAX_WAIT_SEC 调到 60）
- **不要用 execute_code 的 subprocess 跑**（venv/cwd 环境异常导致无输出）；用 terminal 直接跑，脚本内 `sys.executable` + `cwd=BASE` 可
- `--type all` 比限定类型更稳（公开号检索不受类型过滤影响）

## 外国专利（US 等）
CNIPA 无外国专利；用 Google Patents web_extract：`web_extract(urls=["https://patents.google.com/patent/US7739707B2/en"])`，从 Info + Description 提炼著录+核心公开内容，归档独立 md。
