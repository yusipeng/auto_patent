# 专利交底书自动化流水线

把论文预印本 → 公司专利交底书 docx + 检索报告 docx，全程 7 个 Hermes Bot 专人专项协作。

## 快速开始

1. 在 Hermes 桌面 **Bots** 标签页确认 7 个 Bot 在线：patent_searcher / patent_writer / patent_reviewer / patent_auditor / patent_docx / patent_report / patent_reviser
2. 主会话发：`@patent_searcher 检索关键词：<关键词>`（默认近 6 个月）
3. 按 4 个里程碑人工把关推进（选论文 → 确认方案 → 评审意见 → 定稿）
4. 评审任务，主会话发：`@patent_searcher  修订 cases/<发明名称>/：批注在 03_review/xxx.docx，对比专利在 01_source/xxx.pdf：`

## 目录（以下路径均相对仓库根目录）

```
auto_patent/                         # 仓库根（本 README 所在目录）
  templates/                         # 模板基准（只读）
    技术交底书模板-发明新型-用户定稿.docx  # ★输出格式基准（2026-09-07 用户定稿）
    技术交底书模板-发明新型.docx          # 官方原版留档（不再用于输出）
    检索报告模板 （修订版）.docx   # 检索报告（本次未调整）
  cases/<发明名称>/                   # 每个案件：01_source/ 02_draft/ 03_review/ 04_docx/
  tools/                             # 工具脚本（见下）
  .venv_patent/                      # Python venv：python-docx 1.2.0 / pymupdf / matplotlib
```

> 所有命令均在**仓库根目录**执行（示例中的相对路径均以此为基准）。

**输出格式基准**（由用户定稿文件提取，md2docx 全部输出按此排版）：
- 页面 A4，上下边距 2.54cm / 左右 3.17cm，页脚页码
- 大标题黑体 22pt 加粗居中；一级标题黑体 16pt、二/三级 15pt、四级 14pt（段前 16/14/12/10 磅）
- 正文宋体/Times New Roman 小四（12pt），行距 1.25，段前后各 5 磅，首行缩进 2 字符，两端对齐
- 封面值仿宋_GB2312 12pt（保留原蓝色）；术语/参数等表格宋体 10pt，表头加粗、通栏居中
- 标题用 **Word 自动编号**：一级「一、~八、」自动生成（"零、"为文字），子节「3.1 / 5.1 / 6.1」自动生成——增删章节时编号自动重排
- 公式为 Word 原生公式（OMML，可双击编辑）；列表沿用 md 文字编号（"1." 等）

## 版本管理规范

- 产出文件名：`<发明名称>-交底书VN.docx` / `<发明名称>-检索报告VN.docx`，**初始 V1**
- **每次修改**：先由 `tools/versioned_output.py` 把最新旧版复制为 V+1 副本（留档），新内容写入 V+1 文件，**旧版本永不覆盖**
- md 中间源同步 `交底书-vN.md` 递增

```bash
# 查当前最新版本
PYTHONPATH="" .venv_patent/Scripts/python.exe tools/versioned_output.py cases/<案>/04_docx "<发明名称>" 交底书 --peek
# 修改前创建 V+1 副本（输出 TARGET= 应写入的路径）
PYTHONPATH="" .venv_patent/Scripts/python.exe tools/versioned_output.py cases/<案>/04_docx "<发明名称>" 交底书
```

## 工具脚本（tools/）

| 脚本                | 用途                                               | 状态                |
| ------------------- | -------------------------------------------------- | ------------------- |
| md2docx.py          | 交底书 md → docx（用户定稿样式：黑体标题/宋体正文/Word 自动编号；Mermaid、LaTeX→OMML 公式、表格） | ✅ 按定稿格式实测 |
| docx2md.py          | 已有交底书 docx → md 源（导入；兼容自动编号合成、OMML 公式还原） | ✅ 往返实测通过     |
| make_template.py    | 从定稿交底书提取空白"格式模板"（更换格式基准时用）  | ✅ 已用于本次换版   |
| docx_render_pdf.py  | docx → PDF（本机 Word 渲染，排版核对用）           | ✅                  |
| versioned_output.py | 产物版本管理（V1 起步，修改即副本+1）              | ✅ 实测通过         |
| patent_search.py    | Google Patents 检索（走 Clash 127.0.0.1:7897）     | ✅ 实测返回真实专利 |
| extract_pdf.py      | PDF → 纯文本（pymupdf）                           | ✅                  |
| extract_comments.py | 提取 docx 内 Word 批注                             | ✅                  |
| new_case.py         | 创建案件目录结构                                   | ✅                  |
| puppeteer-edge.json | mermaid-cli 复用本机 Edge 的配置                       | ✅                  |
| cdp_drive.py        | CDP 直连本机 Chrome（9223），绕过 browser 工具启动问题 | ✅                  |
| crawl/cnipa_epub_search.py | CNIPA 公布公告系统检索（Playwright 过 WAF；含摘要/IPC；公开号不带 A 后缀） | ✅ 实测 |
| verify_docx.py      | 交底书产出校验：12 章节匹配 / OMML 公式数 / 图片数 / $ 残留 / 失败标注 | ✅ 按定稿格式实测 |
| verify_cover_and_media.py | 封面发明名称回填、媒体内嵌检查、页数（Word COM） | ✅                  |
| page_count.py       | Word COM 统计 docx 页数                               | ✅                  |
| batch_patent_search.py / batch_patent_search2.py | 批量查新检索（QUERIES 列表可改；结果 JSON 供 analyze_patents.py 聚合） | ✅ |
| dl_drugfuture.py    | drugfuture 对比文件 PDF 下载（人工过验证码；`--outdir` 指定案件 01_source） | ✅ |
| fetch_case_refs.py  | 批量抓取对比文件著录+摘要，归档到案件 01_source        | ✅                  |

## 模板结构速查（2026-09 新版交底书）

零 术语定义和解释（三列表格）→ 一 发明名称 → 二 技术领域（14 选）→ 三 现有技术的技术方案 → 四 现有技术的缺点及本申请提案要解决的技术问题 → 五 技术方案详细阐述（≥50% 篇幅）→ 六 关键点和欲保护点 → 七 技术优点 → 八 发散思维以及规避方案思考 → 商业价值 → 侵权证据可获得性/标准进展情况 → 其他技术资料

## 流水线（7 Bot + 4 人工确认点）

```
关键词 → searcher(检索+筛选) → [用户选1~3篇] → searcher(Grill-Me方向细化)
      → [用户确认清单] → writer(撰写) → reviewer(内容评审)
      → 不过则打回 writer(≤2轮) → auditor(格式审计) → 不过则打回(≤2轮)
      → docx(转写docx, V1) → [用户评审意见] → report(检索报告, 对比文件回流writer更新三)
      → reviser(批注+对比专利修订, V+1) → [定稿]
```

## 关键事实

- 模板章节以 `templates/` 最新文件为准（2026-09：零~八 + 3 无编号节）
- **输出格式基准 = `templates/技术交底书模板-发明新型-用户定稿.docx`**（2026-09-07 定稿：黑体标题/宋体正文小四/1.25 倍行距/首行缩进 2 字符/Word 自动编号）；md2docx 已全量按此输出
- 封面固定：申报单位=〔申报单位〕 / 申报类型=发明 / 发明人·技术联系人=〔联系人〕（封面值保留原仿宋蓝色）
- 检索报告模板「二」之后直接「四」（无三），保持跳号原样；本次格式更新不含检索报告
- 新交底书模板无保密页眉（检索报告模板有），各随其模板
- 所有命令需 `PYTHONPATH=""` 前缀（避免 Hermes venv 污染）
- 详细调度手册：`patent-workflow` skill（主会话加载即得）
