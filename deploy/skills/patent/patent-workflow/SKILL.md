---
name: patent-workflow
description: Use when 调度或排查专利交底书自动化流水线。7 个 Bot 专人专项协作总纲。
---

# 专利交底书自动化流水线（D:\auto_patent）

把论文预印本转化为符合《专利申请技术交底书》的交底书 + 检索报告。8 个常驻 Bot（Hermes Bot Mode，每个是独立 profile），在主会话 @ 接力协作。

> **迁移/复制到新机器**：仓库 `deploy/` 收录 5 个 skill 源与 8 个 bot profile 骨架，一键部署 `python deploy/install.py --all`（venv + skills + bots）；步骤、依赖与验证清单见 `deploy/README.md`。

## 模板版本（2026-09 新版，重大变更）

- 交底书模板（章节结构）：`templates/技术交底书模板-发明新型.docx`，章节 **零~八 + 3 个无编号节**（商业价值/侵权证据可获得性/标准进展情况/其他技术资料）；旧「六、价值体现」4 维度已取消；新「三」=现有技术方案（不含缺点），「四」=缺点+技术问题，「六」=关键点和欲保护点，「七」=技术优点，「八」=规避思考；无保密页眉（页脚页码）
- **输出格式基准（2026-09-07 用户定稿）**：`templates/技术交底书模板-发明新型-用户定稿.docx`——黑体标题 16/15/15/14pt、宋体/Times 正文小四 1.25 倍行距首行缩进 2 字符、封面仿宋蓝色、表格宋体 10pt、标题 Word 自动编号（一、~八、+ 子节 N.M）；md2docx 已全量按此输出（旧官方模板仅留档）
- 检索报告模板：`templates/检索报告模板 （修订版）.docx`；二→四跳号保持原样

## Bot 名册与职责

| Bot (profile) | 职责 | 输入 | 输出 |
|---|---|---|---|
| patent_searcher | 检索 arXiv/bioRxiv 筛选 + Grill-Me 方向细化 | 关键词 | 技术方案确认清单.md |
| patent_writer | 按模板撰写交底书 md | 确认清单 + 论文全文 | 交底书-vN.md |
| patent_reviewer | 内容质量评审（技术完整性/创新点层次/论文一致性） | 交底书-vN.md | 评审报告 md，PASS/FAIL |
| patent_auditor | 格式规范审计（章节/Mermaid/公式/编号） | 交底书-vN.md | 格式审计报告 md，PASS/FAIL |
| patent_docx | md → docx（用户定稿格式：样式+自动编号；Mermaid 转图、LaTeX→OMML） | 审计通过的 md | 发明名称-交底书VN.docx |
| patent_report | 撰写专利检索报告 docx | 定稿交底书 | 发明名称-检索报告VN.docx |
| patent_reviser | 按 Word 批注 + 对比专利权利要求书修订 | 批注 docx + 对比文件 | 交底书vN+1 + 变更点清单 |
| patent_examiner | 模拟专利审查员预审（新颖性/创造性/步骤清晰，挑毛病视角） | 双 PASS 后的交底书 md | 审查意见书 md，PASS/FAIL |

## 案件目录结构

```
D:\auto_patent\cases\<发明名称>\
  01_source\    # 论文 PDF + 提取文本、对比专利文件
  02_draft\     # 技术方案确认清单.md、交底书-vN.md
  03_review\    # 评审报告、格式审计报告、变更点清单
  04_docx\      # 最终 发明名称-交底书vN.docx、-检索报告vN.docx
```

## 流程与人工确认点（4 个里程碑）

1. 关键词 → @patent_searcher → 推荐 5~10 篇 → **用户选 1~3 篇**
2. @patent_searcher 方向细化（Grill-Me，每轮≤3问）→ **用户确认技术方案确认清单**
3. @patent_writer 撰写 → @patent_reviewer 评审 → 不通过打回 writer（≤2 轮）→ @patent_auditor 格式审计 → 不通过打回（≤2 轮）→ **@patent_examiner 审查员预审（新颖性/创造性/步骤清晰，质量最后一道关）→ 不通过打回 reviser** → @patent_docx 转 docx → **用户评审意见**
4. @patent_report 检索报告（对比文件回流，writer 更新第三部分）→ @patent_reviser 处理批注/对比专利 → **定稿**

打回规则：评审/审计 FAIL 时自动回 writer 修改，最多 2 轮，仍 FAIL 交人工。每轮版本号 +1。

**结案评分卡（2026-09-04 用户要求，替代交付包，自动留档）**：全流程跑完（定稿/放行）后**不做 zip 打包**，直接给每案一张评分卡并**自动落盘 `cases/评分卡-<日期>.md`**：①分维度评分（新颖性/创造性/清楚性可实施性/撰写格式，各 0-100 与一句话依据）；②初审通过概率（形式审查，通常高）与实审通过概率（创造性风险主导，给出区间）；③难以回避的问题与缺点清单（对比文件风险/数据缺口/参数待实测/范围过窄等）。评分依据=examiner 历轮意见书结论，由主会话汇总产出，不虚构概率。多案同结时出一份汇总表存 `cases/`。

**版本回环评审规则（2026-09-03 起强制）**：任何一次修改——无论来源（评审打回修订、格式修复、工具升级后重转写、用户评审意见、reviser 批注修订）——只要产出新版本（md vN+1 或 docx V+1）并经用户确认，**必须重新执行完整复核**：patent_reviewer 内容评审（技术完整性/论文一致性/与上一版差异）→ patent_auditor 格式审计（章节/公式/图/编号/残留），PASS 后才能进入下一环节（转 docx、检索报告、定稿）。方案核心变化时还要重跑查新（patent_searcher）。复核发现问题的改法同打回规则。

## 模板与工具链

- 模板：`templates/技术交底书模板-发明新型-用户定稿.docx`（★输出格式基准）、`templates/技术交底书模板-发明新型.docx`（官方原版留档）、`templates/检索报告模板 （修订版）.docx`（检索报告，本次格式更新未含）
- 转写：`tools/md2docx.py`（按用户定稿样式输出：Heading1~4/Body Text 样式套用、Word 自动编号一、~八、与子节 N.M、Mermaid 图、LaTeX→OMML 公式、表格宋体 10pt；实测 V2 往返 27→27 页一致）
- 更换格式基准：`tools/make_template.py <定稿docx> <新模板docx>` 提取空白格式（保留样式/编号/封面/页脚，清空正文），再改 md2docx 顶部 DEFAULT_TEMPLATE
- 版本管理：`tools/versioned_output.py <04_docx目录> "<发明名称>" <交底书|检索报告>`（初始 V1；每次修改先复制旧版为 V+1 副本再写新内容，旧版永不覆盖；--peek 查当前版本）
- 公式：```latex 代码块 → pandoc → Word 原生 OMML 可编辑公式（依赖系统 pandoc ≥3.x，机器已装 3.8；需在 PATH）；OMML 失败才降级 matplotlib mathtext 位图。公式编号锚点正文与 OMML 分离（**（式N）** 独立段）。**体例规范**（吸收自 references/交底书模板参考-脱敏版.md 3.4.1）：3.4.1 先建符号表（符号/含义/下标量纲）再列公式；维度用下标 `_{\mathrm{cpu}}` 而非上标 `^{cpu}`；行内分隔符全文统一 `$...$`（勿用普通括号包 LaTeX）；块级公式尽量单行；防零除用 `\max(\varepsilon, ...)`
- 标题层级：md `#`~`####` → Word outlineLvl 0~3（导航窗格可见层级），模板章节(零~八/无编号节)=outlineLvl 0
- Mermaid 渲染：npx @mermaid-js/mermaid-cli + 本机 Edge（puppeteer-edge.json，免下载 Chromium）
- 检索（CN 专利查新，推荐）：`tools/crawl/cnipa_epub_search.py`（Playwright 过 CNIPA WAF，实测本机可用；输出含摘要/IPC/申请人/链接；用法 `python tools/crawl/cnipa_epub_search.py --type invention 词1 词2`；过 WAF 靠轮询等 `#searchStr` 出现，设 `EPUB_WAF_MAX_WAIT_SEC=60`；详解见 `references/查新规范.md`）
- 检索（备用）：`tools/patent_search.py`（Google Patents XHR，走 Clash，503 限流时用 CNIPA 爬虫替代）
- 参考规范（2026-09 吸收自开源 patent-disclosure-skill，保持本流程风格）：`references/交底书模板参考-脱敏版.md`（3.1 领域词三小段/3.2 mermaid框图/3.4.1 符号表+公式体例/脱敏规范/标题贯穿）、`references/disclosure_self_check.md`（§8.1 逻辑闭环/§8.2 公式一致性/§8.3 格式引用 可勾选清单，供 patent_reviewer 评审模板与 patent_writer 自检）、`references/oa_prompts/`（审查答复 prompts 备查，未接流水线）
- 导入：`tools/docx2md.py <已有交底书.docx> <out.md>`（已有 docx→md 源；兼容 Word 自动编号——标题/列表编号自动合成回文字；OMML 公式借 pandoc 还原为 $...$ / ```latex；实测 V2 导入→重新生成 27 页与原件渲染一致）
- 修改已有交底书路径：docx2md 导入 → patent_reviser 在 md 上改（或走 writer 重写受影响章节）→ md2docx 回写新版本号
- 辅助：`tools/extract_pdf.py`（pymupdf）、`tools/extract_comments.py`（Word 批注）、`tools/new_case.py`（建案）、`tools/docx_render_pdf.py`（docx→PDF，本机 Word 渲染核对排版）
- venv：`D:\auto_patent\.venv_patent`（python-docx 1.2.0 / pymupdf / matplotlib）

## 关键约定

- 产出命名：`<发明名称>-交底书VN.docx` / `<发明名称>-检索报告VN.docx`（N 从 1 起，修改即 V+1 副本）；封面字段固定：〔申报单位〕/发明/〔联系人〕
- 语言中文，专有名词保留英文；产物不再标注「保密信息」
- 信息不足标 `[待补充]` 问用户，绝不编造；专利信息必须真实可查
- 全文摘要/PDF：arXiv API export.arxiv.org/api/query、bioRxiv API api.biorxiv.org；PDF 文本用 extract_pdf.py
- 各 Bot 的 SOUL.md 在 `~/.hermes/profiles/<bot>/`，改角色职责即改那里

### 创造性论证核心方法论（2026-09-04 用户确认）

**专利保护表达，不保护原理。** 公开论文/文献公开的是"思想/原理/方法层面"，不构成对"表达层面"的创造性障碍；真正要做的是**综合公开论文（及对比文件）的观点与方法，构建出权利要求层面的具体新颖表达**——特征组合、步骤链、数据流、约束关系、模块耦合方式、量化判定机制等具体化即"表达"，是新颖性与创造性的载体。因此：
- 检索到公开论文/对比文件后，**不因"思想被公开"而收缩方案**；反而把它们当原料，综合提炼出未被任何单篇公开的、结构化的技术方案表达
- 创造性论证的重心在"表达差异"：本案的特征组合/顺序约束/交互机制与每篇现有技术的具体差异（不是与抽象思想比，是与具体技术特征比）
- 不允许 NPL 引用（论文可能被审查员反向用作现有技术），但允许并鼓励**把论文观点方法吸收为本案技术手段**（写成"本方案通过…实现"，无"据论文"表述）
- 数学自洽性是硬要求：公式必须标准定义、符号自洽、与正文闭环（examiner 曾发现式3 期望熵负号错误、式2 非标准熵定义等 reviewer 未抓到的数学硬伤）

## 启动一次新案件

1. `tools/new_case.py "<发明名称>"` 建目录
2. 主会话 @patent_searcher 给关键词，按里程碑推进
